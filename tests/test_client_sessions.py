"""The client-session reception record: its tracking, its check and its
append-only history. Every record here is constructed; the committed file
holds no real session until one is shown."""

from __future__ import annotations

import datetime as datetime_module
import hashlib
import json
import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import client_sessions
from wave_local_ai_v2.client_sessions import (
    DEFAULT_SESSIONS_PATH,
    ShallowHistory,
    append_only_violations,
    changelog_verdict_mismatches,
    check_file,
    check_records,
    git_commit_exists,
    main,
)

REPO = Path(__file__).resolve().parents[1]
CHANGELOG = "## [Unreleased]\n\n## [0.2.0] - 2026-09-22\n\n## [0.1.0] - 2026-08-22\n"
KNOWN_COMMIT = hashlib.sha1(b"a commit the stub knows").hexdigest()
UNKNOWN_COMMIT = hashlib.sha1(b"a commit nobody made").hexdigest()
ABSENT = object()


@pytest.fixture(autouse=True)
def _isolate_git(monkeypatch: pytest.MonkeyPatch) -> None:
    # A git hook (pre-push runs this suite) exports GIT_DIR and GIT_INDEX_FILE;
    # inherited, they point the tmp-repo git calls at the real repository.
    for name in [n for n in os.environ if n.startswith("GIT_")]:
        monkeypatch.delenv(name)


def _challenge(**overrides: Any) -> dict[str, Any]:
    challenge: dict[str, Any] = {
        "role": "client ML engineer",
        "criterion": "the hardware behind each row is disclosed",
        "claims": ["fiche_disclosure"],
        "evidence_offered": "asked which GPU produced the runtime rows",
        "resolving_evidence": "opened the fiche the row cites by fiche_hash",
    }
    for key, value in overrides.items():
        if value is ABSENT:
            challenge.pop(key, None)
        else:
            challenge[key] = value
    return challenge


def _record(**overrides: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "record_format": "1",
        "session_id": "session-0a1b2c3d4e5f",
        "client_id": "client-9f8e7d6c5b4a",
        "session_date": "2026-10-01",
        "logged_date": "2026-10-01",
        "release": "0.2.0",
        "audience": "external",
        "shown": "the classification overview and the runtime table",
        "outcome": "challenged",
        "backfilled": False,
        "challenges": [_challenge()],
    }
    for key, value in overrides.items():
        if value is ABSENT:
            record.pop(key, None)
        else:
            record[key] = value
    return record


def _text(*records: dict[str, Any] | str) -> str:
    return "".join(
        (item if isinstance(item, str) else json.dumps(item)) + "\n" for item in records
    )


def _check(*records: dict[str, Any] | str) -> client_sessions.CheckReport:
    return check_records(_text(*records), CHANGELOG, lambda sha: sha == KNOWN_COMMIT)


def _located(report: client_sessions.CheckReport) -> set[tuple[int, str]]:
    return {(item.line, item.field) for item in report.refusals}


# --- the file and its tracking -------------------------------------------


def test_the_record_file_is_tracked_by_no_ignore_rule() -> None:
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", DEFAULT_SESSIONS_PATH],
        cwd=REPO,
        capture_output=True,
        check=False,
    )

    assert (REPO / DEFAULT_SESSIONS_PATH).is_file()
    assert result.returncode == 1, result.stdout


def test_the_committed_record_file_passes_the_check() -> None:
    report = check_file(REPO / DEFAULT_SESSIONS_PATH, REPO / "CHANGELOG.md")

    assert report.refusals == []


def test_a_planted_malformed_committed_file_fails_the_check(tmp_path: Path) -> None:
    sessions = tmp_path / "client-sessions.jsonl"
    sessions.write_text(_text(_record(outcome="won the deal")), encoding="utf-8")

    report = check_file(sessions, REPO / "CHANGELOG.md")

    assert _located(report) == {(1, "outcome")}


# --- a well-formed file reads back ----------------------------------------


def test_the_empty_file_passes() -> None:
    report = _check()

    assert report.passed and report.records == [] and report.incomplete == []


def test_a_well_formed_file_reads_back_with_its_markings() -> None:
    corrected = _record(session_id="session-111111111111", outcome="accepted")
    corrected["challenges"] = []
    report = _check(
        corrected,
        _record(
            session_id="session-222222222222",
            release="unreleased",
            release_commit=KNOWN_COMMIT,
            backfilled=True,
            corrects="session-111111111111",
        ),
    )

    assert report.passed and report.incomplete == []
    first, second = report.records
    assert (first.outcome, first.challenges, first.release) == ("accepted", 0, "0.2.0")
    assert second.backfilled and second.release_commit == KNOWN_COMMIT
    assert report.corrected_by == {"session-111111111111": "session-222222222222"}
    rendered = client_sessions.render_report(report, "f.jsonl")
    assert "corrected by session-222222222222" in rendered
    assert f"unreleased at commit {KNOWN_COMMIT}" in rendered
    assert "backfilled" in rendered and "corrects session-111111111111" in rendered
    assert rendered.endswith("PASS: 2 record(s), 0 incomplete field(s)\n")


def test_an_explicitly_empty_challenge_list_is_complete() -> None:
    report = _check(_record(outcome="dismissed", challenges=[]))

    assert report.passed and report.incomplete == []
    assert report.records[0].challenges == 0


# --- incomplete, not refused ----------------------------------------------


@pytest.mark.parametrize("content", ["role", "criterion", "evidence_offered"])
def test_a_left_out_content_field_is_incomplete_not_refused(content: str) -> None:
    report = _check(_record(challenges=[_challenge(**{content: ABSENT})]))

    assert report.passed
    assert [(i.field, i.reason) for i in report.incomplete] == [
        (f"challenges[0].{content}", "absent")
    ]
    assert len(report.records) == 1


def test_a_content_field_stated_empty_is_incomplete_and_says_so() -> None:
    report = _check(_record(challenges=[_challenge(role="  ")]))

    assert report.passed
    assert [i.reason for i in report.incomplete] == ["stated empty"]


# --- refusals, each naming its line and field -----------------------------

GOOD = _record(session_id="session-aaaaaaaaaaaa")


@pytest.mark.parametrize(
    ("planted", "field"),
    [
        ("{not json", "<line>"),
        ("[1, 2]", "<line>"),
        ("", "<line>"),
        (_record(record_format=ABSENT), "record_format"),
        (_record(session_id=ABSENT), "session_id"),
        (_record(client_id=ABSENT), "client_id"),
        (_record(session_date=ABSENT), "session_date"),
        (_record(logged_date=ABSENT), "logged_date"),
        (_record(release=ABSENT), "release"),
        (_record(audience=ABSENT), "audience"),
        (_record(shown=ABSENT), "shown"),
        (_record(outcome=ABSENT), "outcome"),
        (_record(backfilled=ABSENT), "backfilled"),
        (_record(challenges=ABSENT), "challenges"),
        (_record(challenges=[_challenge(claims=ABSENT)]), "challenges[0].claims"),
        (
            _record(challenges=[_challenge(resolving_evidence=ABSENT)]),
            "challenges[0].resolving_evidence",
        ),
        (_record(record_format="2"), "record_format"),
        (_record(audience="partner"), "audience"),
        (_record(outcome="won"), "outcome"),
        (_record(challenges=[_challenge(claims=["speed"])]), "challenges[0].claims"),
        (_record(challenges=[_challenge(claims=[])]), "challenges[0].claims"),
        (
            _record(challenges=[_challenge(claims=["other", "other"])]),
            "challenges[0].claims",
        ),
        (_record(session_id="session-ACME00000000"), "session_id"),
        (_record(client_id="client-acme"), "client_id"),
        (_record(corrects="acme"), "corrects"),
        (_record(session_date="01/10/2026"), "session_date"),
        (_record(logged_date="2026-02-30"), "logged_date"),
        (_record(logged_date="2026-09-30"), "logged_date"),
        (_record(session_date="2026-09-01", logged_date="2026-09-01"), "session_date"),
        (_record(release="0.3.0"), "release"),
        (_record(release="unreleased"), "release_commit"),
        (_record(release="unreleased", release_commit="abc"), "release_commit"),
        (
            _record(release="unreleased", release_commit=UNKNOWN_COMMIT),
            "release_commit",
        ),
        (_record(release_commit=KNOWN_COMMIT), "release_commit"),
        (_record(challenges=[]), "challenges"),
        (_record(outcome="accepted"), "challenges"),
        (_record(outcome="dismissed"), "challenges"),
        (_record(challenges={"role": "x"}), "challenges"),
        (_record(challenges=["x"]), "challenges[0]"),
        (_record(client_name="Acme"), "client_name"),
        (_record(challenges=[_challenge(document="x")]), "challenges[0].document"),
        (_record(shown=" "), "shown"),
        (_record(shown=3), "shown"),
        (_record(backfilled="no"), "backfilled"),
        (_record(challenges=[_challenge(role=3)]), "challenges[0].role"),
        (
            _record(challenges=[_challenge(resolving_evidence=3)]),
            "challenges[0].resolving_evidence",
        ),
        (_record(challenges=[_challenge(follow_up=1)]), "challenges[0].follow_up"),
    ],
)
def test_a_planted_defect_is_refused_naming_line_and_field(
    planted: dict[str, Any] | str, field: str
) -> None:
    report = _check(GOOD, planted)

    assert (2, field) in _located(report)
    assert not any(item.line == 1 for item in report.refusals)
    assert not report.passed


def test_two_records_sharing_a_session_id_are_refused() -> None:
    report = _check(GOOD, GOOD)

    assert _located(report) == {(2, "session_id")}
    assert "also on line 1" in report.refusals[0].reason


def test_a_correction_naming_no_earlier_record_is_refused() -> None:
    later = _record(session_id="session-bbbbbbbbbbbb")
    report = _check(
        _record(corrects="session-bbbbbbbbbbbb"),
        later,
        _record(session_id="session-cccccccccccc", corrects="session-cccccccccccc"),
    )

    assert _located(report) == {(1, "corrects"), (3, "corrects")}


def test_a_second_correction_of_the_same_record_is_refused() -> None:
    report = _check(
        GOOD,
        _record(session_id="session-bbbbbbbbbbbb", corrects="session-aaaaaaaaaaaa"),
        _record(session_id="session-cccccccccccc", corrects="session-aaaaaaaaaaaa"),
    )

    assert _located(report) == {(3, "corrects")}
    assert "already corrected by session-bbbbbbbbbbbb" in report.refusals[0].reason


def test_a_chain_of_corrections_is_accepted() -> None:
    report = _check(
        GOOD,
        _record(session_id="session-bbbbbbbbbbbb", corrects="session-aaaaaaaaaaaa"),
        _record(session_id="session-cccccccccccc", corrects="session-bbbbbbbbbbbb"),
    )

    assert report.passed
    assert report.corrected_by == {
        "session-aaaaaaaaaaaa": "session-bbbbbbbbbbbb",
        "session-bbbbbbbbbbbb": "session-cccccccccccc",
    }


def test_an_unreleased_commit_resolves_against_the_real_repository() -> None:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO,
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    exists = git_commit_exists(REPO)

    assert exists(head)
    assert not exists(UNKNOWN_COMMIT)
    assert not git_commit_exists(REPO / "no-such-dir")(head)


# --- the command ----------------------------------------------------------


def _files(tmp_path: Path, text: str) -> list[str]:
    sessions = tmp_path / "client-sessions.jsonl"
    sessions.write_text(text, encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    return ["--sessions", str(sessions), "--changelog", str(changelog)]


def test_the_command_passes_the_empty_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_files(tmp_path, "")) == 0
    assert "PASS: 0 record(s)" in capsys.readouterr().out


def test_the_command_reports_incomplete_and_still_passes(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    text = _text(_record(challenges=[_challenge(role=ABSENT)]))

    assert main(_files(tmp_path, text)) == 0
    out = capsys.readouterr().out
    assert "line 1: challenges[0].role: absent" in out


def test_the_command_fails_on_a_refusal_naming_line_and_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_files(tmp_path, _text(GOOD, "{"))) == 1
    out = capsys.readouterr().out
    assert "line 2: <line>: does not parse" in out
    assert out.endswith("FAIL: 1 refusal(s)\n")


def test_the_command_exits_2_when_nothing_can_be_read(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    missing = str(tmp_path / "absent.jsonl")

    assert main(["--sessions", missing, "--changelog", str(REPO / "CHANGELOG.md")]) == 2
    assert "nothing checked" in capsys.readouterr().err


# --- the secrets scan -----------------------------------------------------


def _secrets_found(path: Path) -> list[str]:
    from detect_secrets.core.secrets_collection import SecretsCollection
    from detect_secrets.settings import transient_settings

    baseline = json.loads((REPO / ".secrets.baseline").read_text(encoding="utf-8"))
    config = {key: baseline[key] for key in ("plugins_used", "filters_used")}
    with transient_settings(config):
        collection = SecretsCollection()
        collection.scan_file(str(path))
    return [secret.type for _, secret in collection]


def test_the_secrets_scan_finds_nothing_in_well_formed_records(tmp_path: Path) -> None:
    dated = _record(session_id="session-7c41e09b2fd3", client_id="client-e5a90c37b18d")
    unreleased = _record(
        session_id="session-b02f6e8d4a19",
        client_id="client-3d7f1a9c0e52",
        release="unreleased",
        release_commit=KNOWN_COMMIT,
    )
    for record in (dated, unreleased):
        assert list(record)[:2] == ["record_format", "session_id"]
    sessions = tmp_path / "client-sessions.jsonl"
    sessions.write_text(_text(dated, unreleased), encoding="utf-8")
    control = tmp_path / "control.jsonl"
    control.write_text(json.dumps({"hash": KNOWN_COMMIT}) + "\n", encoding="utf-8")

    assert _secrets_found(sessions) == []
    assert _secrets_found(control) == ["Hex High Entropy String"]


# --- the append-only history ----------------------------------------------

RECORD = "aidd_docs/results/client-sessions.jsonl"


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True)


def _commit(repo: Path, lines: list[str], message: str) -> None:
    path = repo / RECORD
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(f"{line}\n" for line in lines), encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", message)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-b", "main")
    _git(root, "config", "user.email", "test@example.com")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "core.autocrlf", "false")
    _commit(root, [], "empty record")
    return root


def test_the_repository_history_only_ever_appends() -> None:
    try:
        violations = append_only_violations(REPO, RECORD, ci=bool(os.environ.get("CI")))
    except ShallowHistory as exc:
        pytest.skip(f"{exc}; CI runs this on the full history")
    assert violations == []


def test_a_history_that_only_appends_passes(repo: Path) -> None:
    _commit(repo, ["a"], "one")
    _commit(repo, ["a", "b"], "two")

    assert append_only_violations(repo, RECORD, ci=False) == []


def test_a_version_editing_an_earlier_line_fails(repo: Path) -> None:
    _commit(repo, ["a", "b"], "one")
    _commit(repo, ["a", "B", "c"], "edit")

    violations = append_only_violations(repo, RECORD, ci=False)

    assert len(violations) == 1
    assert "line 2" in violations[0] and "append-only" in violations[0]


def test_a_version_removing_a_line_fails(repo: Path) -> None:
    _commit(repo, ["a", "b"], "one")
    _commit(repo, ["a"], "remove")
    (repo / RECORD).unlink()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "delete")

    assert len(append_only_violations(repo, RECORD, ci=False)) == 2


def test_a_merge_of_two_appending_branches_passes_along_the_first_parent(
    repo: Path,
) -> None:
    _commit(repo, ["a"], "base")
    _git(repo, "checkout", "-b", "other")
    _commit(repo, ["a", "from-other"], "other appends")
    _git(repo, "checkout", "main")
    _commit(repo, ["a", "from-main"], "main appends")
    subprocess.run(
        ["git", "merge", "--no-ff", "other"], cwd=repo, capture_output=True, check=False
    )
    _commit(repo, ["a", "from-main", "from-other"], "merge other")

    assert append_only_violations(repo, RECORD, ci=False) == []


def test_a_history_git_cannot_read_fails_rather_than_passing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Stop git from finding an enclosing repository above the temp directory.
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path.parent))
    violations = append_only_violations(tmp_path, RECORD, ci=False)

    assert len(violations) == 1
    assert violations[0].startswith("the history could not be read")


def test_a_shallow_clone_fails_under_ci_and_skips_outside(
    repo: Path, tmp_path: Path
) -> None:
    _commit(repo, ["a"], "one")
    _commit(repo, ["a", "b"], "two")
    clone = tmp_path / "shallow"
    _git(tmp_path, "clone", "--depth", "1", repo.as_uri(), str(clone))

    violations = append_only_violations(clone, RECORD, ci=True)

    assert len(violations) == 1 and "fetch-depth: 0" in violations[0]
    with pytest.raises(ShallowHistory):
        append_only_violations(clone, RECORD, ci=False)


# --- the procedure ----------------------------------------------------------

PROCEDURE = REPO / "docs/client-session-record.md"


def test_the_procedure_is_linked_from_the_results_readme() -> None:
    readme = (REPO / "aidd_docs/results/README.md").read_text(encoding="utf-8")

    assert "../../docs/client-session-record.md" in readme


def test_the_procedures_worked_example_passes_the_check_in_key_order() -> None:
    procedure = PROCEDURE.read_text(encoding="utf-8")
    blocks = [part.split("```", 1)[0] for part in procedure.split("```jsonl\n")[1:]]
    text = "".join(blocks)
    report = check_records(
        text,
        (REPO / "CHANGELOG.md").read_text(encoding="utf-8"),
        git_commit_exists(REPO),
    )

    assert report.passed and report.incomplete == [], report.refusals
    assert len(report.records) == 2
    order = list(client_sessions.RECORD_KEYS)
    for line in text.splitlines():
        keys = list(json.loads(line))
        assert keys == sorted(keys, key=order.index)
    for key in order:
        assert f"| `{key}` |" in procedure, key
    for key in client_sessions.CHALLENGE_KEYS:
        assert f"| `{key}` |" in procedure, key


# --- sustained challenges and their follow-up items -------------------------

SESSION = "session-0a1b2c3d4e5f"
CLIENT = "client-9f8e7d6c5b4a"
DEFECT = "aidd_docs/backlog/defects/the-runtime-table-names-no-gpu.md"
SPIKE = "aidd_docs/backlog/spikes/is-the-judge-agreement-reproducible.md"


def _item(kind: str, *ids: str, status: str = "open") -> str:
    return (
        f"---\ntype: {kind}\nstatus: {status}\n---\n\n# A follow-up item\n\n"
        f"Opened by {' and '.join(ids)}.\n"
    )


ITEMS = {
    DEFECT: _item("defect", SESSION, CLIENT),
    SPIKE: _item("spike", SESSION, CLIENT),
    "aidd_docs/backlog/stories/a-story.md": _item("story", SESSION, CLIENT),
    "aidd_docs/backlog/defects/typed-as-a-spike.md": _item("spike", SESSION, CLIENT),
    "aidd_docs/backlog/spikes/typed-as-a-defect.md": _item("defect", SESSION, CLIENT),
    "aidd_docs/backlog/defects/no-session.md": _item("defect", CLIENT),
    "aidd_docs/backlog/defects/no-client.md": _item("defect", SESSION),
    "aidd_docs/backlog/defects/no-frontmatter.md": f"# {SESSION} {CLIENT}\n",
    "aidd_docs/backlog/defects/unterminated.md": (
        f"---\nstatus: open\n\n# Body\ntype: defect\n{SESSION} {CLIENT}\n"
    ),
    "aidd_docs/backlog/defects/../defects/x.md": _item("defect", SESSION, CLIENT),
}


def _sustained(**overrides: Any) -> dict[str, Any]:
    return _challenge(**{"resolving_evidence": "", "follow_up": DEFECT, **overrides})


def _check_items(
    *records: dict[str, Any], items: dict[str, str] = ITEMS
) -> client_sessions.CheckReport:
    return check_records(
        _text(*records), CHANGELOG, lambda sha: sha == KNOWN_COMMIT, items.get
    )


@pytest.mark.parametrize("evidence", [None, "", "  \t"])
def test_no_named_resolving_evidence_reads_as_sustained(evidence: str | None) -> None:
    challenge = _sustained(resolving_evidence=evidence)
    report = _check_items(_record(challenges=[challenge]))

    assert client_sessions.is_sustained(challenge)
    assert report.passed, report.refusals
    assert report.records[0].sustained == 1
    assert "1 challenge(s), 1 sustained" in client_sessions.render_report(report, "f")


def test_named_resolving_evidence_reads_as_resolved() -> None:
    report = _check_items(_record())

    assert not client_sessions.is_sustained(_challenge())
    assert report.passed and report.records[0].sustained == 0


@pytest.mark.parametrize(
    "follow_up",
    [
        ABSENT,
        "",
        "  ",
        None,
        "aidd_docs/backlog/stories/a-story.md",
        "aidd_docs/backlog/defects/",
        "aidd_docs/backlog/defects/never-filed.md",
        "aidd_docs/backlog/defects/typed-as-a-spike.md",
        "aidd_docs/backlog/spikes/typed-as-a-defect.md",
        "aidd_docs/backlog/defects/no-session.md",
        "aidd_docs/backlog/defects/no-client.md",
        "aidd_docs/backlog/defects/no-frontmatter.md",
        "aidd_docs/backlog/defects/unterminated.md",
        "aidd_docs/backlog/defects/../defects/x.md",
        f"/{DEFECT}",
        f"C:/repo/{DEFECT}",
        DEFECT.replace("/", "\\"),
    ],
)
def test_a_sustained_challenge_without_a_valid_follow_up_is_refused(
    follow_up: object,
) -> None:
    report = _check_items(_record(challenges=[_sustained(follow_up=follow_up)]))

    assert not report.passed and report.records == []
    assert _located(report) == {(1, "challenges[0].follow_up")}
    assert all(
        f"session {SESSION}, challenge 0" in item.reason for item in report.refusals
    )


@pytest.mark.parametrize("path", [DEFECT, SPIKE])
def test_a_sustained_challenge_pointing_at_a_matching_item_passes(path: str) -> None:
    report = _check_items(_record(challenges=[_sustained(follow_up=path)]))

    assert report.passed, report.refusals


def test_an_item_naming_only_the_replaced_record_serves_its_correction() -> None:
    first = _record(challenges=[_sustained()])
    correction = _record(
        session_id="session-c7149e2a0f85",
        corrects=SESSION,
        logged_date="2026-10-03",
        challenges=[_sustained()],
    )

    report = _check_items(first, correction)

    assert report.passed, report.refusals
    assert [record.sustained for record in report.records] == [1, 1]


def test_an_item_naming_an_unrelated_session_is_refused() -> None:
    other = _record(session_id="session-111111111111", challenges=[_sustained()])

    report = _check_items(_record(challenges=[_sustained()]), other)

    assert _located(report) == {(2, "challenges[0].follow_up")}
    assert "session-111111111111" in report.refusals[0].reason


def test_two_challenges_may_share_one_item() -> None:
    report = _check_items(_record(challenges=[_sustained(), _sustained()]))

    assert report.passed and report.records[0].sustained == 2


def test_a_resolved_challenge_may_link_an_item_and_stays_resolved() -> None:
    report = _check_items(_record(challenges=[_challenge(follow_up=SPIKE)]))

    assert report.passed and report.records[0].sustained == 0


def test_a_resolved_challenge_linking_a_missing_item_is_refused() -> None:
    missing = "aidd_docs/backlog/spikes/never-filed.md"
    report = _check_items(_record(challenges=[_challenge(follow_up=missing)]))

    assert _located(report) == {(1, "challenges[0].follow_up")}


@pytest.mark.parametrize("status", ["cancelled", "done"])
def test_a_closed_item_leaves_its_challenge_sustained(status: str) -> None:
    items = {DEFECT: _item("defect", SESSION, CLIENT, status=status)}

    report = _check_items(_record(challenges=[_sustained()]), items=items)

    assert report.passed and report.records[0].sustained == 1


@pytest.mark.parametrize(
    ("text", "kind"),
    [
        ("---\ntype: defect\n---\n", "defect"),
        ("---\ntype: 'spike'\n---\n", "spike"),
        ('---\nstatus: open\ntype: "spike"\n---\n', "spike"),
        ("---\nstatus: open\n---\ntype: spike\n", None),
        ("---\ntype: spike\n", None),
        ("---\nstatus: open\n\n# Body\ntype: spike\n", None),
        ("\ufeff---\ntype: defect\n---\n", "defect"),
        ("---\nstatus: open\n", None),
        ("type: spike\n", None),
        ("", None),
    ],
)
def test_the_frontmatter_type_is_read_with_the_standard_library(
    text: str, kind: str | None
) -> None:
    assert client_sessions.frontmatter_type(text) == kind


def test_a_correction_loop_through_a_duplicate_id_terminates() -> None:
    first = _record(challenges=[_sustained()])
    second = _record(
        session_id="session-c7149e2a0f85", corrects=SESSION, challenges=[_sustained()]
    )
    loop = _record(corrects="session-c7149e2a0f85", challenges=[_sustained()])

    report = _check_items(first, second, loop)

    assert (3, "session_id") in _located(report)


def _planted_repo(tmp_path: Path) -> tuple[Path, Path]:
    sessions = tmp_path / RECORD
    sessions.parent.mkdir(parents=True)
    sessions.write_text(_text(_record(challenges=[_sustained()])), encoding="utf-8")
    item = tmp_path / DEFECT
    item.parent.mkdir(parents=True)
    item.write_text(ITEMS[DEFECT], encoding="utf-8")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text(CHANGELOG, encoding="utf-8")
    return sessions, changelog


def test_a_cited_item_renamed_after_commit_fails_the_committed_record_check(
    tmp_path: Path,
) -> None:
    sessions, changelog = _planted_repo(tmp_path)
    assert check_file(sessions, changelog).passed

    item = tmp_path / DEFECT
    item.rename(item.with_name("renamed.md"))
    report = check_file(sessions, changelog)

    assert _located(report) == {(1, "challenges[0].follow_up")}
    assert "does not exist" in report.refusals[0].reason


def test_an_item_saved_with_a_byte_order_mark_passes(tmp_path: Path) -> None:
    sessions, changelog = _planted_repo(tmp_path)
    (tmp_path / DEFECT).write_text("\ufeff" + ITEMS[DEFECT], encoding="utf-8")

    assert check_file(sessions, changelog).passed


def test_an_unreadable_item_reads_as_missing(tmp_path: Path) -> None:
    (tmp_path / "binary.md").write_bytes(b"\xff\xfe\x00")
    read = client_sessions.repo_item_reader(tmp_path)

    assert read("binary.md") is None and read("absent.md") is None


# --- each release's credibility verdict -----------------------------------


def _sid(n: int) -> str:
    return f"session-{n:012x}"


def _cid(n: int) -> str:
    return f"client-{n:012x}"


def _any_item(path: str) -> str:
    # One defect that names every planted session and client, so any
    # sustained challenge's follow-up resolves.
    return _item("defect", *(f"{_sid(n)} {_cid(n)}" for n in range(1, 30)))


def _clean(n: int, client: int | None = None, **overrides: Any) -> dict[str, Any]:
    """An accepted, complete, outside-audience session of release 0.2.0."""
    fields: dict[str, Any] = {"outcome": "accepted", "challenges": [], **overrides}
    return _record(
        session_id=_sid(n), client_id=_cid(n if client is None else client), **fields
    )


def _blocking(n: int, *claims: str, **overrides: Any) -> dict[str, Any]:
    challenge = _sustained(claims=list(claims or ["fiche_disclosure"]))
    return _clean(n, outcome="challenged", challenges=[challenge], **overrides)


def _commits(sha: str) -> bool:
    return sha == KNOWN_COMMIT


def _verdicts(
    *records: dict[str, Any], changelog: str = CHANGELOG
) -> dict[str, client_sessions.Verdict]:
    report = check_records(_text(*records), changelog, _commits, _any_item)
    assert report.passed, report.refusals
    return report.verdicts


def _line(*records: dict[str, Any], release: str = "0.2.0") -> str:
    return _verdicts(*records)[release].line()


def _counts(n: int, clients: int, backfilled: int = 0, dismissals: int = 0) -> str:
    return (
        f"({n} of 3 qualifying sessions, {clients} distinct "
        f"client{'' if clients == 1 else 's'}, {backfilled} backfilled, "
        f"{dismissals} dismissal{'' if dismissals == 1 else 's'})"
    )


NOT_YET = "Credibility: not yet validated "
VALIDATED = "Credibility: validated "


def test_no_record_reads_not_yet_validated_zero_of_three_for_every_release() -> None:
    verdicts = _verdicts()

    assert list(verdicts) == ["0.2.0", "0.1.0"]
    assert {v.line() for v in verdicts.values()} == {NOT_YET + _counts(0, 0)}


def test_two_qualifying_sessions_are_not_yet_validated_and_a_third_validates() -> None:
    assert _line(_clean(1), _clean(2)) == NOT_YET + _counts(2, 2)
    assert _line(_clean(1), _clean(2), _clean(3)) == VALIDATED + _counts(3, 3)


def test_a_resolved_challenge_leaves_the_session_qualifying() -> None:
    assert _line(_record(session_id=_sid(1))) == NOT_YET + _counts(1, 1)


def test_an_incomplete_record_does_not_count() -> None:
    incomplete = _record(session_id=_sid(3), challenges=[_challenge(role=ABSENT)])

    assert _line(_clean(1), _clean(2), incomplete) == NOT_YET + _counts(2, 2)


def test_an_internal_session_neither_counts_nor_blocks() -> None:
    internal = _blocking(3, audience="internal")

    assert _line(_clean(1), _clean(2), internal) == NOT_YET + _counts(2, 2)


def test_an_unreleased_record_belongs_to_no_release() -> None:
    unreleased = _clean(1, release="unreleased", release_commit=KNOWN_COMMIT)
    blocking = _blocking(2, release="unreleased", release_commit=KNOWN_COMMIT)

    verdicts = _verdicts(unreleased, blocking)

    assert {v.line() for v in verdicts.values()} == {NOT_YET + _counts(0, 0)}


def test_three_sessions_with_one_client_count_three_with_one_client() -> None:
    line = _line(_clean(1, 7), _clean(2, 7), _clean(3, 7))

    assert line == VALIDATED + _counts(3, 1)


def test_a_backfilled_complete_record_counts_and_an_incomplete_one_does_not() -> None:
    backfilled = _clean(2, backfilled=True)
    incomplete = _record(
        session_id=_sid(3),
        backfilled=True,
        challenges=[_challenge(evidence_offered="")],
    )

    assert _line(_clean(1), backfilled, incomplete) == NOT_YET + _counts(2, 2, 1)


def test_a_blocking_challenge_among_three_clean_sessions_reads_blocked() -> None:
    line = _line(_clean(1), _blocking(2), _clean(3), _clean(4))

    assert line == (
        f"Credibility: blocked by {_sid(2)} on fiche_disclosure " + _counts(3, 3)
    )


def test_a_block_appended_after_validation_revokes_it_whatever_its_date() -> None:
    clean = [_clean(1), _clean(2), _clean(3)]
    revoked = (
        f"Credibility: blocked by {_sid(4)} on fiche_disclosure, validation revoked "
    )
    earlier = _blocking(4, session_date="2026-09-22", logged_date="2026-10-02")

    assert _line(*clean, _blocking(4)) == revoked + _counts(3, 3)
    assert _line(*clean, earlier) == revoked + _counts(3, 3)
    assert _line(*clean, earlier, _clean(5), _clean(6)) == revoked + _counts(5, 5)


def test_a_challenge_on_other_alone_qualifies_and_other_with_judge_blocks() -> None:
    other = _blocking(3, "other")
    mixed = _blocking(3, "other", "judge_agreement")

    assert _line(_clean(1), _clean(2), other) == VALIDATED + _counts(3, 3)
    assert _line(_clean(1), _clean(2), mixed) == (
        f"Credibility: blocked by {_sid(3)} on judge_agreement " + _counts(2, 2)
    )


def test_a_block_names_every_blocking_claim_of_its_session() -> None:
    line = _line(_blocking(1, "judge_agreement", "fiche_disclosure", "other"))

    assert line.startswith(
        f"Credibility: blocked by {_sid(1)} on fiche_disclosure and judge_agreement ("
    )


def test_an_incomplete_or_backfilled_session_still_blocks() -> None:
    challenge = _sustained(role=ABSENT)
    incomplete = _clean(1, outcome="challenged", challenges=[challenge])

    assert _line(incomplete).startswith(f"Credibility: blocked by {_sid(1)}")
    assert _line(_blocking(1, backfilled=True)).startswith("Credibility: blocked")


def test_a_dismissed_session_counts_and_is_reported_as_a_dismissal() -> None:
    dismissed = _clean(2, outcome="dismissed")

    assert _line(_clean(1), dismissed) == NOT_YET + _counts(2, 2, dismissals=1)


def test_a_corrected_record_is_read_as_its_correction() -> None:
    internal = _clean(1, audience="internal")
    to_external = _clean(2, client=1, corrects=_sid(1))
    to_internal = _clean(3, client=1, audience="internal", corrects=_sid(2))

    assert _line(internal) == NOT_YET + _counts(0, 0)
    assert _line(internal, to_external) == NOT_YET + _counts(1, 1)
    assert _line(internal, to_external, to_internal) == NOT_YET + _counts(0, 0)


def test_a_correction_moving_a_session_to_another_release_moves_its_count() -> None:
    moved = _clean(2, client=1, corrects=_sid(1), release="0.1.0")

    verdicts = _verdicts(_clean(1), moved)

    assert verdicts["0.2.0"].qualifying == 0 and verdicts["0.1.0"].qualifying == 1


def test_a_correction_adding_a_block_after_validation_revokes_it() -> None:
    correction = _blocking(4, "table_separation", corrects=_sid(3))
    correction["client_id"] = _cid(3)

    line = _line(_clean(1), _clean(2), _clean(3), correction)

    assert line == (
        f"Credibility: blocked by {_sid(4)} on table_separation, validation "
        "revoked " + _counts(2, 2)
    )


@pytest.mark.parametrize(
    "challenge",
    [
        _challenge(claims=["other"], resolving_evidence=""),
        _challenge(resolving_evidence="opened the fiche the row cites"),
    ],
    ids=["blocking-claim-removed", "resolving-evidence-added"],
)
def test_a_correction_never_removes_a_block(challenge: dict[str, Any]) -> None:
    challenge = {**challenge, "follow_up": DEFECT}
    correction = _clean(
        2, client=1, outcome="challenged", challenges=[challenge], corrects=_sid(1)
    )

    line = _line(_blocking(1), correction, _clean(3), _clean(4), _clean(5))

    assert line == (
        f"Credibility: blocked by {_sid(1)} on fiche_disclosure " + _counts(4, 4)
    )


def _shift(text: str, years: int) -> str:
    return re.sub(
        r"(\d{4})(-\d{2}-\d{2})", lambda m: f"{int(m[1]) + years}{m[2]}", text
    )


def test_shifting_every_date_by_the_same_years_leaves_the_verdict_unchanged() -> None:
    records = _text(_clean(1), _clean(2), _clean(3), _blocking(4), _clean(5))

    now = check_records(records, CHANGELOG, _commits, _any_item)
    later = check_records(_shift(records, 7), _shift(CHANGELOG, 7), _commits, _any_item)

    assert now.passed and later.passed
    assert now.verdicts == later.verdicts
    assert now.verdicts["0.2.0"].blocked_by == _sid(4)


@pytest.mark.parametrize("today", [date(2026, 10, 4), date(2031, 1, 1)])
def test_the_verdict_reads_no_clock(
    monkeypatch: pytest.MonkeyPatch, today: date
) -> None:
    utc = datetime_module.UTC
    moment = datetime_module.datetime(
        today.year, today.month, today.day, 12, tzinfo=utc
    )

    class Frozen(date):
        @classmethod
        def today(cls) -> Frozen:
            return cls(today.year, today.month, today.day)

    class FrozenMoment(datetime_module.datetime):
        @classmethod
        def now(cls, tz: datetime_module.tzinfo | None = None) -> FrozenMoment:
            return cls.fromtimestamp(moment.timestamp(), tz)

        @classmethod
        def today(cls) -> FrozenMoment:
            return cls.now()

    # Every clock the module could read: its own `date`, and the `datetime`
    # module's `date` and `datetime` for any call made through them.
    monkeypatch.setattr(client_sessions, "date", Frozen)
    monkeypatch.setattr(datetime_module, "date", Frozen)
    monkeypatch.setattr(datetime_module, "datetime", FrozenMoment)
    assert datetime_module.datetime.now(utc).date() == today

    assert _line(_clean(1), _clean(2)) == NOT_YET + _counts(2, 2)
    assert _line(_clean(1), _clean(2), _clean(3)) == VALIDATED + _counts(3, 3)


# --- the verdict line in each dated CHANGELOG.md section -------------------


def _flat(text: str) -> str:
    return " ".join(text.split())


def test_the_module_and_the_procedure_state_the_same_verdict_forms() -> None:
    module = _flat(client_sessions.Verdict.__doc__ or "")
    procedure = _flat(PROCEDURE.read_text(encoding="utf-8"))

    for form in client_sessions.VERDICT_FORMS:
        assert form in module, form
        assert form in procedure, form


@pytest.mark.parametrize(
    "records",
    [
        (),
        (_clean(1), _clean(2), _clean(3)),
        (_clean(1), _blocking(2, "other", "judge_agreement", "fiche_disclosure")),
    ],
    ids=["not-yet", "validated", "blocked"],
)
def test_every_printed_line_has_one_of_the_documented_forms(
    records: tuple[dict[str, Any], ...],
) -> None:
    counts = (
        r"\d+ of 3 qualifying sessions, \d+ distinct clients?, "
        r"\d+ backfilled, \d+ dismissals?"
    )
    states = (
        r"validated|not yet validated|blocked by session-[0-9a-f]{12} "
        r"on \w+( and \w+)*(, validation revoked)?"
    )

    line = _line(*records)

    assert re.fullmatch(rf"Credibility: ({states}) \({counts}\)", line), line


def _planted_changelog(line_020: list[str], line_010: list[str]) -> str:
    return (
        "## [Unreleased]\n\n## [0.2.0] - 2026-09-22\n\n"
        + "".join(f"{line}\n" for line in line_020)
        + "\n### Added\n\n- a feature\n\n## [0.1.0] - 2026-08-22\n\n"
        + "".join(f"{line}\n" for line in line_010)
    )


ZERO = NOT_YET + _counts(0, 0)


def test_the_committed_changelog_carries_the_checks_verdict_for_every_release() -> None:
    report = check_file(REPO / DEFAULT_SESSIONS_PATH, REPO / "CHANGELOG.md")
    changelog = (REPO / "CHANGELOG.md").read_text(encoding="utf-8")

    assert report.verdicts, "CHANGELOG.md has no dated release"
    assert changelog_verdict_mismatches(changelog, report.verdicts) == []


def test_a_planted_changelog_agreeing_with_the_check_passes() -> None:
    changelog = _planted_changelog([ZERO], [ZERO])

    assert changelog_verdict_mismatches(changelog, _verdicts()) == []


@pytest.mark.parametrize(
    ("line_020", "reason"),
    [
        ([VALIDATED + _counts(0, 0)], "reads 'Credibility: validated"),
        ([], "no verdict line"),
        ([ZERO, ZERO], "2 verdict lines"),
    ],
    ids=["disagrees", "missing", "doubled"],
)
def test_a_planted_changelog_line_that_is_wrong_fails_naming_the_release(
    line_020: list[str], reason: str
) -> None:
    changelog = _planted_changelog(line_020, [ZERO])

    mismatches = changelog_verdict_mismatches(changelog, _verdicts())

    assert len(mismatches) == 1
    assert mismatches[0].startswith("0.2.0: ") and reason in mismatches[0]
    assert repr(ZERO) in mismatches[0]


def test_the_command_prints_the_expected_line_for_each_release(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(_files(tmp_path, _text(_clean(1)))) == 0

    out = capsys.readouterr().out
    assert "Verdicts (2): each dated release's CHANGELOG.md line" in out
    assert f"  0.2.0: {NOT_YET}{_counts(1, 1)}" in out
    assert f"  0.1.0: {ZERO}" in out
