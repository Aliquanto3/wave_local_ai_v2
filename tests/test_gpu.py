import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.gpu import read_gpu_stats


@pytest.fixture
def stub_pynvml(monkeypatch):
    fake_module = ModuleType("pynvml")
    fake_module.nvmlInit = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlShutdown = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetHandleByIndex = MagicMock(return_value="handle")  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pynvml", fake_module)
    return fake_module


def test_read_gpu_stats_returns_documented_keys(stub_pynvml) -> None:
    stub_pynvml.nvmlDeviceGetMemoryInfo = MagicMock(  # type: ignore[attr-defined]
        return_value=MagicMock(used=3_161 * 1024**2)
    )
    stub_pynvml.nvmlDeviceGetPowerUsage = MagicMock(return_value=45_000)  # type: ignore[attr-defined]

    stats = read_gpu_stats()

    assert stats["vram_used_mib"] == pytest.approx(3161.0)
    assert stats["gpu_draw_w"] == pytest.approx(45.0)


def test_read_gpu_stats_returns_none_fields_on_nvml_failure(stub_pynvml) -> None:
    stub_pynvml.nvmlDeviceGetMemoryInfo = MagicMock(side_effect=RuntimeError("no GPU"))  # type: ignore[attr-defined]

    stats = read_gpu_stats()

    assert stats["vram_used_mib"] is None
    assert stats["gpu_draw_w"] is None
