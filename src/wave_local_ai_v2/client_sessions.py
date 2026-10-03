"""The client-session reception record and its check.

One append-only JSONL file, `aidd_docs/results/client-sessions.jsonl`, holds
one record per session in which a benchmark result was shown to a client or
their engineer: the release shown, the audience, the outcome and, per
challenge, the challenger's role, the criterion disputed, the claims it bears
on, the evidence offered and the evidence that resolved it. The procedure a
consultant follows to write one is `docs/client-session-record.md`.

The record's fields fall into two classes. Identity and attribution fields
are refused when absent; the three content fields the PRD names (`role`,
`criterion`, `evidence_offered`) leave the record in the file, reported as
incomplete. Every refusal names the line and the field. Exit `0` when nothing
is refused (incomplete records are reported, not failed), `1` when anything
is, `2` when the record or the changelog cannot be read at all.

A challenge is sustained exactly when its `resolving_evidence` is null, empty
or whitespace only (`is_sustained`); no field states it, so nothing can
disagree with it. Every sustained challenge names its follow-up item in
`follow_up`: a defect under `aidd_docs/backlog/defects/` or a spike under
`aidd_docs/backlog/spikes/` whose frontmatter `type` matches its folder and
whose text carries the record's `client_id` and the `session_id` of a record
of its correction chain. A `follow_up` given on a resolved challenge is held
to the same rules and leaves the challenge resolved.

`append_only_violations` walks the record's committed versions along the
first-parent line and names every version that is not a line-for-line prefix
of the next: a committed line is never edited or removed.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

DEFAULT_SESSIONS_PATH = "aidd_docs/results/client-sessions.jsonl"
DEFAULT_CHANGELOG_PATH = "CHANGELOG.md"
RECORD_FORMAT = "1"
UNRELEASED = "unreleased"

# The documented key order (docs/client-session-record.md). `session_id`
# leads the line on purpose: the secrets scanner's id heuristic then reads
# every hexadecimal value after it as an identifier, not a secret.
RECORD_KEYS = (
    "record_format",
    "session_id",
    "client_id",
    "session_date",
    "logged_date",
    "release",
    "release_commit",
    "audience",
    "shown",
    "outcome",
    "backfilled",
    "corrects",
    "challenges",
)
CHALLENGE_KEYS = (
    "role",
    "criterion",
    "claims",
    "evidence_offered",
    "resolving_evidence",
    "follow_up",
)
# Identity and attribution: refused when absent. `release_commit` is required
# with an `unreleased` release only; `corrects` is optional.
REQUIRED_RECORD_FIELDS = tuple(
    key for key in RECORD_KEYS if key not in {"release_commit", "corrects"}
)
REQUIRED_CHALLENGE_FIELDS = ("claims", "resolving_evidence")
# Content: absent or stated empty leaves the record incomplete, not refused.
CONTENT_FIELDS = ("role", "criterion", "evidence_offered")

AUDIENCES = ("external", "internal")
OUTCOMES = ("challenged", "dismissed", "accepted")
CLAIMS = ("fiche_disclosure", "table_separation", "judge_agreement", "other")
# Each folder a follow-up item may live in, and the frontmatter `type` its
# items carry (Q65: a defect when a claim was shown wrong, a spike when it was
# left unresolved).
FOLLOW_UP_FOLDERS = {
    "aidd_docs/backlog/defects/": "defect",
    "aidd_docs/backlog/spikes/": "spike",
}

SESSION_ID = re.compile(r"session-[0-9a-f]{12}")
CLIENT_ID = re.compile(r"client-[0-9a-f]{12}")
COMMIT = re.compile(r"[0-9a-f]{40}")
ISO_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
DATED_RELEASE = re.compile(
    r"^## \[(?P<version>[^\]]+)\] - (?P<date>\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE
)


@dataclass(frozen=True)
class Finding:
    """One refusal or incompleteness, located by line and field."""

    line: int
    field: str
    reason: str

    def __str__(self) -> str:
        return f"line {self.line}: {self.field}: {self.reason}"


@dataclass(frozen=True)
class SessionRecord:
    """What a reader who was not there reads back from one accepted line."""

    line: int
    session_id: str
    session_date: str
    release: str
    release_commit: str | None
    audience: str
    outcome: str
    challenges: int
    sustained: int
    backfilled: bool
    corrects: str | None


@dataclass
class CheckReport:
    records: list[SessionRecord] = field(default_factory=list)
    refusals: list[Finding] = field(default_factory=list)
    incomplete: list[Finding] = field(default_factory=list)
    corrected_by: dict[str, str] = field(default_factory=dict)

    @property
    def passed(self) -> bool:
        return not self.refusals


def dated_releases(changelog_text: str) -> dict[str, date]:
    """Each `## [version] - YYYY-MM-DD` heading of the changelog, by version."""
    return {
        match["version"]: date.fromisoformat(match["date"])
        for match in DATED_RELEASE.finditer(changelog_text)
    }


def git_commit_exists(repo: Path) -> Callable[[str], bool]:
    """`git cat-file -e <sha>^{commit}` in `repo`, as a predicate."""

    def exists(sha: str) -> bool:
        try:
            result = subprocess.run(
                ["git", "cat-file", "-e", f"{sha}^{{commit}}"],
                cwd=repo,
                capture_output=True,
                check=False,
            )
        except OSError:
            return False
        return result.returncode == 0

    return exists


def repo_item_reader(repo: Path) -> Callable[[str], str | None]:
    """The text of a repository-relative file in `repo`, or None when it is
    not a readable file."""

    def read(path: str) -> str | None:
        try:
            return (repo / path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            return None

    return read


def _no_item(path: str) -> str | None:
    return None


def is_sustained(challenge: dict[str, Any]) -> bool:
    """True when no evidence presented within the session is named as having
    resolved the challenge: `resolving_evidence` null, empty or whitespace."""
    evidence = challenge.get("resolving_evidence")
    return evidence is None or (isinstance(evidence, str) and not evidence.strip())


def frontmatter_type(text: str) -> str | None:
    """The `type` of a Markdown file's leading `---` frontmatter block; None
    when the block is absent, unterminated or carries no `type`. A leading
    UTF-8 byte order mark is ignored."""
    lines = text.removeprefix("\ufeff").splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    kind = None
    for line in lines[1:]:
        if line.strip() == "---":
            return kind
        key, sep, value = line.partition(":")
        if sep and key == "type" and kind is None:
            kind = value.strip().strip("\"'") or None
    return None


def _follow_up_folder(path: str) -> tuple[str | None, str | None]:
    """The item kind the path's folder requires, or the reason it is refused."""
    if "\\" in path:
        return None, "uses a backslash: write the path with forward slashes"
    if path.startswith("/") or re.match(r"[A-Za-z]:", path):
        return None, "is absolute: write it relative to the repository root"
    if ".." in path.split("/"):
        return None, "contains '..'"
    for folder, kind in FOLLOW_UP_FOLDERS.items():
        if path.startswith(folder) and len(path) > len(folder):
            return kind, None
    return None, f"is outside {' and '.join(FOLLOW_UP_FOLDERS)}"


@dataclass(frozen=True)
class _Citation:
    """One challenge's follow-up path, checked once the whole file is read."""

    index: int
    path: str
    kind: str


class _Line:
    """The findings of one line, gathered while its fields are read."""

    def __init__(self, number: int, record: dict[str, Any]) -> None:
        self.number = number
        self.record = record
        self.refusals: list[Finding] = []
        self.incomplete: list[Finding] = []
        self.citations: list[_Citation] = []
        session_id = record.get("session_id")
        self.session = session_id if isinstance(session_id, str) else "<no session>"

    def refuse(self, name: str, reason: str) -> None:
        self.refusals.append(Finding(self.number, name, reason))

    def string(self, key: str, *, required: bool = True) -> str | None:
        if key not in self.record:
            if required:
                self.refuse(key, "is absent")
            return None
        value = self.record[key]
        if not isinstance(value, str):
            self.refuse(key, "is not a string")
            return None
        return value

    def matching(self, key: str, pattern: re.Pattern[str], shape: str) -> str | None:
        value = self.string(key)
        if value is not None and not pattern.fullmatch(value):
            self.refuse(key, f"{value!r} does not match {shape}")
            return None
        return value

    def one_of(self, key: str, allowed: tuple[str, ...]) -> str | None:
        value = self.string(key)
        if value is not None and value not in allowed:
            self.refuse(key, f"{value!r} is not one of: {', '.join(allowed)}")
            return None
        return value

    def iso_date(self, key: str) -> date | None:
        value = self.string(key)
        if value is None:
            return None
        try:
            if not ISO_DATE.fullmatch(value):
                raise ValueError
            return date.fromisoformat(value)
        except ValueError:
            self.refuse(key, f"{value!r} is not a YYYY-MM-DD date")
            return None


def _check_release(
    line: _Line,
    session_day: date | None,
    releases: dict[str, date],
    commit_exists: Callable[[str], bool],
) -> tuple[str | None, str | None]:
    release = line.string("release")
    commit_given = "release_commit" in line.record
    if release is None:
        return None, None
    if release == UNRELEASED:
        if not commit_given:
            line.refuse(
                "release_commit",
                "is absent: an unreleased release names the full commit hash",
            )
            return None, None
        commit = line.matching("release_commit", COMMIT, "40 lowercase hex digits")
        if commit is not None and not commit_exists(commit):
            line.refuse(
                "release_commit", f"{commit} names no commit in this repository"
            )
            return None, None
        return (release, commit) if commit is not None else (None, None)
    if release not in releases:
        line.refuse(
            "release",
            f"{release!r} is neither a dated section of CHANGELOG.md nor "
            f"{UNRELEASED!r} with a commit",
        )
        return None, None
    if commit_given:
        line.refuse("release_commit", "only an unreleased release names a commit")
    released = releases[release]
    if session_day is not None and session_day < released:
        line.refuse(
            "session_date",
            f"{session_day.isoformat()} is before release {release}'s date "
            f"{released.isoformat()}",
        )
    return release, None


def _check_challenge(line: _Line, index: int, challenge: object) -> None:
    prefix = f"challenges[{index}]"
    if not isinstance(challenge, dict):
        line.refuse(prefix, "is not a JSON object")
        return
    for key in challenge:
        if key not in CHALLENGE_KEYS:
            line.refuse(f"{prefix}.{key}", "is not a field of the record format")
    for key in REQUIRED_CHALLENGE_FIELDS:
        if key not in challenge:
            line.refuse(f"{prefix}.{key}", "is absent")
    claims = challenge.get("claims")
    if "claims" in challenge:
        if not isinstance(claims, list) or not claims:
            line.refuse(f"{prefix}.claims", "is not a non-empty list")
        else:
            for claim in claims:
                if claim not in CLAIMS:
                    line.refuse(
                        f"{prefix}.claims",
                        f"{claim!r} is not one of: {', '.join(CLAIMS)}",
                    )
            if len(set(map(str, claims))) != len(claims):
                line.refuse(f"{prefix}.claims", "names a claim twice")
    evidence = challenge.get("resolving_evidence")
    if evidence is not None and not isinstance(evidence, str):
        line.refuse(f"{prefix}.resolving_evidence", "is not a string or null")
    _check_follow_up(line, index, challenge)
    for key in CONTENT_FIELDS:
        if key not in challenge:
            line.incomplete.append(Finding(line.number, f"{prefix}.{key}", "absent"))
        elif not isinstance(challenge[key], str):
            line.refuse(f"{prefix}.{key}", "is not a string")
        elif not challenge[key].strip():
            line.incomplete.append(
                Finding(line.number, f"{prefix}.{key}", "stated empty")
            )


def _check_follow_up(line: _Line, index: int, challenge: dict[str, Any]) -> None:
    name = f"challenges[{index}].follow_up"
    where = f"session {line.session}, challenge {index}"
    path = challenge.get("follow_up")
    if "follow_up" in challenge and not isinstance(path, str):
        line.refuse(name, f"{where}: is not a string")
        return
    if path is None or not path.strip():
        if "resolving_evidence" in challenge and is_sustained(challenge):
            line.refuse(
                name,
                f"{where}: the challenge is sustained (no resolving evidence "
                "named) and names no follow-up item",
            )
        return
    kind, problem = _follow_up_folder(path)
    if kind is None:
        line.refuse(name, f"{where}: {path!r} {problem}")
        return
    line.citations.append(_Citation(index, path, kind))


def _check_citations(
    line: _Line, chain: list[str], read_item: Callable[[str], str | None]
) -> None:
    client_id = line.record.get("client_id")
    for citation in line.citations:
        name = f"challenges[{citation.index}].follow_up"
        where = f"session {line.session}, challenge {citation.index}"
        text = read_item(citation.path)
        if text is None:
            line.refuse(name, f"{where}: {citation.path} does not exist")
            continue
        kind = frontmatter_type(text)
        if kind != citation.kind:
            line.refuse(
                name,
                f"{where}: {citation.path} has frontmatter type {kind!r}, "
                f"not {citation.kind!r} as its folder requires",
            )
        if not isinstance(client_id, str) or client_id not in text:
            line.refuse(name, f"{where}: {citation.path} does not contain {client_id}")
        if not any(session_id in text for session_id in chain):
            line.refuse(
                name,
                f"{where}: {citation.path} contains no session id of the "
                f"record's correction chain ({', '.join(chain)})",
            )


def _chain(session_id: str, corrected_by: dict[str, str]) -> list[str]:
    """Every session id linked to `session_id` by `corrects`, oldest first."""
    corrects = {later: earlier for earlier, later in corrected_by.items()}
    first = session_id
    # A refused duplicate session id can close a loop; stop at a repeat.
    walked = {first}
    while first in corrects and corrects[first] not in walked:
        first = corrects[first]
        walked.add(first)
    chain = [first]
    while chain[-1] in corrected_by and corrected_by[chain[-1]] not in chain:
        chain.append(corrected_by[chain[-1]])
    return chain


def _check_line(
    line: _Line,
    releases: dict[str, date],
    commit_exists: Callable[[str], bool],
) -> SessionRecord | None:
    record = line.record
    for key in record:
        if key not in RECORD_KEYS:
            line.refuse(key, "is not a field of the record format")
    line.one_of("record_format", (RECORD_FORMAT,))
    session_id = line.matching("session_id", SESSION_ID, "session-<12 lowercase hex>")
    line.matching("client_id", CLIENT_ID, "client-<12 lowercase hex>")
    session_day = line.iso_date("session_date")
    logged_day = line.iso_date("logged_date")
    if session_day and logged_day and logged_day < session_day:
        line.refuse(
            "logged_date",
            f"{logged_day.isoformat()} is before the session date "
            f"{session_day.isoformat()}",
        )
    release, commit = _check_release(line, session_day, releases, commit_exists)
    audience = line.one_of("audience", AUDIENCES)
    shown = line.string("shown")
    if shown is not None and not shown.strip():
        line.refuse("shown", "is stated empty: say in words what was shown")
    outcome = line.one_of("outcome", OUTCOMES)
    if "backfilled" not in record:
        line.refuse("backfilled", "is absent")
    elif not isinstance(record["backfilled"], bool):
        line.refuse("backfilled", "is not true or false")
    corrects = None
    if "corrects" in record:
        corrects = line.matching("corrects", SESSION_ID, "session-<12 lowercase hex>")
    challenges = record.get("challenges")
    if "challenges" not in record:
        line.refuse("challenges", "is absent (state [] when none was raised)")
    elif not isinstance(challenges, list):
        line.refuse("challenges", "is not a list")
    else:
        for index, challenge in enumerate(challenges):
            _check_challenge(line, index, challenge)
        if outcome == "challenged" and not challenges:
            line.refuse("challenges", "a challenged outcome carries no challenge")
        if outcome in {"accepted", "dismissed"} and challenges:
            line.refuse("challenges", f"an {outcome} outcome carries a challenge")
    if line.refusals:
        return None
    assert session_id and session_day and release and audience and outcome
    assert isinstance(challenges, list)
    return SessionRecord(
        line=line.number,
        session_id=session_id,
        session_date=session_day.isoformat(),
        release=release,
        release_commit=commit,
        audience=audience,
        outcome=outcome,
        challenges=len(challenges),
        sustained=sum(map(is_sustained, challenges)),
        backfilled=record["backfilled"],
        corrects=corrects,
    )


def check_records(
    text: str,
    changelog_text: str,
    commit_exists: Callable[[str], bool],
    read_item: Callable[[str], str | None] = _no_item,
) -> CheckReport:
    """Every refusal, incompleteness and read-back of one record file's text.

    `read_item` returns a follow-up item's text by its repository path, or
    None when no such file exists; the default knows no item.
    """
    releases = dated_releases(changelog_text)
    report = CheckReport()
    seen: dict[str, int] = {}
    read_lines: list[tuple[_Line, SessionRecord | None]] = []
    for number, raw in enumerate(text.splitlines(), start=1):
        try:
            record = json.loads(raw)
        except json.JSONDecodeError as exc:
            report.refusals.append(Finding(number, "<line>", f"does not parse: {exc}"))
            continue
        if not isinstance(record, dict):
            report.refusals.append(Finding(number, "<line>", "is not a JSON object"))
            continue
        line = _Line(number, record)
        read = _check_line(line, releases, commit_exists)
        session_id = record.get("session_id")
        if isinstance(session_id, str):
            if session_id in seen:
                line.refuse(
                    "session_id", f"{session_id} is also on line {seen[session_id]}"
                )
            else:
                seen[session_id] = number
        corrects = record.get("corrects")
        if isinstance(corrects, str) and SESSION_ID.fullmatch(corrects):
            if corrects not in seen or seen[corrects] == number:
                line.refuse("corrects", f"{corrects} names no earlier record")
            elif corrects in report.corrected_by:
                line.refuse(
                    "corrects",
                    f"{corrects} is already corrected by {report.corrected_by[corrects]}",
                )
            elif isinstance(session_id, str):
                report.corrected_by[corrects] = session_id
        read_lines.append((line, read))
    # Follow-up items are read once every correction link is known: an item
    # may name any record of the citing record's chain.
    for line, read in read_lines:
        _check_citations(line, _chain(line.session, report.corrected_by), read_item)
        report.refusals.extend(line.refusals)
        report.incomplete.extend(line.incomplete)
        if read is not None and not line.refusals:
            report.records.append(read)
    return report


def check_file(sessions: Path, changelog: Path) -> CheckReport:
    """Check one record file; commits resolve in the changelog's repository."""
    return check_records(
        sessions.read_text(encoding="utf-8"),
        changelog.read_text(encoding="utf-8"),
        git_commit_exists(changelog.resolve().parent),
        repo_item_reader(changelog.resolve().parent),
    )


def _record_line(record: SessionRecord, corrected_by: dict[str, str]) -> str:
    if record.release_commit:
        release = f"unreleased at commit {record.release_commit}"
    else:
        release = f"release {record.release}"
    marks = [
        f"{record.session_date}, {record.audience} audience, {release}",
        (
            f"{record.outcome}, {record.challenges} challenge(s), "
            f"{record.sustained} sustained"
        ),
    ]
    if record.backfilled:
        marks.append("backfilled")
    if record.corrects:
        marks.append(f"corrects {record.corrects}")
    if record.session_id in corrected_by:
        marks.append(f"corrected by {corrected_by[record.session_id]}")
    return f"  line {record.line} {record.session_id}: " + "; ".join(marks)


def render_report(report: CheckReport, source: str) -> str:
    lines = [
        f"Client-session record: {source}",
        f"Records ({len(report.records)})",
        *(_record_line(item, report.corrected_by) for item in report.records),
        f"Incomplete ({len(report.incomplete)}): reported, does not fail the check",
        *(f"  {item}" for item in report.incomplete),
        f"Refusals ({len(report.refusals)})",
        *(f"  {item}" for item in report.refusals),
    ]
    if report.passed:
        lines.append(
            f"PASS: {len(report.records)} record(s), "
            f"{len(report.incomplete)} incomplete field(s)"
        )
    else:
        lines.append(f"FAIL: {len(report.refusals)} refusal(s)")
    return "\n".join(lines) + "\n"


class ShallowHistory(Exception):
    """The repository's history is shallow, so the walk cannot see it all."""


def _git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        check=False,
        text=True,
        encoding="utf-8",
    )


def append_only_violations(repo: Path, path: str, *, ci: bool) -> list[str]:
    """Every committed version of `path` along HEAD's first-parent line that
    is not a line-for-line prefix of the following one, read from blobs.

    A shallow history raises `ShallowHistory` outside CI and is itself a
    violation under CI, where the checkout must fetch the full history.
    """
    if _git(repo, "rev-parse", "--is-shallow-repository").stdout.strip() == "true":
        if ci:
            return [
                (
                    "the history is shallow: the append-only walk needs the "
                    "full history (checkout fetch-depth: 0)"
                )
            ]
        raise ShallowHistory(f"{repo} is a shallow clone")
    log = _git(
        repo, "log", "--first-parent", "--reverse", "--format=%H", "HEAD", "--", path
    )
    if log.returncode != 0:
        return [f"the history could not be read: {log.stderr.strip()}"]
    revisions = log.stdout.split()
    violations = []
    previous: list[str] = []
    previous_rev = ""
    for revision in revisions:
        shown = _git(repo, "show", f"{revision}:{path}")
        current = shown.stdout.splitlines() if shown.returncode == 0 else []
        if current[: len(previous)] != previous:
            first = next(
                (
                    index
                    for index, line in enumerate(previous, start=1)
                    if index > len(current) or current[index - 1] != line
                ),
                len(previous),
            )
            violations.append(
                f"{revision[:12]}: {path} line {first} of {previous_rev[:12]} "
                "was edited or removed; records are append-only"
            )
        previous, previous_rev = current, revision
    return violations


def main(argv: list[str] | None = None) -> int:
    """Run the check on one record file; exit `0` / `1` / `2`."""
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-client-sessions",
        description=(
            "Read back the client-session record, report incomplete records "
            "and refuse malformed ones, naming the line and the field."
        ),
    )
    parser.add_argument("--sessions", type=Path, default=Path(DEFAULT_SESSIONS_PATH))
    parser.add_argument("--changelog", type=Path, default=Path(DEFAULT_CHANGELOG_PATH))
    args = parser.parse_args(argv)
    try:
        report = check_file(args.sessions, args.changelog)
    except (OSError, UnicodeDecodeError) as exc:
        print(f"client-session check: nothing checked: {exc}", file=sys.stderr)
        return 2
    sys.stdout.write(render_report(report, args.sessions.as_posix()))
    return 0 if report.passed else 1
