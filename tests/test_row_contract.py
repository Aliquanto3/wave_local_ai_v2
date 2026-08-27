import pytest

from wave_local_ai_v2 import aggregation
from wave_local_ai_v2.row_contract import (
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


def test_aggregation_map_naming_a_field_the_row_does_not_carry_is_refused() -> None:
    extra_aggregation = {**aggregation.AGGREGATION_LABELS, "made_up_metric": "median"}
    row = {**COMPLETE_RUNTIME_ROW, "aggregation": extra_aggregation}

    with pytest.raises(RowContractError, match="made_up_metric"):
        validate_row("runtime", row)
