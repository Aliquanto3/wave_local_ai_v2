import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.hardware import capture_fiche


def test_capture_fiche_returns_all_documented_keys() -> None:
    fiche = capture_fiche()

    assert set(fiche.keys()) == {
        "cpu",
        "ram_gb",
        "gpu_name",
        "gpu_driver_version",
        "cuda_ceiling",
        "os",
    }
    assert fiche["cpu"]
    assert fiche["os"]


@pytest.fixture
def pynvml_that_raises(monkeypatch):
    """Install a pynvml whose first call raises, at the library boundary.

    Deliberately *not* a monkeypatch of `hardware._capture_gpu_fields`: that is
    the function whose `except` branch this test exists to exercise, so stubbing
    it would leave the real guard unexecuted and the test would pass even if the
    guard were deleted.
    """
    fake_module = ModuleType("pynvml")
    fake_module.nvmlInit = MagicMock(side_effect=RuntimeError("NVML unavailable"))  # type: ignore[attr-defined]
    fake_module.nvmlShutdown = MagicMock()  # type: ignore[attr-defined]
    fake_module.nvmlDeviceGetHandleByIndex = MagicMock()  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "pynvml", fake_module)
    return fake_module


def test_capture_fiche_degrades_gracefully_when_nvml_unavailable(
    pynvml_that_raises,
) -> None:
    fiche = capture_fiche()

    assert fiche["gpu_name"] is None
    assert fiche["gpu_driver_version"] is None
    assert fiche["cuda_ceiling"] is None
    # The non-GPU fields still come from the real collectors.
    assert fiche["cpu"]
    assert fiche["os"]
