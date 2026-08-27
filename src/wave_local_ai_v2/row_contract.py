"""The row contract: one required-field list per row kind, extended by every
later story rather than duplicated.

`append_row` (`results.py`) gates on `validate_row` before writing a line, so
an incomplete row can never land on disk. A key present with value `None` is
not missing -- several fields degrade to an explicit `None` on capture failure
(`hardware.py`, `timings.py`, `gpu.py`, `energy.py`) and are still complete.
"""

from __future__ import annotations

from typing import Any, Literal

from wave_local_ai_v2 import aggregation, prompt_provenance, timings

# "2": the runtime row's shape changed incompatibly (a scalar `gen_tok_per_s`
# became a median over a repetition set). Quality rows move to "2" with it
# because the constant is shared -- splitting into per-kind versions is out
# of scope for this increment.
# "3": `fiche_hash` and `verdict` became required on both row kinds, and the
# ten flattened hardware/run fields left the runtime row (fiche_hash-reproduction-
# verdict increment).
# "4": `energy_method` is gone, replaced by three independently-labelled
# per-channel energy fields plus emissions/scope fields, on both row kinds
# (Story 15: rows-carry-per-channel-energy-emissions-and-their-scope-boundary).
# "5": twelve cost + derivation-input fields became required on both row
# kinds (Story 16: rows-carry-a-cost-and-what-it-was-derived-from).
# "6": `list_price_input_per_million` and `list_price_output_per_million`
# became required on both row kinds. `list_price_per_million_tokens` alone is
# a blended effective rate derived FROM cost_total, so a row carrying only it
# could not recompute its own cost -- the two rates the price table actually
# charges have to be on the row for Story 16's "carries what it was derived
# from" to hold.
# "7": `language_breakdown` (per-language accuracy/n/indicative) became
# required on quality rows (Story 20: the-classification-suite-reaches-
# twenty-items-across-three-languages).
SCHEMA_VERSION = "7"

# The schema version at which `fiche_hash` (and `verdict`) became required.
# Fixed at "3" regardless of future `SCHEMA_VERSION` bumps: a stored row whose
# own `schema_version` is below this predates the fiche-hash contract
# entirely, so its missing `fiche_hash` is not an integrity failure the
# validator should treat as fatal (`fiche_validator.py`'s `legacy` class).
FICHE_HASH_SCHEMA_VERSION = "3"

RowKind = Literal["runtime", "quality"]

REQUIRED_FIELDS: dict[RowKind, frozenset[str]] = {
    "runtime": frozenset(
        {
            "schema_version",
            "run_id",
            "captured_at",
            # provenance.capture_provenance
            "release_version",
            "commit_sha",
            "tree_dirty",
            # roster.load_roster / roster.resolve_entry
            "roster_entry_id",
            "roster_version",
            # prompt_provenance: call-path identity
            "endpoint",
            "prompt_template_id",
            "prompt_template_hash",
            "prompt_capture",
            # fiche_registry: the hardware + run-specific fiche, cited by hash
            "fiche_hash",
            # verdict.runtime_verdict
            "verdict",
            "prompt",
            "max_tokens",
            "wall_clock_s",
            # timings.Timings
            "ttft_ms",
            "prompt_tok_per_s",
            "gen_tok_per_s",
            "ttft_source",
            # gpu.GpuStats
            "vram_used_mib",
            "gpu_draw_w",
            "process_rss_bytes",
            # energy.EnergyResult
            "cpu_energy_kwh",
            "cpu_energy_method",
            "gpu_energy_kwh",
            "gpu_energy_method",
            "ram_energy_kwh",
            "ram_energy_method",
            "energy_kwh",
            # emissions.local_emissions / emissions.scope3_cloud_emissions
            "emissions_kg",
            "emission_factor_kg_per_kwh",
            "emission_region",
            "emissions_scope",
            "emissions_scope_formula_id",
            "scope_comparability",
            # cost.cloud_cost / cost.local_cost / cost.cost_per_million_tokens
            "tokens_in_total",
            "tokens_out_total",
            "cost_total",
            "cost_currency",
            "cost_per_million_tokens",
            "normalization_unit",
            "kwh_price_eur",
            "kwh_price_currency",
            "kwh_price_recorded_at",
            # The two rates the price table charges, plus the blended
            # effective rate this batch's own token mix worked out to.
            "list_price_input_per_million",
            "list_price_output_per_million",
            "list_price_per_million_tokens",
            "list_price_currency",
            "list_price_retrieved_at",
            # repetitions.run_repetition_set / __init__._run
            "sampling",
            "seed_pinned",
            "warmup_count",
            "warmup_repetitions",
            "restart_between_repetitions",
            "cooldown_s",
            "repetitions_n",
            "slot_reset_method",
            "repetitions",
            # aggregation.aggregate_timings / aggregation.AGGREGATION_LABELS
            "aggregation",
            "ttft_ms_mean",
            "ttft_ms_sd",
            "ttft_ms_spread",
            "prompt_tok_per_s_mean",
            "prompt_tok_per_s_sd",
            "prompt_tok_per_s_spread",
            "gen_tok_per_s_mean",
            "gen_tok_per_s_sd",
            "gen_tok_per_s_spread",
            "unreliable",
            "thermal_posture",
        }
    ),
    "quality": frozenset(
        {
            "schema_version",
            "run_id",
            "captured_at",
            # provenance.capture_provenance
            "release_version",
            "commit_sha",
            "tree_dirty",
            # roster.load_roster / roster.resolve_entry
            "roster_entry_id",
            "roster_version",
            # prompt_provenance: call-path identity
            "endpoint",
            "prompt_template_id",
            "prompt_template_hash",
            "prompt_capture",
            "model_id",
            "provider",
            "fiche_hash",
            # energy.EnergyResult / emissions.local_emissions / scope3_cloud_emissions
            # -- same twelve fields as the runtime row (plan.md's Decisions:
            # quality rows carry the same per-channel/emissions/cost shape).
            "cpu_energy_kwh",
            "cpu_energy_method",
            "gpu_energy_kwh",
            "gpu_energy_method",
            "ram_energy_kwh",
            "ram_energy_method",
            "energy_kwh",
            "emissions_kg",
            "emission_factor_kg_per_kwh",
            "emission_region",
            "emissions_scope",
            "emissions_scope_formula_id",
            "scope_comparability",
            # cost.cloud_cost / cost.local_cost / cost.cost_per_million_tokens
            "tokens_in_total",
            "tokens_out_total",
            "cost_total",
            "cost_currency",
            "cost_per_million_tokens",
            "normalization_unit",
            "kwh_price_eur",
            "kwh_price_currency",
            "kwh_price_recorded_at",
            "list_price_input_per_million",
            "list_price_output_per_million",
            "list_price_per_million_tokens",
            "list_price_currency",
            "list_price_retrieved_at",
            # verdict.quality_verdict
            "verdict",
            "task_suite",
            "item_id",
            "prompt",
            "expected_label",
            "predicted_label",
            "correct",
            "suite_accuracy",
            "language_breakdown",
            "sampling",
            "max_output_tokens",
            "stop_sequences",
            "context_length",
            "suite_id",
            "suite_version",
            "prompt_set_hash",
            "language",
            "provenance",
            "contamination_risk",
            "indicative",
            "indicative_reasons",
            # scoring.score_item / score_suite
            "failure_reason",
            "failure_counts",
        }
    ),
}


class RowContractError(ValueError):
    """Raised when a row is missing one or more of its kind's required fields."""


def validate_row(kind: RowKind, row: dict[str, Any]) -> None:
    """Raise `RowContractError` naming every field `kind` requires but `row` lacks.

    A key present with value `None` satisfies the contract; only an absent key
    counts as missing.
    """
    missing = REQUIRED_FIELDS[kind] - row.keys()
    if missing:
        raise RowContractError(
            f"row of kind {kind!r} is missing required field(s): "
            f"{', '.join(sorted(missing))}"
        )

    endpoint = row["endpoint"]
    prompt_template_id = row["prompt_template_id"]
    if not prompt_provenance.is_consistent(endpoint, prompt_template_id):
        raise RowContractError(
            f"row of kind {kind!r} pairs endpoint {endpoint!r} with "
            f"prompt_template_id {prompt_template_id!r}: an endpoint that "
            f"applies a template cannot declare 'none'"
        )

    cost_total = row["cost_total"]
    # The two bases are the values the cost was actually computed from: a kWh
    # price for a local run, the table's own input rate for a cloud one.
    # `list_price_per_million_tokens` is deliberately not accepted here -- it
    # is a blended rate derived FROM cost_total, so a row carrying only it
    # would satisfy the gate without carrying any input at all.
    if (
        cost_total is not None
        and row["kwh_price_eur"] is None
        and row["list_price_input_per_million"] is None
    ):
        raise RowContractError(
            f"row of kind {kind!r} carries cost_total={cost_total!r} but both "
            "kwh_price_eur and list_price_input_per_million are null: a "
            "non-null cost must carry at least one derivation basis"
        )

    if kind == "runtime":
        ttft_source = row["ttft_source"]
        valid_ttft_sources = {
            timings.TTFT_SOURCE_SERVER_REPORTED,
            timings.TTFT_SOURCE_CLIENT_MEASURED,
        }
        if ttft_source not in valid_ttft_sources:
            raise RowContractError(
                f"row of kind 'runtime' has an unrecognised ttft_source: {ttft_source!r}"
            )
        _validate_runtime_repetition_structure(row)


def _validate_runtime_repetition_structure(row: dict[str, Any]) -> None:
    """Raise on a repetition set that cannot back the aggregates it publishes."""
    repetitions_n = row["repetitions_n"]
    if repetitions_n < 2:
        raise RowContractError(
            f"row of kind 'runtime' has repetitions_n={repetitions_n!r}: "
            "the sample sd is undefined below N=2"
        )

    repetitions = row["repetitions"]
    if len(repetitions) != repetitions_n:
        raise RowContractError(
            f"row of kind 'runtime' has {len(repetitions)} repetitions but "
            f"repetitions_n={repetitions_n!r}"
        )
    indices = [rep["index"] for rep in repetitions]
    if indices != list(range(1, repetitions_n + 1)):
        raise RowContractError(
            f"row of kind 'runtime' has non-contiguous repetition indices: "
            f"{indices!r}, expected 1..{repetitions_n}"
        )

    # This catches the declaration drifting from the declared field set. That
    # every name in MEASUREMENT_FIELDS is also a REQUIRED_FIELDS entry -- so a
    # row reaching here already carries all of them, checked above -- is a
    # static invariant between two hand-maintained sets, guarded by
    # tests/test_row_contract.py's
    # test_every_declared_measurement_is_a_required_runtime_field rather than
    # re-derived per row.
    declared = set(row["aggregation"])
    if declared != aggregation.MEASUREMENT_FIELDS:
        raise RowContractError(
            "row of kind 'runtime' has an aggregation map that does not "
            f"match the declared measurement set: {declared!r} != "
            f"{set(aggregation.MEASUREMENT_FIELDS)!r}"
        )
