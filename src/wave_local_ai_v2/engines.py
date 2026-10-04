"""The engine registry: one tracked entry per inference engine.

An engine is half of the stack a local row measures, so it is data rather than
module constants: how its build is read at run time (a live probe, never a
constant), the endpoints it serves, whether this harness spawns it or attaches
to it, where it listens, how its reasoning switch is spelled, how its launch
configuration is made path-free before it is hashed, and the configuration
defaults it applies, each marked as declared by this project or reported by
the engine itself (Methodology 22: an engine whose defaults are unrecorded
cannot be compared against one whose are).

`load_registry` refuses an entry missing any of these, naming the field, the
way `roster.load_roster` refuses an incomplete model entry. The entry id is
the entry's key, the roster's own convention.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, TypedDict

from wave_local_ai_v2 import build_probe, prompt_variants

DEFAULT_REGISTRY_PATH = "aidd_docs/roster/engines.json"

LIFECYCLE_SPAWNED = "spawned"
LIFECYCLE_ATTACHED = "attached"
LIFECYCLES = frozenset({LIFECYCLE_SPAWNED, LIFECYCLE_ATTACHED})

# How a configuration default was obtained: stated by this project (read off
# the engine's documentation for its pinned build), or reported by the
# running engine itself.
SOURCE_DECLARED = "declared"
SOURCE_ENGINE_REPORTED = "engine_reported"
DEFAULT_SOURCES = frozenset({SOURCE_DECLARED, SOURCE_ENGINE_REPORTED})

# An engine that offers no reasoning switch at all declares this. Nothing can
# carry a roster entry's object control to it: `local_client.thinking_kwargs`
# refuses such an entry under `thinking_policy: "disabled"`, and the candidate
# gate refuses a candidate declaring one on it.
THINKING_SWITCH_NONE = "none"

# The value `-m` is replaced with before the configuration hash is taken, so
# two model directories holding the same roster entry hash identically.
ROSTER_REFERENCE_PREFIX = "roster:"

# Every live build probe an entry may name. A new engine adds its own probe
# here; an entry naming an unknown one is refused at load.
_BUILD_PROBES: dict[str, Callable[[Path], str | None]] = {
    # Looked up at call time, so the probe stays the one `build_probe` module
    # attribute every caller (and every test stub) already goes through.
    "version_flag": lambda server_path: build_probe.probe_build(server_path),
}

# Every required field, keyed by the dotted path of the block that holds it
# ("" is the entry itself), parents first so the outermost gap is named.
REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    "": (
        "reference",
        "build_probe",
        "endpoints",
        "lifecycle",
        "host",
        "default_port",
        "thinking_switch",
        "config_normalisation",
        "configuration_defaults",
        "constraint_mechanisms",
    ),
    "build_probe": ("method",),
    "endpoints": ("chat", "health", "prompt_rendering", "template_source"),
    "config_normalisation": ("model_path_flag", "location_flags"),
}

# The three keys every configuration default carries.
DEFAULT_FIELDS = ("value", "source", "read_from")


class EngineFicheFields(TypedDict):
    """The three engine fields a fiche carries for one launch."""

    engine_id: str
    engine_build: str | None
    engine_config_hash: str


class EngineRegistryError(ValueError):
    """Raised when the engine registry, or one of its entries, is malformed."""


@dataclass(frozen=True)
class EngineEntry:
    """One registered engine, parsed and checked."""

    engine_id: str
    reference: bool
    build_probe_method: str
    endpoints: dict[str, str]
    lifecycle: str
    host: str
    default_port: int
    # `THINKING_SWITCH_NONE`, or the request field a roster entry's control is
    # carried in (llama.cpp: `chat_template_kwargs`).
    thinking_switch: str | dict[str, str]
    model_path_flag: str
    location_flags: tuple[str, ...]
    configuration_defaults: dict[str, dict[str, Any]]
    # The output-constraint mechanisms the engine supports, each mapped to
    # the request field that carries a constraint in it (llama.cpp: `gbnf`
    # in `grammar`). Empty: the engine declares none, and no campaign may pair
    # it with a constraining variant.
    constraint_mechanisms: dict[str, str]


@dataclass(frozen=True)
class EngineRegistry:
    registry_version: int
    entries: dict[str, EngineEntry]


def load_registry(path: Path) -> EngineRegistry:
    """Parse `path`, refusing any structurally incomplete entry by name."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise EngineRegistryError(
            f"engine registry not readable at {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise EngineRegistryError(
            f"engine registry at {path} is not valid JSON: {exc}"
        ) from exc

    if (
        not isinstance(raw, dict)
        or "registry_version" not in raw
        or "engines" not in raw
    ):
        raise EngineRegistryError(
            f"engine registry at {path} must be an object with "
            "'registry_version' and 'engines'"
        )
    version = raw["registry_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise EngineRegistryError(
            f"engine registry at {path}: 'registry_version' must be an integer, "
            f"got {version!r}"
        )
    raw_entries = raw["engines"]
    if not isinstance(raw_entries, dict) or not raw_entries:
        raise EngineRegistryError(
            f"engine registry at {path}: 'engines' must be a non-empty object"
        )

    entries = {
        engine_id: _parse_entry(engine_id, raw_entry)
        for engine_id, raw_entry in raw_entries.items()
    }
    references = sorted(e.engine_id for e in entries.values() if e.reference)
    if len(references) != 1:
        raise EngineRegistryError(
            f"engine registry at {path} must declare exactly one reference "
            f"engine, found {references or 'none'}"
        )
    return EngineRegistry(registry_version=version, entries=entries)


def _require_fields(engine_id: str, path: str, block: Any) -> None:
    where = f"{path!r} " if path else ""
    if not isinstance(block, dict):
        raise EngineRegistryError(
            f"engine entry {engine_id!r}: {where}must be an object"
        )
    missing = [key for key in REQUIRED_FIELDS[path] if key not in block]
    if missing:
        prefix = f"{path}." if path else ""
        raise EngineRegistryError(
            f"engine entry {engine_id!r} is missing required field(s): "
            f"{', '.join(prefix + key for key in missing)}"
        )


def _malformed(
    engine_id: str, field: str, expected: str, value: Any
) -> EngineRegistryError:
    return EngineRegistryError(
        f"engine entry {engine_id!r}: {field!r} must be {expected}, got {value!r}"
    )


def _text(engine_id: str, field: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _malformed(engine_id, field, "a non-empty string", value)
    return value


def _parse_entry(engine_id: str, raw: Any) -> EngineEntry:
    # Outermost first: `REQUIRED_FIELDS` lists the entry ("") before its
    # blocks, so a missing block is named as itself.
    for path in REQUIRED_FIELDS:
        _require_fields(engine_id, path, raw[path] if path else raw)

    if not isinstance(raw["reference"], bool):
        raise _malformed(engine_id, "reference", "a boolean", raw["reference"])
    method = raw["build_probe"]["method"]
    if method not in _BUILD_PROBES:
        raise _malformed(
            engine_id, "build_probe.method", f"one of {sorted(_BUILD_PROBES)}", method
        )
    endpoints = {
        key: _text(engine_id, f"endpoints.{key}", raw["endpoints"][key])
        for key in REQUIRED_FIELDS["endpoints"]
    }
    lifecycle = raw["lifecycle"]
    if lifecycle not in LIFECYCLES:
        raise _malformed(
            engine_id, "lifecycle", f"one of {sorted(LIFECYCLES)}", lifecycle
        )
    port = raw["default_port"]
    if not isinstance(port, int) or isinstance(port, bool) or not 0 < port < 65536:
        raise _malformed(engine_id, "default_port", "a TCP port number", port)

    normalisation = raw["config_normalisation"]
    location_flags = normalisation["location_flags"]
    if not isinstance(location_flags, list) or not all(
        isinstance(flag, str) and flag for flag in location_flags
    ):
        raise _malformed(
            engine_id,
            "config_normalisation.location_flags",
            "a list of flag spellings",
            location_flags,
        )

    return EngineEntry(
        engine_id=engine_id,
        reference=raw["reference"],
        build_probe_method=method,
        endpoints=endpoints,
        lifecycle=lifecycle,
        host=_text(engine_id, "host", raw["host"]),
        default_port=port,
        thinking_switch=_parse_thinking_switch(engine_id, raw["thinking_switch"]),
        model_path_flag=_text(
            engine_id,
            "config_normalisation.model_path_flag",
            normalisation["model_path_flag"],
        ),
        location_flags=tuple(location_flags),
        configuration_defaults=_parse_defaults(
            engine_id, raw["configuration_defaults"]
        ),
        constraint_mechanisms=_parse_mechanisms(
            engine_id, raw["constraint_mechanisms"]
        ),
    )


def _parse_mechanisms(engine_id: str, mechanisms: Any) -> dict[str, str]:
    """`{mechanism: {request_field, read_from}}` as `{mechanism: request_field}`.

    `{}` declares none. Each mechanism must be one a variant can express
    (`prompt_variants.CONSTRAINT_MECHANISMS`) and name where it was read.
    """
    if not isinstance(mechanisms, dict):
        raise _malformed(
            engine_id, "constraint_mechanisms", "an object ({} for none)", mechanisms
        )
    parsed: dict[str, str] = {}
    for mechanism, block in mechanisms.items():
        field = f"constraint_mechanisms.{mechanism}"
        if mechanism not in prompt_variants.CONSTRAINT_MECHANISMS:
            raise _malformed(
                engine_id,
                "constraint_mechanisms",
                f"keyed by mechanisms in {sorted(prompt_variants.CONSTRAINT_MECHANISMS)}",
                mechanism,
            )
        if not isinstance(block, dict) or set(block) != {"request_field", "read_from"}:
            raise _malformed(engine_id, field, "{'request_field', 'read_from'}", block)
        _text(engine_id, f"{field}.read_from", block["read_from"])
        parsed[mechanism] = _text(
            engine_id, f"{field}.request_field", block["request_field"]
        )
    return parsed


def _parse_thinking_switch(engine_id: str, switch: Any) -> str | dict[str, str]:
    if switch == THINKING_SWITCH_NONE:
        return THINKING_SWITCH_NONE
    if (
        isinstance(switch, dict)
        and set(switch) == {"request_field"}
        and isinstance(switch["request_field"], str)
        and switch["request_field"]
    ):
        return {"request_field": switch["request_field"]}
    raise _malformed(
        engine_id,
        "thinking_switch",
        f"{THINKING_SWITCH_NONE!r} or an object holding only 'request_field'",
        switch,
    )


def _parse_defaults(engine_id: str, defaults: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(defaults, dict) or not defaults:
        raise _malformed(
            engine_id, "configuration_defaults", "a non-empty object", defaults
        )
    parsed: dict[str, dict[str, Any]] = {}
    for name, default in defaults.items():
        field = f"configuration_defaults.{name}"
        if not isinstance(default, dict):
            raise _malformed(engine_id, field, "an object", default)
        missing = [key for key in DEFAULT_FIELDS if key not in default]
        if missing:
            raise EngineRegistryError(
                f"engine entry {engine_id!r} is missing required field(s): "
                f"{', '.join(f'{field}.{key}' for key in missing)}"
            )
        if default["source"] not in DEFAULT_SOURCES:
            raise _malformed(
                engine_id,
                f"{field}.source",
                f"one of {sorted(DEFAULT_SOURCES)}",
                default["source"],
            )
        _text(engine_id, f"{field}.read_from", default["read_from"])
        parsed[name] = dict(default)
    return parsed


def resolve_engine(registry: EngineRegistry, engine_id: str) -> EngineEntry:
    """The entry named `engine_id`, or `EngineRegistryError` naming it."""
    try:
        return registry.entries[engine_id]
    except KeyError:
        raise EngineRegistryError(
            f"unknown engine id: {engine_id!r} "
            f"(registered: {', '.join(sorted(registry.entries))})"
        ) from None


def reference_engine(registry: EngineRegistry) -> EngineEntry:
    """The one entry the registry declares as the reference engine."""
    return next(entry for entry in registry.entries.values() if entry.reference)


@lru_cache(maxsize=1)
def tracked_registry() -> EngineRegistry:
    """The tracked registry at its default path, loaded once per process."""
    return load_registry(Path(DEFAULT_REGISTRY_PATH))


def tracked_reference_engine() -> EngineEntry:
    """The tracked registry's reference engine (llama.cpp)."""
    return reference_engine(tracked_registry())


def registered_engine_ids() -> frozenset[str]:
    """Every engine id the tracked registry holds: what the writer gate accepts."""
    return frozenset(tracked_registry().entries)


def base_url(engine: EngineEntry) -> str:
    """Where a run reaches `engine`: its declared host on its default port."""
    return f"http://{engine.host}:{engine.default_port}"


def probe_build(engine: EngineEntry, server_path: Path) -> str | None:
    """`engine`'s build as the binary reports it, through the entry's probe."""
    return _BUILD_PROBES[engine.build_probe_method](server_path)


def normalise_config(
    engine: EngineEntry, flags: Sequence[str], roster_entry_id: str
) -> list[str]:
    """`flags` with no filesystem path and no host or port in them.

    The model path flag's value becomes `roster:<roster_entry_id>` (the
    pointer every row already carries), and each location flag is dropped
    with its value: where the engine listens is not part of what it was asked
    to compute (Methodology 14). Raises when the model path flag is absent,
    because a list the path was never removed from cannot be called path-free.
    """
    result: list[str] = []
    replaced = False
    index = 0
    while index < len(flags):
        flag = flags[index]
        if flag in engine.location_flags:
            index += 2
            continue
        if flag == engine.model_path_flag and index + 1 < len(flags):
            result += [flag, f"{ROSTER_REFERENCE_PREFIX}{roster_entry_id}"]
            replaced = True
            index += 2
            continue
        result.append(flag)
        index += 1
    if not replaced:
        raise EngineRegistryError(
            f"engine {engine.engine_id!r}: launch flags carry no "
            f"{engine.model_path_flag!r} value to normalise"
        )
    return result


def config_hash(engine: EngineEntry, flags: Sequence[str], roster_entry_id: str) -> str:
    """SHA-256 over the JSON of `normalise_config`'s path-free flag list."""
    payload = json.dumps(normalise_config(engine, flags, roster_entry_id))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fiche_fields(
    engine: EngineEntry, server_path: Path, flags: Sequence[str], roster_entry_id: str
) -> EngineFicheFields:
    """The three engine fields a fiche carries for one launch.

    The build is probed live; an unreadable build is an explicit `None`,
    never an assumed value.
    """
    return EngineFicheFields(
        engine_id=engine.engine_id,
        engine_build=probe_build(engine, server_path),
        engine_config_hash=config_hash(engine, flags, roster_entry_id),
    )
