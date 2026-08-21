"""Energy measurement via CodeCarbon, tagged with how the number was obtained.

On Windows, CodeCarbon has no RAPL access: CPU energy always falls back to a
TDP-based estimate. GPU energy is a real NVML measurement when CodeCarbon
detects a GPU it can query. `energy_method` reflects the GPU figure, since
that's the one measurement channel that can actually be real on this platform
per `aidd_docs/memory/architecture.md`.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypedDict


class EnergyResult(TypedDict):
    energy_kwh: float | None
    energy_method: str


def measure_energy[T](fn: Callable[[], T]) -> tuple[T, EnergyResult]:
    """Run `fn()` inside a CodeCarbon tracker, return its result plus tagged energy."""
    try:
        from codecarbon import EmissionsTracker

        tracker = EmissionsTracker(output_methods=[], log_level="error")
        tracker.start()
    except Exception:  # noqa: BLE001 - tracker init must never block the measured call
        return fn(), EnergyResult(energy_kwh=None, energy_method="unavailable")

    try:
        result = fn()
    finally:
        tracker.stop()

    data = tracker.final_emissions_data
    if data is None:
        return result, EnergyResult(energy_kwh=None, energy_method="unavailable")

    method = (
        "measured_nvml" if data.gpu_energy and data.gpu_energy > 0 else "estimated_tdp"
    )
    return result, EnergyResult(energy_kwh=data.energy_consumed, energy_method=method)
