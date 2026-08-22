import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.machine_state import (
    CPU_TEMP_SOURCE_UNAVAILABLE,
    read_machine_state,
)

_REASON_HW_THERMAL_SLOWDOWN = 64


@pytest.fixture
def stub_pynvml(monkeypatch):
    fake_module = ModuleType("pynvml")
    fake_module.nvmlInit = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlShutdown = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle")  # type: ignore[attr-defined]
    fake_module.NVML_TEMPERATURE_GPU = 0  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetTemperature = MagicMock(return_value=68)  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetCurrentClocksEventReasons = MagicMock(return_value=0)  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonGpuIdle = 1  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonApplicationsClocksSetting = 2  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonSwPowerCap = 4  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonHwSlowdown = 8  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonSyncBoost = 16  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonSwThermalSlowdown = 32  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonHwThermalSlowdown = _REASON_HW_THERMAL_SLOWDOWN  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonHwPowerBrakeSlowdown = 128  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonDisplayClockSetting = 256  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pynvml", fake_module)
    return fake_module


def test_read_machine_state_happy_path(stub_pynvml) -> None:
    state = read_machine_state()

    assert state["gpu_temp_c"] == 68.0
    assert state["gpu_throttle_reasons"] == []
    # This platform has no `psutil.sensors_temperatures` (confirmed live).
    assert state["cpu_temp_c"] is None
    assert state["cpu_temp_source"] == CPU_TEMP_SOURCE_UNAVAILABLE


def test_read_machine_state_decodes_a_throttle_bitmask(stub_pynvml) -> None:
    stub_pynvml.nvmlDeviceGetCurrentClocksEventReasons = MagicMock(  # type: ignore[attr-defined]
        return_value=_REASON_HW_THERMAL_SLOWDOWN
    )

    state = read_machine_state()

    assert state["gpu_throttle_reasons"] == ["hw_thermal_slowdown"]


def test_read_machine_state_degrades_gpu_fields_on_nvml_unreachable(
    monkeypatch,
) -> None:
    fake_module = ModuleType("pynvml")
    fake_module.nvmlInit = MagicMock(side_effect=RuntimeError("driver not found"))  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pynvml", fake_module)

    state = read_machine_state()

    assert state["gpu_temp_c"] is None
    assert state["gpu_throttle_reasons"] == []


def test_read_machine_state_reports_cpu_temperature_unavailable_on_this_platform() -> (
    None
):
    # No stub: exercises the real, installed `psutil`, matching the story's
    # spike (`hasattr(psutil, "sensors_temperatures")` is `False` here).
    state = read_machine_state()

    assert state["cpu_temp_c"] is None
    assert state["cpu_temp_source"] == CPU_TEMP_SOURCE_UNAVAILABLE
