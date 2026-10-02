"""The candidate gate: the only way a model reaches a roster entry.

One declared candidate (a JSON file: repo, revision, file, quant, family,
thinking control, and the launch block an entry needs) is taken through seven
steps, cheapest first, and the first failure stops every later one:

1. `revision`: the revision is a 40-hex commit sha, never a branch, and the
   file is listed at it.
2. `licence`: the licence id is read off the hub at the revision and its text
   scanned; a sentence forbidding the publication of benchmark results refuses
   the candidate, any other licence passes with its terms recorded.
3. `disk`: free space under the models directory covers the file before any
   download starts.
4. `download`: the file is fetched at the revision, and its sha256 (lowercase
   hex), byte size, architecture and total parameter count are read off the
   bytes on disk -- never off a model card.
5. `load`: one `llama-server` load under the build `build_probe` reads off the
   binary. An architecture that build does not implement is `deferred`, naming
   the architecture and the build; the gate never offers another build.
6. `thinking_control`: the chat template is read from `/props`; an object
   control is refused when the reference engine's registry entry declares no
   thinking switch (`none`) or carries it in another request field, else
   verified with `local_client.verify_thinking_control`; a `none`
   declaration by one live generation returning no reasoning, and `allowed`
   (no verifiable control) skips both and enters with no control declared.
7. `language_claim`: the EN/FR/DE claim and its source are recorded.

Every run appends one record to the candidate record file beside the roster
(`DEFAULT_RECORDS_PATH`). A pass carries the full roster entry block; it is
the author's to copy into `models.json` as a reviewed change, and nothing here
writes that file. A refusal names the step, the evidence and the date.

A malformed declaration, an unreachable hub, a busy port or an unreadable
build is the operator's or the host's problem, not a finding about the
candidate: those exit `2` and record nothing.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import shutil
import struct
import sys
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, BinaryIO, Protocol

import requests

from wave_local_ai_v2 import (
    build_probe,
    engines,
    local_client,
    prompt_provenance,
    roster,
    server,
    settings,
)

RECORD_VERSION = 1
DEFAULT_RECORDS_PATH = "aidd_docs/roster/candidate-records.jsonl"
HUB_URL = "https://huggingface.co"
HTTP_TIMEOUT_S = 60.0
# Enough for a reasoning model to open its reasoning, short enough to be cheap.
REASONING_PROBE_MAX_TOKENS = 64
_DOWNLOAD_CHUNK_BYTES = 1 << 20

STEP_REVISION = "revision"
STEP_LICENCE = "licence"
STEP_DISK = "disk"
STEP_DOWNLOAD = "download"
STEP_LOAD = "load"
STEP_THINKING = "thinking_control"
STEP_LANGUAGE = "language_claim"
STEPS: tuple[str, ...] = (
    STEP_REVISION,
    STEP_LICENCE,
    STEP_DISK,
    STEP_DOWNLOAD,
    STEP_LOAD,
    STEP_THINKING,
    STEP_LANGUAGE,
)

OUTCOME_PASSED = "passed"
OUTCOME_REFUSED = "refused"
OUTCOME_DEFERRED = "deferred"

# A declaration with no verifiable control: the entry enters with no
# `thinking_control`, which `local_client.thinking_kwargs` refuses under
# `thinking_policy: disabled`, so it can only ever run under `allowed`.
THINKING_ALLOWED = "allowed"

_COMMIT_SHA = re.compile(r"[0-9a-f]{40}")
_LICENCE_FILE = re.compile(r"licen[cs]e(\.(md|txt))?", re.IGNORECASE)
_UNKNOWN_ARCHITECTURE = re.compile(r"unknown model architecture", re.IGNORECASE)
_ERROR_LINE = re.compile(r"error", re.IGNORECASE)
# The one licence refusal the epic allows: a sentence that names benchmarks,
# publication and a prohibition together.
_BENCHMARK = re.compile(r"benchmark", re.IGNORECASE)
_PUBLISH = re.compile(r"publish|disclos|make public", re.IGNORECASE)
_PROHIBITION = re.compile(
    r"\b(may not|shall not|must not|cannot|can not|will not|not permitted|"
    r"prohibit|forbid)|without (the )?(prior|express)",
    re.IGNORECASE,
)

_DECLARATION_TEXT_FIELDS = (
    "entry_id",
    "repo",
    "revision",
    "repo_file",
    "file",
    "display_id",
    "quant",
)
_DECLARATION_FIELDS = (
    *_DECLARATION_TEXT_FIELDS,
    "family",
    "thinking_control",
    "active_params_b",
    "client_commercial_use",
    "language_claim",
    "server_flags",
    "validated_host",
)


class CandidateError(ValueError):
    """A declaration the gate cannot take: exit 2, nothing recorded."""


class GateAborted(RuntimeError):
    """A host or network failure that says nothing about the candidate."""


class HubNotFound(LookupError):
    """The hub has no such repo, revision or file."""


class DownloadError(RuntimeError):
    """The hub refused the file's bytes (an HTTP status other than 200)."""


class GgufError(ValueError):
    """The downloaded file is not a readable GGUF."""


class StepRefused(Exception):
    """One step's failure: the step, its evidence, and refused or deferred."""

    def __init__(
        self, step: str, evidence: str, *, outcome: str = OUTCOME_REFUSED
    ) -> None:
        super().__init__(f"{step}: {evidence}")
        self.step = step
        self.evidence = evidence
        self.outcome = outcome


@dataclass(frozen=True)
class Candidate:
    """A parsed declaration; `raw` is recorded verbatim on every record."""

    entry_id: str
    repo: str
    revision: str
    repo_file: str
    file: str
    display_id: str
    quant: str
    family: str
    thinking_control: dict[str, Any] | str
    active_params_b: float
    client_commercial_use: bool
    language_claim: Any
    server_flags: dict[str, Any]
    validated_host: dict[str, Any]
    raw: dict[str, Any]


@dataclass(frozen=True)
class RepoListing:
    """What the hub lists at one revision."""

    commit: str
    # Repo path -> byte size, `None` when the listing gives none.
    files: dict[str, int | None]
    licence_id: str | None


@dataclass(frozen=True)
class GgufFacts:
    """What the GGUF header states about the model, read without its tensors."""

    architecture: str
    expert_count: int
    total_params: int


class Hub(Protocol):
    """The read-only hub seam."""

    def listing(self, repo: str, revision: str) -> RepoListing: ...

    def read_text(self, repo: str, revision: str, path: str) -> str: ...


@dataclass(frozen=True)
class GateSeams:
    """Everything the gate reaches outside this process, injectable for tests."""

    hub: Hub
    download: Callable[[str, str, str, Path], None]
    disk_free: Callable[[Path], int]
    probe_build: Callable[[Path], str | None]
    launch: Callable[[Path, list[str]], AbstractContextManager[object]]
    port_in_use: Callable[[], bool]


def parse_candidate(raw: Any) -> Candidate:
    """Shape-check a declaration, refusing it naming the field.

    The launch block is checked by `roster.parse_entry` itself, over a
    provisional entry, so a declaration that passes the gate cannot produce a
    pass record the roster loader would refuse.
    """
    if not isinstance(raw, dict):
        raise CandidateError("the candidate declaration must be a JSON object")
    missing = [key for key in _DECLARATION_FIELDS if key not in raw]
    if missing:
        raise CandidateError(f"the candidate declares no {', '.join(missing)}")
    for key in _DECLARATION_TEXT_FIELDS:
        if not isinstance(raw[key], str) or not raw[key].strip():
            raise CandidateError(f"{key!r} must be a non-empty string")
    if raw["family"] not in roster.KNOWN_FAMILIES:
        raise CandidateError(
            f"'family' {raw['family']!r} is not a known family "
            f"({', '.join(sorted(roster.KNOWN_FAMILIES))})"
        )
    control = raw["thinking_control"]
    if control not in (roster.THINKING_CONTROL_NONE, THINKING_ALLOWED) and not (
        isinstance(control, dict) and control
    ):
        raise CandidateError(
            f"'thinking_control' must be {roster.THINKING_CONTROL_NONE!r}, "
            f"{THINKING_ALLOWED!r} or a non-empty object of request arguments, "
            f"got {control!r}"
        )
    active = raw["active_params_b"]
    if not isinstance(active, int | float) or isinstance(active, bool) or active <= 0:
        raise CandidateError(
            f"'active_params_b' must be a positive number, got {active!r}"
        )
    if not isinstance(raw["client_commercial_use"], bool):
        raise CandidateError(
            "'client_commercial_use' must be a boolean read off the licence, "
            f"got {raw['client_commercial_use']!r}"
        )
    candidate = Candidate(
        entry_id=raw["entry_id"],
        repo=raw["repo"],
        revision=raw["revision"],
        repo_file=raw["repo_file"],
        file=raw["file"],
        display_id=raw["display_id"],
        quant=raw["quant"],
        family=raw["family"],
        thinking_control=control,
        active_params_b=float(active),
        client_commercial_use=raw["client_commercial_use"],
        language_claim=raw["language_claim"],
        server_flags=raw["server_flags"],
        validated_host=raw["validated_host"],
        raw=raw,
    )
    try:
        _roster_entry(candidate, sha256="0" * 64, kind="dense", expert_count=0)
    except roster.RosterError as exc:
        raise CandidateError(str(exc)) from None
    return candidate


def _entry_block(
    candidate: Candidate,
    *,
    sha256: str,
    kind: str,
    expert_count: int,
    licence: dict[str, Any] | None = None,
    language_claim: dict[str, Any] | None = None,
    total_params: int | None = None,
    bytes_on_disk: int | None = None,
) -> dict[str, Any]:
    """The roster entry block, in `models.json`'s own key order.

    With the figures read off the file, the block carries them and the size
    class their total falls in (`roster.size_class_for`): a band, not a
    judgement, so the composition check agrees with it by construction.
    """
    block: dict[str, Any] = {
        "repo": candidate.repo,
        "revision": candidate.revision,
        "file": candidate.file,
        "display_id": candidate.display_id,
        "quant": candidate.quant,
        "sha256": sha256,
    }
    if total_params is not None:
        block["size_class"] = roster.size_class_for(total_params)
    if bytes_on_disk is not None:
        block["bytes_on_disk"] = bytes_on_disk
    block["family"] = candidate.family
    if candidate.thinking_control != THINKING_ALLOWED:
        block["thinking_control"] = candidate.thinking_control
    if licence is not None:
        block["licence"] = licence
    if language_claim is not None:
        block["language_claim"] = language_claim
    block["architecture"] = {
        "kind": kind,
        "expert_count": expert_count,
        "active_params_b": candidate.active_params_b,
    }
    if total_params is not None:
        block["architecture"]["total_params"] = total_params
    block["server_flags"] = candidate.server_flags
    block["validated_host"] = candidate.validated_host
    return block


def _roster_entry(
    candidate: Candidate, *, sha256: str, kind: str, expert_count: int
) -> roster.RosterEntry:
    return roster.parse_entry(
        candidate.entry_id,
        _entry_block(candidate, sha256=sha256, kind=kind, expert_count=expert_count),
    )


def forbidding_clause(text: str) -> str | None:
    """The first sentence of `text` forbidding publication of benchmark results."""
    flattened = " ".join(text.split())
    for sentence in re.split(r"(?<=[.;!?])\s+", flattened):
        if (
            _BENCHMARK.search(sentence)
            and _PUBLISH.search(sentence)
            and _PROHIBITION.search(sentence)
        ):
            return sentence
    return None


def sha256_file(path: Path) -> str:
    """The file's sha256, lowercase hex, read off its bytes."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_DOWNLOAD_CHUNK_BYTES), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _decisive_line(message: str) -> str:
    """The shortest decisive line of a server failure.

    The line naming an unknown architecture when there is one, else the first
    error line: llama.cpp follows its cause with a generic "exiting due to
    model loading error" that names nothing.
    """
    lines = [line.strip() for line in message.splitlines() if line.strip()]
    for pattern in (_UNKNOWN_ARCHITECTURE, _ERROR_LINE):
        for line in lines:
            if pattern.search(line):
                return line
    return lines[0] if lines else message


def _blob_url(repo: str, revision: str, path: str) -> str:
    return f"{HUB_URL}/{repo}/blob/{revision}/{path}"


@dataclass
class _Run:
    """One gate run's inputs and the facts observed so far."""

    candidate: Candidate
    models_dir: Path
    server_path: Path
    host_threads: int
    seams: GateSeams
    today: str
    observed: dict[str, Any]


def _step_revision(run: _Run) -> RepoListing:
    c = run.candidate
    if _COMMIT_SHA.fullmatch(c.revision) is None:
        raise StepRefused(
            STEP_REVISION,
            f"revision {c.revision!r} is not a 40-hex commit sha: a branch or "
            "tag can move under the entry",
        )
    try:
        listing = run.seams.hub.listing(c.repo, c.revision)
    except HubNotFound as exc:
        raise StepRefused(STEP_REVISION, str(exc)) from None
    if listing.commit != c.revision:
        raise StepRefused(
            STEP_REVISION,
            f"the hub resolves {c.revision!r} to commit {listing.commit!r}",
        )
    if c.repo_file not in listing.files:
        raise StepRefused(
            STEP_REVISION,
            f"file {c.repo_file!r} does not exist in {c.repo} at {c.revision}",
        )
    return listing


def _step_licence(run: _Run, listing: RepoListing) -> dict[str, Any]:
    c = run.candidate
    if not listing.licence_id:
        raise StepRefused(STEP_LICENCE, f"{c.repo} declares no licence at {c.revision}")
    licence_files = sorted(p for p in listing.files if _LICENCE_FILE.fullmatch(p))
    if licence_files:
        source = licence_files[0]
    elif "README.md" in listing.files:
        source = "README.md"
    else:
        raise StepRefused(
            STEP_LICENCE,
            f"{c.repo} carries no licence text (no LICENSE file, no README.md) "
            f"at {c.revision}",
        )
    try:
        text = run.seams.hub.read_text(c.repo, c.revision, source)
    except HubNotFound as exc:
        raise StepRefused(STEP_LICENCE, str(exc)) from None
    source_url = _blob_url(c.repo, c.revision, source)
    clause = forbidding_clause(text)
    if clause is not None:
        raise StepRefused(
            STEP_LICENCE,
            f"licence {listing.licence_id!r} ({source_url}) forbids publishing "
            f"benchmark results: {clause!r}",
        )
    return {
        "id": listing.licence_id,
        "client_commercial_use": c.client_commercial_use,
        "read_on": run.today,
        "source_url": source_url,
    }


def _step_disk(run: _Run, listing: RepoListing) -> int:
    c = run.candidate
    size = listing.files[c.repo_file]
    if size is None:
        raise StepRefused(
            STEP_DISK, f"the hub listing gives no size for {c.repo_file!r}"
        )
    free = run.seams.disk_free(run.models_dir)
    run.observed["disk_free_bytes"] = free
    if free < size:
        raise StepRefused(
            STEP_DISK,
            f"{free} bytes free under {run.models_dir}, {size} needed for "
            f"{c.repo_file!r}; nothing downloaded",
        )
    return size


def _step_download(run: _Run, size: int) -> tuple[Path, str, GgufFacts]:
    c = run.candidate
    dest = run.models_dir / c.file
    try:
        run.seams.download(c.repo, c.revision, c.repo_file, dest)
    except DownloadError as exc:
        raise StepRefused(STEP_DOWNLOAD, str(exc)) from None
    if not dest.is_file():
        raise StepRefused(
            STEP_DOWNLOAD, f"no file at {dest} after the download: nothing to hash"
        )
    on_disk = dest.stat().st_size
    run.observed["bytes"] = on_disk
    if on_disk != size:
        raise StepRefused(
            STEP_DOWNLOAD,
            f"{dest} holds {on_disk} bytes, the hub lists {size} at {c.revision}",
        )
    sha256 = sha256_file(dest)
    run.observed["sha256"] = sha256
    try:
        facts = read_gguf_facts(dest)
    except GgufError as exc:
        raise StepRefused(STEP_DOWNLOAD, str(exc)) from None
    run.observed["gguf_architecture"] = facts.architecture
    run.observed["expert_count"] = facts.expert_count
    run.observed["total_params"] = facts.total_params
    return dest, sha256, facts


def _step_load_and_thinking(
    run: _Run, model_path: Path, sha256: str, facts: GgufFacts
) -> dict[str, Any]:
    """Steps 5 and 6: one load, and the template read while it is up."""
    c = run.candidate
    build = run.seams.probe_build(run.server_path)
    if build is None:
        raise GateAborted(
            f"build_probe cannot read the build of {run.server_path}: a load "
            "under an unknown build would name nothing"
        )
    run.observed["llama_cpp_build"] = build
    kind = _kind(facts)
    try:
        entry = _roster_entry(
            c, sha256=sha256, kind=kind, expert_count=facts.expert_count
        )
        flags = server.build_flags(entry, None, run.host_threads, model_path)
    except roster.RosterError as exc:
        raise StepRefused(
            STEP_LOAD,
            f"the declared launch block does not fit the file's {kind} "
            f"architecture {facts.architecture!r}: {exc}",
        ) from None
    if run.seams.port_in_use():
        engine = engines.tracked_reference_engine()
        raise GateAborted(
            f"port {engine.default_port} on {engine.host} is already in use: stop the "
            "running llama-server before the gate's load"
        )
    try:
        with run.seams.launch(run.server_path, flags):
            return _step_thinking(run, entry)
    except server.ServerStartupError as exc:
        line = _decisive_line(str(exc))
        if _UNKNOWN_ARCHITECTURE.search(str(exc)):
            raise StepRefused(
                STEP_LOAD,
                f"build {build} does not implement architecture "
                f"{facts.architecture!r}; deferred under the pinned build: {line}",
                outcome=OUTCOME_DEFERRED,
            ) from None
        raise StepRefused(
            STEP_LOAD,
            f"architecture {facts.architecture!r} failed to load under build "
            f"{build}: {line}",
        ) from None


def _step_thinking(run: _Run, entry: roster.RosterEntry) -> dict[str, Any]:
    engine = engines.tracked_reference_engine()
    base_url = engines.base_url(engine)
    control = run.candidate.thinking_control
    try:
        template = local_client.chat_template(base_url, timeout=HTTP_TIMEOUT_S)
        run.observed["chat_template_hash"] = prompt_provenance.template_hash(template)
        if control == THINKING_ALLOWED:
            return {"declared": THINKING_ALLOWED, "verified": False}
        if control == roster.THINKING_CONTROL_NONE:
            reasoning = local_client.probe_reasoning(
                base_url, max_tokens=REASONING_PROBE_MAX_TOKENS, timeout=HTTP_TIMEOUT_S
            )
            if reasoning:
                raise StepRefused(
                    STEP_THINKING,
                    f"declared {roster.THINKING_CONTROL_NONE!r} but one "
                    f"generation returned reasoning: {reasoning[:200]!r}",
                )
            return {"declared": roster.THINKING_CONTROL_NONE, "verified": True}
        # An object control the engine's switch cannot carry (an engine
        # declaring `none`, or another request field) is refused before it is
        # rendered: a batch would refuse it anyway.
        if isinstance(control, dict):
            local_client.check_engine_carries(entry.entry_id, control, engine)
        probe = local_client.verify_thinking_control(
            base_url, entry, chat_template=template, timeout=HTTP_TIMEOUT_S
        )
    except (local_client.LocalRequestError, requests.RequestException) as exc:
        raise StepRefused(STEP_THINKING, str(exc)) from None
    return {
        "declared": control,
        "verified": True,
        "with_control": probe["with_control"],
        "without_control": probe["without_control"],
    }


def _step_language(run: _Run) -> dict[str, Any]:
    claim = run.candidate.language_claim
    if not isinstance(claim, dict):
        raise StepRefused(STEP_LANGUAGE, f"no language claim declared: {claim!r}")
    languages = claim.get("languages")
    if (
        not isinstance(languages, list)
        or any(language not in roster.CLAIMABLE_LANGUAGES for language in languages)
        or len(set(languages)) != len(languages)
    ):
        raise StepRefused(
            STEP_LANGUAGE,
            "the claim's languages must be distinct values from "
            f"{', '.join(roster.CLAIMABLE_LANGUAGES)}, got {languages!r}",
        )
    source_url = claim.get("source_url")
    if not isinstance(source_url, str) or not source_url.strip():
        raise StepRefused(STEP_LANGUAGE, f"the claim names no source: {source_url!r}")
    block: dict[str, Any] = {
        "languages": languages,
        "source_url": source_url,
        "read_on": run.today,
    }
    statement = claim.get("statement")
    if statement is not None:
        if not isinstance(statement, str) or not statement.strip():
            raise StepRefused(
                STEP_LANGUAGE, f"the claim's statement is empty: {statement!r}"
            )
        block["statement"] = statement
    return block


def _kind(facts: GgufFacts) -> str:
    return "moe" if facts.expert_count > 0 else "dense"


def run_gate(
    candidate: Candidate,
    *,
    models_dir: Path,
    server_path: Path,
    host_threads: int,
    seams: GateSeams,
    now: datetime,
) -> dict[str, Any]:
    """Take `candidate` through the seven steps; return the record to append.

    Raises `GateAborted` for a failure that is not the candidate's.
    """
    run = _Run(
        candidate=candidate,
        models_dir=models_dir,
        server_path=server_path,
        host_threads=host_threads,
        seams=seams,
        today=now.date().isoformat(),
        observed={},
    )
    record: dict[str, Any] = {
        "record_version": RECORD_VERSION,
        "entry_id": candidate.entry_id,
        "checked_at": now.isoformat(),
        "checked_on": run.today,
        "outcome": OUTCOME_PASSED,
        "step": None,
        "evidence": None,
        "candidate": candidate.raw,
        "entry": None,
        "observed": run.observed,
    }
    try:
        listing = _step_revision(run)
        licence = _step_licence(run, listing)
        size = _step_disk(run, listing)
        model_path, sha256, facts = _step_download(run, size)
        run.observed["thinking"] = _step_load_and_thinking(
            run, model_path, sha256, facts
        )
        language_claim = _step_language(run)
    except StepRefused as refusal:
        record.update(
            outcome=refusal.outcome, step=refusal.step, evidence=refusal.evidence
        )
        return record
    entry = _entry_block(
        candidate,
        sha256=sha256,
        kind=_kind(facts),
        expert_count=facts.expert_count,
        licence=licence,
        language_claim=language_claim,
        total_params=facts.total_params,
        bytes_on_disk=size,
    )
    # Proven loadable by the roster's own parser, not by a copy of its rules.
    roster.parse_entry(candidate.entry_id, entry)
    record["entry"] = entry
    return record


def append_record(path: Path, record: dict[str, Any]) -> None:
    """Append one record as a JSON line; earlier lines are never rewritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")


def _hub_headers() -> dict[str, str]:
    """A bearer token when `HF_TOKEN` is set, for a gated repository."""
    token = os.environ.get("HF_TOKEN")
    return {"Authorization": f"Bearer {token}"} if token else {}


def _hub_get(url: str, **kwargs: Any) -> requests.Response:
    try:
        response = requests.get(
            url, headers=_hub_headers(), timeout=HTTP_TIMEOUT_S, **kwargs
        )
    except requests.RequestException as exc:
        raise GateAborted(f"the hub is unreachable at {url}: {exc}") from exc
    if response.status_code == 404:
        raise HubNotFound(f"the hub answers 404 for {url}")
    _refuse_unauthorised(response.status_code, url)
    return response


# A gated repository answers these without a token: the operator's access,
# not a finding about the candidate, so nothing is recorded.
_UNAUTHORISED = frozenset({401, 403})


def _refuse_unauthorised(status: int, url: str) -> None:
    if status in _UNAUTHORISED:
        raise GateAborted(
            f"the hub answers {status} for {url}: the repository may be gated "
            "and need HF_TOKEN set"
        )


class HuggingFaceHub:
    """The Hugging Face Hub, read-only, over its public HTTP API."""

    def listing(self, repo: str, revision: str) -> RepoListing:
        url = f"{HUB_URL}/api/models/{repo}/revision/{revision}"
        response = _hub_get(url, params={"blobs": "true"})
        if response.status_code != 200:
            raise GateAborted(f"the hub answers {response.status_code} for {url}")
        payload: Any = response.json()
        files: dict[str, int | None] = {}
        for sibling in payload.get("siblings") or []:
            size = sibling.get("size")
            files[sibling["rfilename"]] = size if isinstance(size, int) else None
        card = payload.get("cardData") or {}
        licence = card.get("license")
        if licence == "other" and isinstance(card.get("license_name"), str):
            licence = card["license_name"]
        return RepoListing(
            commit=str(payload.get("sha", "")),
            files=files,
            licence_id=licence if isinstance(licence, str) and licence else None,
        )

    def read_text(self, repo: str, revision: str, path: str) -> str:
        url = f"{HUB_URL}/{repo}/resolve/{revision}/{path}"
        response = _hub_get(url)
        if response.status_code != 200:
            raise GateAborted(f"the hub answers {response.status_code} for {url}")
        return response.text


def stream_download(repo: str, revision: str, repo_file: str, dest: Path) -> None:
    """Fetch `repo_file` at `revision` into `dest`, through a `.part` file.

    The destination only ever holds a complete download: the bytes land in
    `<dest>.part` and are moved into place once the stream ends.
    """
    url = f"{HUB_URL}/{repo}/resolve/{revision}/{repo_file}"
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = dest.with_name(dest.name + ".part")
    try:
        with requests.get(
            url, headers=_hub_headers(), stream=True, timeout=HTTP_TIMEOUT_S
        ) as response:
            _refuse_unauthorised(response.status_code, url)
            if response.status_code != 200:
                raise DownloadError(f"GET {url} answered {response.status_code}")
            with part.open("wb") as handle:
                for chunk in response.iter_content(chunk_size=_DOWNLOAD_CHUNK_BYTES):
                    handle.write(chunk)
    except requests.RequestException as exc:
        part.unlink(missing_ok=True)
        raise GateAborted(f"the download of {url} broke off: {exc}") from exc
    os.replace(part, dest)


# GGUF value types (llama.cpp `gguf` spec): the fixed-width scalars, then the
# two variable-length ones.
_GGUF_SCALARS: dict[int, str] = {
    0: "<B",
    1: "<b",
    2: "<H",
    3: "<h",
    4: "<I",
    5: "<i",
    6: "<f",
    7: "<?",
    10: "<Q",
    11: "<q",
    12: "<d",
}
_GGUF_STRING = 8
_GGUF_ARRAY = 9


def _read_exact(handle: BinaryIO, size: int) -> bytes:
    data = handle.read(size)
    if len(data) != size:
        raise GgufError("the GGUF header is truncated")
    return data


def _unpack(handle: BinaryIO, fmt: str) -> Any:
    return struct.unpack(fmt, _read_exact(handle, struct.calcsize(fmt)))[0]


def _read_string(handle: BinaryIO) -> str:
    return _read_exact(handle, _unpack(handle, "<Q")).decode("utf-8", "replace")


def _read_value(handle: BinaryIO, value_type: int) -> Any:
    """One metadata value; arrays are read through and returned as `None`."""
    if value_type in _GGUF_SCALARS:
        return _unpack(handle, _GGUF_SCALARS[value_type])
    if value_type == _GGUF_STRING:
        return _read_string(handle)
    if value_type == _GGUF_ARRAY:
        item_type = _unpack(handle, "<I")
        for _ in range(_unpack(handle, "<Q")):
            _read_value(handle, item_type)
        return None
    raise GgufError(f"unknown GGUF metadata value type {value_type}")


def read_gguf_facts(path: Path) -> GgufFacts:
    """Architecture, expert count and total parameters, off the GGUF header.

    The parameter count is the sum over every tensor of the product of its
    dimensions: exact, and present in every GGUF, where the optional
    `general.parameter_count` key is not.
    """
    with path.open("rb") as handle:
        magic = handle.read(4)
        if magic != b"GGUF":
            raise GgufError(f"{path} is not a GGUF file (magic {magic!r})")
        version = _unpack(handle, "<I")
        if version < 2:
            raise GgufError(f"{path} is GGUF version {version}; 2 or later is read")
        tensor_count = _unpack(handle, "<Q")
        metadata: dict[str, Any] = {}
        for _ in range(_unpack(handle, "<Q")):
            key = _read_string(handle)
            metadata[key] = _read_value(handle, _unpack(handle, "<I"))
        total = 0
        for _ in range(tensor_count):
            _read_string(handle)
            n_dims = _unpack(handle, "<I")
            dims = struct.unpack(f"<{n_dims}Q", _read_exact(handle, 8 * n_dims))
            _read_exact(handle, 12)  # tensor type (u32) and data offset (u64)
            total += math.prod(dims)
    architecture = metadata.get("general.architecture")
    if not isinstance(architecture, str) or not architecture:
        raise GgufError(f"{path} declares no general.architecture")
    expert_count = metadata.get(f"{architecture}.expert_count", 0)
    return GgufFacts(
        architecture=architecture,
        expert_count=int(expert_count),
        total_params=total,
    )


def _launch(server_path: Path, flags: list[str]) -> AbstractContextManager[object]:
    # A refusal raised inside the context is the gate's finding, already one
    # line, so it does not trigger the server's stderr dump.
    return server.running_server(server_path, flags, quiet_exceptions=(StepRefused,))


def default_seams() -> GateSeams:
    """The real hub, downloader, disk, build probe and server."""
    return GateSeams(
        hub=HuggingFaceHub(),
        download=stream_download,
        disk_free=lambda path: shutil.disk_usage(path).free,
        probe_build=build_probe.probe_build,
        launch=_launch,
        port_in_use=lambda: server._port_is_open(
            engines.tracked_reference_engine().host,
            engines.tracked_reference_engine().default_port,
        ),
    )


def main(argv: list[str] | None = None, *, seams: GateSeams | None = None) -> int:
    """Run the gate on one declaration and append its record.

    Exit `0` on a pass, `1` on a refusal or a deferral (both recorded), `2`
    when nothing could be recorded.
    """
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-candidate-gate",
        description="Take one candidate model through the roster's verification gate.",
    )
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--records", type=Path, default=Path(DEFAULT_RECORDS_PATH))
    args = parser.parse_args(argv)
    try:
        raw = json.loads(args.candidate.read_text(encoding="utf-8"))
        candidate = parse_candidate(raw)
        config = settings.load_settings()
        record = run_gate(
            candidate,
            models_dir=config.slm_models_dir,
            server_path=config.llama_server_path,
            host_threads=config.host_threads,
            seams=seams or default_seams(),
            now=datetime.now(UTC),
        )
    except (
        OSError,
        json.JSONDecodeError,
        CandidateError,
        settings.SettingsError,
        GateAborted,
    ) as exc:
        print(f"candidate gate: nothing recorded: {exc}", file=sys.stderr)
        return 2
    append_record(args.records, record)
    if record["outcome"] == OUTCOME_PASSED:
        print(f"{candidate.entry_id}: passed; record appended to {args.records}")
        return 0
    print(
        f"{candidate.entry_id}: {record['outcome']} at step {record['step']}: "
        f"{record['evidence']}"
    )
    return 1
