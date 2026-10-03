import dataclasses
from pathlib import Path

import pytest

from wave_local_ai_v2 import (
    FIXED_PROMPT,
    aggregation,
    engines,
    harness,
    machines,
    prompt_variants,
    quality_rows,
    roster,
    score_interval,
    suite_registry,
    timings,
)
from wave_local_ai_v2.results import append_row
from wave_local_ai_v2.row_contract import (
    CAMPAIGN_SCHEMA_VERSION,
    CODE_FIELDS,
    ENGINE_FICHE_SCHEMA_VERSION,
    ENGINE_NOT_APPLICABLE,
    GRADED_FIELDS,
    HARNESS_FIELDS,
    HARNESS_SCHEMA_VERSION,
    ITEM_MEASUREMENT_FIELDS,
    JUDGE_EGRESS_FIELDS,
    JUDGED_FIELDS,
    MACHINE_FICHE_SCHEMA_VERSION,
    MACHINE_NOT_APPLICABLE,
    NO_CAMPAIGN,
    PARTIAL_NULL_SCORE_FIELDS,
    PROFILE_FIELDS,
    PROFILE_NOT_APPLICABLE,
    PROFILE_SCHEMA_VERSION,
    REQUIRED_FIELDS,
    SCHEMA_VERSION,
    SCORE_INTERVAL_FIELDS,
    SCORE_INTERVAL_SCHEMA_VERSION,
    SUBJECT_COMPOSITION_FIELDS,
    SUBJECT_COMPOSITION_SCHEMA_VERSION,
    VRAM_NOT_APPLICABLE,
    VRAM_NOT_APPLICABLE_SCHEMA_VERSION,
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
    "engine_id": "llama.cpp",
    "engine_build": "b10537",
    "machine_id": "laptop-mobile-gpu",
    "compute_mode": "gpu",
    "profile_id": "qwen3.6-35b-a3b-ud-iq4xs@laptop-mobile-gpu/gpu",
    "profile_overrides": {},
    "campaign_id": "none",
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
    "prompt_variant_noop": False,
    "constraint_mechanism": "none",
    "constraint_grammar_hash": None,
    "prompt_before_template": _AUTHORED_PROMPT,
    "model_id": "Qwen3.6-35B-A3B",
    "provider": "local",
    "subject_egress": "none",
    "engine_id": "llama.cpp",
    "engine_build": "b10537",
    "machine_id": "laptop-mobile-gpu",
    "compute_mode": "gpu",
    "profile_id": "qwen3.6-35b-a3b-ud-iq4xs@laptop-mobile-gpu/gpu",
    "profile_overrides": {},
    "campaign_id": "none",
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
    # A local subject's block: decided on identical output, under no tolerance.
    "verdict": {
        "verdict": "not_comparable",
        "reference_run_id": None,
        "subject_rule": "identical",
        "tolerance": None,
        "divergence": None,
        "single_run_indicative": None,
    },
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
    # The reference harness, its version read from the installed package and
    # its overhead measured: the engine's 57 tokens were the item's own.
    "harness_id": "direct",
    "harness_version": harness.harness_version("direct"),
    "harness_prompt_overhead": {"tokens": 0, "null_reason": None},
    # The batch's interval over its one item: constant, so zero_width; the
    # two empty language cells name no_items.
    "score_interval": score_interval.interval_block(
        [{"item_id": "billing-01", "language": "en"}], [1.0]
    ),
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
    assert SCHEMA_VERSION == "30"


def test_the_schema_version_moved_for_the_runtime_energy_window() -> None:
    # "12" fixes audit finding C3: the runtime row's energy figures used to
    # span the whole counted-repetition window, cooldowns included. Required
    # only on runtime rows -- quality rows carry no energy window at all.
    assert SCHEMA_VERSION == "30"
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
    assert SCHEMA_VERSION == "30"
    assert set(NEW_JUDGE_RECORD_FIELDS).isdisjoint(REQUIRED_FIELDS["quality"])
    assert set(NEW_JUDGE_RECORD_FIELDS).isdisjoint(JUDGED_FIELDS)
    validate_row("quality", COMPLETE_QUALITY_ROW)


def test_the_schema_version_moved_for_the_prompt_variant() -> None:
    # "14" makes both row kinds name the variant they ran under and carry the
    # prompt as the variant left it. Not conditional: every row ran under some
    # variant, and a row below "14" is never back-filled with `baseline`.
    assert SCHEMA_VERSION == "30"
    for kind in ("runtime", "quality"):
        assert set(PROMPT_VARIANT_FIELDS) <= REQUIRED_FIELDS[kind]


def test_the_schema_version_moved_for_the_engine() -> None:
    # "22" makes every row name the engine that produced it and its build,
    # and moves the cited fiche to the projection carrying the engine fields.
    assert SCHEMA_VERSION == "30"
    assert ENGINE_FICHE_SCHEMA_VERSION == "22"
    for kind in ("runtime", "quality"):
        assert {"engine_id", "engine_build"} <= REQUIRED_FIELDS[kind]


@pytest.mark.parametrize(
    ("kind", "row"),
    [("runtime", COMPLETE_RUNTIME_ROW), ("quality", COMPLETE_QUALITY_ROW)],
    ids=["runtime", "local-quality"],
)
@pytest.mark.parametrize("field", ["engine_id", "engine_build"])
def test_a_local_row_missing_an_engine_field_is_refused_naming_it(
    kind: str, row: dict, field: str
) -> None:
    incomplete = {key: value for key, value in row.items() if key != field}

    with pytest.raises(RowContractError, match=field):
        validate_row(kind, incomplete)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kind", "row"),
    [("runtime", COMPLETE_RUNTIME_ROW), ("quality", COMPLETE_QUALITY_ROW)],
    ids=["runtime", "local-quality"],
)
def test_an_unregistered_engine_is_refused_through_the_gate_naming_it(
    tmp_path, kind: str, row: dict
) -> None:
    path = tmp_path / f"{kind}.jsonl"

    with pytest.raises(RowContractError, match="engine_id 'ollama'.*not a registered"):
        append_row(path, kind, {**row, "engine_id": "ollama"})  # type: ignore[arg-type]

    assert not path.exists()


def test_a_local_row_with_an_unreadable_build_still_validates() -> None:
    validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "engine_build": None})


@pytest.mark.parametrize("build", ["", 10537])
def test_a_malformed_engine_build_is_refused(build: object) -> None:
    with pytest.raises(RowContractError, match="malformed engine_build"):
        validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "engine_build": build})


# What a cloud subject's row states for the engine, the machine and the mode:
# no local model produced it.
_NO_ENGINE = {
    "engine_id": ENGINE_NOT_APPLICABLE,
    "engine_build": None,
    "machine_id": MACHINE_NOT_APPLICABLE,
    "compute_mode": MACHINE_NOT_APPLICABLE,
    "profile_id": PROFILE_NOT_APPLICABLE,
    "profile_overrides": PROFILE_NOT_APPLICABLE,
}


def _cloud_verdict(row: dict, **changes: object) -> dict:
    """A cloud subject's verdict block, decided under the row's own suite."""
    return {
        "verdict": "reproduced",
        "reference_run_id": "run-0",
        "subject_rule": "within_tolerance",
        "tolerance": {
            "value": 0.1,
            "unit": "fraction_of_items",
            "suite_id": row["suite_id"],
            "suite_version": row["suite_version"],
        },
        "divergence": 0.05,
        "single_run_indicative": None,
        **changes,
    }


def _cloud_row(provider: str, **changes: object) -> dict:
    """A complete quality row for a `provider` subject, before `changes`."""
    row = {
        **COMPLETE_QUALITY_ROW,
        "provider": provider,
        "subject_egress": provider,
        "retry_budget": {provider: 4},
        "family": provider,
        "size_class": None,
        **_NO_ENGINE,
        **changes,
    }
    if "verdict" not in changes:
        row["verdict"] = _cloud_verdict(row)
    return row


def test_a_cloud_row_states_the_engine_does_not_apply() -> None:
    validate_row("quality", _cloud_row("mistral"))


def test_a_row_below_the_engine_schema_validates_without_the_engine_fields() -> None:
    old = {
        key: value
        for key, value in COMPLETE_QUALITY_ROW.items()
        if key not in {"engine_id", "engine_build"}
    }

    validate_row("quality", {**old, "schema_version": "21"})
    with pytest.raises(RowContractError, match="engine_build, engine_id"):
        validate_row("quality", {**old, "schema_version": "22"})


def test_a_row_below_the_engine_schema_is_not_held_to_the_registry() -> None:
    # A "21" row predates the engine fields: whatever it carries under those
    # keys is not this contract's to judge, and it is never back-filled.
    validate_row(
        "quality",
        {**COMPLETE_QUALITY_ROW, "schema_version": "21", "engine_id": "ollama"},
    )


@pytest.mark.parametrize(
    ("engine_id", "engine_build"),
    [
        ("llama.cpp", "b10537"),
        ("llama.cpp", None),
        ("not_applicable", "b10537"),
        (None, None),
    ],
)
def test_a_cloud_row_never_carries_an_engine(
    engine_id: object, engine_build: object
) -> None:
    cloud = _cloud_row("google", engine_id=engine_id, engine_build=engine_build)

    with pytest.raises(RowContractError, match="produced by no local engine"):
        validate_row("quality", cloud)


def test_an_unreadable_engine_registry_refuses_the_row(monkeypatch) -> None:
    def unreadable() -> frozenset[str]:
        raise engines.EngineRegistryError("engine registry not readable")

    monkeypatch.setattr(engines, "registered_engine_ids", unreadable)

    with pytest.raises(RowContractError, match="engine registry cannot be read"):
        validate_row("runtime", COMPLETE_RUNTIME_ROW)


def test_the_schema_version_moved_for_the_machine_and_mode() -> None:
    # "23" makes every row name the declared machine and the compute mode,
    # and moves the cited fiche to the projection carrying both.
    assert SCHEMA_VERSION == "30"
    assert MACHINE_FICHE_SCHEMA_VERSION == "23"
    for kind in ("runtime", "quality"):
        assert {"machine_id", "compute_mode"} <= REQUIRED_FIELDS[kind]


@pytest.mark.parametrize(
    ("kind", "row"),
    [("runtime", COMPLETE_RUNTIME_ROW), ("quality", COMPLETE_QUALITY_ROW)],
    ids=["runtime", "local-quality"],
)
@pytest.mark.parametrize("field", ["machine_id", "compute_mode"])
def test_a_row_missing_the_machine_or_the_mode_is_refused_naming_it(
    kind: str, row: dict, field: str
) -> None:
    incomplete = {key: value for key, value in row.items() if key != field}

    with pytest.raises(RowContractError, match=field):
        validate_row(kind, incomplete)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("kind", "row"),
    [("runtime", COMPLETE_RUNTIME_ROW), ("quality", COMPLETE_QUALITY_ROW)],
    ids=["runtime", "local-quality"],
)
def test_an_undeclared_machine_is_refused_through_the_gate_naming_the_declared(
    tmp_path, kind: str, row: dict
) -> None:
    path = tmp_path / f"{kind}.jsonl"

    with pytest.raises(
        RowContractError, match="machine_id 'my-box'.*declared: laptop-mobile-gpu"
    ):
        append_row(path, kind, {**row, "machine_id": "my-box"})  # type: ignore[arg-type]

    assert not path.exists()


@pytest.mark.parametrize("mode", [None, "hybrid", MACHINE_NOT_APPLICABLE])
def test_a_local_row_names_gpu_or_cpu_only(mode: object) -> None:
    with pytest.raises(RowContractError, match="compute_mode"):
        validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "compute_mode": mode})


def test_a_cpu_only_row_on_the_no_gpu_machine_validates() -> None:
    validate_row(
        "quality",
        {
            **COMPLETE_QUALITY_ROW,
            "machine_id": "pro-pc-no-gpu",
            "compute_mode": "cpu_only",
        },
    )


@pytest.mark.parametrize(
    ("machine_id", "compute_mode"),
    [
        ("laptop-mobile-gpu", "gpu"),
        (MACHINE_NOT_APPLICABLE, "cpu_only"),
        ("laptop-mobile-gpu", MACHINE_NOT_APPLICABLE),
        (None, None),
    ],
)
def test_a_cloud_row_never_carries_a_machine_or_a_mode(
    machine_id: object, compute_mode: object
) -> None:
    cloud = _cloud_row("mistral", machine_id=machine_id, compute_mode=compute_mode)

    with pytest.raises(RowContractError, match="produced by no local model"):
        validate_row("quality", cloud)


def test_a_row_below_the_machine_schema_validates_without_both_fields() -> None:
    old = {
        key: value
        for key, value in COMPLETE_RUNTIME_ROW.items()
        if key not in {"machine_id", "compute_mode"}
    }

    validate_row("runtime", {**old, "schema_version": "22"})
    validate_row(
        "runtime",
        {**COMPLETE_RUNTIME_ROW, "schema_version": "22", "machine_id": "my-box"},
    )
    with pytest.raises(RowContractError, match="compute_mode, machine_id"):
        validate_row("runtime", {**old, "schema_version": "23"})


def test_an_unreadable_machine_registry_refuses_the_row(monkeypatch) -> None:
    def unreadable() -> frozenset[str]:
        raise machines.MachineRegistryError("machine registry not readable")

    monkeypatch.setattr(machines, "declared_machine_ids", unreadable)

    with pytest.raises(RowContractError, match="machine registry cannot be read"):
        validate_row("runtime", COMPLETE_RUNTIME_ROW)


def test_the_schema_version_moved_for_the_suite_level() -> None:
    # "15" makes every quality row name the level its suite was certified at
    # and its item's licence, source and source revision. Not conditional:
    # every suite is certified at some level. Quality rows only -- a runtime
    # row runs no suite.
    assert SCHEMA_VERSION == "30"
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
    row = {**COMPLETE_QUALITY_ROW, "prompt_variant_id": "input_compressed"}

    with pytest.raises(RowContractError, match="prompt_variant_id 'input_compressed'"):
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


def test_a_non_baseline_row_below_27_is_not_held_to_the_authored_text(
    monkeypatch,
) -> None:
    # Below "27" the authored-text rule was baseline's own; such a row is
    # never re-checked under the rule "27" added.
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
        "schema_version": "26",
        "prompt_variant_id": "test_variant",
        "prompt_before_template": "anything at all",
    }
    del row["prompt_variant_noop"]

    validate_row("quality", row)


# --------------------------------------------------------------------------
# The variant no-op (schema "27"): a quality row says whether its variant
# skipped the item's task family, and the gate checks it and the prompt.


def _output_compressed_row(**changes) -> dict:
    variant = prompt_variants.resolve(prompt_variants.OUTPUT_COMPRESSED_ID, "1")
    row = {
        **COMPLETE_QUALITY_ROW,
        "prompt_variant_id": variant.variant_id,
        "prompt_variant_version": variant.version,
        "prompt_before_template": prompt_variants.apply_variant(
            variant, _AUTHORED_PROMPT, COMPLETE_QUALITY_ROW["task_suite"]
        ).prompt,
        "prompt_variant_noop": False,
    }
    row.update(changes)
    return row


def test_an_output_compressed_classification_row_validates() -> None:
    validate_row("quality", _output_compressed_row())


def test_a_quality_row_at_27_missing_the_noop_field_is_refused_by_name() -> None:
    row = dict(COMPLETE_QUALITY_ROW)
    del row["prompt_variant_noop"]

    with pytest.raises(RowContractError, match="prompt_variant_noop"):
        validate_row("quality", row)


def test_a_quality_row_below_27_owes_no_noop_field() -> None:
    row = {**COMPLETE_QUALITY_ROW, "schema_version": "26"}
    del row["prompt_variant_noop"]

    validate_row("quality", row)


@pytest.mark.parametrize("noop", [True, 1, None])
def test_a_noop_value_disagreeing_with_the_registry_is_refused(noop) -> None:
    row = _output_compressed_row(prompt_variant_noop=noop)

    with pytest.raises(RowContractError, match="prompt_variant_noop") as excinfo:
        validate_row("quality", row)
    assert "applies to task family 'classification'" in str(excinfo.value)


def test_a_variant_row_whose_prompt_is_not_the_variant_output_is_refused() -> None:
    row = _output_compressed_row(prompt_before_template=_AUTHORED_PROMPT)

    with pytest.raises(RowContractError, match="'output_compressed'"):
        validate_row("quality", row)


def test_a_variant_row_whose_item_cannot_be_resolved_is_not_held_to_a_text() -> None:
    # Only `baseline` refuses an unresolvable item: another variant's row
    # still carries its no-op check.
    row = _output_compressed_row(suite_id="an-unknown-suite")

    validate_row("quality", row)


def test_a_noop_row_carries_the_authored_text_and_says_so(monkeypatch) -> None:
    # A family the variant does not declare: the item still runs, with the
    # authored prompt unchanged, and the row states the no-op.
    row = _output_compressed_row(
        task_suite="judge-probe",
        prompt_before_template=_AUTHORED_PROMPT,
        prompt_variant_noop=True,
    )

    validate_row("quality", row)

    with pytest.raises(RowContractError, match="prompt_variant_noop"):
        validate_row("quality", {**row, "prompt_variant_noop": False})


# --------------------------------------------------------------------------
# The decoding constraint (schema "28"): a quality row names the mechanism its
# answer ran under and the grammar's hash, checked against the registry.

_CLASSIFICATION_GRAMMAR_HASH = prompt_variants.grammar_hash(
    'root ::= "account" | "billing" | "other" | "technical"'
)


def _constrained_row(**changes) -> dict:
    variant = prompt_variants.resolve(prompt_variants.CONSTRAINED_OUTPUT_ID, "1")
    row = {
        **COMPLETE_QUALITY_ROW,
        "prompt_variant_id": variant.variant_id,
        "prompt_variant_version": variant.version,
        "prompt_variant_noop": False,
        "constraint_mechanism": "gbnf",
        "constraint_grammar_hash": _CLASSIFICATION_GRAMMAR_HASH,
    }
    row.update(changes)
    return row


def test_a_constrained_classification_row_names_gbnf_and_its_grammar_hash() -> None:
    assert COMPLETE_QUALITY_ROW["task_suite"] == "classification"

    validate_row("quality", _constrained_row())


@pytest.mark.parametrize(
    ("changes", "named"),
    [
        ({"constraint_mechanism": "none"}, "constraint_mechanism 'none'"),
        ({"constraint_grammar_hash": "0" * 64}, "constraint_grammar_hash"),
        ({"constraint_grammar_hash": None}, "constraint_grammar_hash None"),
    ],
)
def test_a_constraint_disagreeing_with_the_registry_is_refused(changes, named) -> None:
    with pytest.raises(RowContractError, match=named):
        validate_row("quality", _constrained_row(**changes))


def test_an_unconstrained_row_claiming_a_grammar_is_refused() -> None:
    row = {**COMPLETE_QUALITY_ROW, "constraint_mechanism": "gbnf"}

    with pytest.raises(RowContractError, match="sends 'none'"):
        validate_row("quality", row)


def test_a_constrained_noop_row_names_no_mechanism() -> None:
    row = _constrained_row(
        task_suite="judge-probe",
        prompt_variant_noop=True,
        constraint_mechanism="none",
        constraint_grammar_hash=None,
    )

    validate_row("quality", row)


@pytest.mark.parametrize("field", ["constraint_mechanism", "constraint_grammar_hash"])
def test_a_quality_row_at_28_missing_a_constraint_field_is_refused(field) -> None:
    row = dict(COMPLETE_QUALITY_ROW)
    del row[field]

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


def test_a_quality_row_below_28_owes_no_constraint_field() -> None:
    row = {**COMPLETE_QUALITY_ROW, "schema_version": "27"}
    del row["constraint_mechanism"]
    del row["constraint_grammar_hash"]

    validate_row("quality", row)


# --------------------------------------------------------------------------
# Subject egress (schema "16"): where the subject prompt went, on every row.


def test_the_schema_version_moved_for_the_subject_egress() -> None:
    # "16" makes every row of either kind state where its subject prompt went.
    # Not conditional: every row was produced by sending a prompt somewhere.
    assert SCHEMA_VERSION == "30"
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
            "verdict": _cloud_verdict(COMPLETE_QUALITY_ROW),
            **_NO_ENGINE,
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
    assert SCHEMA_VERSION == "30"
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
        "verdict": _cloud_verdict(COMPLETE_QUALITY_ROW),
        **_NO_ENGINE,
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
        "verdict": _cloud_verdict(COMPLETE_QUALITY_ROW),
        **_NO_ENGINE,
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
            "score_interval": None,
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
            "score_interval": None,
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
    assert SCHEMA_VERSION == "30"
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
    assert int(SCHEMA_VERSION) >= 19
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
        "verdict": _cloud_verdict(COMPLETE_QUALITY_ROW),
        **_NO_ENGINE,
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


# Schema "20": the harness that ran the row, its version and its overhead


def test_the_schema_version_moved_for_the_harness_fields() -> None:
    # "20" puts the harness id, its installed version and its per-call prompt
    # overhead on every quality row; the runtime row is untouched.
    assert SCHEMA_VERSION == "30"
    assert HARNESS_SCHEMA_VERSION == "20"
    assert HARNESS_FIELDS == {
        "harness_id",
        "harness_version",
        "harness_prompt_overhead",
    }
    assert HARNESS_FIELDS <= REQUIRED_FIELDS["quality"]
    assert HARNESS_FIELDS.isdisjoint(REQUIRED_FIELDS["runtime"])


def test_a_direct_fixture_row_carrying_all_three_validates() -> None:
    # Built by the writers' own block: the engine received 57 prompt tokens,
    # the item's own rendered prompt counts 57 under the same tokenizer.
    measurement = timings.parse_item_measurement(
        {"usage": {"prompt_tokens": 57, "completion_tokens": 2}}
    )
    block = quality_rows.direct_harness_fields(measurement, 57)

    assert block == {
        "harness_id": "direct",
        "harness_version": harness.harness_version("direct"),
        "harness_prompt_overhead": {"tokens": 0, "null_reason": None},
    }
    validate_row("quality", {**COMPLETE_QUALITY_ROW, **block})


@pytest.mark.parametrize(
    "harness_id", ["crewai", "autogen", "Direct", "llama-index", "", None, 1]
)
def test_a_row_naming_a_harness_outside_the_five_is_refused(harness_id) -> None:
    with pytest.raises(RowContractError, match="has harness_id"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "harness_id": harness_id})


@pytest.mark.parametrize(
    "harness_id", ["direct", "smolagents", "langgraph", "pydantic-ai", "llamaindex"]
)
def test_each_of_the_five_candidates_is_accepted(harness_id) -> None:
    validate_row("quality", {**COMPLETE_QUALITY_ROW, "harness_id": harness_id})


@pytest.mark.parametrize("field", sorted(HARNESS_FIELDS))
def test_a_quality_row_without_a_harness_field_is_refused_by_name(field) -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", row)


def test_an_earlier_version_row_without_the_harness_fields_still_validates() -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k not in HARNESS_FIELDS}

    validate_row("quality", {**row, "schema_version": "19"})


@pytest.mark.parametrize("version", ["20", "21", "not-a-version", None])
def test_a_row_at_or_past_20_or_with_no_readable_version_owes_them(version) -> None:
    row = {
        k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != "harness_prompt_overhead"
    }

    with pytest.raises(RowContractError, match="harness_prompt_overhead"):
        validate_row("quality", {**row, "schema_version": version})


@pytest.mark.parametrize("version", [None, "", 2])
def test_a_harness_version_that_was_not_read_is_refused(version) -> None:
    with pytest.raises(RowContractError, match="has harness_version"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "harness_version": version})


@pytest.mark.parametrize(
    "overhead",
    [
        None,
        0,
        "unmeasurable",
        {"tokens": 0},
        {"tokens": 0, "null_reason": None, "unit": "tokens"},
    ],
)
def test_an_overhead_that_is_not_the_two_key_object_is_refused(overhead) -> None:
    with pytest.raises(RowContractError, match="exactly tokens and null_reason"):
        validate_row(
            "quality", {**COMPLETE_QUALITY_ROW, "harness_prompt_overhead": overhead}
        )


@pytest.mark.parametrize("tokens", [-1, 1.5, True, "3"])
def test_an_overhead_count_that_is_not_a_non_negative_integer_is_refused(
    tokens,
) -> None:
    overhead = {"tokens": tokens, "null_reason": None}

    with pytest.raises(RowContractError, match="non-negative token count"):
        validate_row(
            "quality", {**COMPLETE_QUALITY_ROW, "harness_prompt_overhead": overhead}
        )


def test_a_measured_overhead_beside_a_null_reason_is_refused() -> None:
    overhead = {"tokens": 4, "null_reason": "unmeasurable"}

    with pytest.raises(RowContractError, match="a measured overhead has no reason"):
        validate_row(
            "quality", {**COMPLETE_QUALITY_ROW, "harness_prompt_overhead": overhead}
        )


@pytest.mark.parametrize("reason", [None, "zero", "not_measured"])
def test_a_null_overhead_without_a_known_reason_is_refused(reason) -> None:
    overhead = {"tokens": None, "null_reason": reason}

    with pytest.raises(RowContractError, match="null harness_prompt_overhead"):
        validate_row(
            "quality", {**COMPLETE_QUALITY_ROW, "harness_prompt_overhead": overhead}
        )


@pytest.mark.parametrize("reason", sorted(harness.OVERHEAD_NULL_REASONS))
def test_a_null_overhead_with_its_reason_validates(reason) -> None:
    overhead = {"tokens": None, "null_reason": reason}

    validate_row(
        "quality", {**COMPLETE_QUALITY_ROW, "harness_prompt_overhead": overhead}
    )


def test_a_harness_the_rule_cannot_measure_writes_unmeasurable_not_zero(
    monkeypatch,
) -> None:
    # A fixture harness that rewrites the item's prompt: the engine's count is
    # known, the item's too, and still no number is published. Its package is
    # pointed at one this environment has, so the version read is real.
    monkeypatch.setitem(harness.HARNESS_DISTRIBUTIONS, "smolagents", "pytest")
    overhead = harness.prompt_overhead(
        engine_prompt_tokens=57,
        engine_null_reason=None,
        item_prompt_tokens=57,
        wraps_item_prompt=False,
    )
    row = {
        **COMPLETE_QUALITY_ROW,
        **harness.row_fields("smolagents", overhead),
    }

    assert row["harness_prompt_overhead"] == {
        "tokens": None,
        "null_reason": "unmeasurable",
    }
    validate_row("quality", row)


# --- score_interval (schema "21") -----------------------------------------


def test_the_interval_block_is_owed_from_schema_21_on_quality_rows_only() -> None:
    assert SCORE_INTERVAL_SCHEMA_VERSION == "21"
    assert SCORE_INTERVAL_FIELDS == {"score_interval"}
    assert SCORE_INTERVAL_FIELDS <= REQUIRED_FIELDS["quality"]
    assert SCORE_INTERVAL_FIELDS.isdisjoint(REQUIRED_FIELDS["runtime"])
    assert "score_interval" in PARTIAL_NULL_SCORE_FIELDS


def test_a_schema_21_row_without_its_interval_is_refused_by_name() -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != "score_interval"}
    with pytest.raises(RowContractError, match="score_interval"):
        validate_row("quality", row)


def test_a_row_below_schema_21_validates_without_an_interval() -> None:
    row = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != "score_interval"}
    validate_row("quality", {**row, "schema_version": "20"})


def _with_suite_cell(**cell: object) -> dict:
    block = COMPLETE_QUALITY_ROW["score_interval"]
    return {
        **COMPLETE_QUALITY_ROW,
        "score_interval": {**block, "suite": {**block["suite"], **cell}},
    }


def test_a_defined_interval_cell_validates() -> None:
    validate_row(
        "quality",
        _with_suite_cell(
            lower=0.9, upper=1.0, minimum_detectable_effect=0.05, null_reason=None
        ),
    )


@pytest.mark.parametrize(
    "cell",
    [
        # A value beside a reason.
        {"lower": 0.9, "upper": 1.0, "minimum_detectable_effect": 0.05},
        # A reason outside the closed set.
        {"null_reason": "too_small"},
        # Neither values nor a reason.
        {"null_reason": None},
        # A boolean is not a bound.
        {
            "lower": True,
            "upper": 1.0,
            "minimum_detectable_effect": 0.0,
            "null_reason": None,
        },
    ],
)
def test_an_interval_cell_is_values_or_one_reason_never_both(cell: dict) -> None:
    with pytest.raises(RowContractError, match="score_interval suite cell"):
        validate_row("quality", _with_suite_cell(**cell))


@pytest.mark.parametrize("n", [-1, True, "1"])
def test_an_interval_cell_counts_its_items(n: object) -> None:
    with pytest.raises(RowContractError, match="score_interval suite n="):
        validate_row("quality", _with_suite_cell(n=n))


@pytest.mark.parametrize(
    ("key", "value", "match"),
    [
        ("resamples", 100, "resamples=100"),
        ("confidence_level", 0.9, "confidence_level=0.9"),
        ("method", "bca", "method='bca'"),
        ("draw_procedure_id", "other/1", "draw_procedure_id='other/1'"),
        ("seed", "7", "seed '7'"),
        ("generator", {"library": "numpy"}, "generator"),
        ("by_language", {"en": {}}, "by_language"),
        ("suite", None, "suite cell None"),
    ],
)
def test_a_malformed_interval_header_is_refused_naming_it(
    key: str, value: object, match: str
) -> None:
    block = {**COMPLETE_QUALITY_ROW["score_interval"], key: value}
    with pytest.raises(RowContractError, match=match):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "score_interval": block})


def test_an_interval_block_missing_a_key_is_refused() -> None:
    block = dict(COMPLETE_QUALITY_ROW["score_interval"])
    del block["seed"]
    with pytest.raises(RowContractError, match="carrying exactly"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "score_interval": block})


def test_a_published_score_without_its_interval_is_refused() -> None:
    with pytest.raises(RowContractError, match="null score_interval"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "score_interval": None})


def test_an_interval_beside_no_published_score_is_refused() -> None:
    row = {**COMPLETE_QUALITY_ROW, "suite_accuracy": None, "language_breakdown": None}
    with pytest.raises(RowContractError, match="beside no suite score"):
        validate_row("quality", row)


def test_a_partial_row_carrying_an_interval_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        "partial_failure": dict(_PARTIAL),
        "suite_accuracy": None,
        "language_breakdown": None,
    }
    with pytest.raises(RowContractError, match="is partial but carries score_interval"):
        validate_row("quality", row)


@pytest.mark.parametrize(
    "cell",
    [
        {"n": 1, "null_reason": "no_items"},
        {"n": 0, "null_reason": "zero_width"},
        {
            "n": 0,
            "lower": 0.5,
            "upper": 0.9,
            "minimum_detectable_effect": 0.2,
            "null_reason": None,
        },
    ],
)
def test_an_interval_reason_is_only_the_one_its_item_count_names(cell: dict) -> None:
    with pytest.raises(RowContractError, match=r"n=\d"):
        validate_row("quality", _with_suite_cell(**cell))


def test_the_schema_version_moved_for_the_campaign() -> None:
    # "24" makes every row name the campaign it belongs to, or none.
    assert SCHEMA_VERSION >= "25"
    assert CAMPAIGN_SCHEMA_VERSION == "24"
    for kind in ("runtime", "quality"):
        assert "campaign_id" in REQUIRED_FIELDS[kind]


@pytest.mark.parametrize("kind", ["runtime", "quality"])
def test_a_row_missing_its_campaign_is_refused_naming_it(kind: str) -> None:
    complete = COMPLETE_RUNTIME_ROW if kind == "runtime" else COMPLETE_QUALITY_ROW
    row = {key: value for key, value in complete.items() if key != "campaign_id"}

    with pytest.raises(RowContractError, match="missing required field.*campaign_id"):
        validate_row(kind, row)


def test_a_row_below_the_campaign_schema_validates_without_it() -> None:
    old = {
        key: value
        for key, value in COMPLETE_RUNTIME_ROW.items()
        if key != "campaign_id"
    }

    validate_row("runtime", {**old, "schema_version": "23"})


def test_a_row_names_its_campaign() -> None:
    validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "campaign_id": "engine-campaign"})
    validate_row("quality", {**COMPLETE_QUALITY_ROW, "campaign_id": "engine-campaign"})


@pytest.mark.parametrize("campaign_id", [None, "", "  ", 3])
def test_a_campaign_id_that_is_not_a_name_is_refused(campaign_id: object) -> None:
    with pytest.raises(RowContractError, match="campaign_id"):
        validate_row("runtime", {**COMPLETE_RUNTIME_ROW, "campaign_id": campaign_id})


def test_a_cloud_row_belongs_to_no_campaign() -> None:
    validate_row("quality", _cloud_row("mistral", campaign_id=NO_CAMPAIGN))

    with pytest.raises(RowContractError, match="cloud subject belongs to no campaign"):
        validate_row("quality", _cloud_row("mistral", campaign_id="engine-campaign"))


# --------------------------------------------------------------------------
# Schema "25": a cpu_only row's VRAM is not applicable, a gpu row's never is
# --------------------------------------------------------------------------


def _with_vram(row: dict, value: object) -> dict:
    """`row` with every `vram_used_mib` (peak, warm-ups, counted) set to `value`."""
    return {
        **row,
        "vram_used_mib": value,
        "warmup_repetitions": [
            {**rep, "vram_used_mib": value} for rep in row["warmup_repetitions"]
        ],
        "repetitions": [{**rep, "vram_used_mib": value} for rep in row["repetitions"]],
    }


def _cpu_only_runtime_row() -> dict:
    return _with_vram(
        {**COMPLETE_RUNTIME_ROW, "compute_mode": "cpu_only"},
        VRAM_NOT_APPLICABLE,
    )


def test_the_schema_version_moved_for_vram_not_applicable() -> None:
    assert SCHEMA_VERSION == "30"
    assert VRAM_NOT_APPLICABLE_SCHEMA_VERSION == "25"
    assert VRAM_NOT_APPLICABLE == "not_applicable"


def test_a_cpu_only_runtime_row_marked_not_applicable_everywhere_validates() -> None:
    validate_row("runtime", _cpu_only_runtime_row())


@pytest.mark.parametrize("value", [0, 0.0, 254.7, None])
@pytest.mark.parametrize("place", ["peak", "warmup", "counted"])
def test_a_cpu_only_runtime_row_carrying_any_vram_value_is_refused(
    place: str, value: object
) -> None:
    row = _cpu_only_runtime_row()
    if place == "peak":
        row["vram_used_mib"] = value
    elif place == "warmup":
        row["warmup_repetitions"][0]["vram_used_mib"] = value
    else:
        row["repetitions"][2]["vram_used_mib"] = value

    with pytest.raises(RowContractError, match="cpu_only"):
        validate_row("runtime", row)


@pytest.mark.parametrize("value", [3161.0, None])
def test_a_gpu_runtime_row_carries_a_number_or_a_failed_read(value: object) -> None:
    validate_row("runtime", _with_vram(COMPLETE_RUNTIME_ROW, value))


@pytest.mark.parametrize("value", [VRAM_NOT_APPLICABLE, True, "3161"])
def test_a_gpu_runtime_row_never_carries_the_marker_or_a_non_number(
    value: object,
) -> None:
    with pytest.raises(RowContractError, match="number, or null"):
        validate_row("runtime", _with_vram(COMPLETE_RUNTIME_ROW, value))


def test_a_runtime_row_below_25_is_not_rechecked_for_vram() -> None:
    validate_row(
        "runtime",
        {
            **COMPLETE_RUNTIME_ROW,
            "schema_version": "24",
            "compute_mode": "cpu_only",
            "vram_used_mib": 254.7,
        },
    )


def test_a_non_list_repetition_field_is_refused_by_the_vram_check() -> None:
    # The structure check reads `repetitions` first, so the VRAM check's own
    # guard is reached through `warmup_repetitions`.
    row = {**COMPLETE_RUNTIME_ROW, "warmup_repetitions": "not-a-list"}

    with pytest.raises(RowContractError, match="non-list warmup_repetitions"):
        validate_row("runtime", row)


def test_a_repetition_without_vram_is_refused_by_the_vram_check() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "warmup_repetitions": [{"index": 0}]}

    with pytest.raises(RowContractError, match=r"warmup_repetitions\[0\]"):
        validate_row("runtime", row)


# --------------------------------------------------------------------------
# Schema "26": every row names its run profile and any operator override
# --------------------------------------------------------------------------


def test_the_schema_version_moved_for_the_run_profile() -> None:
    assert SCHEMA_VERSION == "30"
    assert PROFILE_SCHEMA_VERSION == "26"
    for kind in ("runtime", "quality"):
        assert PROFILE_FIELDS <= REQUIRED_FIELDS[kind]


@pytest.mark.parametrize("kind", ["runtime", "quality"])
@pytest.mark.parametrize("field", sorted(PROFILE_FIELDS))
def test_a_row_missing_a_profile_field_is_refused_naming_it(
    kind: str, field: str
) -> None:
    complete = COMPLETE_RUNTIME_ROW if kind == "runtime" else COMPLETE_QUALITY_ROW
    row = {key: value for key, value in complete.items() if key != field}

    with pytest.raises(RowContractError, match=f"missing required field.*{field}"):
        validate_row(kind, row)


def test_a_row_below_the_profile_schema_validates_without_them() -> None:
    old = {
        key: value
        for key, value in COMPLETE_RUNTIME_ROW.items()
        if key not in PROFILE_FIELDS
    }

    validate_row("runtime", {**old, "schema_version": "25"})


def test_an_overridden_row_names_its_override() -> None:
    validate_row(
        "runtime",
        {
            **COMPLETE_RUNTIME_ROW,
            "profile_overrides": {
                "threads": {"profile": 8, "operator": 12},
                "n_cpu_moe": {"profile": None, "operator": 30},
            },
        },
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"profile_id": None},
        {"profile_id": "  "},
        {"profile_id": PROFILE_NOT_APPLICABLE},
        {"profile_overrides": None},
        {"profile_overrides": PROFILE_NOT_APPLICABLE},
        {"profile_overrides": {"flash": {"profile": 1, "operator": 2}}},
        {"profile_overrides": {"threads": {"operator": 12}}},
        {"profile_overrides": {"threads": 12}},
    ],
)
def test_a_local_row_with_no_profile_or_a_malformed_override_is_refused(
    changes: dict,
) -> None:
    with pytest.raises(RowContractError, match="profile"):
        validate_row("runtime", {**COMPLETE_RUNTIME_ROW, **changes})
    with pytest.raises(RowContractError, match="profile"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, **changes})


@pytest.mark.parametrize(
    "changes",
    [
        {"profile_id": "qwen3.6-35b-a3b-ud-iq4xs@laptop-mobile-gpu/gpu"},
        {"profile_overrides": {}},
    ],
)
def test_a_cloud_row_states_no_profile_applies(changes: dict) -> None:
    validate_row("quality", _cloud_row("mistral"))
    with pytest.raises(RowContractError, match="produced by no local model"):
        validate_row("quality", _cloud_row("mistral", **changes))


# --- the verdict's subject rule (schema "29") -------------------------------

_SUBJECT_RULE_KEYS = (
    "subject_rule",
    "tolerance",
    "divergence",
    "single_run_indicative",
)


def test_a_deterministic_local_row_validates_under_the_identical_rule() -> None:
    assert SCHEMA_VERSION == "30"
    validate_row("quality", COMPLETE_QUALITY_ROW)


@pytest.mark.parametrize("field", _SUBJECT_RULE_KEYS)
def test_a_quality_row_missing_a_verdict_rule_field_is_refused(field) -> None:
    verdict_block = {
        k: v for k, v in COMPLETE_QUALITY_ROW["verdict"].items() if k != field
    }

    with pytest.raises(RowContractError, match=f"missing field.*{field}"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "verdict": verdict_block})


def test_a_row_below_29_validates_without_the_verdict_rule_fields() -> None:
    old = {
        **COMPLETE_QUALITY_ROW,
        "schema_version": "28",
        "verdict": {"verdict": "not_comparable", "reference_run_id": None},
    }

    validate_row("quality", old)


def test_a_cloud_row_decided_under_its_suites_tolerance_validates() -> None:
    validate_row("quality", _cloud_row("mistral"))


@pytest.mark.parametrize(
    ("verdict_changes", "match"),
    [
        ({"subject_rule": "identical"}, "expected 'within_tolerance'"),
        ({"tolerance": None}, "does not name"),
        ({"single_run_indicative": "rate_limited"}, "is not one of"),
        ({"single_run_indicative": "no_seed"}, "never 'reproduced'"),
        ({"divergence": 1.5}, "divergence 1.5"),
    ],
)
def test_a_malformed_cloud_verdict_rule_is_refused(verdict_changes, match) -> None:
    row = _cloud_row("mistral")
    row["verdict"] = _cloud_verdict(row, **verdict_changes)

    with pytest.raises(RowContractError, match=match):
        validate_row("quality", row)


@pytest.mark.parametrize(
    ("tolerance_changes", "match"),
    [
        ({"suite_version": "0"}, "not by the row's own suite"),
        ({"unit": "items"}, "not a declared unit"),
        ({"value": True}, "not a number in"),
    ],
)
def test_a_cloud_verdict_tolerance_naming_the_wrong_suite_or_value_is_refused(
    tolerance_changes, match
) -> None:
    row = _cloud_row("mistral")
    block = _cloud_verdict(row)
    block["tolerance"] = {**block["tolerance"], **tolerance_changes}
    row["verdict"] = block

    with pytest.raises(RowContractError, match=match):
        validate_row("quality", row)


def test_a_single_run_indicative_cloud_row_is_not_comparable() -> None:
    row = _cloud_row("google")
    row["verdict"] = _cloud_verdict(
        row,
        verdict="not_comparable",
        divergence=None,
        single_run_indicative="model_not_served",
    )

    validate_row("quality", row)


@pytest.mark.parametrize(
    "verdict_changes",
    [
        {"subject_rule": "within_tolerance"},
        {"tolerance": {"value": 0.1}},
        {"single_run_indicative": "no_seed"},
    ],
)
def test_a_local_row_is_never_decided_under_a_tolerance(verdict_changes) -> None:
    block = {**COMPLETE_QUALITY_ROW["verdict"], **verdict_changes}

    with pytest.raises(RowContractError):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "verdict": block})


def test_a_verdict_that_is_not_a_block_is_refused() -> None:
    with pytest.raises(RowContractError, match="is not a block"):
        validate_row("quality", {**COMPLETE_QUALITY_ROW, "verdict": "reproduced"})


# --- the code block (schema "30") ---------------------------------------------

_CODE_SUITE = suite_registry.resolve("code-generation-python-javascript")
COMPLETE_CODE_QUALITY_ROW = {
    **COMPLETE_GRADED_QUALITY_ROW,
    "task_suite": "code-generation",
    "suite_id": _CODE_SUITE.suite_id,
    "suite_version": _CODE_SUITE.suite_version,
    "item_id": _CODE_SUITE.items[0]["item_id"],
    "prompt_before_template": _CODE_SUITE.items[0]["prompt"],
    "item_score": 1.0,
    "failure_reason": None,
    "metric_id": "unit_tests_pass",
    "metric_version": "1",
    "metric_params": {"pass_rule": "every_test_passes"},
    "reference_output": _CODE_SUITE.items[0]["tests"],
    "programming_language": "python",
    "sandbox": {
        "runtime": "docker",
        "image": "python:3.12-slim",
        "image_id": "sha256:feed",
        "network": "none",
        "host_mount": False,
        "wall_clock_cap_s": 20,
        "memory_cap_mib": 256,
        "pids_cap": 64,
    },
    "programming_language_breakdown": {
        "python": {"score": 0.5, "n": 12},
        "javascript": {"score": 0.25, "n": 12},
    },
}


def test_a_complete_code_row_passes() -> None:
    validate_row("quality", COMPLETE_CODE_QUALITY_ROW)


@pytest.mark.parametrize("field", sorted(CODE_FIELDS))
def test_a_code_row_missing_one_code_field_is_refused_by_name(field: str) -> None:
    incomplete = {k: v for k, v in COMPLETE_CODE_QUALITY_ROW.items() if k != field}

    with pytest.raises(RowContractError, match=field):
        validate_row("quality", incomplete)


def test_a_code_block_without_the_graded_block_is_refused() -> None:
    row = {
        **COMPLETE_QUALITY_ROW,
        **{field: COMPLETE_CODE_QUALITY_ROW[field] for field in CODE_FIELDS},
    }

    with pytest.raises(RowContractError, match="without the graded block"):
        validate_row("quality", row)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"programming_language": "rust"}, "programming_language 'rust'"),
        (
            {"failure_reason": "made_up", "item_score": 0.0},
            "code failure_reason 'made_up'",
        ),
        ({"item_score": 0.5}, "code item_score 0.5"),
        ({"sandbox": {"runtime": "docker"}}, "sandbox block"),
        ({"programming_language_breakdown": {}}, "no cell for its own language"),
        (
            {
                "programming_language_breakdown": {
                    "python": {"score": 1.0, "n": 1},
                    "rust": {"score": 1.0, "n": 1},
                }
            },
            "a language no code suite tags",
        ),
        (
            {"programming_language_breakdown": {"python": {"score": 2.0, "n": 1}}},
            "malformed programming_language_breakdown cell",
        ),
    ],
)
def test_a_malformed_code_block_is_refused(overrides: dict, message: str) -> None:
    with pytest.raises(RowContractError, match=message):
        validate_row("quality", {**COMPLETE_CODE_QUALITY_ROW, **overrides})


@pytest.mark.parametrize(
    ("key", "value", "message"),
    [
        ("network", "bridge", "no network and no host mount"),
        ("host_mount", True, "no network and no host mount"),
        ("image", "", "malformed image"),
        ("memory_cap_mib", 0, "memory_cap_mib=0"),
        ("pids_cap", True, "pids_cap=True"),
    ],
)
def test_a_sandbox_with_a_network_a_mount_or_no_cap_is_refused(
    key: str, value: object, message: str
) -> None:
    sandbox = {**COMPLETE_CODE_QUALITY_ROW["sandbox"], key: value}

    with pytest.raises(RowContractError, match=message):
        validate_row("quality", {**COMPLETE_CODE_QUALITY_ROW, "sandbox": sandbox})


def test_a_failed_code_item_scores_zero() -> None:
    validate_row(
        "quality",
        {**COMPLETE_CODE_QUALITY_ROW, "failure_reason": "timeout", "item_score": 0.0},
    )
    with pytest.raises(RowContractError, match="a failed generation scores 0.0"):
        validate_row(
            "quality", {**COMPLETE_CODE_QUALITY_ROW, "failure_reason": "timeout"}
        )


def test_a_partial_code_row_publishes_no_per_language_score() -> None:
    assert "programming_language_breakdown" in PARTIAL_NULL_SCORE_FIELDS
