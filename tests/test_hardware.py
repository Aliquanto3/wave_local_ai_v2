import sys
from types import ModuleType
from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.hardware import (
    FICHE_PROJECTIONS,
    FicheProjectionError,
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
        "engine_id": "llama.cpp",
        "engine_build": "b10537",
        "engine_config_hash": "e" * 64,
        "machine_id": "laptop-mobile-gpu",
        "compute_mode": "gpu",
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


@pytest.mark.parametrize(
    ("field", "other"),
    [
        ("engine_id", "ollama"),
        ("engine_build", "b10600"),
        ("engine_config_hash", "f" * 64),
    ],
)
def test_each_engine_field_changes_the_hash(field: str, other: str) -> None:
    assert fiche_hash(_fixture_fiche()) != fiche_hash(_fixture_fiche(**{field: other}))


def test_the_legacy_projection_hashes_llama_cpp_build_and_ignores_engine_fields() -> (
    None
):
    legacy = {
        key: value
        for key, value in _fixture_fiche().items()
        if not key.startswith("engine_")
    }
    legacy["llama_cpp_build"] = "b10537"

    assert set(normalise_fiche(legacy, "1")) == set(FICHE_PROJECTIONS["1"])
    assert "llama_cpp_build" in normalise_fiche(legacy, "1")
    assert fiche_hash(legacy, "1") != fiche_hash(
        {**legacy, "llama_cpp_build": "b1"}, "1"
    )


def test_a_fiche_lacking_a_projection_key_is_refused_naming_it() -> None:
    legacy = {
        key: value
        for key, value in _fixture_fiche().items()
        if not key.startswith("engine_")
    }

    with pytest.raises(FicheProjectionError, match="engine_id, engine_build"):
        fiche_hash(legacy)


def test_a_gpu_and_a_cpu_only_fiche_of_one_machine_hash_differently() -> None:
    """Epic success check 1 at the identity: the flag lists differ only
    outside the projection, so `compute_mode` alone must separate them."""
    gpu = _fixture_fiche(compute_mode="gpu", flags=["-ngl", "99"])
    cpu_only = _fixture_fiche(
        compute_mode="cpu_only", flags=["-ngl", "0", "--device", "none"]
    )

    assert fiche_hash(gpu) != fiche_hash(cpu_only)  # type: ignore[arg-type]


def test_two_machine_ids_with_identical_captured_fields_hash_differently() -> None:
    laptop = _fixture_fiche(machine_id="laptop-mobile-gpu")
    tower = _fixture_fiche(machine_id="tower-desktop-gpu")

    assert fiche_hash(laptop) != fiche_hash(tower)  # type: ignore[arg-type]


def test_projection_2_ignores_machine_and_mode_and_projection_3_requires_them() -> None:
    fiche = _fixture_fiche()
    without = {
        key: value
        for key, value in fiche.items()
        if key not in {"machine_id", "compute_mode"}
    }

    assert set(normalise_fiche(fiche, "3")) == set(FICHE_PROJECTIONS["3"])
    assert fiche_hash(fiche, "2") == fiche_hash(without, "2")
    assert fiche_hash(fiche, "2") == fiche_hash(
        {**fiche, "compute_mode": "cpu_only"}, "2"
    )
    with pytest.raises(FicheProjectionError, match="machine_id, compute_mode"):
        fiche_hash(without)


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
        engine_id="llama.cpp",
        engine_build="b10537",
        engine_config_hash="e" * 64,
        machine_id="laptop-mobile-gpu",
        compute_mode="cpu_only",
        profile_id="fake-entry@laptop-mobile-gpu/cpu_only",
        roster_entry_id="fake-entry",
        model_sha256="0" * 64,
        quant="UD-IQ4_XS",
        flags=["-ngl", "99"],
    )

    assert fiche["cpu"] == "x"
    assert fiche["profile_id"] == "fake-entry@laptop-mobile-gpu/cpu_only"
    assert fiche["engine_id"] == "llama.cpp"
    assert fiche["engine_build"] == "b10537"
    assert fiche["engine_config_hash"] == "e" * 64
    assert fiche["machine_id"] == "laptop-mobile-gpu"
    assert fiche["compute_mode"] == "cpu_only"
    assert fiche["roster_entry_id"] == "fake-entry"
    assert fiche["model_sha256"] == "0" * 64
    assert fiche["quant"] == "UD-IQ4_XS"
    assert fiche["flags"] == ["-ngl", "99"]


def test_renaming_a_profile_does_not_move_the_fiche_hash() -> None:
    """`profile_id` is evidence like `flags`, outside every projection."""
    machine = {
        "cpu": "x",
        "ram_gb": 32.0,
        "gpu_name": "y",
        "gpu_driver_version": "1.2.3",
        "os": "z",
        "cuda_ceiling": "12.4",
    }

    def fiche_named(profile_id: str) -> dict[str, object]:
        return dict(
            build_fiche(
                machine,  # type: ignore[arg-type]
                engine_id="llama.cpp",
                engine_build="b10537",
                engine_config_hash="e" * 64,
                machine_id="laptop-mobile-gpu",
                compute_mode="gpu",
                profile_id=profile_id,
                roster_entry_id="fake-entry",
                model_sha256="0" * 64,
                quant="UD-IQ4_XS",
                flags=["-ngl", "99"],
            )
        )

    original = fiche_named("fake-entry@laptop-mobile-gpu/gpu")
    renamed = fiche_named("a-renamed-profile")

    assert original["profile_id"] != renamed["profile_id"]
    for projection in FICHE_PROJECTIONS:
        assert "profile_id" not in FICHE_PROJECTIONS[projection]
    assert fiche_hash(original) == fiche_hash(renamed)
