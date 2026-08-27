"""Energy measurement via CodeCarbon, tagged per-channel with how each
number was obtained.

On Windows, CodeCarbon has no RAPL access: CPU energy always falls back to a
TDP-based estimate, and RAM energy is always a fixed-constant estimate (a
W-per-8GB rule, never a measured channel on any platform). GPU energy is a
real NVML measurement, but only when CodeCarbon's `gpu_count` confirms it
found a GPU to query -- a channel that genuinely drew ~0W in a short run must
stay distinguishable from a channel that was never measured at all, so GPU
availability (not the energy magnitude) decides its method label. See
`aidd_docs/memory/architecture.md` for the RAPL gotcha.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    # Type-only: the runtime import stays inside `measure_energy`, where it is
    # allowed to fail without taking the module down.
    from codecarbon import OfflineEmissionsTracker

ENERGY_METHOD_ESTIMATED_TDP = "estimated_tdp"
ENERGY_METHOD_ESTIMATED_CONSTANT = "estimated_constant"
ENERGY_METHOD_MEASURED_NVML = "measured_nvml"
ENERGY_METHOD_UNAVAILABLE = "unavailable"


class EnergyResult(TypedDict):
    cpu_energy_kwh: float | None
    cpu_energy_method: str
    gpu_energy_kwh: float | None
    gpu_energy_method: str
    ram_energy_kwh: float | None
    ram_energy_method: str
    energy_kwh: float | None


def _unavailable_energy_result() -> EnergyResult:
    return EnergyResult(
        cpu_energy_kwh=None,
        cpu_energy_method=ENERGY_METHOD_UNAVAILABLE,
        gpu_energy_kwh=None,
        gpu_energy_method=ENERGY_METHOD_UNAVAILABLE,
        ram_energy_kwh=None,
        ram_energy_method=ENERGY_METHOD_UNAVAILABLE,
        energy_kwh=None,
    )


def measure_energy[T](
    fn: Callable[[], T], *, country_iso_code: str
) -> tuple[T, EnergyResult]:
    """Run `fn()` inside an offline CodeCarbon tracker, return its result plus
    per-channel tagged energy.

    `country_iso_code` selects the static grid mix CodeCarbon ships with, so
    no live IP-geolocation lookup happens (offline mode).
    """
    try:
        from codecarbon import OfflineEmissionsTracker

        tracker = OfflineEmissionsTracker(
            country_iso_code=country_iso_code, output_methods=[], log_level="error"
        )
        tracker.start()
    except Exception:  # noqa: BLE001 - tracker init must never block the measured call
        return fn(), _unavailable_energy_result()

    try:
        result = fn()
    finally:
        # _stop_tracker cannot raise, so this finally can no longer replace an
        # exception fn() raised with one from the tracker's teardown.
        stopped = _stop_tracker(tracker)

    if not stopped:
        # "unavailable", not a partial number read from final_emissions_data: a
        # tracker that failed to stop has no trustworthy total to report.
        return result, _unavailable_energy_result()

    data = tracker.final_emissions_data
    if data is None:
        return result, _unavailable_energy_result()

    if data.gpu_count and data.gpu_count > 0:
        gpu_energy_kwh: float | None = data.gpu_energy
        gpu_energy_method = ENERGY_METHOD_MEASURED_NVML
    else:
        gpu_energy_kwh = None
        gpu_energy_method = ENERGY_METHOD_UNAVAILABLE

    return result, EnergyResult(
        cpu_energy_kwh=data.cpu_energy,
        cpu_energy_method=ENERGY_METHOD_ESTIMATED_TDP,
        gpu_energy_kwh=gpu_energy_kwh,
        gpu_energy_method=gpu_energy_method,
        ram_energy_kwh=data.ram_energy,
        ram_energy_method=ENERGY_METHOD_ESTIMATED_CONSTANT,
        energy_kwh=data.energy_consumed,
    )


def _stop_tracker(tracker: OfflineEmissionsTracker) -> bool:
    """Stop the tracker, reporting success. Never raises.

    Called from a `finally`: anything escaping here would mask the measured
    function's own exception, or throw away a measurement that already
    succeeded.
    """
    try:
        tracker.stop()
    except Exception:  # noqa: BLE001 - teardown must never break a finished run
        return False
    return True
