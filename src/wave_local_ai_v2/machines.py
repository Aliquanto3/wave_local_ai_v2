"""The declared machine registry: one tracked entry per target machine.

A machine id names a declared **configuration**, not a physical box: a RAM
upgrade or a GPU swap is a new entry with a new id, the way a driver change
already moves a fiche. Every row and every fiche names the machine that
produced it by this id, and the id enters the fiche's hashed projection, so
the facts a fiche cannot capture (memory type and speed, whether a GPU is
present at all, allocatable VRAM) reach the identity by reference.

Each fact is `{value, source, read_from}` under the same honesty discipline as
the energy method labels and the engine registry's defaults: `declared` means
the value was read (from the machine, by the tool `read_from` names, or from
the PRD's own machine definition), and `not_yet_declared` means nobody has
read it yet -- its value is `null` and `read_from` names what it awaits. A
fact is never filled in from memory.

`load_registry` refuses an entry missing any fact, naming it, the way
`roster.load_roster` refuses an incomplete model entry.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_REGISTRY_PATH = "aidd_docs/roster/machines.json"

# The two compute modes a local run is executed under (Methodology 21):
# `gpu` launches the roster entry's own flag set, `cpu_only` puts every layer
# on the CPU as a deliberately declared profile, never as a fallback.
COMPUTE_MODE_GPU = "gpu"
COMPUTE_MODE_CPU_ONLY = "cpu_only"
COMPUTE_MODES: tuple[str, ...] = (COMPUTE_MODE_GPU, COMPUTE_MODE_CPU_ONLY)

SOURCE_DECLARED = "declared"
SOURCE_NOT_YET_DECLARED = "not_yet_declared"
FACT_SOURCES = frozenset({SOURCE_DECLARED, SOURCE_NOT_YET_DECLARED})

# The facts every entry carries, all of which a fiche cannot capture or
# captures only as a label (`platform.processor()` is a family/model/stepping
# string, `ram_gb` carries no type or speed).
REQUIRED_FACTS: tuple[str, ...] = (
    "cpu_model",
    "cpu_cores",
    "cpu_threads",
    "instruction_set_notes",
    "ram_installed_gb",
    "memory_type",
    "memory_rated_speed_mts",
    "memory_configured_speed_mts",
    "memory_channels",
    "gpu_present",
    "gpu_model",
    "vram_nominal_gb",
    "vram_allocatable_gb",
    "os",
)

# The facts a machine declaring no GPU declares absent: `declared` with a
# `null` value, which is a statement ("there is none"), not a gap.
GPU_FACTS: frozenset[str] = frozenset(
    {"gpu_model", "vram_nominal_gb", "vram_allocatable_gb"}
)

FACT_FIELDS: tuple[str, ...] = ("value", "source", "read_from")


class MachineRegistryError(ValueError):
    """Raised when the machine registry, or one of its entries, is malformed."""


@dataclass(frozen=True)
class MachineEntry:
    """One declared machine configuration, parsed and checked."""

    machine_id: str
    description: str
    facts: dict[str, dict[str, Any]]

    @property
    def gpu_present(self) -> bool:
        """Whether this configuration declares a GPU (always declared)."""
        return bool(self.facts["gpu_present"]["value"])


@dataclass(frozen=True)
class MachineRegistry:
    registry_version: int
    entries: dict[str, MachineEntry]


def load_registry(path: Path) -> MachineRegistry:
    """Parse `path`, refusing any structurally incomplete entry by name."""
    try:
        raw: Any = json.loads(path.read_text(encoding="utf-8"))
    except OSError as exc:
        raise MachineRegistryError(
            f"machine registry not readable at {path}: {exc}"
        ) from exc
    except json.JSONDecodeError as exc:
        raise MachineRegistryError(
            f"machine registry at {path} is not valid JSON: {exc}"
        ) from exc

    if (
        not isinstance(raw, dict)
        or "registry_version" not in raw
        or "machines" not in raw
    ):
        raise MachineRegistryError(
            f"machine registry at {path} must be an object with "
            "'registry_version' and 'machines'"
        )
    version = raw["registry_version"]
    if not isinstance(version, int) or isinstance(version, bool):
        raise MachineRegistryError(
            f"machine registry at {path}: 'registry_version' must be an "
            f"integer, got {version!r}"
        )
    raw_entries = raw["machines"]
    if not isinstance(raw_entries, dict) or not raw_entries:
        raise MachineRegistryError(
            f"machine registry at {path}: 'machines' must be a non-empty object"
        )
    entries = {
        machine_id: _parse_entry(machine_id, raw_entry)
        for machine_id, raw_entry in raw_entries.items()
    }
    return MachineRegistry(registry_version=version, entries=entries)


def _parse_entry(machine_id: str, raw: Any) -> MachineEntry:
    if not isinstance(raw, dict):
        raise MachineRegistryError(f"machine entry {machine_id!r} must be an object")
    missing = [key for key in ("description", "facts") if key not in raw]
    if missing:
        raise MachineRegistryError(
            f"machine entry {machine_id!r} is missing required field(s): "
            f"{', '.join(missing)}"
        )
    description = raw["description"]
    if not isinstance(description, str) or not description.strip():
        raise MachineRegistryError(
            f"machine entry {machine_id!r}: 'description' must be a non-empty string"
        )
    facts = raw["facts"]
    if not isinstance(facts, dict):
        raise MachineRegistryError(
            f"machine entry {machine_id!r}: 'facts' must be an object"
        )
    missing = [key for key in REQUIRED_FACTS if key not in facts]
    if missing:
        raise MachineRegistryError(
            f"machine entry {machine_id!r} is missing required fact(s): "
            f"{', '.join('facts.' + key for key in missing)}"
        )
    for name in REQUIRED_FACTS:
        _check_fact(machine_id, name, facts[name])

    gpu_present = facts["gpu_present"]
    if gpu_present["source"] != SOURCE_DECLARED or not isinstance(
        gpu_present["value"], bool
    ):
        raise MachineRegistryError(
            f"machine entry {machine_id!r}: 'facts.gpu_present' must be a "
            f"declared true or false, got {gpu_present!r}: a run's refusal and "
            "its verdict both depend on it"
        )
    for name in REQUIRED_FACTS:
        fact = facts[name]
        declared_absent = name in GPU_FACTS and not gpu_present["value"]
        if (
            fact["source"] == SOURCE_DECLARED
            and fact["value"] is None
            and not declared_absent
        ):
            raise MachineRegistryError(
                f"machine entry {machine_id!r}: 'facts.{name}' is declared with "
                f"no value; a fact nobody has read is {SOURCE_NOT_YET_DECLARED!r}"
            )
    return MachineEntry(
        machine_id=machine_id,
        description=description,
        facts={name: dict(facts[name]) for name in REQUIRED_FACTS},
    )


def _check_fact(machine_id: str, name: str, fact: Any) -> None:
    where = f"machine entry {machine_id!r}: 'facts.{name}'"
    if not isinstance(fact, dict):
        raise MachineRegistryError(f"{where} must be an object")
    missing = [key for key in FACT_FIELDS if key not in fact]
    if missing:
        raise MachineRegistryError(f"{where} is missing {', '.join(missing)}")
    if fact["source"] not in FACT_SOURCES:
        raise MachineRegistryError(
            f"{where}: 'source' must be one of {sorted(FACT_SOURCES)}, "
            f"got {fact['source']!r}"
        )
    read_from = fact["read_from"]
    if not isinstance(read_from, str) or not read_from.strip():
        raise MachineRegistryError(f"{where}: 'read_from' must be a non-empty string")
    if fact["source"] == SOURCE_NOT_YET_DECLARED and fact["value"] is not None:
        raise MachineRegistryError(
            f"{where} is {SOURCE_NOT_YET_DECLARED!r} but carries a value "
            f"({fact['value']!r}): a value nobody has read is never published"
        )


def resolve_machine(registry: MachineRegistry, machine_id: str) -> MachineEntry:
    """The entry for `machine_id`, or `MachineRegistryError` naming the declared ids."""
    try:
        return registry.entries[machine_id]
    except KeyError:
        raise MachineRegistryError(
            f"machine id {machine_id!r} is not a declared machine "
            f"(declared: {', '.join(sorted(registry.entries))})"
        ) from None


@lru_cache(maxsize=1)
def tracked_registry() -> MachineRegistry:
    """The tracked registry, loaded once per process."""
    return load_registry(Path(DEFAULT_REGISTRY_PATH))


def declared_machine_ids() -> frozenset[str]:
    """Every machine id the tracked registry declares."""
    return frozenset(tracked_registry().entries)


def declares_no_gpu(machine_id: object) -> bool:
    """True only when the tracked registry declares `machine_id` GPU-less.

    An unknown id, an unreadable registry or a non-string id is not a
    declaration of anything, so it is `False`: a GPU field that is null on such
    a fiche stays an unknown value, never a declared absence.
    """
    if not isinstance(machine_id, str):
        return False
    try:
        entry = tracked_registry().entries.get(machine_id)
    except MachineRegistryError:
        return False
    return entry is not None and not entry.gpu_present
