"""The model roster: a tracked, versioned file pinning every model's identity
and flag set.

`load_roster` refuses (raises `RosterError`) any entry missing a required
field, `sha256` included, so an incomplete entry can never be resolved.
`resolve_entry` and `validate_host_fit` are the two gates a caller passes
through before launching a model: an unknown id, a dense entry whose resolved
run profile (`profiles.py`) carries an `n_cpu_moe`, or an MoE entry whose
`n_cpu_moe` exceeds its expert count are all refused here rather than surfacing as a confusing llama-server error
downstream.

Deliberately does not import `server.py`: phase 2 imports this module from
`server.py`, not the reverse, so the two never form a cycle.
"""

from __future__ import annotations

import dataclasses
import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Any

from wave_local_ai_v2 import machines

if TYPE_CHECKING:
    from wave_local_ai_v2.profiles import ResolvedProfile

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
}

# The minimum requirements every entry declares per compute mode (Methodology
# 21), each a `{value, source, read_from}` fact in decimal GB (10^9 bytes):
# total system RAM, VRAM the GPU can allocate (`gpu` only: a `cpu_only` run
# puts no layer on it) and free disk on the models volume (checked only when
# the weights are not on disk yet). `preflight.py` checks them before the
# weights are looked for or any process starts.
REQUIREMENTS_BY_MODE: dict[str, tuple[str, ...]] = {
    machines.COMPUTE_MODE_GPU: ("ram_gb", "vram_gb", "disk_gb"),
    machines.COMPUTE_MODE_CPU_ONLY: ("ram_gb", "disk_gb"),
}

_SHA256_PATTERN = re.compile(r"[0-9a-f]{64}")

# The one `thinking_control` value that is not a request-argument object: the
# model does not reason, so `thinking_policy: disabled` has nothing to send.
# The declaration is the entry's to justify; a live generation is where it is
# checked, not here.
THINKING_CONTROL_NONE = "none"

# Model family: the attribute judge independence is enforced on (a judge never
# scores output from its own family) and the roster composition rule counts.
# Declared here rather than in `judge.py` because it is an identity fact about
# a model, the same class of fact as the rest of this module. A family is the
# vendor lineage, not the model line: Gemma is `google`, Ministral is
# `mistral`, Granite is `ibm`, LFM2 is `liquid`, Phi is `microsoft`; the
# entry's `display_id` keeps the model line visible.
FAMILY_QWEN = "qwen"
FAMILY_MISTRAL = "mistral"
FAMILY_GOOGLE = "google"
FAMILY_IBM = "ibm"
FAMILY_LIQUID = "liquid"
FAMILY_MICROSOFT = "microsoft"
KNOWN_FAMILIES: frozenset[str] = frozenset(
    {
        FAMILY_QWEN,
        FAMILY_MISTRAL,
        FAMILY_GOOGLE,
        FAMILY_IBM,
        FAMILY_LIQUID,
        FAMILY_MICROSOFT,
    }
)

# The languages a roster entry's language claim can name: the suites' own
# EN/FR/DE set, never a wider one the suites cannot test.
CLAIMABLE_LANGUAGES: tuple[str, ...] = ("en", "fr", "de")

# The size classes Methodology 13's composition rule counts families in, in
# order, each with the lowest total parameter count it holds (owner answer
# Q10 (a)): below 1B is ~0.5B, 1B to below 3B is ~2B, 3B to below 6B is ~4B,
# 6B and up is ~8B-and-up. Banded on total parameters, never on bytes on
# disk: the bytes are the footprint published beside the class, and whether
# an entry fits a machine is the machine epic's profiles' to say. The edges
# are revisable after the first full-roster run; moving one is a value change
# here and a re-class of the entries it crosses, never a rewrite of the
# composition check, which reads this table.
SIZE_CLASS_BANDS: tuple[tuple[str, int], ...] = (
    ("~0.5B", 0),
    ("~2B", 1_000_000_000),
    ("~4B", 3_000_000_000),
    ("~8B-and-up", 6_000_000_000),
)
SIZE_CLASSES: tuple[str, ...] = tuple(name for name, _ in SIZE_CLASS_BANDS)


def size_class_for(total_params: int) -> str:
    """The size class whose band holds `total_params`."""
    for name, lower_edge in reversed(SIZE_CLASS_BANDS):
        if total_params >= lower_edge:
            return name
    raise ValueError(f"total_params must not be negative, got {total_params!r}")


# Keyed by the literal dated model id, never by `mistral_client.MODEL` /
# `google_client.MODEL` -- same rule and same reason as
# `cost.MISTRAL_PRICE_TABLE`'s own comment: keying by the variable would make
# this mapping unfalsifiable and let a model rotation inherit the retired
# model's family, silently disabling the independence guard. This module does
# not import the client modules; the ids are written out.
MODEL_FAMILIES: dict[str, str] = {
    "Qwen3.6-35B-A3B": FAMILY_QWEN,
    "mistral-small-2603": FAMILY_MISTRAL,
    "gemini-3.5-flash-lite": FAMILY_GOOGLE,
}


class RosterError(ValueError):
    """Raised when the roster file, an entry, or a host-fit check is invalid."""


@dataclass(frozen=True)
class Architecture:
    """A roster entry's model-architecture facts, used to validate host fit."""

    kind: str
    expert_count: int
    active_params_b: float
    # Every parameter the file holds, summed over its tensors as the GGUF
    # header states them: the figure the entry's size class is banded on.
    # Optional at load for the reason `RosterEntry.family` is; the
    # composition check names an entry without it.
    total_params: int | None = None


@dataclass(frozen=True)
class Licence:
    """The terms a roster entry's weights ship under, as read on a given day.

    Terms move, so the entry says when and where they were read, the same
    discipline Methodology 16 applies to a list price.
    """

    # SPDX identifier where one exists.
    licence_id: str
    # Whether the terms permit commercial use on a client's own machine.
    client_commercial_use: bool
    read_on: date
    # The licence or model card the terms were read from, at the entry's
    # revision.
    source_url: str


@dataclass(frozen=True)
class LanguageClaim:
    """Which of EN, FR and DE the vendor states the model supports.

    A claim, never a score: only the roster file writes it, no suite result
    does, and a suite row contradicting it leaves it in place, since that
    contradiction is itself a finding about the model.
    """

    # The subset of `CLAIMABLE_LANGUAGES` the source names, possibly empty:
    # a source claiming "many languages" without naming one names none.
    languages: tuple[str, ...]
    source_url: str
    read_on: date
    # The source's own wording on language support, verbatim, or `None` when
    # it has none.
    statement: str | None


@dataclass(frozen=True)
class RosterEntry:
    """One roster entry: model identity and its model-intrinsic flag set.

    The host-fitted values (thread count, `--n-cpu-moe`) are not roster data:
    they live in the run profile of each (entry x machine x mode) triple
    (`profiles.py`).
    """

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
    # The model's family, when the roster file carries one. Optional and
    # deliberately absent from REQUIRED_FIELDS: the shipped roster is not
    # edited by the increment that introduced this, so every existing entry
    # must still load and `roster_version` must not move -- published rows and
    # the reference-bundle test compare against it. `family_of` prefers this
    # value when it is there and falls back to `MODEL_FAMILIES` until
    # Methodology 13's roster carries one.
    family: str | None = None
    # The request arguments that disable reasoning under this entry's own chat
    # template (merged into both the `/apply-template` and the chat request),
    # `THINKING_CONTROL_NONE` for a model that does not reason, or `None` when
    # the entry declares nothing -- which `local_client.thinking_kwargs`
    # refuses under `thinking_policy: disabled` rather than guessing a
    # spelling. Optional for the same reason `family` is: a constructed entry
    # without it must still load so that refusal can name it.
    thinking_control: dict[str, Any] | str | None = None
    # The licence block and the vendor's language claim, when the roster file
    # carries them. Optional on the entry for the reason `family` is; the
    # shipped file carries both on every entry, which its own test asserts.
    licence: Licence | None = None
    language_claim: LanguageClaim | None = None
    # One of `SIZE_CLASSES`, and the GGUF's size on disk in bytes: the class
    # the composition rule counts the entry in, and the footprint published
    # beside it. Optional at load so the composition check can name an entry
    # that omits them rather than the loader refusing it first.
    size_class: str | None = None
    bytes_on_disk: int | None = None
    # compute mode -> requirement name -> `{value, source, read_from}`, per
    # `REQUIREMENTS_BY_MODE`. Required by `load_roster` (a run reads only
    # roster files) and optional to `parse_entry`, whose candidate has no
    # measured peak to calibrate a minimum from before its first run.
    requirements: dict[str, dict[str, dict[str, Any]]] | None = None


@dataclass(frozen=True)
class SizeClassDeclaration:
    """What the roster states about one size class, beside its entries.

    The entries say which families and architectures a class holds; only the
    roster's author can say whether a single-family class is a deliberate
    ladder and whether a MoE was looked for, so a blank is never read as
    either.
    """

    # The class is published as a single-family ladder: a comparison of one
    # vendor's line, not of the market.
    single_family_ladder: bool
    # A MoE candidate was searched for in this class.
    moe_sought: bool
    # The entry id of the MoE representing the class, or `None`.
    moe_entry: str | None
    # Why no MoE represents the class, or `None`.
    moe_absent_reason: str | None


@dataclass(frozen=True)
class RosterFile:
    """A parsed roster: its version, every entry keyed by entry id, and the
    per-class declarations keyed by size class (empty when it carries none)."""

    roster_version: int
    entries: dict[str, RosterEntry]
    size_classes: dict[str, SizeClassDeclaration] = dataclasses.field(
        default_factory=dict
    )


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
        if isinstance(raw_entry, dict) and "requirements" not in raw_entry:
            raise RosterError(
                f"roster entry {entry_id!r} is missing required field(s): requirements"
            )

    return RosterFile(
        roster_version=roster_version,
        entries=entries,
        size_classes=_parse_size_classes(path, raw.get("size_classes", {})),
    )


def _parse_size_classes(path: Path, raw_block: Any) -> dict[str, SizeClassDeclaration]:
    """The per-class declarations, refusing a malformed one naming its class.

    Shape only: whether a declaration agrees with the entries of its class is
    the composition check's to say, where it is named rather than refused.
    """
    if not isinstance(raw_block, dict):
        raise RosterError(f"roster file at {path}: 'size_classes' must be an object")
    declarations: dict[str, SizeClassDeclaration] = {}
    for size_class, raw in raw_block.items():
        where = f"roster file at {path}: size class {size_class!r}"
        if size_class not in SIZE_CLASSES:
            raise RosterError(
                f"{where} is not a size class ({', '.join(SIZE_CLASSES)})"
            )
        fields = (
            "single_family_ladder",
            "moe_sought",
            "moe_entry",
            "moe_absent_reason",
        )
        if not isinstance(raw, dict):
            raise RosterError(f"{where} must be an object")
        missing = [key for key in fields if key not in raw]
        if missing:
            raise RosterError(f"{where} is missing field(s): {', '.join(missing)}")
        for key in ("single_family_ladder", "moe_sought"):
            if not isinstance(raw[key], bool):
                raise RosterError(
                    f"{where}: {key!r} must be a boolean, got {raw[key]!r}"
                )
        for key in ("moe_entry", "moe_absent_reason"):
            value = raw[key]
            if value is not None and (not isinstance(value, str) or not value.strip()):
                raise RosterError(
                    f"{where}: {key!r} must be null or a non-empty string, "
                    f"got {value!r}"
                )
        declarations[size_class] = SizeClassDeclaration(
            single_family_ladder=raw["single_family_ladder"],
            moe_sought=raw["moe_sought"],
            moe_entry=raw["moe_entry"],
            moe_absent_reason=raw["moe_absent_reason"],
        )
    return declarations


def parse_entry(entry_id: str, raw_entry: Any) -> RosterEntry:
    """Parse one entry under exactly the rules `load_roster` applies to the file.

    For a caller holding an entry that is not in a roster file yet -- the
    candidate gate's pass record -- so "it would load" is proven by the same
    code, not by a copy of it.
    """
    return _parse_entry(entry_id, raw_entry)


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

    family = raw_entry.get("family")
    if "family" in raw_entry and (
        not isinstance(family, str) or family not in KNOWN_FAMILIES
    ):
        raise RosterError(
            f"roster entry {entry_id!r}: 'family' {family!r} is not a known "
            f"family ({', '.join(sorted(KNOWN_FAMILIES))})"
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
            total_params=_optional_count(
                entry_id, raw_architecture, "total_params", "architecture."
            ),
        ),
        server_flags=raw_entry["server_flags"],
        family=family,
        thinking_control=_parse_thinking_control(entry_id, raw_entry),
        licence=_parse_licence(entry_id, raw_entry),
        language_claim=_parse_language_claim(entry_id, raw_entry),
        size_class=_parse_size_class(entry_id, raw_entry),
        bytes_on_disk=_optional_count(entry_id, raw_entry, "bytes_on_disk"),
        requirements=_parse_requirements(entry_id, raw_entry),
    )


def _parse_requirements(
    entry_id: str, raw_entry: dict[str, Any]
) -> dict[str, dict[str, dict[str, Any]]] | None:
    """The declared minimums per compute mode, or `None` when absent.

    Every mode of `REQUIREMENTS_BY_MODE` and every requirement of each is
    required, and nothing else is accepted (a `vram_gb` under `cpu_only` is
    refused, not ignored). A `declared` value is a positive number; a
    `not_yet_declared` one is `null` and names what it awaits.
    """
    if "requirements" not in raw_entry:
        return None
    block = raw_entry["requirements"]
    if not isinstance(block, dict):
        raise RosterError(
            f"roster entry {entry_id!r}: 'requirements' must be an object"
        )
    _require_exact_keys(entry_id, "requirements", block, tuple(REQUIREMENTS_BY_MODE))
    parsed: dict[str, dict[str, dict[str, Any]]] = {}
    for mode, names in REQUIREMENTS_BY_MODE.items():
        where = f"requirements.{mode}"
        mode_block = block[mode]
        if not isinstance(mode_block, dict):
            raise RosterError(f"roster entry {entry_id!r}: {where!r} must be an object")
        _require_exact_keys(entry_id, where, mode_block, names)
        parsed[mode] = {
            name: _requirement_fact(entry_id, f"{where}.{name}", mode_block[name])
            for name in names
        }
    return parsed


def _require_exact_keys(
    entry_id: str, where: str, block: dict[str, Any], names: tuple[str, ...]
) -> None:
    missing = [name for name in names if name not in block]
    if missing:
        raise RosterError(
            f"roster entry {entry_id!r} is missing required field(s): "
            f"{', '.join(f'{where}.{name}' for name in missing)}"
        )
    unknown = sorted(set(block) - set(names))
    if unknown:
        raise RosterError(
            f"roster entry {entry_id!r}: {where!r} declares unknown field(s) "
            f"{', '.join(unknown)} (expected: {', '.join(names)})"
        )


def _requirement_fact(entry_id: str, where: str, fact: Any) -> dict[str, Any]:
    if not isinstance(fact, dict) or set(fact) != set(machines.FACT_FIELDS):
        raise _malformed(
            entry_id, where, "an object with exactly value, source, read_from", fact
        )
    read_from = fact["read_from"]
    if not isinstance(read_from, str) or not read_from.strip():
        raise _malformed(
            entry_id, f"{where}.read_from", "a non-empty string", read_from
        )
    value = fact["value"]
    if fact["source"] == machines.SOURCE_DECLARED:
        if not isinstance(value, int | float) or isinstance(value, bool) or value <= 0:
            raise _malformed(entry_id, f"{where}.value", "a positive number", value)
    elif fact["source"] == machines.SOURCE_NOT_YET_DECLARED:
        if value is not None:
            raise _malformed(
                entry_id,
                f"{where}.value",
                "null while not_yet_declared (a minimum nobody calibrated is "
                "never published)",
                value,
            )
    else:
        raise _malformed(
            entry_id,
            f"{where}.source",
            f"one of {sorted(machines.FACT_SOURCES)}",
            fact["source"],
        )
    return dict(fact)


def _parse_size_class(entry_id: str, raw_entry: dict[str, Any]) -> str | None:
    """The entry's declared size class, or `None` when it declares none."""
    if "size_class" not in raw_entry:
        return None
    size_class = raw_entry["size_class"]
    if size_class not in SIZE_CLASSES:
        raise _malformed(
            entry_id, "size_class", f"one of {', '.join(SIZE_CLASSES)}", size_class
        )
    return str(size_class)


def _optional_count(
    entry_id: str, block: dict[str, Any], key: str, prefix: str = ""
) -> int | None:
    """`block[key]` as a positive integer, or `None` when the key is absent.

    A float is refused rather than rounded: both figures are read off the
    file, where they are exact.
    """
    if key not in block:
        return None
    value = block[key]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise _malformed(entry_id, prefix + key, "a positive integer", value)
    return value


def _optional_block(
    entry_id: str, raw_entry: dict[str, Any], name: str, fields: tuple[str, ...]
) -> dict[str, Any] | None:
    """The optional block `name` as an object holding `fields`, or `None`."""
    if name not in raw_entry:
        return None
    block = raw_entry[name]
    if not isinstance(block, dict):
        raise RosterError(f"roster entry {entry_id!r}: {name!r} must be an object")
    missing = [key for key in fields if key not in block]
    if missing:
        raise RosterError(
            f"roster entry {entry_id!r} is missing required field(s): "
            f"{', '.join(f'{name}.{key}' for key in missing)}"
        )
    return block


def _malformed(entry_id: str, field: str, expected: str, value: Any) -> RosterError:
    return RosterError(
        f"roster entry {entry_id!r}: {field!r} must be {expected}, got {value!r}"
    )


def _text(entry_id: str, field: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _malformed(entry_id, field, "a non-empty string", value)
    return value


def _read_on(entry_id: str, field: str, value: Any) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise _malformed(entry_id, field, "an ISO 8601 date", value) from None


def _parse_licence(entry_id: str, raw_entry: dict[str, Any]) -> Licence | None:
    """The entry's licence block, or `None` when it carries none."""
    block = _optional_block(
        entry_id,
        raw_entry,
        "licence",
        ("id", "client_commercial_use", "read_on", "source_url"),
    )
    if block is None:
        return None
    commercial = block["client_commercial_use"]
    # A "yes" or a 1 is an operator's guess at the terms, not a reading of them.
    if not isinstance(commercial, bool):
        raise _malformed(
            entry_id, "licence.client_commercial_use", "a boolean", commercial
        )
    return Licence(
        licence_id=_text(entry_id, "licence.id", block["id"]),
        client_commercial_use=commercial,
        read_on=_read_on(entry_id, "licence.read_on", block["read_on"]),
        source_url=_text(entry_id, "licence.source_url", block["source_url"]),
    )


def _parse_language_claim(
    entry_id: str, raw_entry: dict[str, Any]
) -> LanguageClaim | None:
    """The entry's language claim, or `None` when it carries none."""
    block = _optional_block(
        entry_id, raw_entry, "language_claim", ("languages", "source_url", "read_on")
    )
    if block is None:
        return None
    languages = block["languages"]
    if (
        not isinstance(languages, list)
        or any(language not in CLAIMABLE_LANGUAGES for language in languages)
        or len(set(languages)) != len(languages)
    ):
        raise _malformed(
            entry_id,
            "language_claim.languages",
            f"a list of distinct values from {', '.join(CLAIMABLE_LANGUAGES)}",
            languages,
        )
    return LanguageClaim(
        languages=tuple(languages),
        source_url=_text(entry_id, "language_claim.source_url", block["source_url"]),
        read_on=_read_on(entry_id, "language_claim.read_on", block["read_on"]),
        statement=(
            _text(entry_id, "language_claim.statement", block["statement"])
            if "statement" in block
            else None
        ),
    )


def _parse_thinking_control(
    entry_id: str, raw_entry: dict[str, Any]
) -> dict[str, Any] | str | None:
    """The entry's declared thinking control, or `None` when it declares none.

    A present key must be `THINKING_CONTROL_NONE` or a non-empty object of
    request arguments. An empty object would send nothing while claiming a
    control, and an explicit `null` is not the same statement as `"none"`;
    both are refused here, naming the field, rather than read as either.
    """
    if "thinking_control" not in raw_entry:
        return None
    control = raw_entry["thinking_control"]
    if control == THINKING_CONTROL_NONE:
        return THINKING_CONTROL_NONE
    if isinstance(control, dict) and control:
        return control
    raise RosterError(
        f"roster entry {entry_id!r}: 'thinking_control' must be "
        f"{THINKING_CONTROL_NONE!r} or a non-empty object of request "
        f"arguments, got {control!r}"
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


def family_of(model_id: str, entry: RosterEntry | None = None) -> str:
    """Resolve `model_id`'s family, preferring `entry`'s own declaration.

    The roster entry is the seam: when Methodology 13's roster file carries a
    `family`, that is what a row reads; until it does, `MODEL_FAMILIES` is the
    in-code fallback. An unknown model is a refusal, never a default -- a
    wrong default silently disables the independence guard a judged row
    depends on, and a silently disabled guard is worse than a failed run.
    """
    if entry is not None and entry.family is not None:
        family = entry.family
        source = f"roster entry {entry.entry_id!r}"
    else:
        family = MODEL_FAMILIES.get(model_id, "")
        source = "the in-code MODEL_FAMILIES declaration"
        if not family:
            raise RosterError(
                f"unknown model family for model id {model_id!r} "
                f"(declared ids: {', '.join(sorted(MODEL_FAMILIES))})"
            )

    if family not in KNOWN_FAMILIES:
        raise RosterError(
            f"model id {model_id!r} resolves to family {family!r} through "
            f"{source}, which is not a known family "
            f"({', '.join(sorted(KNOWN_FAMILIES))})"
        )
    return family


def validate_host_fit(entry: RosterEntry, profile: ResolvedProfile) -> None:
    """Raise `RosterError` when the resolved profile's `n_cpu_moe` cannot be
    applied to `entry`.

    Reads the value the run will launch with: the profile's, or the operator
    override laid over it. A dense entry never accepts an `n_cpu_moe` value.
    An MoE entry accepts any value at or below its `architecture.expert_count`;
    `None` (no `--n-cpu-moe` at all) is always accepted. Under `cpu_only` no
    value is accepted: every layer is already on the CPU, and `--n-cpu-moe 0`
    would mean the opposite (offload no experts), so a supplied value is
    refused naming the mode, never dropped. The registry refuses one declared
    under `cpu_only`, so only an operator override can reach this check.
    """
    n_cpu_moe = profile.n_cpu_moe
    if n_cpu_moe is None:
        return

    if profile.compute_mode == "cpu_only":
        raise RosterError(
            f"roster entry {entry.entry_id!r} runs under compute mode "
            f"'cpu_only': it cannot take an n_cpu_moe value "
            f"({n_cpu_moe!r} given); unset SERVER_N_CPU_MOE"
        )

    if entry.architecture.kind == "dense":
        raise RosterError(
            f"roster entry {entry.entry_id!r} is dense: it cannot take an "
            f"n_cpu_moe value ({n_cpu_moe!r} given, run profile "
            f"{profile.profile_id!r})"
        )

    if n_cpu_moe > entry.architecture.expert_count:
        raise RosterError(
            f"roster entry {entry.entry_id!r} has expert_count="
            f"{entry.architecture.expert_count}: n_cpu_moe={n_cpu_moe} "
            f"(run profile {profile.profile_id!r}) exceeds that ceiling"
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
