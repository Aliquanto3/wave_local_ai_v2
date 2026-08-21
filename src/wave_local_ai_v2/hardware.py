"""Hardware fiche capture: the machine-bound fields every runtime row must carry.

Run-specific fields (llama.cpp build, model file, quant, flags) are NOT captured
here — they belong to the caller, since they describe the run, not the machine.
"""

from __future__ import annotations

import platform
from typing import TypedDict

from wave_local_ai_v2.nvml import decode_nvml_str, nvml_device


class HardwareFiche(TypedDict):
    cpu: str
    ram_gb: float | None
    gpu_name: str | None
    gpu_driver_version: str | None
    os: str
    cuda_ceiling: str | None


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
