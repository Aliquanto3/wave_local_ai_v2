"""Cost: the two derivations (cloud list-price, local kWh-price), the
normalization unit, and the per-provider price tables.

No live pricing API exists for either provider; the tables below are
manually retrieved snapshots, dated.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any, TypedDict

from wave_local_ai_v2 import google_client, mistral_client

NORMALIZATION_UNIT = "cost_per_million_total_tokens"


class Price(TypedDict):
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
MISTRAL_PRICE_TABLE: dict[str, Price] = {
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

# Keyed by the literal id, never by `google_client.MODEL`, same rule and same
# reason as MISTRAL_PRICE_TABLE above. Paid Standard tier -- the tier this
# project's key is served on -- confirmed against Google's list price on
# 2026-08-27 (aidd_docs/memory/external/google-ai-studio-api.md). Free-tier
# runs cost nothing; that fact belongs on the row, not implied by a zero rate
# here.
GOOGLE_PRICE_TABLE: dict[str, Price] = {
    "gemini-3.5-flash-lite": {
        "input_per_million": 0.30,
        "output_per_million": 2.50,
        "currency": "USD",
        "retrieved_at": "2026-08-27",
    },
}

if google_client.MODEL not in GOOGLE_PRICE_TABLE:
    raise CostTableError(
        f"GOOGLE_PRICE_TABLE has no entry for google_client.MODEL "
        f"({google_client.MODEL!r}) -- add one before costing a batch run"
    )

# Generic per-provider lookup for quality_cli's cloud dispatch table.
# MISTRAL_PRICE_TABLE and GOOGLE_PRICE_TABLE stay public and unchanged in
# shape -- this is an additional view onto them, not a replacement.
PRICE_TABLES: dict[str, dict[str, Price]] = {
    "mistral": MISTRAL_PRICE_TABLE,
    "google": GOOGLE_PRICE_TABLE,
}

# Whether a provider bills reasoning tokens inside its reported output count
# or beside it. Keyed like PRICE_TABLES, and declared rather than inferred:
# getting this wrong either prices a reasoning token twice or not at all.
#
# - mistral: ASSUMED, not confirmed against a live reasoning call or
#   Mistral's billing documentation. Inferred from the usage block carrying
#   prompt/completion/total and no reasoning counter (`mistral_client`'s
#   docstring): if Mistral bills any reasoning, the only count it could be
#   billed under is `completion_tokens`. Revisit if a Mistral judge or
#   subject is ever sent a reasoning-effort control.
# - google: `thoughtsTokenCount` is billed on top of `candidatesTokenCount`
#   (aidd_docs/memory/external/google-ai-studio-api.md: the cost input
#   becomes `candidatesTokenCount + thoughtsTokenCount`). On the pinned
#   model, which reports no `thoughtsTokenCount`, the count is derived from
#   the response's own totals (`google_client._reasoning_tokens`), so the
#   cost stays reportable.
REASONING_BILLED_INSIDE_OUTPUT = "inside_output"
REASONING_BILLED_BESIDE_OUTPUT = "beside_output"
REASONING_TOKEN_BILLING_BASES = (
    REASONING_BILLED_INSIDE_OUTPUT,
    REASONING_BILLED_BESIDE_OUTPUT,
)

REASONING_TOKEN_BILLING: dict[str, str] = {
    "mistral": REASONING_BILLED_INSIDE_OUTPUT,
    "google": REASONING_BILLED_BESIDE_OUTPUT,
}


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


def cloud_cost(prompt_tokens: int, completion_tokens: int, price: Price) -> float:
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


def judge_cost_fields(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Cost a row's judge calls at each judge provider's own table rates.

    Takes `judge.JudgeCallRecord`s structurally rather than by type, so this
    module keeps importing no judge module and the judge path keeps importing
    this one. Returns the row's `judge_cost` record: the aggregate token
    counts and cost, plus one `per_provider` entry carrying that provider's
    tokens, its cost, and the two rates and retrieval date it was charged at
    -- everything a reader needs to recompute the figure.

    The row's own `cost_total` is untouched by this: it stays the subject
    generation's cost, priced at the subject provider's rates. Summing a
    Google judge's tokens into a Mistral subject's `cost_total` would break
    the contract rule that a non-null `cost_total` is recomputable from the
    row's own `list_price_*` rates.

    Reasoning tokens are reported per provider beside output tokens, with
    the basis that provider bills them on, and priced exactly once: under
    `inside_output` they are already in `tokens_out` and add nothing; under
    `beside_output` they are added to the output tokens charged. A null
    reasoning count billed beside output makes that provider's cost `None`,
    the same unknown-not-smaller rule as a missing token count; billed inside
    output it moves nothing.

    A model id absent from its provider's price table raises `CostTableError`
    naming it -- never a default-costed zero, the same rule the import-time
    guards above already enforce. One missing token count makes that
    provider's total, and therefore the aggregate `cost_total`, `None` rather
    than smaller (`total_or_none`). Two price tables in different currencies
    are refused rather than summed; both are USD today, so this guards a
    future table rather than anything shipped.
    """
    grouped: dict[tuple[str, str], list[Mapping[str, Any]]] = {}
    for record in records:
        grouped.setdefault((record["provider"], record["model_id"]), []).append(record)

    per_provider: list[dict[str, Any]] = []
    currencies: set[str] = set()
    for (provider, model_id), group in sorted(grouped.items()):
        table = PRICE_TABLES.get(provider)
        if table is None:
            raise CostTableError(
                f"no price table for judge provider {provider!r} "
                f"(known: {', '.join(sorted(PRICE_TABLES))})"
            )
        price = table.get(model_id)
        if price is None:
            raise CostTableError(
                f"{provider} price table has no entry for judge model "
                f"{model_id!r} -- add one before costing a judged row"
            )

        billing = REASONING_TOKEN_BILLING.get(provider)
        if billing is None:
            raise CostTableError(
                f"no reasoning-token billing basis for judge provider "
                f"{provider!r} -- declare whether it bills reasoning inside "
                "or beside its output count before costing a judged row"
            )

        tokens_in = total_or_none(record["tokens_in"] for record in group)
        tokens_out = total_or_none(record["tokens_out"] for record in group)
        reasoning_tokens = total_or_none(record["reasoning_tokens"] for record in group)
        null_reasons = sorted(
            {
                record["reasoning_tokens_null_reason"]
                for record in group
                if record["reasoning_tokens"] is None
            }
        )
        billed_out: int | None
        if billing == REASONING_BILLED_INSIDE_OUTPUT or tokens_out is None:
            billed_out = tokens_out
        elif reasoning_tokens is None:
            billed_out = None
        else:
            billed_out = tokens_out + reasoning_tokens
        provider_cost = (
            None
            if tokens_in is None or billed_out is None
            else cloud_cost(tokens_in, billed_out, price)
        )
        currencies.add(price["currency"])
        per_provider.append(
            {
                "provider": provider,
                "model_id": model_id,
                "tokens_in": tokens_in,
                "tokens_out": tokens_out,
                "reasoning_tokens": reasoning_tokens,
                "reasoning_tokens_null_reason": (
                    ", ".join(null_reasons) if null_reasons else None
                ),
                "reasoning_tokens_billing": billing,
                "cost_total": provider_cost,
                "list_price_input_per_million": price["input_per_million"],
                "list_price_output_per_million": price["output_per_million"],
                "list_price_retrieved_at": price["retrieved_at"],
            }
        )

    if len(currencies) > 1:
        raise CostTableError(
            f"judge calls priced in more than one currency "
            f"({', '.join(sorted(currencies))}): a single cost_total across "
            "two currencies would be a number with no unit"
        )

    provider_costs = [entry["cost_total"] for entry in per_provider]
    return {
        "tokens_in_total": total_or_none(record["tokens_in"] for record in records),
        "tokens_out_total": total_or_none(record["tokens_out"] for record in records),
        # `not provider_costs` first: no judge call is an unknown cost, not a
        # free one, and `sum([])` would publish it as 0.0.
        "cost_total": (
            None
            if not provider_costs or any(value is None for value in provider_costs)
            else sum(provider_costs)
        ),
        "cost_currency": next(iter(currencies), None),
        "per_provider": per_provider,
    }
