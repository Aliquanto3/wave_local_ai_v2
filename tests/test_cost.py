import importlib
from pathlib import Path
from unittest.mock import patch

import pytest

from wave_local_ai_v2 import cost, google_client, mistral_client
from wave_local_ai_v2.cost import (
    GOOGLE_PRICE_TABLE,
    MISTRAL_PRICE_TABLE,
    NORMALIZATION_UNIT,
    PRICE_TABLES,
    CostTableError,
    cloud_cost,
    cost_per_million_tokens,
    local_cost,
    total_or_none,
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


def test_cost_per_million_tokens_is_none_on_unknown_cost() -> None:
    assert cost_per_million_tokens(None, 1000) is None


def test_the_price_table_is_keyed_by_a_literal_id_not_by_the_model_constant() -> None:
    # Keyed by the variable, the module's own import-time guard could never
    # fire and a model rotation would silently cost at the retired model's
    # rates. The literal key is what makes the guard falsifiable.
    for key in MISTRAL_PRICE_TABLE:
        assert isinstance(key, str)
    source = Path(cost.__file__).read_text(encoding="utf-8")
    assert '"mistral-small-2603": {' in source
    assert "mistral_client.MODEL: {" not in source
    assert '"gemini-3.5-flash-lite": {' in source
    assert "google_client.MODEL: {" not in source


def test_an_unpriced_model_is_refused_at_import_rather_than_costed_at_zero() -> None:
    try:
        # RuntimeError, not CostTableError: a reload defines a fresh exception
        # class, so the raised one is not the imported one by identity. Both
        # subclass RuntimeError, and the name is asserted below.
        with (
            patch.object(mistral_client, "MODEL", "mistral-not-in-the-table-2799"),
            pytest.raises(RuntimeError, match="mistral-not-in-the-table-2799") as exc,
        ):
            importlib.reload(cost)
        assert type(exc.value).__name__ == CostTableError.__name__
    finally:
        # The failed reload left the module half-built (every definition below
        # the guard is gone). Restore it under the real MODEL, whatever the
        # assertions above did.
        importlib.reload(cost)


def test_google_price_table_carries_one_dated_sourced_entry_for_the_model() -> None:
    price = GOOGLE_PRICE_TABLE[google_client.MODEL]

    assert price["input_per_million"] > 0
    assert price["output_per_million"] > 0
    assert price["currency"]
    assert price["retrieved_at"]


def test_price_tables_maps_provider_id_to_the_matching_table_by_identity() -> None:
    assert PRICE_TABLES["mistral"] is MISTRAL_PRICE_TABLE
    assert PRICE_TABLES["google"] is GOOGLE_PRICE_TABLE


def test_an_unpriced_google_model_is_refused_at_import_rather_than_costed_at_zero() -> (
    None
):
    try:
        with (
            patch.object(google_client, "MODEL", "gemini-not-in-the-table-2799"),
            pytest.raises(RuntimeError, match="gemini-not-in-the-table-2799") as exc,
        ):
            importlib.reload(cost)
        assert type(exc.value).__name__ == CostTableError.__name__
    finally:
        importlib.reload(cost)


def test_total_or_none_sums_when_every_sample_is_present() -> None:
    assert total_or_none([1, 2, 3]) == 6


def test_total_or_none_is_none_when_any_sample_is_absent() -> None:
    # Not 3: a partial sum published as a total understates a cost
    # denominator with nothing on the row saying a sample was missing.
    assert total_or_none([1, None, 2]) is None
