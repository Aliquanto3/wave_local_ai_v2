import pytest

from wave_local_ai_v2 import aggregation
from wave_local_ai_v2.row_contract import (
    GRADED_FIELDS,
    JUDGED_FIELDS,
    REQUIRED_FIELDS,
    SCHEMA_VERSION,
    RowContractError,
    validate_row,
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
    "model_id": "Qwen3.6-35B-A3B",
    "provider": "local",
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
    "context_length": 32768,
    "suite_id": "classification-support-routing",
    "suite_version": "1",
    "prompt_set_hash": "deadbeef",
    "language": "en",
    "provenance": "hand_written",
    "contamination_risk": False,
    "indicative": True,
    "indicative_reasons": ["item_count 10 is below the minimum of 20"],
    "failure_reason": None,
    "failure_counts": {
        "empty": 0,
        "unparseable": 0,
        "truncated_max_tokens": 0,
        "truncated_context": 0,
    },
    "retries": 0,
    "resumed": False,
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
    }


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
    "item_id": "en-fr-01",
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


def test_the_schema_version_moved_once_for_the_graded_block() -> None:
    # "9" declared the judge block, "10" declares the graded one. Both are
    # conditional on a row carrying any of their fields, which is what lets
    # an exact-match classification row validate unchanged across the bump.
    assert SCHEMA_VERSION == "10"
