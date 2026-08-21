"""NVML GPU stats: VRAM used and instantaneous power draw. Real measurements, not estimates."""

from __future__ import annotations

from typing import TypedDict

from wave_local_ai_v2.nvml import nvml_device


class GpuStats(TypedDict):
    vram_used_mib: float | None
    gpu_draw_w: float | None


def read_gpu_stats(device_index: int = 0) -> GpuStats:
    """Read VRAM used and power draw via NVML. Returns None fields on any failure."""
    try:
        import pynvml

        with nvml_device(device_index) as handle:
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            power_mw = pynvml.nvmlDeviceGetPowerUsage(handle)
            return GpuStats(
                vram_used_mib=memory_info.used / (1024**2),
                gpu_draw_w=power_mw / 1000,
            )
    except Exception:  # noqa: BLE001 - best-effort measurement, must never crash the run
        return GpuStats(vram_used_mib=None, gpu_draw_w=None)
