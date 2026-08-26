"""Cost: the two derivations (cloud list-price, local kWh-price), the
normalization unit, and the Mistral price table.

No live Mistral price API exists; the table below is a manually retrieved
snapshot, dated.
"""

from __future__ import annotations

from typing import TypedDict

from wave_local_ai_v2 import mistral_client

NORMALIZATION_UNIT = "cost_per_million_total_tokens"


class MistralPrice(TypedDict):
    input_per_million: float
    output_per_million: float
    currency: str
    retrieved_at: str


class CostTableError(RuntimeError):
    """Raised when a model id has no entry in MISTRAL_PRICE_TABLE."""


# mistral-small-2603: $0.15/M input, $0.60/M output, confirmed against
# https://openrouter.ai/mistralai/mistral-small-2603 (mirroring Mistral's own
# published rate) on 2026-08-26.
MISTRAL_PRICE_TABLE: dict[str, MistralPrice] = {
    mistral_client.MODEL: {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
        "currency": "USD",
        "retrieved_at": "2026-08-26",
    },
}

if mistral_client.MODEL not in MISTRAL_PRICE_TABLE:
    # Raised at import time, not per-lookup: a caller that indexes
    # MISTRAL_PRICE_TABLE[mistral_client.MODEL] directly (quality_cli.py)
    # would otherwise get a bare KeyError instead of a named failure, or --
    # worse -- a future caller could default-cost a missing entry at 0.
    raise CostTableError(
        f"MISTRAL_PRICE_TABLE has no entry for mistral_client.MODEL "
        f"({mistral_client.MODEL!r}) -- add one before costing a batch run"
    )


def cloud_cost(
    prompt_tokens: int, completion_tokens: int, price: MistralPrice
) -> float:
    """Total cost of a cloud batch from its token counts and list price."""
    return (
        prompt_tokens / 1e6 * price["input_per_million"]
        + completion_tokens / 1e6 * price["output_per_million"]
    )


def local_cost(energy_kwh: float | None, kwh_price: float) -> float | None:
    """Total cost of a local run from its measured energy and the kWh price.

    Returns `None` when `energy_kwh` is `None` (mirrors `emissions.local_emissions`).
    """
    if energy_kwh is None:
        return None
    return energy_kwh * kwh_price


def cost_per_million_tokens(
    cost_total: float, total_tokens: int | None
) -> float | None:
    """Normalize `cost_total` to a per-million-token rate.

    Returns `None` when `total_tokens` is `None` or `0` -- undefined, not a
    fabricated `0.0` or a `ZeroDivisionError` (same rule `aggregation.spread`
    applies to a zero median).
    """
    if not total_tokens:
        return None
    return cost_total / total_tokens * 1_000_000
