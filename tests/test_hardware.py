import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.hardware import (
    build_fiche,
    capture_fiche,
    fiche_hash,
    normalise_fiche,
)


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


def _fixture_fiche(**overrides):
    base = {
        "cpu": "x",
        "ram_gb": 32.0,
        "gpu_name": "y",
        "gpu_driver_version": "1.2.3",
        "os": "z",
        "cuda_ceiling": "12.4",
        "llama_cpp_build": "b10537",
        "roster_entry_id": "qwen3.6-35b-a3b-ud-iq4xs",
        "model_sha256": "0" * 64,
        "quant": "UD-IQ4_XS",
        "flags": ["-ngl", "99"],
    }
    base.update(overrides)
    return base


def test_normalise_fiche_has_no_flags_key_and_no_filesystem_path() -> None:
    fiche = _fixture_fiche(flags=["-m", "D:\\ia\\models\\fake.gguf", "-ngl", "99"])

    normalised = normalise_fiche(fiche)  # type: ignore[arg-type]

    assert "flags" not in normalised
    assert not any("D:\\ia\\models" in str(v) for v in normalised.values())


def test_hash_identical_for_two_fiches_differing_only_by_flags() -> None:
    a = _fixture_fiche(flags=["-m", "D:\\ia\\models\\fake.gguf"])
    b = _fixture_fiche(flags=[])

    assert fiche_hash(a) == fiche_hash(b)  # type: ignore[arg-type]


def test_hash_differs_when_gpu_name_differs() -> None:
    a = _fixture_fiche(gpu_name="RTX 4090")
    b = _fixture_fiche(gpu_name="RTX 3090")

    assert fiche_hash(a) != fiche_hash(b)  # type: ignore[arg-type]


def test_hash_is_independent_of_dict_key_insertion_order() -> None:
    a = _fixture_fiche()
    # Rebuild with keys in reverse insertion order -- still equal by value.
    b = {key: a[key] for key in reversed(list(a.keys()))}

    assert fiche_hash(a) == fiche_hash(b)  # type: ignore[arg-type]


def test_build_fiche_merges_machine_capture_with_run_specific_fields() -> None:
    machine = {
        "cpu": "x",
        "ram_gb": 32.0,
        "gpu_name": "y",
        "gpu_driver_version": "1.2.3",
        "os": "z",
        "cuda_ceiling": "12.4",
    }

    fiche = build_fiche(
        machine,  # type: ignore[arg-type]
        llama_cpp_build="b10537",
        roster_entry_id="fake-entry",
        model_sha256="0" * 64,
        quant="UD-IQ4_XS",
        flags=["-ngl", "99"],
    )

    assert fiche["cpu"] == "x"
    assert fiche["llama_cpp_build"] == "b10537"
    assert fiche["roster_entry_id"] == "fake-entry"
    assert fiche["model_sha256"] == "0" * 64
    assert fiche["quant"] == "UD-IQ4_XS"
    assert fiche["flags"] == ["-ngl", "99"]
