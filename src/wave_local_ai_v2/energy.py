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
    # Type-only: the runtime import stays inside `measure_energy` and
    # `RepetitionEnergyTracker.__init__`, where it is allowed to fail without
    # taking the module down.
    from codecarbon import OfflineEmissionsTracker
    from codecarbon.output_methods.emissions_data import (
        EmissionsData as TaskEmissionsData,
    )

ENERGY_METHOD_ESTIMATED_TDP = "estimated_tdp"
ENERGY_METHOD_ESTIMATED_CONSTANT = "estimated_constant"
ENERGY_METHOD_MEASURED_NVML = "measured_nvml"
ENERGY_METHOD_UNAVAILABLE = "unavailable"

# `RepetitionEnergyTracker.window_method`: which span the row's energy figures
# were measured over. Phase 1 of the 2026-09-22 runtime-energy-active-window
# plan probed `start_task`/`stop_task` overhead (~1.6ms median) against a 10s
# cooldown and found it negligible, so `per_repetition_tasks` -- summing each
# counted repetition's own isolated energy delta -- is the only method
# implemented; `ENERGY_WINDOW_METHOD_UNAVAILABLE` names a row whose energy
# could not be measured over every counted repetition (tracker never started,
# or one repetition's delta was lost), not a second method.
ENERGY_WINDOW_METHOD_PER_REPETITION = "per_repetition_tasks"
ENERGY_WINDOW_METHOD_UNAVAILABLE = "unavailable"


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


class RepetitionEnergyTracker:
    """Sums one `OfflineEmissionsTracker`'s per-repetition energy deltas,
    isolating each counted repetition's own active span from the cooldown
    that follows it.

    Mirrors `measure_energy`'s discipline (tracker init failure never blocks
    the measured call, teardown never raises) but does not wrap a single
    `fn()`: `wrap()` produces a zero-arg closure per repetition, fed to
    `repetitions.run_repetition_set`'s `send`, and `finish()` sums whatever
    `start_task`/`stop_task` recorded across all of them.
    """

    def __init__(self, *, country_iso_code: str) -> None:
        self._deltas: list[TaskEmissionsData | None] = []
        self._task_index = 0
        try:
            from codecarbon import OfflineEmissionsTracker

            self._tracker: OfflineEmissionsTracker | None = OfflineEmissionsTracker(
                country_iso_code=country_iso_code, output_methods=[], log_level="error"
            )
            self._tracker.start()
        except Exception:  # noqa: BLE001 - tracker init must never block the measured call
            self._tracker = None

    def wrap[T](self, fn: Callable[[], T]) -> Callable[[], T]:
        """Return a zero-arg callable that isolates one call's energy delta.

        When no tracker is held, `fn()` still runs -- unchanged behaviour,
        every repetition executes regardless of measurement availability.
        """

        def _call() -> T:
            if self._tracker is None:
                return fn()
            task_name = f"repetition-{self._task_index}"
            self._task_index += 1
            self._tracker.start_task(task_name)
            try:
                result = fn()
            finally:
                self._deltas.append(_stop_task(self._tracker, task_name))
            return result

        return _call

    def finish(self) -> tuple[EnergyResult, str]:
        """Stop the tracker and sum the recorded deltas.

        Returns the same all-or-nothing `EnergyResult` shape `measure_energy`
        returns, plus the window-method label for the row's
        `energy_window_method` field.
        """
        if self._tracker is None:
            return _unavailable_energy_result(), ENERGY_WINDOW_METHOD_UNAVAILABLE

        stopped = _stop_tracker(self._tracker)
        if not stopped or not self._deltas or any(d is None for d in self._deltas):
            return _unavailable_energy_result(), ENERGY_WINDOW_METHOD_UNAVAILABLE

        deltas = [d for d in self._deltas if d is not None]
        data = self._tracker.final_emissions_data
        if data is not None and data.gpu_count and data.gpu_count > 0:
            gpu_energy_kwh: float | None = sum(d.gpu_energy for d in deltas)
            gpu_energy_method = ENERGY_METHOD_MEASURED_NVML
        else:
            gpu_energy_kwh = None
            gpu_energy_method = ENERGY_METHOD_UNAVAILABLE

        return EnergyResult(
            cpu_energy_kwh=sum(d.cpu_energy for d in deltas),
            cpu_energy_method=ENERGY_METHOD_ESTIMATED_TDP,
            gpu_energy_kwh=gpu_energy_kwh,
            gpu_energy_method=gpu_energy_method,
            ram_energy_kwh=sum(d.ram_energy for d in deltas),
            ram_energy_method=ENERGY_METHOD_ESTIMATED_CONSTANT,
            energy_kwh=sum(d.energy_consumed for d in deltas),
        ), ENERGY_WINDOW_METHOD_PER_REPETITION


def _stop_task(
    tracker: OfflineEmissionsTracker, task_name: str
) -> TaskEmissionsData | None:
    """`tracker.stop_task()`, reporting `None` on failure. Never raises.

    Called from a `finally`: anything escaping here would mask the measured
    call's own exception.
    """
    try:
        return tracker.stop_task(task_name)
    except Exception:  # noqa: BLE001 - one failed task must not break the row
        return None


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
