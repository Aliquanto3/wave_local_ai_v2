from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2.energy import measure_energy


def _fake_emissions_data(
    *,
    cpu_energy: float = 0.0007,
    gpu_energy: float = 0.0,
    ram_energy: float = 0.0001,
    gpu_count: int = 0,
    energy_consumed: float = 0.001,
) -> MagicMock:
    data = MagicMock()
    data.cpu_energy = cpu_energy
    data.gpu_energy = gpu_energy
    data.ram_energy = ram_energy
    data.gpu_count = gpu_count
    data.energy_consumed = energy_consumed
    return data


def test_measure_energy_tags_measured_nvml_when_gpu_present() -> None:
    fake_tracker = MagicMock()
    fake_tracker.final_emissions_data = _fake_emissions_data(
        cpu_energy=0.0007, gpu_energy=0.0005, ram_energy=0.0001, gpu_count=1
    )

    with patch("codecarbon.OfflineEmissionsTracker", return_value=fake_tracker):
        result, energy = measure_energy(lambda: "done", country_iso_code="FRA")

    assert result == "done"
    assert energy["cpu_energy_kwh"] == 0.0007
    assert energy["cpu_energy_method"] == "estimated_tdp"
    assert energy["gpu_energy_kwh"] == 0.0005
    assert energy["gpu_energy_method"] == "measured_nvml"
    assert energy["ram_energy_kwh"] == 0.0001
    assert energy["ram_energy_method"] == "estimated_constant"
    assert energy["energy_kwh"] == 0.001


def test_measure_energy_tags_gpu_unavailable_when_no_gpu_detected() -> None:
    # gpu_count=0 with a nonzero gpu_energy: availability (not magnitude)
    # decides the label, and an absent GPU is never a labelled zero.
    fake_tracker = MagicMock()
    fake_tracker.final_emissions_data = _fake_emissions_data(
        cpu_energy=0.0007, gpu_energy=0.0, ram_energy=0.0001, gpu_count=0
    )

    with patch("codecarbon.OfflineEmissionsTracker", return_value=fake_tracker):
        result, energy = measure_energy(lambda: "done", country_iso_code="FRA")

    assert result == "done"
    assert energy["gpu_energy_kwh"] is None
    assert energy["gpu_energy_method"] == "unavailable"
    assert energy["cpu_energy_method"] == "estimated_tdp"
    assert energy["ram_energy_method"] == "estimated_constant"


def test_measure_energy_falls_back_to_unavailable_on_tracker_init_failure() -> None:
    with patch("codecarbon.OfflineEmissionsTracker", side_effect=RuntimeError("boom")):
        result, energy = measure_energy(lambda: "done", country_iso_code="FRA")

    assert result == "done"
    assert energy["cpu_energy_kwh"] is None
    assert energy["cpu_energy_method"] == "unavailable"
    assert energy["gpu_energy_kwh"] is None
    assert energy["gpu_energy_method"] == "unavailable"
    assert energy["ram_energy_kwh"] is None
    assert energy["ram_energy_method"] == "unavailable"
    assert energy["energy_kwh"] is None


def test_measure_energy_keeps_the_result_when_the_tracker_fails_to_stop() -> None:
    fake_tracker = MagicMock()
    fake_tracker.stop.side_effect = RuntimeError("teardown boom")
    fake_tracker.final_emissions_data = _fake_emissions_data(gpu_count=1)

    with patch("codecarbon.OfflineEmissionsTracker", return_value=fake_tracker):
        result, energy = measure_energy(lambda: "done", country_iso_code="FRA")

    assert result == "done"
    # Not the partial figures sitting in final_emissions_data: a tracker that
    # failed to stop has no trustworthy total.
    assert energy["cpu_energy_kwh"] is None
    assert energy["cpu_energy_method"] == "unavailable"
    assert energy["gpu_energy_kwh"] is None
    assert energy["gpu_energy_method"] == "unavailable"
    assert energy["ram_energy_kwh"] is None
    assert energy["ram_energy_method"] == "unavailable"
    assert energy["energy_kwh"] is None


def test_measure_energy_propagates_the_measured_functions_exception() -> None:
    fake_tracker = MagicMock()
    fake_tracker.stop.side_effect = RuntimeError("teardown boom")

    def failing() -> str:
        raise ValueError("the request failed")

    with (
        patch("codecarbon.OfflineEmissionsTracker", return_value=fake_tracker),
        pytest.raises(ValueError, match="the request failed"),
    ):
        measure_energy(failing, country_iso_code="FRA")
