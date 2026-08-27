"""Cost: the two derivations (cloud list-price, local kWh-price), the
normalization unit, and the Mistral price table.

No live Mistral price API exists; the table below is a manually retrieved
snapshot, dated.
"""

from __future__ import annotations

from collections.abc import Iterable
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


# Keyed by the literal dated model id, never by `mistral_client.MODEL`: keying
# by the variable would make the guard below unfalsifiable and let a model
# rotation silently cost the new model at the retired model's rates.
#
# mistral-small-2603: $0.15/M input, $0.60/M output, confirmed against
# Mistral's own https://mistral.ai/pricing/api on 2026-08-27. That page lists
# the rate against the `mistral-small-latest` alias ("Mistral Small 4"); this
# project pins the dated id the alias resolved to when it was read live
# (see mistral_client.py's docstring), so the rate is recorded here against
# the dated id it was actually charged for.
MISTRAL_PRICE_TABLE: dict[str, MistralPrice] = {
    "mistral-small-2603": {
        "input_per_million": 0.15,
        "output_per_million": 0.60,
        "currency": "USD",
        "retrieved_at": "2026-08-27",
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


def total_or_none(values: Iterable[int | None]) -> int | None:
    """Sum `values`, or `None` if any one of them is absent.

    Not "sum what is there": a partial sum published as a total is the
    understated-figure failure the row contract exists to prevent, and a token
    total is a cost denominator. One missing sample makes the total unknown,
    not smaller. Deliberately stricter than `aggregation.peak`, which reports
    a maximum over the samples that did read: a peak over fewer samples is
    still a real observed maximum, a sum over fewer samples is not a total.
    """
    materialized = list(values)
    if any(value is None for value in materialized):
        return None
    return sum(value for value in materialized if value is not None)


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
    cost_total: float | None, total_tokens: int | None
) -> float | None:
    """Normalize `cost_total` to a per-million-token rate.

    Returns `None` when `cost_total` is `None`, or when `total_tokens` is
    `None` or `0` -- undefined, not a fabricated `0.0` or a
    `ZeroDivisionError` (same rule `aggregation.spread` applies to a zero
    median). Every rate this project publishes per million tokens goes
    through here, so no call site re-derives the division and re-introduces
    the zero-denominator case.
    """
    if cost_total is None or not total_tokens:
        return None
    return cost_total / total_tokens * 1_000_000
