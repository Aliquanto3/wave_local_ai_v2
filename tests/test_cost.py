import pytest

from wave_local_ai_v2 import mistral_client
from wave_local_ai_v2.cost import (
    MISTRAL_PRICE_TABLE,
    NORMALIZATION_UNIT,
    cloud_cost,
    cost_per_million_tokens,
    local_cost,
)


def test_cloud_cost_matches_hand_computed_price() -> None:
    price = MISTRAL_PRICE_TABLE[mistral_client.MODEL]

    cost = cloud_cost(prompt_tokens=1000, completion_tokens=500, price=price)

    expected = (
        1000 / 1e6 * price["input_per_million"]
        + 500 / 1e6 * price["output_per_million"]
    )
    assert cost == pytest.approx(expected)


def test_local_cost_multiplies_energy_by_the_kwh_price() -> None:
    assert local_cost(0.002, 0.194) == pytest.approx(0.002 * 0.194)


def test_local_cost_is_none_when_energy_is_none() -> None:
    assert local_cost(None, 0.194) is None


def test_cost_per_million_tokens_matches_hand_computed_value() -> None:
    assert cost_per_million_tokens(0.5, 1000) == pytest.approx(500.0)


def test_cost_per_million_tokens_is_none_on_zero_total_tokens() -> None:
    assert cost_per_million_tokens(0.5, 0) is None


def test_cost_per_million_tokens_is_none_on_unknown_total_tokens() -> None:
    assert cost_per_million_tokens(0.5, None) is None


def test_mistral_price_table_carries_one_dated_sourced_entry_for_the_model() -> None:
    price = MISTRAL_PRICE_TABLE[mistral_client.MODEL]

    assert price["input_per_million"] > 0
    assert price["output_per_million"] > 0
    assert price["currency"]
    assert price["retrieved_at"]


def test_normalization_unit_is_the_named_constant() -> None:
    assert NORMALIZATION_UNIT == "cost_per_million_total_tokens"
