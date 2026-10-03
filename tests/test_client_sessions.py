"""The client-session reception record: its tracking, its check and its
append-only history. Every record here is constructed; the committed file
holds no real session until one is shown."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import client_sessions
from wave_local_ai_v2.client_sessions import (
    DEFAULT_SESSIONS_PATH,
    ShallowHistory,
    append_only_violations,
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
            _record(challenges=[_challenge(resolving_evidence=None)]),
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
