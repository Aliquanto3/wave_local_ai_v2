"""The per-batch energy/emissions/cost fields and the per-item suite-level
fields every quality row carries, declared once for both CLIs that write
quality rows.

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
from types import MappingProxyType
from typing import Any

from wave_local_ai_v2 import cost, emissions, harness, roster, row_contract, timings
from wave_local_ai_v2.energy import ENERGY_METHOD_UNAVAILABLE, EnergyResult
from wave_local_ai_v2.engines import EngineFicheFields
from wave_local_ai_v2.settings import Settings
from wave_local_ai_v2.suite_gate import SuiteGateResult

# What a cloud subject's quality row carries for the engine: no local engine
# produced it, which the row states rather than leaving null.
ENGINE_NOT_APPLICABLE_FIELDS: Mapping[str, str | None] = MappingProxyType(
    {"engine_id": row_contract.ENGINE_NOT_APPLICABLE, "engine_build": None}
)


def local_engine_fields(fiche_fields: EngineFicheFields) -> dict[str, str | None]:
    """The two engine fields a local row carries, read off its own fiche's."""
    return {
        "engine_id": fiche_fields["engine_id"],
        "engine_build": fiche_fields["engine_build"],
    }


def suite_item_fields(
    gate_result: SuiteGateResult, item: Mapping[str, Any]
) -> dict[str, Any]:
    """The level the suite was certified at and the item's own licence and
    source declarations, as one quality row carries them.

    The level is the gate's certified one, never the suite's raw
    declaration: the two are equal only because the gate refuses a suite
    that falls short. An item that declares no source (a hand-written one)
    publishes `None`, a recorded absence, never an invented provenance.
    """
    return {
        "suite_level": gate_result["level"],
        "item_licence": item.get("licence"),
        "item_source": item.get("source"),
        "item_source_revision": item.get("source_revision"),
    }


def subject_composition_fields(
    model_id: str, provider: str, roster_entry: roster.RosterEntry
) -> dict[str, Any]:
    """The subject's family and size class, as one quality row carries them
    (schema "19").

    A local row's subject is `roster_entry` itself: its family resolves
    through the entry (the flagship through the in-code fallback, with no
    exception carved out) and its size class is the entry's declaration. A
    cloud row cites the local entry only as the one it ran beside, so its
    family is its own model's and its size class is `None`: a cloud model is
    not banded.
    """
    if provider == row_contract.SUBJECT_PROVIDER_LOCAL:
        return {
            "family": roster.family_of(model_id, roster_entry),
            "size_class": roster_entry.size_class,
        }
    return {"family": roster.family_of(model_id), "size_class": None}


def item_measurement_fields(
    measurement: timings.ItemMeasurement, *, first_in_batch: bool
) -> dict[str, Any]:
    """The per-item measurement block one quality row carries (schema "18").

    The item's own tokens in and out, its engine-reported first-token time
    under its `ttft_source` label, and the prompt tokens the engine reused
    from its cache, each a value or null with its reason. Labelled a single
    per-item generation (no warm-up exclusion, no repetitions), so it is
    never read as Methodology 6's runtime figure, and the batch's first
    generation -- the one a freshly launched server served cold -- is marked
    so a reader can exclude it.
    """
    return {
        "item_tokens_in": measurement["tokens_in"],
        "item_tokens_in_null_reason": measurement["tokens_in_null_reason"],
        "item_tokens_out": measurement["tokens_out"],
        "item_tokens_out_null_reason": measurement["tokens_out_null_reason"],
        "item_ttft_ms": measurement["ttft_ms"],
        "item_ttft_ms_null_reason": measurement["ttft_ms_null_reason"],
        "item_ttft_source": measurement["ttft_source"],
        "item_prompt_tokens_cached": measurement["prompt_tokens_cached"],
        "item_prompt_tokens_cached_null_reason": measurement[
            "prompt_tokens_cached_null_reason"
        ],
        "item_measurement_kind": timings.ITEM_MEASUREMENT_SINGLE_GENERATION,
        "item_first_in_batch": first_in_batch,
    }


def direct_harness_fields(
    measurement: timings.ItemMeasurement, item_prompt_tokens: int | None
) -> dict[str, Any]:
    """The harness block a `direct` row carries (schema "20").

    `direct` sends the item's own rendered prompt and nothing around it, so
    it wraps the item trivially and the rule measures it like any wrapper:
    the engine's own prompt-token count (`measurement`'s, the row's
    `item_tokens_in`) minus `item_prompt_tokens`, the item's rendered prompt
    -- tool definitions included -- counted under the same tokenizer. A
    cloud subject has no such count (`None`), and its overhead is null with
    that reason rather than an assumed zero.
    """
    return harness.row_fields(
        harness.HARNESS_DIRECT,
        harness.prompt_overhead(
            engine_prompt_tokens=measurement["tokens_in"],
            engine_null_reason=measurement["tokens_in_null_reason"],
            item_prompt_tokens=item_prompt_tokens,
            wraps_item_prompt=True,
        ),
    )


def cloud_item_measurement(
    prompt_tokens: int | None, generated_tokens: int | None, *, called: bool = True
) -> timings.ItemMeasurement:
    """One cloud item's measurement: the provider's own per-call token counts.

    A cloud provider reports no first-token time and no prompt-cache count, so
    both are null with `not_reported_by_provider`; a token count the response
    did not carry is null with the same reason. An item refused before any
    generation call (`called=False`, Google's context pre-flight) has nothing
    to report at all: every value is null with `no_generation_call`.
    """
    if not called:
        absent = timings.ITEM_NULL_NO_GENERATION_CALL
        prompt_tokens = generated_tokens = None
    else:
        absent = timings.ITEM_NULL_NOT_REPORTED_BY_PROVIDER
    return timings.ItemMeasurement(
        tokens_in=prompt_tokens,
        tokens_in_null_reason=absent if prompt_tokens is None else None,
        tokens_out=generated_tokens,
        tokens_out_null_reason=absent if generated_tokens is None else None,
        ttft_ms=None,
        ttft_ms_null_reason=absent,
        ttft_source=None,
        prompt_tokens_cached=None,
        prompt_tokens_cached_null_reason=absent,
    )


def local_batch_fields(
    settings: Settings,
    energy: EnergyResult,
    completions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """The per-batch energy/emissions/cost fields shared by every local row.

    `tokens_in_total` is the batch's prompt-token total when the completions
    carry one and `None` when they do not. The local chat endpoint reports it
    in `usage`; the raw `/completion` path never did, which is why this field
    was hardcoded null until the subject path moved. A completion missing the
    count makes the total unknown rather than zero, the same
    `cost.total_or_none` rule the cloud batch follows -- a batch is never
    priced as if its prompts were free.
    """
    emissions_kg = emissions.local_emissions(
        energy["energy_kwh"], settings.emission_factor_kg_per_kwh
    )
    cost_total = cost.local_cost(energy["energy_kwh"], settings.kwh_price_eur)
    tokens_out_total = sum(completion["generated_tokens"] for completion in completions)
    tokens_in_total = cost.total_or_none(
        completion.get("prompt_tokens") for completion in completions
    )
    total_tokens = (
        tokens_in_total + tokens_out_total if tokens_in_total is not None else None
    )
    return {
        **energy,
        "emissions_kg": emissions_kg,
        "emission_factor_kg_per_kwh": settings.emission_factor_kg_per_kwh,
        "emission_region": settings.emission_region,
        "emissions_scope": emissions.EMISSIONS_SCOPE_2,
        "emissions_scope_formula_id": None,
        "scope_comparability": None,
        "tokens_in_total": tokens_in_total,
        "tokens_out_total": tokens_out_total,
        "cost_total": cost_total,
        "cost_currency": "EUR",
        # Derived, never hardcoded: this stayed null for as long as
        # tokens_in_total did, and started publishing on its own the day the
        # local path began capturing prompt tokens.
        "cost_per_million_tokens": cost.cost_per_million_tokens(
            cost_total, total_tokens
        ),
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
