"""The model roster: a tracked, versioned file pinning every model's identity
and flag set.

`load_roster` refuses (raises `RosterError`) any entry missing a required
field, `sha256` included, so an incomplete entry can never be resolved.
`resolve_entry` and `validate_host_fit` are the two gates a caller passes
through before launching a model: an unknown id, a dense entry given a host
`n_cpu_moe`, or an MoE entry whose host `n_cpu_moe` exceeds its expert count
are all refused here rather than surfacing as a confusing llama-server error
downstream.

Deliberately does not import `server.py`: phase 2 imports this module from
`server.py`, not the reverse, so the two never form a cycle.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Every required field, keyed by the dotted path of the block that holds it
# ("" is the entry itself). Parents are listed before their children so the
# walk in `_parse_entry` reports the outermost missing block first: an entry
# with no `server_flags` at all is named as that, not as five missing sampler
# keys. Every value `build_flags_from_entry` and `server.build_flags` read is
# listed here, so an entry that loads can be turned into a flag list without a
# KeyError escaping as a traceback.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "": (
        "repo",
        "revision",
        "file",
        "display_id",
        "quant",
        "sha256",
        "architecture",
        "server_flags",
        "validated_host",
    ),
    "architecture": ("kind", "expert_count", "active_params_b"),
    "server_flags": (
        "n_gpu_layers",
        "context_size",
        "flash_attention",
        "jinja",
        "parallel_slots",
        "load_mode",
        "sampler",
    ),
    "server_flags.sampler": (
        "temperature",
        "top_p",
        "top_k",
        "min_p",
        "presence_penalty",
    ),
    "validated_host": ("n_cpu_moe", "threads", "fiche_summary"),
}

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")


class RosterError(ValueError):
    """Raised when the roster file, an entry, or a host-fit check is invalid."""


@dataclass(frozen=True)
class Architecture:
    """A roster entry's model-architecture facts, used to validate host fit."""

    kind: str
    expert_count: int
    active_params_b: float


@dataclass(frozen=True)
class RosterEntry:
    """One roster entry: model identity, its flag set, and its validated host."""

    entry_id: str
    repo: str
    revision: str
    file: str
    # The name a published row reports as its `model_id`: the model as a
    # human names it, without the GGUF packager's repo suffix. Roster data
    # rather than a CLI constant, so selecting another entry cannot leave a
    # row naming the model it did not run.
    display_id: str
    quant: str
    sha256: str
    architecture: Architecture
    server_flags: dict[str, Any]
    validated_host: dict[str, Any]


@dataclass(frozen=True)
class RosterFile:
    """A parsed roster: its version and every entry, keyed by entry id."""

    roster_version: int
    entries: dict[str, RosterEntry]


def load_roster(path: Path) -> RosterFile:
    """Parse `path` into a `RosterFile`, refusing any structurally invalid entry.

    Raises `RosterError` when the file is not valid JSON, is missing
    `roster_version` or `entries` at the top level, or when any entry is
    missing one of `REQUIRED_FIELDS` at any depth (`sha256` included) or
    carries a malformed `sha256`.
    """
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise RosterError(f"roster file not readable at {path}: {exc}") from exc

    try:
        raw: Any = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise RosterError(f"roster file at {path} is not valid JSON: {exc}") from exc

    if not isinstance(raw, dict) or "roster_version" not in raw or "entries" not in raw:
        raise RosterError(
            f"roster file at {path} must be an object with "
            "'roster_version' and 'entries'"
        )

    roster_version = raw["roster_version"]
    # `bool` is an `int` subclass, and `true` in the JSON would otherwise be
    # published verbatim as every row's roster version.
    if not isinstance(roster_version, int) or isinstance(roster_version, bool):
        raise RosterError(
            f"roster file at {path}: 'roster_version' must be an integer, "
            f"got {roster_version!r}"
        )

    raw_entries = raw["entries"]
    if not isinstance(raw_entries, dict):
        raise RosterError(f"roster file at {path}: 'entries' must be an object")

    entries: dict[str, RosterEntry] = {}
    for entry_id, raw_entry in raw_entries.items():
        entries[entry_id] = _parse_entry(entry_id, raw_entry)

    return RosterFile(roster_version=roster_version, entries=entries)


def _block_at(raw_entry: dict[str, Any], path: str) -> Any:
    """The nested block `path` names, walked from the entry ("" is the entry)."""
    block: Any = raw_entry
    if path:
        for key in path.split("."):
            block = block[key]
    return block


def _require_fields(entry_id: str, path: str, block: Any) -> None:
    """Raise `RosterError` unless `block` is an object holding `path`'s fields.

    A missing field is reported by its full dotted path
    (`server_flags.sampler.top_p`), so the operator editing the roster file
    is told where to look rather than which key some later `[...]` lookup
    happened to raise on.
    """
    where = f"{path!r} " if path else ""
    if not isinstance(block, dict):
        raise RosterError(f"roster entry {entry_id!r}: {where}must be an object")

    missing = [key for key in REQUIRED_FIELDS[path] if key not in block]
    if missing:
        prefix = f"{path}." if path else ""
        raise RosterError(
            f"roster entry {entry_id!r} is missing required field(s): "
            f"{', '.join(prefix + key for key in missing)}"
        )


def _parse_entry(entry_id: str, raw_entry: Any) -> RosterEntry:
    if not isinstance(raw_entry, dict):
        raise RosterError(f"roster entry {entry_id!r} must be an object")

    # Outermost first: `REQUIRED_FIELDS` is ordered parents-before-children,
    # so a block is proven present and object-shaped before its own required
    # fields are walked and `_block_at` reaches into it.
    for path in REQUIRED_FIELDS:
        _require_fields(entry_id, path, _block_at(raw_entry, path))

    sha256 = raw_entry["sha256"]
    if not isinstance(sha256, str) or _SHA256_PATTERN.fullmatch(sha256) is None:
        raise RosterError(
            f"roster entry {entry_id!r}: 'sha256' must be 64 lowercase hex "
            f"characters, got {sha256!r}"
        )

    raw_architecture = raw_entry["architecture"]
    return RosterEntry(
        entry_id=entry_id,
        repo=raw_entry["repo"],
        revision=raw_entry["revision"],
        file=raw_entry["file"],
        display_id=raw_entry["display_id"],
        quant=raw_entry["quant"],
        sha256=sha256,
        architecture=Architecture(
            kind=raw_architecture["kind"],
            expert_count=raw_architecture["expert_count"],
            active_params_b=raw_architecture["active_params_b"],
        ),
        server_flags=raw_entry["server_flags"],
        validated_host=raw_entry["validated_host"],
    )


def resolve_entry(roster: RosterFile, entry_id: str) -> RosterEntry:
    """Return the entry named `entry_id`, or raise `RosterError` naming it."""
    try:
        return roster.entries[entry_id]
    except KeyError:
        raise RosterError(
            f"unknown roster entry id: {entry_id!r} "
            f"(known ids: {', '.join(sorted(roster.entries)) or '<none>'})"
        ) from None


def validate_host_fit(entry: RosterEntry, n_cpu_moe: int | None) -> None:
    """Raise `RosterError` when `n_cpu_moe` cannot be applied to `entry`.

    A dense entry never accepts a host `n_cpu_moe` value. An MoE entry
    accepts any value at or below its `architecture.expert_count`; a `None`
    value is always accepted (a caller decision outside this rule's scope).
    """
    if n_cpu_moe is None:
        return

    if entry.architecture.kind == "dense":
        raise RosterError(
            f"roster entry {entry.entry_id!r} is dense: it cannot take a "
            f"host n_cpu_moe value ({n_cpu_moe!r} given)"
        )

    if n_cpu_moe > entry.architecture.expert_count:
        raise RosterError(
            f"roster entry {entry.entry_id!r} has expert_count="
            f"{entry.architecture.expert_count}: host n_cpu_moe={n_cpu_moe} "
            "exceeds that ceiling"
        )


def build_flags_from_entry(entry: RosterEntry) -> list[str]:
    """Build the model-intrinsic flag list `entry.server_flags` describes.

    Same ordered-list shape `server.build_flags` returns, minus the flags
    that are host settings rather than roster data: the model path (`-m`),
    `--n-cpu-moe`, `-t`/threads, and `--host`/`--port`. Phase 2 combines this
    list with those host-supplied flags; this module does not import
    `server.py` to build them itself.
    """
    flags = entry.server_flags
    sampler = flags["sampler"]
    result = [
        "-ngl",
        str(flags["n_gpu_layers"]),
        "-c",
        str(flags["context_size"]),
        "-fa",
        str(flags["flash_attention"]),
    ]
    if flags["jinja"]:
        result.append("--jinja")
    result += [
        "-np",
        str(flags["parallel_slots"]),
        "--load-mode",
        str(flags["load_mode"]),
        "--temp",
        str(sampler["temperature"]),
        "--top-p",
        str(sampler["top_p"]),
        "--top-k",
        str(sampler["top_k"]),
        "--min-p",
        str(sampler["min_p"]),
        "--presence-penalty",
        str(sampler["presence_penalty"]),
    ]
    return result
