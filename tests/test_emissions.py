import pytest

from wave_local_ai_v2.emissions import local_emissions, scope3_cloud_emissions


def test_local_emissions_multiplies_energy_by_the_configured_factor() -> None:
    assert local_emissions(0.002, 0.056039) == pytest.approx(0.000112078)


def test_local_emissions_is_none_when_energy_is_none() -> None:
    assert local_emissions(None, 0.056039) is None


def test_scope3_cloud_emissions_matches_hand_computed_values() -> None:
    energy_kwh, emissions_kg = scope3_cloud_emissions(
        total_tokens=1000, wh_per_token=0.0003, factor_kg_per_kwh=0.056039
    )

    # 1000 tokens * 0.0003 Wh/token / 1000 = 0.0003 kWh
    assert energy_kwh == pytest.approx(0.0003)
    assert emissions_kg == pytest.approx(0.0003 * 0.056039)
