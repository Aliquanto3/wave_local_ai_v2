"""The pre-flight check: a run below its roster entry's declared minimum refuses.

Every roster entry declares, per compute mode, a minimum total RAM, VRAM
(`gpu` only) and free disk (`roster.REQUIREMENTS_BY_MODE`). Each writer calls
`enforce` right after its run profile resolves and before the weights are
looked for, the build is probed or `llama-server` starts, so a machine that
cannot hold a model refuses it without first downloading or loading it.

What the check compares against is what the machine reports: total RAM
(`psutil`), the VRAM it can allocate (the machine registry's declared
`vram_allocatable_gb` where one is declared, else NVML's reported total), and
the free disk on the models volume, only while the weights are not on disk
yet. It tests the declaration, not the machine: nothing verifies that a
declared minimum is right, and a too-low one surfaces as a run that starts and
then fails (stated in `docs/setup.md`).

A refusal names the requirement, the mode, the declared minimum and the
observed value, writes one refusal record (`row_contract.REFUSAL_FIELDS`) to
the machine's own tracked file, and raises; no runtime or quality row is ever
written for it. Nothing is substituted: no smaller quant, no shorter context,
no switch from `gpu` to `cpu_only`. A refused `gpu` run names the `cpu_only`
profile that exists for the same entry and machine, and runs nothing.
"""

from __future__ import annotations

import shutil
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import psutil

from wave_local_ai_v2 import (
    machine_results,
    machines,
    profiles,
    provenance,
    results,
    roster,
    row_contract,
)
from wave_local_ai_v2.nvml import nvml_device

# Decimal GB, the unit every declaration and observation is stated in.
_BYTES_PER_GB = 10**9

# The order requirements are checked in; the first that fails is the refusal.
CHECK_ORDER: tuple[str, ...] = ("ram_gb", "vram_gb", "disk_gb")


class PreflightError(roster.RosterError):
    """A declared minimum the pre-flight could not compare: nothing observed it.

    Not a refusal: no record is written, since a record would claim a
    shortfall nobody measured. A `RosterError`, so every writer's handler
    prints it as one line and exits non-zero before anything starts.
    """


class RequirementRefusal(roster.RosterError):
    """A run below its entry's declared minimum, refused and recorded."""

    def __init__(self, message: str, record: dict[str, Any]) -> None:
        super().__init__(message)
        self.record = record


@dataclass(frozen=True)
class Observation:
    """What the machine reports, in decimal GB; `None` where nothing was read.

    `disk_free_gb` is `None` when the weights are already on disk: the disk
    requirement then has nothing left to need.
    """

    ram_gb: float | None
    vram_gb: float | None
    disk_free_gb: float | None


def refusal_path(machine_results_root: Path, machine_id: str) -> Path:
    """The refusal file of the machine's tracked results location."""
    return machine_results.location(machine_results_root, machine_id).refusals


def observe(
    machine: machines.MachineEntry,
    compute_mode: str,
    models_dir: Path,
    entry: roster.RosterEntry,
) -> Observation:
    """Read the machine: total RAM, allocatable VRAM, free disk.

    VRAM is read only for a `gpu` run whose entry declares a VRAM minimum:
    an NVML session costs most of a second and nothing would compare it.
    """
    weights_present = (models_dir / entry.file).exists()
    vram_declared = compute_mode == machines.COMPUTE_MODE_GPU and (
        _requirements_for(entry, compute_mode)["vram_gb"]["source"]
        == machines.SOURCE_DECLARED
    )
    return Observation(
        ram_gb=_total_ram_gb(),
        vram_gb=_allocatable_vram_gb(machine) if vram_declared else None,
        disk_free_gb=None if weights_present else _free_disk_gb(models_dir),
    )


def _total_ram_gb() -> float | None:
    try:
        return float(psutil.virtual_memory().total) / _BYTES_PER_GB
    except Exception:  # noqa: BLE001 - an unreadable figure is reported as None
        return None


def _free_disk_gb(models_dir: Path) -> float | None:
    try:
        return shutil.disk_usage(models_dir).free / _BYTES_PER_GB
    except OSError:
        return None


def _allocatable_vram_gb(machine: machines.MachineEntry) -> float | None:
    """The machine's declared allocatable VRAM, else NVML's reported total."""
    declared = machine.facts["vram_allocatable_gb"]
    if declared["source"] == machines.SOURCE_DECLARED and declared["value"] is not None:
        return float(declared["value"])
    try:
        import pynvml

        with nvml_device() as handle:
            return float(pynvml.nvmlDeviceGetMemoryInfo(handle).total) / _BYTES_PER_GB
    except Exception:  # noqa: BLE001 - no NVML is "not observed", decided by the caller
        return None


def first_failure(
    entry: roster.RosterEntry, compute_mode: str, observation: Observation
) -> tuple[str, float, float] | None:
    """The first declared minimum the observation falls below, or `None`.

    Returns `(requirement, declared, observed)`. A `not_yet_declared`
    requirement is not checked (`unchecked` names them). Raises
    `PreflightError` for a declared minimum nothing observed.
    """
    declared = _requirements_for(entry, compute_mode)
    observed = {
        "ram_gb": observation.ram_gb,
        "vram_gb": observation.vram_gb,
        "disk_gb": observation.disk_free_gb,
    }
    for name in CHECK_ORDER:
        fact = declared.get(name)
        if fact is None or fact["source"] != machines.SOURCE_DECLARED:
            continue
        if name == "disk_gb" and observed[name] is None:
            # The weights are already on disk, or the free space could not be
            # read; either way the run needs no further disk to start.
            continue
        value = observed[name]
        if value is None:
            raise PreflightError(
                f"pre-flight: roster entry {entry.entry_id!r} declares a minimum "
                f"{name} of {fact['value']} under compute mode {compute_mode!r}, "
                "but the machine reported no value to compare it with; nothing "
                "was started"
            )
        if value < fact["value"]:
            return name, float(fact["value"]), round(value, 2)
    return None


def unchecked(entry: roster.RosterEntry, compute_mode: str) -> list[str]:
    """The requirements of this mode nobody has declared yet: not checked."""
    return [
        name
        for name, fact in _requirements_for(entry, compute_mode).items()
        if fact["source"] == machines.SOURCE_NOT_YET_DECLARED
    ]


def _requirements_for(
    entry: roster.RosterEntry, compute_mode: str
) -> dict[str, dict[str, Any]]:
    if entry.requirements is None:
        raise PreflightError(
            f"pre-flight: roster entry {entry.entry_id!r} declares no "
            "requirements; a run needs its declared minimums to start"
        )
    return entry.requirements[compute_mode]


def refusal_record(
    entry: roster.RosterEntry,
    profile: profiles.ResolvedProfile,
    requirement: str,
    declared: float,
    observed: float,
) -> dict[str, Any]:
    """The refusal record: never a row, carrying its own contract version."""
    return {
        "record_kind": row_contract.REFUSAL_RECORD_KIND,
        "refusal_contract_version": row_contract.REFUSAL_CONTRACT_VERSION,
        "roster_entry_id": entry.entry_id,
        "machine_id": profile.machine_id,
        "compute_mode": profile.compute_mode,
        "profile_id": profile.profile_id,
        "requirement": requirement,
        "declared": declared,
        "observed": observed,
        "unit": "GB",
        "release_version": provenance.release_version(),
        "commit_sha": provenance.commit_sha(),
        "refused_at": results.captured_at(),
    }


def enforce(
    entry: roster.RosterEntry,
    machine: machines.MachineEntry,
    profile: profiles.ResolvedProfile,
    *,
    models_dir: Path,
    machine_results_root: Path,
    observe_machine: Callable[..., Observation] = observe,
    profile_registry: profiles.ProfileRegistry | None = None,
) -> None:
    """Refuse the run, recording it, when the machine is below a declared minimum.

    Called by each writer after its run profile resolves and before the model
    path is resolved, the build is probed or any process starts.
    """
    mode = profile.compute_mode
    declared_minimums = _requirements_for(entry, mode)
    for name in unchecked(entry, mode):
        print(
            f"pre-flight: {name} not checked under {mode}: roster entry "
            f"{entry.entry_id!r} declares no minimum yet "
            f"({declared_minimums[name]['read_from']})",
            file=sys.stderr,
        )
    observation = observe_machine(machine, mode, models_dir, entry)
    failure = first_failure(entry, mode, observation)
    if failure is None:
        return
    requirement, declared, observed = failure
    record = refusal_record(entry, profile, requirement, declared, observed)
    path = refusal_path(machine_results_root, profile.machine_id)
    results.append_refusal(path, record)
    message = (
        f"refused: roster entry {entry.entry_id!r} under compute mode {mode!r} "
        f"requires {requirement} >= {declared} GB "
        f"({declared_minimums[requirement]['read_from']}); machine "
        f"{profile.machine_id!r} reports {observed} GB. Nothing was started and "
        f"no row was written; the refusal is recorded in {path}"
    )
    if mode == machines.COMPUTE_MODE_GPU:
        registry = profile_registry or profiles.tracked_registry()
        cpu_key = (profile.machine_id, machines.COMPUTE_MODE_CPU_ONLY)
        if cpu_key in registry.defaults:
            message += (
                ". A cpu_only profile exists for this entry on this machine ("
                + profiles.profile_id_for(entry.entry_id, *cpu_key)
                + "); it is not run in this one's place: set COMPUTE_MODE=cpu_only "
                "to run it"
            )
    raise RequirementRefusal(message, record)
