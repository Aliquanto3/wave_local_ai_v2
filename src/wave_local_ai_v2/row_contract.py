"""The row contract: one required-field list per row kind, extended by every
later story rather than duplicated.

`append_row` (`results.py`) gates on `validate_row` before writing a line, so
an incomplete row can never land on disk. A key present with value `None` is
not missing -- several fields degrade to an explicit `None` on capture failure
(`hardware.py`, `timings.py`, `gpu.py`, `energy.py`) and are still complete.
"""

from __future__ import annotations

from typing import Any, Literal

from wave_local_ai_v2 import (
    aggregation,
    judge,
    judge_protocol,
    prompt_provenance,
    timings,
)

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
# "8": `retries` and `resumed` became required on quality rows only (a
# rate-limited run persists, resumes and never re-pays) -- the runtime row is
# untouched, since resume and retry are quality-CLI-only in this story's scope.
# "9": a judged quality row carries a judge block -- each judge's own call
# record, the prompt/rubric provenance the score was produced under, either an
# agreement figure over two judges or the single-judge flag, the contested
# state, and the judge calls' egress and cost (`JUDGED_FIELDS`). Required only
# on a row that carries any of it, so a deterministic quality row -- today's
# classification rows, which declare no rubric -- validates unchanged.
SCHEMA_VERSION = "9"

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
            # retry.call_with_retry / quality_cli's --resume (Story: a
            # rate-limited run persists, resumes and never re-pays)
            "retries",
            "resumed",
        }
    ),
}


# The complete judge block. Not a member of REQUIRED_FIELDS["quality"]: a
# quality row carrying none of these validates exactly as it did under "8",
# and a row carrying any of them owes all of them. That conditional shape is
# what lets a deterministic classification row stay unchanged while a judged
# row is held to the whole set -- an unconditional list would force every
# deterministic row to write a dozen null judge keys.
JUDGED_FIELDS: frozenset[str] = frozenset(
    {
        # judge_protocol.render_judge_prompt: which prompt was issued, in
        # which language, against which rubric revision.
        "judge_prompt_id",
        "judge_prompt_template_hash",
        "judge_prompt_language",
        "rubric_id",
        "rubric_version",
        "rubric_kind",
        # judge.run_judge_call: one JudgeCallRecord per judge that ran.
        "judges",
        # Independence and agreement: either a named statistic over two judges
        # of different families, or the flag saying only one judged.
        "single_judge",
        "single_judge_reason",
        "agreement",
        "agreement_statistic",
        # agreement.is_contested / agreement.headline_score: the disagreement
        # stays visible, only the headline excludes it and says how many.
        "contested",
        "contested_reason",
        "contested_threshold",
        "judged_headline_score",
        "judged_headline_excluded_n",
        # Where the item and the subject output went, and how many calls it took.
        "judge_egress",
        # cost.judge_cost_fields: the judge calls' own tokens and cost, priced
        # per judge provider. Deliberately not summed into `cost_total`, which
        # stays the subject generation's.
        "judge_cost",
    }
)

# The inner key sets a judged row's three records carry. Declared here, on the
# contract, rather than in the modules that build them: this is the module a
# reader checks a published row against.
JUDGE_EGRESS_FIELDS: frozenset[str] = frozenset(
    {
        "item_left_machine",
        "subject_output_left_machine",
        "providers",
        "generation_count",
        "judge_call_count",
    }
)

JUDGE_COST_FIELDS: frozenset[str] = frozenset(
    {
        "tokens_in_total",
        "tokens_out_total",
        "cost_total",
        "cost_currency",
        "per_provider",
    }
)


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

    if kind == "quality":
        _validate_judged_fields(row)


def _validate_judged_fields(row: dict[str, Any]) -> None:
    """Hold a row that declares itself judged to the whole judge block.

    A quality row carrying none of `JUDGED_FIELDS` is deterministic and
    returns untouched. Carrying any of them is the declaration: the row is a
    judged score, and every remaining judge field is named as missing.
    """
    present = JUDGED_FIELDS & row.keys()
    if not present:
        return

    missing = JUDGED_FIELDS - row.keys()
    if missing:
        raise RowContractError(
            f"row of kind 'quality' declares itself judged by carrying "
            f"{', '.join(sorted(present))} but is missing judge field(s): "
            f"{', '.join(sorted(missing))}"
        )

    _validate_judged_structure(row)


def _validate_judged_structure(row: dict[str, Any]) -> None:
    """Raise on a judge block that cannot back the judgement it publishes."""
    judges = row["judges"]
    if not isinstance(judges, list) or not judges:
        raise RowContractError(
            f"row of kind 'quality' has judges={judges!r}: a judged row "
            "carries at least one judge call record"
        )
    for index, record in enumerate(judges):
        if not isinstance(record, dict):
            raise RowContractError(
                f"row of kind 'quality' has a non-object judges[{index}]: {record!r}"
            )
        missing_keys = judge.JUDGE_CALL_RECORD_FIELDS - record.keys()
        if missing_keys:
            raise RowContractError(
                f"row of kind 'quality' has judges[{index}] missing "
                f"field(s): {', '.join(sorted(missing_keys))}"
            )

    language = row["judge_prompt_language"]
    if language not in judge_protocol.JUDGE_LANGUAGES:
        raise RowContractError(
            f"row of kind 'quality' has judge_prompt_language {language!r}: "
            f"must be one of {', '.join(judge_protocol.JUDGE_LANGUAGES)}"
        )

    rubric_kind = row["rubric_kind"]
    if rubric_kind not in judge_protocol.RUBRIC_KINDS:
        raise RowContractError(
            f"row of kind 'quality' has rubric_kind {rubric_kind!r}: must be "
            f"one of {', '.join(judge_protocol.RUBRIC_KINDS)}"
        )

    # A judged score states how it was reached: either two judges agreed to
    # some measured degree, or one judged and the row says so. Neither is an
    # unattributed number.
    row_agreement = row["agreement"]
    single_judge = row["single_judge"]
    if row_agreement is None and single_judge is not True:
        raise RowContractError(
            "row of kind 'quality' carries agreement=None and "
            f"single_judge={single_judge!r}: a judged score must carry either "
            "an agreement figure or the single_judge flag, and this row "
            "carries neither"
        )
    if single_judge is True and row_agreement is not None:
        raise RowContractError(
            "row of kind 'quality' carries single_judge=True alongside a "
            f"non-null agreement ({row_agreement!r}): one judge produces no "
            "agreement figure, so the row cannot be both"
        )

    _require_block_fields(row, "judge_egress", JUDGE_EGRESS_FIELDS)
    _require_block_fields(row, "judge_cost", JUDGE_COST_FIELDS)

    egress = row["judge_egress"]
    if not egress["providers"]:
        raise RowContractError(
            "row of kind 'quality' has an empty judge_egress providers list: "
            "a judged row was scored by someone"
        )
    if egress["judge_call_count"] != len(judges):
        raise RowContractError(
            f"row of kind 'quality' has judge_egress judge_call_count="
            f"{egress['judge_call_count']!r} but carries {len(judges)} judge "
            "call record(s): an egress record that disagrees with the calls "
            "on the row is worse than no record"
        )


def _require_block_fields(
    row: dict[str, Any], field: str, required: frozenset[str]
) -> None:
    """Raise unless `row[field]` is an object carrying every key in `required`."""
    block = row[field]
    if not isinstance(block, dict):
        raise RowContractError(
            f"row of kind 'quality' has a non-object {field}: {block!r}"
        )
    missing = required - block.keys()
    if missing:
        raise RowContractError(
            f"row of kind 'quality' has {field} missing field(s): "
            f"{', '.join(sorted(missing))}"
        )


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
