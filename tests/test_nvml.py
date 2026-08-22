import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.nvml import (
    decode_clocks_event_reasons,
    decode_nvml_str,
    nvml_device,
    read_clocks_event_reasons,
    read_gpu_temperature_c,
)

# Real bit values from `nvidia-ml-py==13.610.43` (see plan.md's Resources
# table) -- kept literal here rather than imported, so the test also catches
# a value drift in the installed binding.
_REASON_GPU_IDLE = 1
_REASON_APPLICATIONS_CLOCKS_SETTING = 2
_REASON_SW_POWER_CAP = 4
_REASON_HW_SLOWDOWN = 8
_REASON_SYNC_BOOST = 16
_REASON_SW_THERMAL_SLOWDOWN = 32
_REASON_HW_THERMAL_SLOWDOWN = 64
_REASON_HW_POWER_BRAKE_SLOWDOWN = 128
_REASON_DISPLAY_CLOCK_SETTING = 256


@pytest.fixture
def stub_pynvml(monkeypatch):
    fake_module = ModuleType("pynvml")
    fake_module.nvmlInit = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlShutdown = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle")  # type: ignore[attr-defined]
    fake_module.NVML_TEMPERATURE_GPU = 0  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonGpuIdle = _REASON_GPU_IDLE  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonApplicationsClocksSetting = (  # type: ignore[attr-defined]
        _REASON_APPLICATIONS_CLOCKS_SETTING
    )
    fake_module.nvmlClocksEventReasonSwPowerCap = _REASON_SW_POWER_CAP  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonHwSlowdown = _REASON_HW_SLOWDOWN  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonSyncBoost = _REASON_SYNC_BOOST  # type: ignore[attr-defined]
    fake_module.nvmlClocksEventReasonSwThermalSlowdown = (  # type: ignore[attr-defined]
        _REASON_SW_THERMAL_SLOWDOWN
    )
    fake_module.nvmlClocksEventReasonHwThermalSlowdown = (  # type: ignore[attr-defined]
        _REASON_HW_THERMAL_SLOWDOWN
    )
    fake_module.nvmlClocksEventReasonHwPowerBrakeSlowdown = (  # type: ignore[attr-defined]
        _REASON_HW_POWER_BRAKE_SLOWDOWN
    )
    fake_module.nvmlClocksEventReasonDisplayClockSetting = (  # type: ignore[attr-defined]
        _REASON_DISPLAY_CLOCK_SETTING
    )
    monkeypatch.setitem(sys.modules, "pynvml", fake_module)
    return fake_module


def test_nvml_device_inits_yields_handle_and_shuts_down(stub_pynvml) -> None:
    with nvml_device(0) as handle:
        assert handle == "handle"

    stub_pynvml.nvmlInit.assert_called_once()
    stub_pynvml.nvmlDeviceGetHandleByIndex.assert_called_once_with(0)
    stub_pynvml.nvmlShutdown.assert_called_once()


def test_nvml_device_shuts_down_even_on_exception(stub_pynvml) -> None:
    with pytest.raises(RuntimeError), nvml_device(0):
        raise RuntimeError("boom")

    stub_pynvml.nvmlShutdown.assert_called_once()


def test_decode_nvml_str_decodes_bytes() -> None:
    assert decode_nvml_str(b"572.70") == "572.70"


def test_decode_nvml_str_passes_through_str() -> None:
    assert decode_nvml_str("572.70") == "572.70"


def test_read_gpu_temperature_c_returns_the_reported_value(stub_pynvml) -> None:
    stub_pynvml.nvmlDeviceGetTemperature = MagicMock(return_value=68)  # type: ignore[attr-defined]

    assert read_gpu_temperature_c("handle") == 68.0


def test_read_gpu_temperature_c_returns_none_on_nvml_failure(stub_pynvml) -> None:
    stub_pynvml.nvmlDeviceGetTemperature = MagicMock(side_effect=RuntimeError("no GPU"))  # type: ignore[attr-defined]

    assert read_gpu_temperature_c("handle") is None


def test_decode_clocks_event_reasons_zero_bitmask_is_empty() -> None:
    assert decode_clocks_event_reasons(0) == []


def test_decode_clocks_event_reasons_decodes_set_bits() -> None:
    bitmask = _REASON_HW_THERMAL_SLOWDOWN | _REASON_SW_POWER_CAP
    assert decode_clocks_event_reasons(bitmask) == [
        "hw_thermal_slowdown",
        "sw_power_cap",
    ]


def test_read_clocks_event_reasons_decodes_the_queried_bitmask(stub_pynvml) -> None:
    stub_pynvml.nvmlDeviceGetCurrentClocksEventReasons = MagicMock(  # type: ignore[attr-defined]
        return_value=_REASON_HW_SLOWDOWN
    )

    assert read_clocks_event_reasons("handle") == ["hw_slowdown"]


def test_read_clocks_event_reasons_returns_empty_list_on_nvml_failure(
    stub_pynvml,
) -> None:
    stub_pynvml.nvmlDeviceGetCurrentClocksEventReasons = MagicMock(  # type: ignore[attr-defined]
        side_effect=RuntimeError("no GPU")
    )

    assert read_clocks_event_reasons("handle") == []
