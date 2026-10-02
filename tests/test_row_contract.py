import dataclasses
from pathlib import Path

import pytest

from wave_local_ai_v2 import (
    FIXED_PROMPT,
    aggregation,
    prompt_variants,
    quality_rows,
    roster,
    suite_registry,
    timings,
)
from wave_local_ai_v2.results import append_row
from wave_local_ai_v2.row_contract import (
    GRADED_FIELDS,
    ITEM_MEASUREMENT_FIELDS,
    JUDGE_EGRESS_FIELDS,
    JUDGED_FIELDS,
    REQUIRED_FIELDS,
    SCHEMA_VERSION,
    SUBJECT_COMPOSITION_FIELDS,
    SUBJECT_COMPOSITION_SCHEMA_VERSION,
    RowContractError,
    subject_egress_for,
    validate_row,
)

_CLASSIFICATION = suite_registry.resolve("classification-support-routing")
_TRANSLATION = suite_registry.resolve("translation-business-short-form")

# The authored text of the item the quality fixture names: a baseline
# row carries it unchanged, and the gate checks that it does.
_AUTHORED_PROMPT = next(
    item["prompt"] for item in _CLASSIFICATION.items if item["item_id"] == "billing-01"
)


def _repetition(index: int) -> dict:
    return {
        "index": index,
        "ttft_ms": 100.0 + index,
        "ttft_source": "server_reported",
        "prompt_tok_per_s": 280.0,
        "gen_tok_per_s": 26.0,
        "vram_used_mib": 3161.0,
        "gpu_draw_w": 45.0,
        "process_rss_bytes": 500_000_000,
        "wall_clock_s": 5.0,
        "stop_type": "limit",
        "tokens_predicted": 128,
        "tokens_evaluated": 512,
    }


COMPLETE_RUNTIME_ROW = {
    "schema_version": SCHEMA_VERSION,
    "run_id": "run-1",
    "captured_at": "2026-08-22T00:00:00+00:00",
    "release_version": "v0.1.0",
    "commit_sha": "deadbeef",
    "tree_dirty": False,
    "roster_entry_id": "qwen3.6-35b-a3b-ud-iq4xs",
    "roster_version": 1,
    "endpoint": "/completion",
    "prompt_template_id": "none",
    "prompt_template_hash": None,
    "prompt_capture": "captured",
    "prompt_variant_id": "baseline",
    "prompt_variant_version": "1",
    "prompt_before_template": FIXED_PROMPT,
    "subject_egress": "none",
    "fiche_hash": "a" * 64,
    "verdict": {"verdict": "not_comparable", "reference_run_id": None},
    "prompt": "hello",
    "max_tokens": 128,
    "wall_clock_s": 25.0,
    "ttft_ms": 103.0,
    "ttft_source": "server_reported",
    "ttft_ms_mean": 103.0,
    "ttft_ms_sd": 1.5811388300841898,
    "ttft_ms_spread": 0.01535,
    "prompt_tok_per_s": 280.0,
    "prompt_tok_per_s_mean": 280.0,
    "prompt_tok_per_s_sd": 0.0,
    "prompt_tok_per_s_spread": 0.0,
    "gen_tok_per_s": 26.0,
    "gen_tok_per_s_mean": 26.0,
    "gen_tok_per_s_sd": 0.0,
    "gen_tok_per_s_spread": 0.0,
    "unreliable": False,
    "thermal_posture": "fixed_cooldown",
    "vram_used_mib": 3161.0,
    "gpu_draw_w": 45.0,
    "process_rss_bytes": 500_000_000,
    "cpu_energy_kwh": 0.0003,
    "cpu_energy_method": "estimated_tdp",
    "gpu_energy_kwh": None,
    "gpu_energy_method": "unavailable",
    "ram_energy_kwh": 0.00012,
    "ram_energy_method": "estimated_constant",
    "energy_kwh": 0.00042,
    "active_window_s": 15.0,
    "idle_window_s": 40.0,
    "energy_window_method": "per_repetition_tasks",
    "emissions_kg": 0.0000235,
    "emission_factor_kg_per_kwh": 0.056039,
    "emission_region": "FR",
    "emissions_scope": "scope_2",
    "emissions_scope_formula_id": None,
    "scope_comparability": None,
    "tokens_in_total": None,
    "tokens_out_total": 640,
    "cost_total": 0.0000815,
    "cost_currency": "EUR",
    "cost_per_million_tokens": None,
    "normalization_unit": "cost_per_million_total_tokens",
    "kwh_price_eur": 0.194,
    "kwh_price_currency": "EUR",
    "kwh_price_recorded_at": "2026-02-01",
    "list_price_input_per_million": None,
    "list_price_output_per_million": None,
    "list_price_per_million_tokens": None,
    "list_price_currency": None,
    "list_price_retrieved_at": None,
    "sampling": {"seed": 20260822, "temperature": 1.0},
    "seed_pinned": True,
    "warmup_count": 1,
    "warmup_repetitions": [_repetition(0)],
    "restart_between_repetitions": False,
    "cooldown_s": 10.0,
    "repetitions_n": 5,
    "slot_reset_method": "cache_prompt_false",
    "repetitions": [_repetition(i) for i in range(1, 6)],
    "aggregation": dict(aggregation.AGGREGATION_LABELS),
}

COMPLETE_QUALITY_ROW = {
    "schema_version": SCHEMA_VERSION,
    "run_id": "run-1",
    "captured_at": "2026-08-22T00:00:00+00:00",
    "release_version": "v0.1.0",
    "commit_sha": "deadbeef",
    "tree_dirty": False,
    "roster_entry_id": "qwen3.6-35b-a3b-ud-iq4xs",
    "roster_version": 1,
    "endpoint": "/completion",
    "prompt_template_id": "none",
    "prompt_template_hash": None,
    "prompt_capture": "captured",
    "prompt_variant_id": "baseline",
    "prompt_variant_version": "1",
    "prompt_before_template": _AUTHORED_PROMPT,
    "model_id": "Qwen3.6-35B-A3B",
    "provider": "local",
    "subject_egress": "none",
    "fiche_hash": "a" * 64,
    "cpu_energy_kwh": 0.0003,
    "cpu_energy_method": "estimated_tdp",
    "gpu_energy_kwh": None,
    "gpu_energy_method": "unavailable",
    "ram_energy_kwh": 0.00012,
    "ram_energy_method": "estimated_constant",
    "energy_kwh": 0.00042,
    "emissions_kg": 0.0000235,
    "emission_factor_kg_per_kwh": 0.056039,
    "emission_region": "FR",
    "emissions_scope": "scope_2",
    "emissions_scope_formula_id": None,
    "scope_comparability": None,
    "tokens_in_total": None,
    "tokens_out_total": 640,
    "cost_total": 0.0000815,
    "cost_currency": "EUR",
    "cost_per_million_tokens": None,
    "normalization_unit": "cost_per_million_total_tokens",
    "kwh_price_eur": 0.194,
    "kwh_price_currency": "EUR",
    "kwh_price_recorded_at": "2026-02-01",
    "list_price_input_per_million": None,
    "list_price_output_per_million": None,
    "list_price_per_million_tokens": None,
    "list_price_currency": None,
    "list_price_retrieved_at": None,
    "verdict": {"verdict": "not_comparable", "reference_run_id": None},
    "task_suite": "classification",
    "item_id": "billing-01",
    "prompt": "hello",
    "expected_label": "billing",
    "predicted_label": "billing",
    "correct": True,
    "suite_accuracy": 1.0,
    "language_breakdown": {
        "en": {"accuracy": 1.0, "n": 1, "indicative": True},
        "fr": {"accuracy": 0.0, "n": 0, "indicative": True},
        "de": {"accuracy": 0.0, "n": 0, "indicative": True},
    },
    "sampling": {"seed": 1},
    "max_output_tokens": 32,
    "stop_sequences": [],
    "thinking_policy": "disabled",
    "context_length": 32768,
    "suite_id": "classification-support-routing",
    "suite_version": _CLASSIFICATION.suite_version,
    "prompt_set_hash": "deadbeef",
    "language": "en",
    "provenance": "hand_written",
    "contamination_risk": False,
    "indicative": True,
    "indicative_reasons": ["item_count 10 is below the minimum of 20"],
    "suite_level": "development",
    "item_licence": "CC-BY-4.0",
    "item_source": None,
    "item_source_revision": None,
    "failure_reason": None,
    "failure_counts": {
        "empty": 0,
        "unparseable": 0,
        "truncated_max_tokens": 0,
        "truncated_context": 0,
    },
    "retries": 0,
    "resumed": False,
    "retry_budget": {},
    "partial_failure": None,
    "item_tokens_in": 57,
    "item_tokens_in_null_reason": None,
    "item_tokens_out": 2,
    "item_tokens_out_null_reason": None,
    "item_ttft_ms": 13.7,
    "item_ttft_ms_null_reason": None,
    "item_ttft_source": "server_reported",
    "item_prompt_tokens_cached": 0,
    "item_prompt_tokens_cached_null_reason": None,
    "item_measurement_kind": "single_generation",
    "item_first_in_batch": True,
    "family": "qwen",
    "size_class": "~8B-and-up",
}


def _judge_record(provider: str, family: str, model_id: str, score: int) -> dict:
    return {
        "model_id": model_id,
        "provider": provider,
        "family": family,
        "score": score,
        "raw_text": str(score),
        "failure_reason": None,
        "tokens_in": 120,
        "tokens_out": 2,
        "retries": 0,
        "answering_provider": provider,
        "answering_provider_source": "direct_endpoint",
        "reasoning_effort": "not_sent",
        "reasoning_tokens": None,
        "reasoning_tokens_source": None,
        "reasoning_tokens_null_reason": "provider_reports_no_reasoning_count",
    }


# The six fields schema "13" added to every judge call record.
NEW_JUDGE_RECORD_FIELDS = (
    "answering_provider",
    "answering_provider_source",
    "reasoning_effort",
    "reasoning_tokens",
    "reasoning_tokens_source",
    "reasoning_tokens_null_reason",
)


def _cost_entry(**changes) -> dict:
    entry = {
        "provider": "mistral",
        "model_id": "mistral-small-2603",
        "tokens_in": 120,
        "tokens_out": 2,
        "reasoning_tokens": None,
        "reasoning_tokens_null_reason": "provider_reports_no_reasoning_count",
        "reasoning_tokens_billing": "inside_output",
        "cost_total": 0.00003,
        "list_price_input_per_million": 0.15,
        "list_price_output_per_million": 0.60,
        "list_price_retrieved_at": "2026-08-27",
    }
    entry.update(changes)
    return entry


JUDGE_BLOCK = {
    "judge_prompt_id": "judge-prompt-en",
    "judge_prompt_template_hash": "b" * 64,
    "judge_prompt_language": "en",
    "rubric_id": "open-ended-quality-1to5",
    "rubric_version": "1",
    "rubric_kind": "ordinal_1_5",
    "judges": [
        _judge_record("mistral", "mistral", "mistral-small-2603", 4),
        _judge_record("google", "google", "gemini-3.5-flash-lite", 4),
    ],
    "single_judge": False,
    "single_judge_reason": None,
    "agreement": {
        "statistic": "cohens_kappa_quadratic_weighted",
        "value": None,
        "value_null_reason": "insufficient_items",
        "exact_match_rate": 1.0,
        "within_one_rate": 1.0,
        "n_items": 1,
        "n_items_excluded": 0,
    },
    "agreement_statistic": "cohens_kappa_quadratic_weighted",
    "contested": False,
    "contested_reason": None,
    "contested_threshold": {"max_ordinal_delta": 1},
    "judged_headline_score": 4.0,
    "judged_headline_excluded_n": 0,
    "judge_egress": {
        "item_left_machine": True,
        "subject_output_left_machine": True,
        "providers": ["google", "mistral"],
        "generation_count": 1,
        "judge_call_count": 2,
    },
    "judge_cost": {
        "tokens_in_total": 240,
        "tokens_out_total": 4,
        "cost_total": 0.0001,
        "cost_currency": "USD",
        "per_provider": [],
    },
}

COMPLETE_JUDGED_QUALITY_ROW = {**COMPLETE_QUALITY_ROW, **JUDGE_BLOCK}

GRADED_BLOCK = {
    "metric_id": "chrf",
    "metric_version": "1",
    "metric_params": {
        "char_order": 6,
        "beta": 2,
        "whitespace": False,
        "scale": "0..1",
    },
    "item_score": 0.87,
    "suite_score": 0.61,
    "score_breakdown": {
        "en": {"score": 0.87, "n": 7, "indicative": True},
        "fr": {"score": 0.55, "n": 7, "indicative": True},
        "de": {"score": 0.41, "n": 7, "indicative": True},
    },
    "reference_output": "Bonjour, la livraison arrive demain.",
    "subject_output": "Bonjour, la livraison arrive demain.",
}

# A graded row nulls every exact-match field: the two score shapes never
# appear on one row.
COMPLETE_GRADED_QUALITY_ROW = {
    **COMPLETE_QUALITY_ROW,
    **GRADED_BLOCK,
    "task_suite": "translation",
    "suite_id": _TRANSLATION.suite_id,
    "suite_version": _TRANSLATION.suite_version,
    "item_id": "en-fr-01",
    "prompt_before_template": _TRANSLATION.items[0]["prompt"],
    "expected_label": None,
    "predicted_label": None,
    "correct": None,
    "suite_accuracy": None,
    "language_breakdown": None,
}


def test_complete_runtime_row_passes() -> None:
    validate_row("runtime", COMPLETE_RUNTIME_ROW)


def test_complete_quality_row_passes() -> None:
    validate_row("quality", COMPLETE_QUALITY_ROW)


def test_missing_field_raises_and_names_it() -> None:
    incomplete = {k: v for k, v in COMPLETE_RUNTIME_ROW.items() if k != "fiche_hash"}

    with pytest.raises(RowContractError, match="fiche_hash"):
        validate_row("runtime", incomplete)


def test_row_carrying_only_the_old_energy_method_field_is_refused() -> None:
    # Pre-increment shape: the single composite energy_method field, none of
    # the twelve per-channel/emissions fields it was replaced by.
    per_channel_fields = {
        "cpu_energy_kwh",
        "cpu_energy_method",
        "gpu_energy_kwh",
        "gpu_energy_method",
        "ram_energy_kwh",
        "ram_energy_method",
        "emissions_kg",
        "emission_factor_kg_per_kwh",
        "emission_region",
        "emissions_scope",
        "emissions_scope_formula_id",
        "scope_comparability",
    }
    legacy_row = {
        k: v for k, v in COMPLETE_RUNTIME_ROW.items() if k not in per_channel_fields
    }
    legacy_row["energy_method"] = "estimated_tdp"
    legacy_row["aggregation"] = {
        k: v
        for k, v in legacy_row["aggregation"].items()
        if k not in ("cpu_energy_kwh", "gpu_energy_kwh", "ram_energy_kwh")
    }

    with pytest.raises(RowContractError, match="cpu_energy_kwh"):
        validate_row("runtime", legacy_row)


@pytest.mark.parametrize("field", ["roster_entry_id", "roster_version"])
def test_runtime_row_missing_a_roster_field_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_RUNTIME_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("runtime", incomplete)


@pytest.mark.parametrize("field", ["roster_entry_id", "roster_version"])
def test_quality_row_missing_a_roster_field_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", incomplete)


@pytest.mark.parametrize(
    "field",
    [
        "gen_tok_per_s_spread",
        "ttft_ms_spread",
        "prompt_tok_per_s_spread",
        "unreliable",
        "thermal_posture",
        "ttft_source",
    ],
)
def test_missing_spread_or_posture_field_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_RUNTIME_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("runtime", incomplete)


def test_ttft_source_accepts_both_declared_values() -> None:
    validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "ttft_source": "server_reported"})
    validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "ttft_source": "client_measured"})


def test_ttft_source_with_an_unrecognised_value_is_refused_and_named() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "ttft_source": "guessed"}

    with pytest.raises(RowContractError, match="guessed"):
        validate_row("runtime", row)


def test_explicit_none_value_is_accepted() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "fiche_hash": None}

    validate_row("runtime", row)


def test_repetitions_n_below_two_is_refused() -> None:
    row = {
        **COMPLETE_RUNTIME_ROW,
        "repetitions_n": 1,
        "repetitions": [_repetition(1)],
    }

    with pytest.raises(RowContractError, match="repetitions_n"):
        validate_row("runtime", row)


def test_repetitions_length_disagreeing_with_repetitions_n_is_refused() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "repetitions": [_repetition(i) for i in range(1, 5)]}

    with pytest.raises(RowContractError, match="repetitions"):
        validate_row("runtime", row)


def test_non_contiguous_repetition_indices_are_refused() -> None:
    bad_repetitions = [
        _repetition(1),
        _repetition(2),
        _repetition(2),
        _repetition(4),
        _repetition(5),
    ]
    row = {**COMPLETE_RUNTIME_ROW, "repetitions": bad_repetitions}

    with pytest.raises(RowContractError, match="non-contiguous"):
        validate_row("runtime", row)


def test_aggregation_map_missing_a_declared_measurement_is_refused() -> None:
    incomplete_aggregation = dict(aggregation.AGGREGATION_LABELS)
    del incomplete_aggregation["gen_tok_per_s"]
    row = {**COMPLETE_RUNTIME_ROW, "aggregation": incomplete_aggregation}

    with pytest.raises(RowContractError, match="aggregation"):
        validate_row("runtime", row)


def test_every_declared_measurement_is_a_required_runtime_field() -> None:
    # The two sets are maintained by hand in different modules. A measurement
    # labelled in AGGREGATION_LABELS but absent from REQUIRED_FIELDS would let
    # a row declare a statistic for a field it never has to carry, which is
    # exactly the silent omission the aggregation block exists to prevent.
    unbacked = aggregation.MEASUREMENT_FIELDS - REQUIRED_FIELDS["runtime"]

    assert unbacked == frozenset()


def test_cost_present_without_either_derivation_basis_is_refused() -> None:
    row = {
        **COMPLETE_RUNTIME_ROW,
        "cost_total": 0.0000815,
        "kwh_price_eur": None,
        "list_price_input_per_million": None,
    }

    with pytest.raises(RowContractError, match="cost_total"):
        validate_row("runtime", row)


def test_cost_present_with_only_list_price_basis_passes() -> None:
    row = {
        **COMPLETE_RUNTIME_ROW,
        "cost_total": 0.003,
        "kwh_price_eur": None,
        "list_price_input_per_million": 0.15,
    }

    validate_row("runtime", row)


def test_a_blended_rate_alone_is_not_a_derivation_basis() -> None:
    # list_price_per_million_tokens is cost_total / total_tokens: a row
    # carrying only it satisfies nothing, because the "input" it cites was
    # computed from the very cost it is supposed to explain.
    row = {
        **COMPLETE_RUNTIME_ROW,
        "cost_total": 0.003,
        "kwh_price_eur": None,
        "list_price_input_per_million": None,
        "list_price_per_million_tokens": 0.4235,
    }

    with pytest.raises(RowContractError, match="list_price_input_per_million"):
        validate_row("runtime", row)


def test_cost_absent_with_both_price_bases_null_passes() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "cost_total": None}

    validate_row("runtime", row)


@pytest.mark.parametrize("field", ["retries", "resumed"])
def test_quality_row_missing_retries_or_resumed_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", incomplete)


def test_runtime_row_does_not_require_retries_or_resumed() -> None:
    # Resume/retry are quality-CLI-only in this story's scope: the runtime
    # harness has no cloud calls and no resume flag.
    assert "retries" not in REQUIRED_FIELDS["runtime"]
    assert "resumed" not in REQUIRED_FIELDS["runtime"]
    validate_row("runtime", COMPLETE_RUNTIME_ROW)


def test_a_deterministic_quality_row_carries_no_judge_field_and_still_validates() -> (
    None
):
    assert JUDGED_FIELDS & COMPLETE_QUALITY_ROW.keys() == set()

    validate_row("quality", COMPLETE_QUALITY_ROW)


def test_a_complete_judged_quality_row_passes() -> None:
    validate_row("quality", COMPLETE_JUDGED_QUALITY_ROW)


@pytest.mark.parametrize("field", sorted(JUDGED_FIELDS))
def test_a_judged_row_missing_one_judge_field_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_JUDGED_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", incomplete)


def test_a_judged_row_with_an_empty_judges_list_is_refused() -> None:
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "judges": []}

    with pytest.raises(RowContractError, match="judges"):
        validate_row("quality", row)


def test_a_judge_record_missing_raw_text_is_refused_by_name() -> None:
    first, second = COMPLETE_JUDGED_QUALITY_ROW["judges"]
    stripped = {k: v for k, v in first.items() if k != "raw_text"}
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "judges": [stripped, second]}

    with pytest.raises(RowContractError, match="raw_text"):
        validate_row("quality", row)


@pytest.mark.parametrize("field", NEW_JUDGE_RECORD_FIELDS)
def test_a_judge_record_missing_a_schema_13_field_is_refused_by_name(
    field: str,
) -> None:
    first, second = COMPLETE_JUDGED_QUALITY_ROW["judges"]
    stripped = {k: v for k, v in first.items() if k != field}
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "judges": [stripped, second]}

    with pytest.raises(
        RowContractError, match=rf"judges\[0\] missing field\(s\): {field}$"
    ):
        validate_row("quality", row)


def _with_first_record(**changes) -> dict:
    first, second = COMPLETE_JUDGED_QUALITY_ROW["judges"]
    return {**COMPLETE_JUDGED_QUALITY_ROW, "judges": [{**first, **changes}, second]}


def test_a_record_answered_by_another_provider_is_refused_naming_both() -> None:
    row = _with_first_record(answering_provider="deepinfra")

    with pytest.raises(RowContractError) as excinfo:
        validate_row("quality", row)

    message = str(excinfo.value)
    assert "'deepinfra'" in message
    assert "'mistral'" in message


def test_a_record_answered_as_bound_read_from_the_response_validates() -> None:
    validate_row("quality", _with_first_record(answering_provider_source="response"))


def test_an_unknown_answering_provider_source_is_refused_by_value() -> None:
    with pytest.raises(RowContractError, match="'guessed'"):
        validate_row("quality", _with_first_record(answering_provider_source="guessed"))


@pytest.mark.parametrize("effort", ["", None])
def test_a_record_with_no_stated_reasoning_effort_is_refused(effort) -> None:
    with pytest.raises(RowContractError, match="reasoning_effort"):
        validate_row("quality", _with_first_record(reasoning_effort=effort))


@pytest.mark.parametrize("tokens", ["12", -1, True, 1.5])
def test_a_reasoning_count_that_is_not_a_non_negative_integer_is_refused(
    tokens,
) -> None:
    row = _with_first_record(
        reasoning_tokens=tokens,
        reasoning_tokens_source="reported",
        reasoning_tokens_null_reason=None,
    )

    with pytest.raises(RowContractError, match="non-negative integer"):
        validate_row("quality", row)


def test_a_reasoning_count_with_no_source_is_refused() -> None:
    row = _with_first_record(
        reasoning_tokens=0,
        reasoning_tokens_source=None,
        reasoning_tokens_null_reason=None,
    )

    with pytest.raises(RowContractError, match="reasoning_tokens_source None"):
        validate_row("quality", row)


def test_a_null_reasoning_count_with_a_source_is_refused() -> None:
    row = _with_first_record(reasoning_tokens_source="derived_from_totals")

    with pytest.raises(RowContractError, match="a null count has no source"):
        validate_row("quality", row)


def test_a_derived_zero_reasoning_count_validates() -> None:
    row = _with_first_record(
        reasoning_tokens=0,
        reasoning_tokens_source="derived_from_totals",
        reasoning_tokens_null_reason=None,
    )

    validate_row("quality", row)


def _with_cost_entries(*entries) -> dict:
    return {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "judge_cost": {
            **COMPLETE_JUDGED_QUALITY_ROW["judge_cost"],
            "per_provider": list(entries),
        },
    }


def test_a_complete_per_provider_cost_entry_validates() -> None:
    validate_row("quality", _with_cost_entries(_cost_entry()))


@pytest.mark.parametrize(
    "field",
    ["reasoning_tokens", "reasoning_tokens_null_reason", "reasoning_tokens_billing"],
)
def test_a_per_provider_cost_entry_missing_a_reasoning_field_is_refused_by_name(
    field,
) -> None:
    entry = {k: v for k, v in _cost_entry().items() if k != field}

    with pytest.raises(RowContractError, match=rf"per_provider\[0\].*{field}"):
        validate_row("quality", _with_cost_entries(entry))


def test_a_per_provider_cost_entry_with_an_unknown_billing_basis_is_refused() -> None:
    entry = _cost_entry(reasoning_tokens_billing="unknown")

    with pytest.raises(RowContractError, match="'unknown'"):
        validate_row("quality", _with_cost_entries(entry))


@pytest.mark.parametrize("per_provider", [None, ["not-an-object"]])
def test_a_malformed_per_provider_cost_record_is_refused(per_provider) -> None:
    row = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "judge_cost": {
            **COMPLETE_JUDGED_QUALITY_ROW["judge_cost"],
            "per_provider": per_provider,
        },
    }

    with pytest.raises(RowContractError, match="per_provider"):
        validate_row("quality", row)


def test_a_null_reasoning_count_without_a_reason_is_refused() -> None:
    row = _with_first_record(reasoning_tokens=None, reasoning_tokens_null_reason=None)

    with pytest.raises(RowContractError, match="reasoning_tokens=None"):
        validate_row("quality", row)


def test_a_reported_reasoning_count_carrying_a_null_reason_is_refused() -> None:
    row = _with_first_record(
        reasoning_tokens=12,
        reasoning_tokens_source="reported",
        reasoning_tokens_null_reason="provider_reports_no_reasoning_count",
    )

    with pytest.raises(RowContractError, match="reasoning_tokens=12"):
        validate_row("quality", row)


def test_a_reported_reasoning_count_validates() -> None:
    row = _with_first_record(
        reasoning_tokens=12,
        reasoning_tokens_source="reported",
        reasoning_tokens_null_reason=None,
    )

    validate_row("quality", row)


def test_a_judged_row_in_an_unsupported_language_is_refused_by_value() -> None:
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "judge_prompt_language": "es"}

    with pytest.raises(RowContractError, match="'es'"):
        validate_row("quality", row)


def test_a_judged_row_with_an_unknown_rubric_kind_is_refused_by_value() -> None:
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "rubric_kind": "ternary"}

    with pytest.raises(RowContractError, match="ternary"):
        validate_row("quality", row)


def test_a_judged_row_with_an_incomplete_egress_record_is_refused_by_name() -> None:
    egress = {
        k: v
        for k, v in COMPLETE_JUDGED_QUALITY_ROW["judge_egress"].items()
        if k != "providers"
    }
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "judge_egress": egress}

    with pytest.raises(RowContractError, match="providers"):
        validate_row("quality", row)


def test_a_judged_row_with_an_incomplete_cost_record_is_refused_by_name() -> None:
    judge_cost = {
        k: v
        for k, v in COMPLETE_JUDGED_QUALITY_ROW["judge_cost"].items()
        if k != "per_provider"
    }
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "judge_cost": judge_cost}

    with pytest.raises(RowContractError, match="per_provider"):
        validate_row("quality", row)


def test_a_runtime_row_is_never_held_to_the_judge_block() -> None:
    # The judge block is a quality-row concept: the runtime harness makes no
    # judged calls, so a stray judge key there must not trigger the gate.
    row = {**COMPLETE_RUNTIME_ROW, "single_judge": True}

    validate_row("runtime", row)


def test_aggregation_map_naming_a_field_the_row_does_not_carry_is_refused() -> None:
    extra_aggregation = {**aggregation.AGGREGATION_LABELS, "made_up_metric": "median"}
    row = {**COMPLETE_RUNTIME_ROW, "aggregation": extra_aggregation}

    with pytest.raises(RowContractError, match="made_up_metric"):
        validate_row("runtime", row)


def test_a_judged_row_with_neither_agreement_nor_the_flag_is_refused() -> None:
    row = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "agreement": None,
        "single_judge": False,
    }

    with pytest.raises(RowContractError) as excinfo:
        validate_row("quality", row)

    assert "agreement" in str(excinfo.value)
    assert "single_judge" in str(excinfo.value)


def test_a_row_claiming_one_judge_and_an_agreement_is_refused() -> None:
    row = {**COMPLETE_JUDGED_QUALITY_ROW, "single_judge": True}

    with pytest.raises(RowContractError, match="single_judge=True"):
        validate_row("quality", row)


def test_a_single_judge_row_with_no_agreement_validates() -> None:
    row = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "judges": COMPLETE_JUDGED_QUALITY_ROW["judges"][:1],
        "single_judge": True,
        "single_judge_reason": "cloud_subject_other_family_only",
        "agreement": None,
        "agreement_statistic": None,
        "judge_egress": {
            **COMPLETE_JUDGED_QUALITY_ROW["judge_egress"],
            "providers": ["mistral"],
            "judge_call_count": 1,
        },
    }

    validate_row("quality", row)


def test_an_egress_count_disagreeing_with_the_calls_is_refused() -> None:
    row = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "judges": COMPLETE_JUDGED_QUALITY_ROW["judges"][:1],
        "single_judge": True,
        "single_judge_reason": "cloud_subject_other_family_only",
        "agreement": None,
        "agreement_statistic": None,
    }

    with pytest.raises(RowContractError, match="judge_call_count"):
        validate_row("quality", row)


def test_an_empty_egress_provider_list_is_refused() -> None:
    row = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "judge_egress": {
            **COMPLETE_JUDGED_QUALITY_ROW["judge_egress"],
            "providers": [],
        },
    }

    with pytest.raises(RowContractError, match="providers"):
        validate_row("quality", row)


def test_no_judge_field_can_collide_with_a_required_quality_field() -> None:
    # What makes "cost_total stays the subject generation's" structural rather
    # than a convention: the judge block's cost lives under its own
    # `judge_cost` key, so no judge field can overwrite a row-level one.
    assert JUDGED_FIELDS & REQUIRED_FIELDS["quality"] == frozenset()
    assert (
        COMPLETE_JUDGED_QUALITY_ROW["cost_total"] == COMPLETE_QUALITY_ROW["cost_total"]
    )


def test_a_complete_graded_quality_row_passes() -> None:
    validate_row("quality", COMPLETE_GRADED_QUALITY_ROW)


def test_an_exact_match_row_carries_no_graded_field_and_still_validates() -> None:
    assert GRADED_FIELDS & COMPLETE_QUALITY_ROW.keys() == set()

    validate_row("quality", COMPLETE_QUALITY_ROW)


@pytest.mark.parametrize("field", sorted(GRADED_FIELDS))
def test_a_graded_row_missing_one_graded_field_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_GRADED_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", incomplete)


def test_subject_output_alone_does_not_declare_a_row_graded() -> None:
    # `judge_probe.py` writes `subject_output` on every probe row as a
    # non-required extra key. Putting it in GRADED_FIELDS would make each of
    # those rows declare itself graded and then fail for seven metric fields
    # it never carries.
    assert "subject_output" not in GRADED_FIELDS

    judged_with_output = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "subject_output": "the answer the subject produced",
    }

    validate_row("quality", judged_with_output)


def test_a_graded_row_with_no_subject_output_is_refused() -> None:
    row = {
        k: v for k, v in COMPLETE_GRADED_QUALITY_ROW.items() if k != "subject_output"
    }

    with pytest.raises(RowContractError, match="subject_output"):
        validate_row("quality", row)


@pytest.mark.parametrize("field", ["item_score", "suite_score"])
@pytest.mark.parametrize("value", [-0.01, 1.01, 42])
def test_a_graded_score_outside_zero_to_one_is_refused(
    field: str, value: float
) -> None:
    row = {**COMPLETE_GRADED_QUALITY_ROW, field: value}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


@pytest.mark.parametrize("field", ["item_score", "suite_score"])
@pytest.mark.parametrize("value", ["0.5", None, True])
def test_a_non_numeric_graded_score_is_refused(field: str, value: object) -> None:
    row = {**COMPLETE_GRADED_QUALITY_ROW, field: value}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


def test_a_named_failure_with_a_non_zero_score_is_refused() -> None:
    # Methodology 9 checked at the writer: a failed generation scores 0.0.
    row = {
        **COMPLETE_GRADED_QUALITY_ROW,
        "failure_reason": "truncated_max_tokens",
        "item_score": 0.4,
    }

    with pytest.raises(RowContractError, match="failure_reason"):
        validate_row("quality", row)


def test_a_named_failure_scoring_zero_is_accepted() -> None:
    validate_row(
        "quality",
        {
            **COMPLETE_GRADED_QUALITY_ROW,
            "failure_reason": "empty",
            "item_score": 0.0,
        },
    )


@pytest.mark.parametrize(
    ("field", "value"), [("correct", True), ("correct", False), ("suite_accuracy", 0.9)]
)
def test_a_graded_row_claiming_an_exact_match_score_is_refused(
    field: str, value: object
) -> None:
    row = {**COMPLETE_GRADED_QUALITY_ROW, field: value}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


def test_a_graded_row_still_requires_language_breakdown_as_a_key() -> None:
    # `language_breakdown` stays in REQUIRED_FIELDS and is None on a graded
    # row, the way judge_probe.py already nulls it -- present, not absent.
    assert "language_breakdown" in REQUIRED_FIELDS["quality"]
    row = {
        k: v
        for k, v in COMPLETE_GRADED_QUALITY_ROW.items()
        if k != "language_breakdown"
    }

    with pytest.raises(RowContractError, match="language_breakdown"):
        validate_row("quality", row)


def test_a_score_breakdown_missing_a_language_is_refused() -> None:
    row = {
        **COMPLETE_GRADED_QUALITY_ROW,
        "score_breakdown": {"en": {"score": 1.0, "n": 7, "indicative": True}},
    }

    with pytest.raises(RowContractError, match="score_breakdown"):
        validate_row("quality", row)


def test_a_score_breakdown_cell_missing_a_key_is_refused() -> None:
    row = {
        **COMPLETE_GRADED_QUALITY_ROW,
        "score_breakdown": {
            **COMPLETE_GRADED_QUALITY_ROW["score_breakdown"],
            "de": {"score": 0.41, "n": 7},
        },
    }

    with pytest.raises(RowContractError, match="indicative"):
        validate_row("quality", row)


@pytest.mark.parametrize("breakdown", ["not-an-object", 3, ["en", "fr", "de"]])
def test_a_non_object_score_breakdown_is_refused(breakdown: object) -> None:
    row = {**COMPLETE_GRADED_QUALITY_ROW, "score_breakdown": breakdown}

    with pytest.raises(RowContractError, match="score_breakdown"):
        validate_row("quality", row)


def test_a_non_object_score_breakdown_cell_is_refused() -> None:
    row = {
        **COMPLETE_GRADED_QUALITY_ROW,
        "score_breakdown": {
            **COMPLETE_GRADED_QUALITY_ROW["score_breakdown"],
            "fr": 0.55,
        },
    }

    with pytest.raises(RowContractError, match="score_breakdown"):
        validate_row("quality", row)


def test_the_schema_version_moved_once_for_the_thinking_policy() -> None:
    # "9" declared the judge block and "10" the graded one, both conditional
    # on a row carrying any of their fields. "11" is not conditional:
    # `thinking_policy` is required on every quality row, because a score
    # produced with the subject allowed to reason and one produced without it
    # are not the same measurement and a row has to say which it is.
    assert SCHEMA_VERSION == "19"


def test_the_schema_version_moved_for_the_runtime_energy_window() -> None:
    # "12" fixes audit finding C3: the runtime row's energy figures used to
    # span the whole counted-repetition window, cooldowns included. Required
    # only on runtime rows -- quality rows carry no energy window at all.
    assert SCHEMA_VERSION == "19"
    assert {"active_window_s", "idle_window_s", "energy_window_method"} <= (
        REQUIRED_FIELDS["runtime"]
    )
    assert {"active_window_s", "idle_window_s", "energy_window_method"}.isdisjoint(
        REQUIRED_FIELDS["quality"]
    )


def test_the_schema_version_moved_for_the_judge_call_record_extension() -> None:
    # "13" adds five fields inside each judge call record. Additive inside the
    # conditional judge block: neither row kind's required set moves, so a
    # deterministic quality row validates unchanged.
    assert SCHEMA_VERSION == "19"
    assert set(NEW_JUDGE_RECORD_FIELDS).isdisjoint(REQUIRED_FIELDS["quality"])
    assert set(NEW_JUDGE_RECORD_FIELDS).isdisjoint(JUDGED_FIELDS)
    validate_row("quality", COMPLETE_QUALITY_ROW)


def test_the_schema_version_moved_for_the_prompt_variant() -> None:
    # "14" makes both row kinds name the variant they ran under and carry the
    # prompt as the variant left it. Not conditional: every row ran under some
    # variant, and a row below "14" is never back-filled with `baseline`.
    assert SCHEMA_VERSION == "19"
    for kind in ("runtime", "quality"):
        assert set(PROMPT_VARIANT_FIELDS) <= REQUIRED_FIELDS[kind]


def test_the_schema_version_moved_for_the_suite_level() -> None:
    # "15" makes every quality row name the level its suite was certified at
    # and its item's licence, source and source revision. Not conditional:
    # every suite is certified at some level. Quality rows only -- a runtime
    # row runs no suite.
    assert SCHEMA_VERSION == "19"
    assert set(SUITE_LEVEL_FIELDS) <= REQUIRED_FIELDS["quality"]
    assert set(SUITE_LEVEL_FIELDS).isdisjoint(REQUIRED_FIELDS["runtime"])


SUITE_LEVEL_FIELDS = (
    "suite_level",
    "item_licence",
    "item_source",
    "item_source_revision",
)


@pytest.mark.parametrize("field", SUITE_LEVEL_FIELDS)
def test_a_quality_row_missing_a_suite_level_field_is_refused_by_name(field) -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


def test_a_quality_row_with_an_unknown_level_is_refused() -> None:
    row = {**COMPLETE_QUALITY_ROW, "suite_level": "draft"}

    with pytest.raises(RowContractError, match="suite_level 'draft'"):
        validate_row("quality", row)


_PUBLICATION_ROW = {
    **COMPLETE_QUALITY_ROW,
    "suite_level": "publication",
    "item_licence": "MIT",
    "item_source": "example-benchmark",
    "item_source_revision": "abc123",
}


def test_a_publication_row_naming_its_licence_and_source_validates() -> None:
    validate_row("quality", _PUBLICATION_ROW)


@pytest.mark.parametrize("field", SUITE_LEVEL_FIELDS[1:])
def test_a_publication_row_with_a_null_item_declaration_is_refused(field) -> None:
    row = {**_PUBLICATION_ROW, field: None}

    with pytest.raises(RowContractError, match=f"{field} is null"):
        validate_row("quality", row)


@pytest.mark.parametrize("value", ["", 7])
def test_a_malformed_item_declaration_is_refused(value) -> None:
    row = {**COMPLETE_QUALITY_ROW, "item_licence": value}

    with pytest.raises(RowContractError, match="malformed item_licence"):
        validate_row("quality", row)


PROMPT_VARIANT_FIELDS = (
    "prompt_variant_id",
    "prompt_variant_version",
    "prompt_before_template",
)


@pytest.mark.parametrize("kind", ["runtime", "quality"])
@pytest.mark.parametrize("field", PROMPT_VARIANT_FIELDS)
def test_a_row_missing_a_prompt_variant_field_is_refused_by_name(
    kind: str, field: str
) -> None:
    complete = COMPLETE_RUNTIME_ROW if kind == "runtime" else COMPLETE_QUALITY_ROW
    row = {key: value for key, value in complete.items() if key != field}

    with pytest.raises(RowContractError, match=field):
        validate_row(kind, row)


def test_a_hand_built_baseline_row_with_a_transformed_prompt_is_refused() -> None:
    # Epic success check 1, the variant half: the row claims `baseline` while
    # the prompt it carries before templating was transformed -- here, the
    # authored item with a terse-output instruction appended, which is what an
    # output-compression variant would have sent.
    hand_built = {
        **COMPLETE_QUALITY_ROW,
        "prompt_before_template": _AUTHORED_PROMPT + "\nAnswer in one word.",
    }

    with pytest.raises(RowContractError, match="prompt_before_template") as excinfo:
        validate_row("quality", hand_built)

    # Printed so `pytest -s` publishes the gate's own words as the evidence.
    print(f"refused: {excinfo.value}")


def test_a_baseline_runtime_row_with_a_transformed_fixed_prompt_is_refused() -> None:
    hand_built = {
        **COMPLETE_RUNTIME_ROW,
        "prompt_before_template": FIXED_PROMPT.upper(),
    }

    with pytest.raises(RowContractError, match="prompt_before_template"):
        validate_row("runtime", hand_built)


def test_a_genuine_baseline_row_of_each_kind_passes() -> None:
    assert COMPLETE_QUALITY_ROW["prompt_before_template"] == _AUTHORED_PROMPT
    validate_row("quality", COMPLETE_QUALITY_ROW)
    validate_row("runtime", COMPLETE_RUNTIME_ROW)


def test_an_unregistered_prompt_variant_is_refused_naming_the_field() -> None:
    row = {**COMPLETE_QUALITY_ROW, "prompt_variant_id": "output_compressed"}

    with pytest.raises(RowContractError, match="prompt_variant_id 'output_compressed'"):
        validate_row("quality", row)


def test_an_unregistered_prompt_variant_version_is_refused_naming_the_field() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "prompt_variant_version": "2"}

    with pytest.raises(RowContractError, match="prompt_variant_version '2'"):
        validate_row("runtime", row)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"suite_id": "an-unknown-suite"}, "not a suite this code defines"),
        ({"suite_version": "1"}, "is at version"),
        ({"item_id": "no-such-item"}, "has no item 'no-such-item'"),
    ],
)
def test_a_baseline_row_whose_authored_text_cannot_be_resolved_is_refused(
    changes: dict, reason: str
) -> None:
    # An unresolvable item leaves the claim unchecked, and an unchecked
    # `baseline` is the label this gate exists to stop trusting.
    row = {**COMPLETE_QUALITY_ROW, **changes}

    with pytest.raises(RowContractError, match="prompt_before_template") as excinfo:
        validate_row("quality", row)
    assert reason in str(excinfo.value)


def test_a_registered_non_baseline_variant_is_not_held_to_the_authored_text(
    monkeypatch,
) -> None:
    # The authored-text rule is baseline's own: another variant's job is to
    # transform the prompt, so its pre-template string differs by design.
    definition = {"transformation": "identity", "description": "test-only"}
    registry = prompt_variants.load_registry(
        [
            *prompt_variants.REGISTERED_VARIANTS,
            {
                "variant_id": "test_variant",
                "version": "1",
                "definition": definition,
                "definition_hash": prompt_variants.definition_hash(definition),
            },
        ]
    )
    monkeypatch.setattr(prompt_variants, "REGISTRY", registry)
    row = {
        **COMPLETE_QUALITY_ROW,
        "prompt_variant_id": "test_variant",
        "prompt_before_template": "anything at all",
    }

    validate_row("quality", row)


# --------------------------------------------------------------------------
# Subject egress (schema "16"): where the subject prompt went, on every row.


def test_the_schema_version_moved_for_the_subject_egress() -> None:
    # "16" makes every row of either kind state where its subject prompt went.
    # Not conditional: every row was produced by sending a prompt somewhere.
    assert SCHEMA_VERSION == "19"
    for kind in ("runtime", "quality"):
        assert "subject_egress" in REQUIRED_FIELDS[kind]
    # The subject field is not a member of the judge block, and the judge
    # block's own egress record keeps its shape.
    assert "subject_egress" not in JUDGED_FIELDS
    assert "subject_egress" not in JUDGE_EGRESS_FIELDS


def _complete_row(kind: str) -> dict:
    return dict(COMPLETE_RUNTIME_ROW if kind == "runtime" else COMPLETE_QUALITY_ROW)


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_a_row_missing_its_subject_egress_is_refused_by_name(kind: str) -> None:
    row = {k: v for k, v in _complete_row(kind).items() if k != "subject_egress"}

    with pytest.raises(RowContractError, match="subject_egress"):
        validate_row(kind, row)


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_a_row_with_a_null_subject_egress_is_refused_by_name(kind: str) -> None:
    row = {**_complete_row(kind), "subject_egress": None}

    with pytest.raises(RowContractError, match="subject_egress null"):
        validate_row(kind, row)


@pytest.mark.parametrize("kind", ["runtime", "quality"])
@pytest.mark.parametrize("value", ["", "  ", 7, True])
def test_a_malformed_subject_egress_is_refused(kind: str, value: object) -> None:
    row = {**_complete_row(kind), "subject_egress": value}

    with pytest.raises(RowContractError, match="malformed subject_egress"):
        validate_row(kind, row)


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_the_writer_gate_appends_nothing_for_a_row_without_subject_egress(
    kind: str, tmp_path: Path
) -> None:
    path = tmp_path / "rows.jsonl"
    row = {k: v for k, v in _complete_row(kind).items() if k != "subject_egress"}

    with pytest.raises(RowContractError, match="subject_egress"):
        append_row(path, kind, row)

    assert not path.exists()


def test_a_runtime_row_recording_none_validates() -> None:
    assert COMPLETE_RUNTIME_ROW["subject_egress"] == "none"
    validate_row("runtime", COMPLETE_RUNTIME_ROW)


@pytest.mark.parametrize("egress", ["mistral", "google"])
def test_a_runtime_row_recording_a_provider_is_refused(egress: str) -> None:
    row = {**COMPLETE_RUNTIME_ROW, "subject_egress": egress}

    with pytest.raises(RowContractError, match=f"subject_egress {egress!r}"):
        validate_row("runtime", row)


def test_a_local_quality_row_recording_none_validates() -> None:
    assert COMPLETE_QUALITY_ROW["provider"] == "local"
    assert COMPLETE_QUALITY_ROW["subject_egress"] == "none"
    validate_row("quality", COMPLETE_QUALITY_ROW)


@pytest.mark.parametrize("provider", ["mistral", "google"])
def test_a_cloud_quality_row_recording_its_provider_validates(provider: str) -> None:
    validate_row(
        "quality",
        {
            **COMPLETE_QUALITY_ROW,
            "provider": provider,
            "subject_egress": provider,
            "retry_budget": {provider: 4},
            "family": provider,
            "size_class": None,
        },
    )


@pytest.mark.parametrize("egress", ["mistral", "google"])
def test_a_local_quality_row_recording_a_provider_is_refused(egress: str) -> None:
    row = {**COMPLETE_QUALITY_ROW, "subject_egress": egress}

    with pytest.raises(RowContractError) as excinfo:
        validate_row("quality", row)

    message = str(excinfo.value)
    assert f"subject_egress {egress!r}" in message
    assert "provider 'local'" in message


@pytest.mark.parametrize("provider", ["mistral", "google"])
def test_a_cloud_quality_row_recording_none_is_refused(provider: str) -> None:
    row = {**COMPLETE_QUALITY_ROW, "provider": provider, "subject_egress": "none"}

    with pytest.raises(RowContractError) as excinfo:
        validate_row("quality", row)

    message = str(excinfo.value)
    assert "subject_egress 'none'" in message
    assert f"provider {provider!r}" in message


def test_a_cloud_quality_row_recording_another_provider_is_refused() -> None:
    row = {**COMPLETE_QUALITY_ROW, "provider": "mistral", "subject_egress": "google"}

    with pytest.raises(RowContractError, match="subject_egress 'google'"):
        validate_row("quality", row)


def test_subject_egress_for_maps_local_to_none_and_a_cloud_provider_to_itself() -> None:
    assert subject_egress_for("local") == "none"
    assert subject_egress_for("mistral") == "mistral"
    assert subject_egress_for("google") == "google"


def test_a_judged_row_keeps_its_judge_egress_beside_the_subject_egress() -> None:
    # A local subject judged by two cloud judges: the subject prompt stayed on
    # the machine, the item left it for judging. Two facts, two fields, and
    # neither is merged into the other.
    row = COMPLETE_JUDGED_QUALITY_ROW
    assert row["subject_egress"] == "none"
    assert row["judge_egress"]["item_left_machine"] is True
    assert set(row["judge_egress"]) == JUDGE_EGRESS_FIELDS

    validate_row("quality", row)


def test_the_schema_version_moved_for_the_retry_budget_and_partial_batches() -> None:
    # "17" makes every quality row name the retry budget its batch ran under
    # and whether that batch was left partial. The runtime row makes no cloud
    # call and has no resume, so it is untouched.
    assert SCHEMA_VERSION == "19"
    for field in ("retry_budget", "partial_failure"):
        assert field in REQUIRED_FIELDS["quality"]
        assert field not in REQUIRED_FIELDS["runtime"]


@pytest.mark.parametrize("field", ["retry_budget", "partial_failure"])
def test_a_quality_row_without_a_schema_17_field_is_refused_by_name(field: str) -> None:
    row = {key: value for key, value in COMPLETE_QUALITY_ROW.items() if key != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


@pytest.mark.parametrize(
    "budget",
    [None, [], {"mistral": -1}, {"mistral": True}, {"mistral": 1.5}, {"": 3}],
)
def test_a_malformed_retry_budget_is_refused(budget: object) -> None:
    row = {**COMPLETE_QUALITY_ROW, "retry_budget": budget}

    with pytest.raises(RowContractError, match="retry_budget"):
        validate_row("quality", row)


def test_a_cloud_row_that_does_not_name_its_own_providers_budget_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "provider": "mistral",
        "subject_egress": "mistral",
        "retry_budget": {"google": 4},
    }

    with pytest.raises(RowContractError, match="no retry_budget entry for it"):
        validate_row("quality", row)


def test_a_row_whose_retries_exceed_its_providers_budget_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "provider": "google",
        "subject_egress": "google",
        "retry_budget": {"google": 2},
        "retries": 3,
    }

    with pytest.raises(RowContractError, match="above its provider's retry_budget"):
        validate_row("quality", row)


_PARTIAL = {"provider": "mistral", "item_id": "billing-02", "reason": "429"}


def test_a_partial_row_naming_its_failure_and_carrying_no_score_validates() -> None:
    validate_row(
        "quality",
        {
            **COMPLETE_QUALITY_ROW,
            "partial_failure": dict(_PARTIAL),
            "suite_accuracy": None,
            "language_breakdown": None,
        },
    )


@pytest.mark.parametrize(
    "failure",
    [
        "429",
        {"provider": "mistral", "item_id": "billing-02"},
        {"provider": "", "item_id": "billing-02", "reason": "429"},
        {"provider": "mistral", "item_id": None, "reason": "429"},
    ],
)
def test_a_malformed_partial_failure_is_refused(failure: object) -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "partial_failure": failure,
        "suite_accuracy": None,
        "language_breakdown": None,
    }

    with pytest.raises(RowContractError, match="partial_failure"):
        validate_row("quality", row)


def test_a_partial_row_publishing_a_suite_score_is_refused_by_name() -> None:
    # A mean over the items that finished before the failure is a biased
    # sample, not a partial score.
    row = {
        **COMPLETE_QUALITY_ROW,
        "partial_failure": dict(_PARTIAL),
        "language_breakdown": None,
    }

    with pytest.raises(RowContractError, match="suite_accuracy"):
        validate_row("quality", row)


def test_a_partial_graded_row_validates_with_its_suite_score_null() -> None:
    validate_row(
        "quality",
        {
            **COMPLETE_GRADED_QUALITY_ROW,
            "partial_failure": dict(_PARTIAL),
            "suite_score": None,
            "score_breakdown": None,
        },
    )


def test_a_complete_graded_row_with_a_null_suite_score_is_still_refused() -> None:
    row = {**COMPLETE_GRADED_QUALITY_ROW, "suite_score": None}

    with pytest.raises(RowContractError, match="suite_score"):
        validate_row("quality", row)


def test_a_partial_judged_row_publishing_a_headline_is_refused_by_name() -> None:
    row = {
        **COMPLETE_JUDGED_QUALITY_ROW,
        "partial_failure": dict(_PARTIAL),
        "suite_accuracy": None,
        "language_breakdown": None,
        "judged_headline_score": 4.0,
    }

    with pytest.raises(RowContractError, match="judged_headline_score"):
        validate_row("quality", row)


# --------------------------------------------------------------------------
# Schema "18": the item's own tokens and first-token time


def test_the_schema_version_moved_for_the_per_item_measurement() -> None:
    # "18" puts each item's own tokens, engine-reported TTFT and cached prompt
    # tokens on every quality row (Q24 (a)); the runtime row keeps its
    # Methodology 6 aggregate and is untouched.
    assert SCHEMA_VERSION == "19"
    assert ITEM_MEASUREMENT_FIELDS <= REQUIRED_FIELDS["quality"]
    assert ITEM_MEASUREMENT_FIELDS.isdisjoint(REQUIRED_FIELDS["runtime"])


def test_the_row_block_the_writers_build_is_exactly_the_contracts() -> None:
    block = quality_rows.item_measurement_fields(
        timings.parse_item_measurement({}), first_in_batch=False
    )

    assert set(block) == ITEM_MEASUREMENT_FIELDS
    validate_row("quality", {**COMPLETE_QUALITY_ROW, **block})


@pytest.mark.parametrize("field", sorted(ITEM_MEASUREMENT_FIELDS))
def test_a_quality_row_missing_a_per_item_field_is_refused_by_name(field) -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


@pytest.mark.parametrize(
    "field", ["item_tokens_in", "item_tokens_out", "item_prompt_tokens_cached"]
)
def test_a_null_value_without_its_reason_is_refused(field) -> None:
    row = {**COMPLETE_QUALITY_ROW, field: None}

    with pytest.raises(RowContractError, match=f"{field} null"):
        validate_row("quality", row)


def test_a_null_ttft_with_its_reason_and_no_source_validates() -> None:
    validate_row(
        "quality",
        {
            **COMPLETE_QUALITY_ROW,
            "item_ttft_ms": None,
            "item_ttft_ms_null_reason": "not_reported_by_engine",
            "item_ttft_source": None,
        },
    )


def test_a_reported_value_beside_a_null_reason_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "item_tokens_out_null_reason": "not_reported_by_engine",
    }

    with pytest.raises(RowContractError, match="item_tokens_out=2 beside"):
        validate_row("quality", row)


def test_an_unknown_null_reason_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "item_tokens_in": None,
        "item_tokens_in_null_reason": "zero",
    }

    with pytest.raises(RowContractError, match="item_tokens_in null"):
        validate_row("quality", row)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("item_tokens_in", -1),
        ("item_tokens_out", 2.5),
        ("item_prompt_tokens_cached", True),
        ("item_ttft_ms", "13.7"),
        ("item_ttft_ms", -0.1),
    ],
)
def test_a_malformed_per_item_value_is_refused(field, value) -> None:
    row = {**COMPLETE_QUALITY_ROW, field: value}

    with pytest.raises(RowContractError, match=f"malformed {field}"):
        validate_row("quality", row)


def test_a_ttft_must_name_a_recognised_source() -> None:
    row = {**COMPLETE_QUALITY_ROW, "item_ttft_source": "stopwatch"}

    with pytest.raises(RowContractError, match="unrecognised item_ttft_source"):
        validate_row("quality", row)


def test_a_source_without_a_ttft_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "item_ttft_ms": None,
        "item_ttft_ms_null_reason": "not_reported_by_provider",
    }

    with pytest.raises(RowContractError, match="item_ttft_source"):
        validate_row("quality", row)


def test_the_measurement_kind_is_the_single_generation_label() -> None:
    row = {**COMPLETE_QUALITY_ROW, "item_measurement_kind": "median_of_5"}

    with pytest.raises(RowContractError, match="item_measurement_kind"):
        validate_row("quality", row)


def test_the_first_generation_mark_is_a_boolean() -> None:
    row = {**COMPLETE_QUALITY_ROW, "item_first_in_batch": None}

    with pytest.raises(RowContractError, match="item_first_in_batch"):
        validate_row("quality", row)


# --------------------------------------------------------------------------
# Schema "19": the subject's family and size class


def test_the_schema_version_moved_for_the_subject_composition() -> None:
    # "19" puts the subject's family and size class on every quality row; the
    # runtime row is untouched.
    assert SCHEMA_VERSION == "19"
    assert SUBJECT_COMPOSITION_SCHEMA_VERSION == "19"
    assert SUBJECT_COMPOSITION_FIELDS == {"family", "size_class"}
    assert SUBJECT_COMPOSITION_FIELDS <= REQUIRED_FIELDS["quality"]
    assert SUBJECT_COMPOSITION_FIELDS.isdisjoint(REQUIRED_FIELDS["runtime"])


@pytest.mark.parametrize("field", ["family", "size_class"])
def test_a_quality_row_without_family_or_size_class_is_refused_at_19(field) -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


def test_an_earlier_version_row_without_either_field_still_validates() -> None:
    row = {
        k: v
        for k, v in COMPLETE_QUALITY_ROW.items()
        if k not in SUBJECT_COMPOSITION_FIELDS
    }

    validate_row("quality", {**row, "schema_version": "18"})


@pytest.mark.parametrize("version", ["19", "20", "not-a-version", None])
def test_a_row_at_or_past_19_or_with_no_readable_version_owes_both(version) -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != "size_class"}

    with pytest.raises(RowContractError, match="size_class"):
        validate_row("quality", {**row, "schema_version": version})


@pytest.mark.parametrize("family", ["gemma", None, "", ["qwen"]])
def test_an_unknown_family_is_refused_by_value(family) -> None:
    with pytest.raises(RowContractError, match="has family"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "family": family})


@pytest.mark.parametrize("size_class", ["8B", "~8b-and-up", 4])
def test_an_unknown_size_class_is_refused_by_value(size_class) -> None:
    with pytest.raises(RowContractError, match="has size_class"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "size_class": size_class})


def test_a_local_row_whose_entry_declares_no_class_records_null() -> None:
    validate_row("quality", {**COMPLETE_QUALITY_ROW, "size_class": None})


def test_a_cloud_row_with_a_size_class_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "provider": "mistral",
        "subject_egress": "mistral",
        "model_id": "mistral-small-2603",
        "family": "mistral",
        "retry_budget": {"mistral": 4},
    }

    validate_row("quality", {**row, "size_class": None})
    with pytest.raises(RowContractError, match="a cloud subject has no size class"):
        validate_row("quality", row)


def _entry(**changes) -> roster.RosterEntry:
    base = roster.RosterEntry(
        entry_id="flagship",
        repo="r",
        revision="main",
        file="f.gguf",
        display_id="Qwen3.6-35B-A3B",
        quant="q",
        sha256="0" * 64,
        architecture=roster.Architecture("moe", 40, 3.1),
        server_flags={},
        validated_host={},
        size_class="~8B-and-up",
    )
    return dataclasses.replace(base, **changes)


def test_the_writers_block_names_the_local_subject_and_its_class() -> None:
    # The flagship declares no family of its own: it resolves through the
    # in-code fallback, with no exception carved out.
    block = quality_rows.subject_composition_fields(
        "Qwen3.6-35B-A3B", "local", _entry()
    )

    assert block == {"family": "qwen", "size_class": "~8B-and-up"}
    validate_row("quality", {**COMPLETE_QUALITY_ROW, **block})


def test_the_writers_block_names_a_cloud_subject_by_its_own_family() -> None:
    # The cloud row cites the local entry it ran beside; the family it carries
    # is still its own model's, never the entry's.
    block = quality_rows.subject_composition_fields(
        "gemini-3.5-flash-lite", "google", _entry()
    )

    assert block == {"family": "google", "size_class": None}
