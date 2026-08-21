from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2.energy import measure_energy


def _fake_emissions_data(
    gpu_energy: float, energy_consumed: float = 0.001
) -> MagicMock:
    data = MagicMock()
    data.gpu_energy = gpu_energy
    data.energy_consumed = energy_consumed
    return data


def test_measure_energy_tags_measured_nvml_when_gpu_energy_present() -> None:
    fake_tracker = MagicMock()
    fake_tracker.final_emissions_data = _fake_emissions_data(gpu_energy=0.0005)

    with patch("codecarbon.EmissionsTracker", return_value=fake_tracker):
        result, energy = measure_energy(lambda: "done")

    assert result == "done"
    assert energy["energy_method"] == "measured_nvml"
    assert energy["energy_kwh"] == 0.001


def test_measure_energy_tags_estimated_tdp_when_no_gpu_energy() -> None:
    fake_tracker = MagicMock()
    fake_tracker.final_emissions_data = _fake_emissions_data(gpu_energy=0.0)

    with patch("codecarbon.EmissionsTracker", return_value=fake_tracker):
        result, energy = measure_energy(lambda: "done")

    assert result == "done"
    assert energy["energy_method"] == "estimated_tdp"


def test_measure_energy_falls_back_to_unavailable_on_tracker_init_failure() -> None:
    with patch("codecarbon.EmissionsTracker", side_effect=RuntimeError("boom")):
        result, energy = measure_energy(lambda: "done")

    assert result == "done"
    assert energy["energy_kwh"] is None
    assert energy["energy_method"] == "unavailable"


def test_measure_energy_keeps_the_result_when_the_tracker_fails_to_stop() -> None:
    fake_tracker = MagicMock()
    fake_tracker.stop.side_effect = RuntimeError("teardown boom")
    fake_tracker.final_emissions_data = _fake_emissions_data(gpu_energy=0.0005)

    with patch("codecarbon.EmissionsTracker", return_value=fake_tracker):
        result, energy = measure_energy(lambda: "done")

    assert result == "done"
    assert energy["energy_kwh"] is None
    # Not the partial figure sitting in final_emissions_data: a tracker that
    # failed to stop has no trustworthy total.
    assert energy["energy_method"] == "unavailable"


def test_measure_energy_propagates_the_measured_functions_exception() -> None:
    fake_tracker = MagicMock()
    fake_tracker.stop.side_effect = RuntimeError("teardown boom")

    def failing() -> str:
        raise ValueError("the request failed")

    with (
        patch("codecarbon.EmissionsTracker", return_value=fake_tracker),
        pytest.raises(ValueError, match="the request failed"),
    ):
        measure_energy(failing)
