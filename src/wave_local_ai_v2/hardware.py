"""Hardware fiche capture: the machine-bound fields every runtime row must carry.

`capture_fiche()` stays machine-only: run-specific fields (llama.cpp build,
roster entry id + its sha256, quant, flags) are supplied by the caller (the
two CLIs) via `build_fiche`, which merges them with no re-reading of the
machine and no side effects -- this keeps `build_fiche` composable with a
plain dict in tests, without needing a live roster entry.
"""

from __future__ import annotations

import hashlib
import json
import platform
from typing import Any, TypedDict

from wave_local_ai_v2.nvml import decode_nvml_str, nvml_device


class HardwareFiche(TypedDict):
    cpu: str
    ram_gb: float | None
    gpu_name: str | None
    gpu_driver_version: str | None
    os: str
    cuda_ceiling: str | None


class Fiche(HardwareFiche):
    """The machine fiche plus the run-specific fields that describe one launch."""

    llama_cpp_build: str | None
    roster_entry_id: str
    model_sha256: str
    quant: str
    flags: list[str]


# The exact projection `fiche_hash` is computed over. `flags`, host and port
# are never in it: `flags` stays on the stored fiche as raw evidence only
# (plan.md's Decisions table), and host/port never existed on the fiche at
# all -- stated here so a future field addition doesn't reintroduce them
# silently.
_NORMALISED_KEYS = (
    "cpu",
    "ram_gb",
    "gpu_name",
    "gpu_driver_version",
    "os",
    "cuda_ceiling",
    "llama_cpp_build",
    "quant",
    "roster_entry_id",
    "model_sha256",
)


def capture_fiche() -> HardwareFiche:
    """Capture the machine's hardware fiche. GPU fields degrade to None on failure."""
    gpu_name, gpu_driver_version, cuda_ceiling = _capture_gpu_fields()

    return HardwareFiche(
        cpu=platform.processor() or platform.machine(),
        ram_gb=_capture_ram_gb(),
        gpu_name=gpu_name,
        gpu_driver_version=gpu_driver_version,
        cuda_ceiling=cuda_ceiling,
        os=f"{platform.system()} {platform.release()}",
    )


def build_fiche(
    machine: HardwareFiche,
    *,
    llama_cpp_build: str | None,
    roster_entry_id: str,
    model_sha256: str,
    quant: str,
    flags: list[str],
) -> Fiche:
    """Merge a machine capture with the fields that describe one run.

    No re-reading of the machine, no side effects: a plain dict for
    `machine` is enough to exercise this in a test.
    """
    return Fiche(
        **machine,
        llama_cpp_build=llama_cpp_build,
        roster_entry_id=roster_entry_id,
        model_sha256=model_sha256,
        quant=quant,
        flags=list(flags),
    )


def normalise_fiche(fiche: Fiche) -> dict[str, Any]:
    """Project `fiche` to exactly the fields its identity hash is computed over.

    No `flags` key (the raw flag list, including any filesystem path it
    carries, stays evidence-only on the stored fiche, never part of the
    hashed projection) and no host or port (neither ever existed on the
    fiche at all).
    """
    return {key: fiche[key] for key in _NORMALISED_KEYS}  # type: ignore[literal-required]


def fiche_hash(fiche: Fiche) -> str:
    """SHA-256 over the sorted-key JSON of `fiche`'s normalised projection.

    Sorted keys make the hash independent of dict insertion order without a
    bespoke serializer.
    """
    payload = json.dumps(normalise_fiche(fiche), sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _capture_ram_gb() -> float | None:
    try:
        import psutil

        return round(psutil.virtual_memory().total / (1024**3), 1)
    except Exception:  # noqa: BLE001 - best-effort capture, must never crash the run
        return None


def _capture_gpu_fields() -> tuple[str | None, str | None, str | None]:
    try:
        import pynvml

        with nvml_device(0) as handle:
            name = decode_nvml_str(pynvml.nvmlDeviceGetName(handle))
            driver_version = decode_nvml_str(pynvml.nvmlSystemGetDriverVersion())
            cuda_version = pynvml.nvmlSystemGetCudaDriverVersion()
            cuda_ceiling = f"{cuda_version // 1000}.{(cuda_version % 1000) // 10}"
            return name, driver_version, cuda_ceiling
    except Exception:  # noqa: BLE001 - best-effort capture, must never crash the run
        return None, None, None
