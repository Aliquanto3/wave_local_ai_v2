import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.nvml import decode_nvml_str, nvml_device


@pytest.fixture
def stub_pynvml(monkeypatch):
    fake_module = ModuleType("pynvml")
    fake_module.nvmlInit = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlShutdown = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle")  # type: ignore[attr-defined]
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
