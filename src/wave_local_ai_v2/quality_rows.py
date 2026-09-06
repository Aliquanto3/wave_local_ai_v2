"""The per-batch energy/emissions/cost fields every quality row carries,
declared once for both CLIs that write quality rows.

`quality_cli.py`'s four batches (local, mistral, google) and `judge_probe.py`'s
two (local, google) derive the same block. A second copy would be a parallel
declaration of `row_contract`'s cost rules -- the `None`-makes-a-total-unknown
rule, the three price figures rather than one, the null halves a local row and
a cloud row each carry -- and the first divergence between the copies would
publish two different cost derivations under one schema version.

Both functions take their per-item completions structurally (`generated_tokens`
off a mapping), never a CLI's own `_Completion` type: this module is imported
by the CLIs, not the other way round.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from wave_local_ai_v2 import cost, emissions
from wave_local_ai_v2.energy import ENERGY_METHOD_UNAVAILABLE, EnergyResult
from wave_local_ai_v2.settings import Settings


def local_batch_fields(
    settings: Settings,
    energy: EnergyResult,
    completions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The per-batch energy/emissions/cost fields shared by every local row.

    tokens_in_total stays null: the local `/completion` path these suites call
    never captures a prompt-token count, so publishing one here would
    fabricate it (same honesty rule `__init__.py`'s runtime tokens_in_total
    follows).
    """
    emissions_kg = emissions.local_emissions(
        energy["energy_kwh"], settings.emission_factor_kg_per_kwh
    )
    cost_total = cost.local_cost(energy["energy_kwh"], settings.kwh_price_eur)
    tokens_out_total = sum(completion["generated_tokens"] for completion in completions)
    return {
        **energy,
        "emissions_kg": emissions_kg,
        "emission_factor_kg_per_kwh": settings.emission_factor_kg_per_kwh,
        "emission_region": settings.emission_region,
        "emissions_scope": emissions.EMISSIONS_SCOPE_2,
        "emissions_scope_formula_id": None,
        "scope_comparability": None,
        "tokens_in_total": None,
        "tokens_out_total": tokens_out_total,
        "cost_total": cost_total,
        "cost_currency": "EUR",
        # Derived, not hardcoded null: total_tokens is unknown while
        # tokens_in_total is, so the rate is undefined today -- but it starts
        # publishing on its own the day the local path captures prompt tokens.
        "cost_per_million_tokens": cost.cost_per_million_tokens(cost_total, None),
        "normalization_unit": cost.NORMALIZATION_UNIT,
        "kwh_price_eur": settings.kwh_price_eur,
        "kwh_price_currency": "EUR",
        "kwh_price_recorded_at": settings.kwh_price_recorded_at,
        "list_price_input_per_million": None,
        "list_price_output_per_million": None,
        "list_price_per_million_tokens": None,
        "list_price_currency": None,
        "list_price_retrieved_at": None,
    }


def cloud_batch_fields(
    settings: Settings,
    model: str,
    price_table: dict[str, cost.Price],
    prompt_tokens: list[int | None],
    completion_tokens_total: int,
) -> dict[str, Any]:
    """The per-batch energy/emissions/cost fields shared by every cloud row.

    Generic over `model`/`price_table` so one function serves both Mistral
    and Google rather than being copy-pasted per provider (plan.md's
    Decisions). No on-machine energy exists to attribute to a network call:
    the three CodeCarbon channels stay null/"unavailable", and
    energy_kwh/emissions_kg instead come from the Scope-3 Wh-per-token
    formula, keyed to this batch's total tokens.

    A `None` entry in `prompt_tokens` (an absent count on a real response)
    makes the batch's input token count unknown, not zero: every figure keyed
    to a token total -- the Scope-3 energy and emissions estimate, the cost,
    the normalized rate -- degrades to `None` rather than silently pricing
    the prompts at nothing. The price snapshot itself still lands on the row:
    it is what the provider charges, not something this batch derived.
    """
    prompt_tokens_total = cost.total_or_none(prompt_tokens)
    total_tokens = (
        prompt_tokens_total + completion_tokens_total
        if prompt_tokens_total is not None
        else None
    )
    price = price_table[model]
    if total_tokens is None or prompt_tokens_total is None:
        energy_kwh: float | None = None
        emissions_kg: float | None = None
        cost_total: float | None = None
    else:
        energy_kwh, emissions_kg = emissions.scope3_cloud_emissions(
            total_tokens,
            settings.scope3_wh_per_token,
            settings.emission_factor_kg_per_kwh,
        )
        cost_total = cost.cloud_cost(
            prompt_tokens_total, completion_tokens_total, price
        )
    # Three price figures, not one: the two rates the table actually charges,
    # so a reader can recompute cost_total from tokens_in_total and
    # tokens_out_total a year later, plus the blended rate this batch's own
    # token mix worked out to. The blend alone is derived FROM cost_total, so
    # publishing only it would be circular.
    return {
        "cpu_energy_kwh": None,
        "cpu_energy_method": ENERGY_METHOD_UNAVAILABLE,
        "gpu_energy_kwh": None,
        "gpu_energy_method": ENERGY_METHOD_UNAVAILABLE,
        "ram_energy_kwh": None,
        "ram_energy_method": ENERGY_METHOD_UNAVAILABLE,
        "energy_kwh": energy_kwh,
        "emissions_kg": emissions_kg,
        "emission_factor_kg_per_kwh": settings.emission_factor_kg_per_kwh,
        "emission_region": settings.emission_region,
        "emissions_scope": emissions.EMISSIONS_SCOPE_3,
        "emissions_scope_formula_id": emissions.SCOPE3_FORMULA_ID,
        "scope_comparability": emissions.SCOPE_COMPARABILITY_NOTE,
        "tokens_in_total": prompt_tokens_total,
        "tokens_out_total": completion_tokens_total,
        "cost_total": cost_total,
        # The currency the price table quotes, published even when cost_total
        # is null: it names the unit the list-price fields beside it are in.
        "cost_currency": price["currency"],
        "cost_per_million_tokens": cost.cost_per_million_tokens(
            cost_total, total_tokens
        ),
        "normalization_unit": cost.NORMALIZATION_UNIT,
        "kwh_price_eur": None,
        "kwh_price_currency": None,
        "kwh_price_recorded_at": None,
        "list_price_input_per_million": price["input_per_million"],
        "list_price_output_per_million": price["output_per_million"],
        "list_price_per_million_tokens": cost.cost_per_million_tokens(
            cost_total, total_tokens
        ),
        "list_price_currency": price["currency"],
        "list_price_retrieved_at": price["retrieved_at"],
    }
