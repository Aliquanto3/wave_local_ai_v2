"""Tests for the paired comparison: the two tests, the refusals, the record."""

from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path
from typing import Any

import pytest
from scipy import stats

from wave_local_ai_v2 import comparison
from wave_local_ai_v2.comparison import (
    NULL_ALL_DIFFERENCES_ZERO,
    NULL_COMPARISON_REFUSED,
    NULL_NO_DISCORDANT_PAIRS,
    NULL_ODDS_RATIO_EMPTY_CELL,
    NULL_PAIRED_N_BELOW_MINIMUM,
    ComparisonInputError,
    FamilyError,
    Side,
    compare_sides,
    holm_adjust,
    mcnemar_exact,
    wilcoxon_signed_rank,
)

REFERENCE_BUNDLE = Path("aidd_docs/results/quality-reference.jsonl")
RUN_5E = "5e13166da0654390a7d63f346ea5d4f1"  # pragma: allowlist secret
REFERENCE = Side("run-ref", {"model_id": "model-a"})
CANDIDATE = Side("run-cand", {"model_id": "model-b"})


# --------------------------------------------------------------------------
# Constructed rows


def _row(run_id: str, model_id: str, item_id: str, **overrides: Any) -> dict[str, Any]:
    row: dict[str, Any] = {
        "schema_version": "15",
        "run_id": run_id,
        "captured_at": "2026-10-01T00:00:00+00:00",
        "model_id": model_id,
        "provider": "local",
        "fiche_hash": f"fiche-{model_id}",
        "item_id": item_id,
        "task_suite": "classification",
        "suite_id": "classification-support-routing",
        "suite_version": "2",
        "prompt_set_hash": "prompt-set",
        "suite_level": "development",
        "max_output_tokens": 32,
        "stop_sequences": [],
        "context_length": 32768,
        "thinking_policy": "disabled",
        "prompt_variant_id": "baseline",
        "prompt_variant_version": "1",
        "correct": True,
        "suite_accuracy": 0.5,
    }
    row.update(overrides)
    return row


def _binary_rows(
    run_id: str, model_id: str, outcomes: list[bool], **overrides: Any
) -> list[dict[str, Any]]:
    return [
        _row(run_id, model_id, f"item-{i:02d}", correct=outcome, **overrides)
        for i, outcome in enumerate(outcomes)
    ]


def _graded_rows(
    run_id: str, model_id: str, scores: list[float], **overrides: Any
) -> list[dict[str, Any]]:
    graded = {
        "task_suite": "translation",
        "suite_id": "translation-business-short-form",
        "suite_version": "1",
        "max_output_tokens": 128,
        "correct": None,
        "metric_id": "chrf",
        "metric_version": "1",
        "metric_params": {"beta": 2, "char_order": 6},
        "suite_score": 0.5,
    }
    graded.update(overrides)
    return [
        _row(run_id, model_id, f"item-{i:02d}", item_score=score, **graded)
        for i, score in enumerate(scores)
    ]


def _pairs_outcomes(
    both_correct: int, reference_only: int, candidate_only: int, both_wrong: int
) -> tuple[list[bool], list[bool]]:
    reference = (
        [True] * both_correct
        + [True] * reference_only
        + [False] * candidate_only
        + [False] * both_wrong
    )
    candidate = (
        [True] * both_correct
        + [False] * reference_only
        + [True] * candidate_only
        + [False] * both_wrong
    )
    return reference, candidate


def _compare(
    reference_rows: list[dict[str, Any]],
    candidate_rows: list[dict[str, Any]],
    **kwargs: Any,
) -> dict[str, Any]:
    return compare_sides(reference_rows, candidate_rows, REFERENCE, CANDIDATE, **kwargs)


# --------------------------------------------------------------------------
# McNemar


@pytest.mark.parametrize(
    ("reference_only", "candidate_only", "expected_p"),
    [
        # The epic's published arithmetic on the two committed pairs: run
        # 5e13166d, 4/1 discordant; run d20afbda, 4/2 discordant.
        (1, 4, 0.375),
        (2, 4, 0.6875),
    ],
)
def test_mcnemar_reproduces_the_epics_published_pairs(
    reference_only: int, candidate_only: int, expected_p: float
) -> None:
    concordant = 20 - reference_only - candidate_only
    ref, cand = _pairs_outcomes(concordant - 2, reference_only, candidate_only, 2)
    result = mcnemar_exact(list(zip(ref, cand, strict=True)))
    assert result["p_value"] == expected_p
    assert result["statistic"] == min(reference_only, candidate_only)
    assert result["effect_size"] == candidate_only / reference_only
    assert result["direction"] == comparison.DIRECTION_CANDIDATE_HIGHER
    assert result["zero_difference_count"] == concordant
    assert result["discordant_n"] == reference_only + candidate_only


def test_mcnemar_2x2_matches_the_scipy_binomial_oracle() -> None:
    rng = random.Random(20261001)
    for _ in range(40):
        b, c = rng.randint(0, 30), rng.randint(0, 30)
        if b + c == 0:
            continue
        ref, cand = _pairs_outcomes(rng.randint(0, 20), b, c, rng.randint(0, 20))
        result = mcnemar_exact(list(zip(ref, cand, strict=True)))
        oracle = stats.binomtest(c, b + c, 0.5, alternative="two-sided").pvalue
        assert result["p_value"] == pytest.approx(oracle, abs=1e-12)


def test_mcnemar_publishes_named_reasons_never_numbers() -> None:
    ref, cand = _pairs_outcomes(5, 0, 0, 3)
    no_discordance = mcnemar_exact(list(zip(ref, cand, strict=True)))
    assert no_discordance["p_value"] is None
    assert no_discordance["p_value_null_reason"] == NULL_NO_DISCORDANT_PAIRS
    assert no_discordance["direction"] == comparison.DIRECTION_NONE

    ref, cand = _pairs_outcomes(5, 0, 3, 3)
    empty_cell = mcnemar_exact(list(zip(ref, cand, strict=True)))
    assert empty_cell["p_value"] == 0.25
    assert empty_cell["effect_size"] is None
    assert empty_cell["effect_size_null_reason"] == NULL_ODDS_RATIO_EMPTY_CELL

    nothing = mcnemar_exact([])
    assert nothing["p_value"] is None
    assert nothing["p_value_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM
    assert nothing["effect_size_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM


# --------------------------------------------------------------------------
# Wilcoxon


def test_wilcoxon_reproduces_the_published_signed_rank_table() -> None:
    # Wikipedia's worked example: ten pairs, one zero difference dropped,
    # leaving nine with one tie (5, 5): W+ = 27, W- = 18, W = 9.
    nonzero = [15.0, -7.0, 5.0, 20.0, -9.0, 17.0, -12.0, 5.0, -10.0]
    result = wilcoxon_signed_rank(nonzero)
    assert result["statistic"] == 27
    assert result["w_minus"] == 18
    assert result["statistic"] - result["w_minus"] == 9
    assert result["tie_count"] == 2
    assert result["effect_size"] == pytest.approx(9 / 45)
    oracle = stats.wilcoxon(nonzero, zero_method="pratt", correction=False)
    assert result["p_value"] == pytest.approx(oracle.pvalue, abs=1e-12)


def test_wilcoxon_keeps_a_both_failed_tie_under_pratt() -> None:
    differences = [15.0, -7.0, 5.0, 20.0, 0.0, -9.0, 17.0, -12.0, 5.0, -10.0]
    result = wilcoxon_signed_rank(differences)
    assert result["zero_difference_count"] == 1
    # Pratt ranks the zero first, shifting every other rank by one.
    assert result["statistic"] == 32
    assert result["w_minus"] == 22
    assert result["conventions"]["zero_method"] == "pratt"
    assert result["conventions"]["continuity_correction"] is False
    assert result["conventions"]["exact_max_nonzero"] == 50
    assert result["p_value_method"] == "exact_sign_flip"
    oracle = stats.wilcoxon(differences, zero_method="pratt", correction=False)
    assert result["p_value"] == pytest.approx(oracle.pvalue, abs=1e-12)


def test_wilcoxon_exact_matches_scipy_without_ties() -> None:
    rng = random.Random(7)
    for size in (5, 12, 20, 40):
        differences = [rng.uniform(-1, 1) for _ in range(size)]
        result = wilcoxon_signed_rank(differences)
        oracle = stats.wilcoxon(differences, method="exact")
        assert result["p_value"] == pytest.approx(oracle.pvalue, abs=1e-12)
        assert min(result["statistic"], result["w_minus"]) == oracle.statistic


def test_wilcoxon_normal_approximation_matches_scipy_with_zeros_and_ties() -> None:
    rng = random.Random(11)
    differences = [
        rng.choice([-0.3, -0.2, -0.1, 0.0, 0.1, 0.2, 0.4]) for _ in range(90)
    ]
    result = wilcoxon_signed_rank(differences)
    assert result["p_value_method"] == "normal_approximation"
    oracle = stats.wilcoxon(
        differences, zero_method="pratt", correction=False, method="asymptotic"
    )
    assert result["p_value"] == pytest.approx(oracle.pvalue, abs=1e-9)


def test_wilcoxon_publishes_named_reasons_never_numbers() -> None:
    all_zero = wilcoxon_signed_rank([0.0, 0.0, 0.0])
    assert all_zero["p_value"] is None
    assert all_zero["p_value_null_reason"] == NULL_ALL_DIFFERENCES_ZERO
    assert all_zero["effect_size_null_reason"] == NULL_ALL_DIFFERENCES_ZERO
    assert all_zero["direction"] == comparison.DIRECTION_NONE

    nothing = wilcoxon_signed_rank([])
    assert nothing["p_value_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM
    assert nothing["effect_size_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM


# --------------------------------------------------------------------------
# Routing and records


def test_a_classification_suite_routes_to_mcnemar_without_the_caller() -> None:
    ref, cand = _pairs_outcomes(14, 1, 4, 1)
    member = _compare(
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", "model-b", cand),
    )
    assert member["test"] == comparison.TEST_MCNEMAR
    assert member["compared_field"] == "correct"
    assert member["scoring_kind"] == "binary"
    assert member["comparison_kind"] == comparison.KIND_TEST
    assert member["result"]["p_value"] == 0.375
    assert member["adjusted_p_value"] == member["result"]["p_value"]
    assert member["verdict"] == comparison.VERDICT_NOT_DISTINGUISHABLE
    assert member["paired_n"] == 20
    assert member["unpaired_count"] == 0
    assert member["differing_fields"] == ["fiche_hash", "model_id"]
    assert member["suite_id"] == "classification-support-routing"
    assert member["suite_version"] == "2"


def test_a_translation_suite_routes_to_wilcoxon_without_the_caller() -> None:
    reference_scores = [0.5 + 0.01 * i for i in range(10)]
    candidate_scores = [score + 0.2 for score in reference_scores]
    member = _compare(
        _graded_rows("run-ref", "model-a", reference_scores),
        _graded_rows("run-cand", "model-b", candidate_scores),
    )
    assert member["test"] == comparison.TEST_WILCOXON
    assert member["compared_field"] == "item_score"
    assert member["result"]["direction"] == comparison.DIRECTION_CANDIDATE_HIGHER
    assert member["result"]["effect_size"] == 1.0
    assert member["result"]["p_value"] == pytest.approx(2 / 2**10)
    assert member["verdict"] == comparison.VERDICT_DISTINGUISHABLE


@pytest.mark.parametrize(
    ("override", "field", "reason"),
    [
        ({"suite_version": "3"}, "suite_version", "differs"),
        ({"max_output_tokens": 64}, "max_output_tokens", "differs"),
        ({"thinking_policy": "allowed"}, "thinking_policy", "differs"),
        ({"suite_level": "publication"}, "suite_level", "differs"),
        ({"thinking_policy": None}, "thinking_policy", "absent"),
    ],
)
def test_a_binary_comparison_is_refused_naming_its_field(
    override: dict[str, Any], field: str, reason: str
) -> None:
    ref, cand = _pairs_outcomes(14, 1, 4, 1)
    member = _compare(
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", "model-b", cand, **override),
    )
    assert [(entry["field"], entry["reason"]) for entry in member["refusal"]] == [
        (field, reason)
    ]
    assert member["comparison_kind"] == comparison.KIND_REFUSAL
    assert member["verdict"] == comparison.VERDICT_NOT_COMPARABLE
    assert member["result"] is None


def test_a_differing_metric_version_on_a_graded_row_is_refused() -> None:
    member = _compare(
        _graded_rows("run-ref", "model-a", [0.4, 0.5]),
        _graded_rows("run-cand", "model-b", [0.6, 0.7], metric_version="2"),
    )
    assert [entry["field"] for entry in member["refusal"]] == ["metric_version"]


def test_a_scoring_kind_mismatch_is_refused_naming_it() -> None:
    member = _compare(
        _binary_rows("run-ref", "model-a", [True, False]),
        _graded_rows(
            "run-cand",
            "model-b",
            [0.6, 0.7],
            suite_id="classification-support-routing",
            suite_version="2",
            max_output_tokens=32,
        ),
    )
    fields = [entry["field"] for entry in member["refusal"]]
    assert "scoring_kind" in fields
    assert "compared_field" in fields
    scoring = next(e for e in member["refusal"] if e["field"] == "scoring_kind")
    assert (scoring["reference_value"], scoring["candidate_value"]) == (
        "binary",
        "graded",
    )


def test_a_constraint_absent_on_both_sides_is_never_a_match() -> None:
    ref = [_row("run-ref", "model-a", "item-00")]
    cand = [_row("run-cand", "model-b", "item-00")]
    for row in [*ref, *cand]:
        del row["thinking_policy"]
    member = _compare(ref, cand)
    assert member["refusal"] == [
        {
            "field": "thinking_policy",
            "reason": "absent",
            "reference_value": None,
            "candidate_value": None,
        }
    ]


def test_a_suite_level_neither_side_declares_is_not_two_levels() -> None:
    ref = _binary_rows("run-ref", "model-a", [True, False])
    cand = _binary_rows("run-cand", "model-b", [True, True])
    for row in [*ref, *cand]:
        del row["suite_level"]
    member = _compare(ref, cand)
    assert member["refusal"] == []
    assert member["suite_level"] is None


def test_a_field_varying_within_a_side_is_refused() -> None:
    cand = _binary_rows("run-cand", "model-b", [True, True])
    cand[1]["suite_version"] = "3"
    member = _compare(_binary_rows("run-ref", "model-a", [True, False]), cand)
    assert member["refusal"][0]["field"] == "suite_version"
    assert member["refusal"][0]["reason"] == comparison.REFUSAL_VARIES_WITHIN_SIDE


def test_rows_with_no_scoring_kind_are_refused_as_absent() -> None:
    ref = _binary_rows("run-ref", "model-a", [True])
    cand = _binary_rows("run-cand", "model-b", [True])
    for row in [*ref, *cand]:
        row["correct"] = None
    member = _compare(ref, cand)
    assert {(e["field"], e["reason"]) for e in member["refusal"]} == {
        ("scoring_kind", "absent"),
        ("compared_field", "absent"),
    }


def test_a_side_mixing_two_scoring_kinds_is_refused() -> None:
    cand = _binary_rows("run-cand", "model-b", [True])
    cand += _graded_rows("run-cand", "model-b", [0.5], suite_id=cand[0]["suite_id"])
    cand[1]["item_id"] = "item-01"
    member = _compare(_binary_rows("run-ref", "model-a", [True, False]), cand)
    scoring = next(e for e in member["refusal"] if e["field"] == "scoring_kind")
    assert scoring["reason"] == comparison.REFUSAL_VARIES_WITHIN_SIDE


def test_unpaired_items_are_counted_and_named_to_their_side() -> None:
    ref = _graded_rows("run-ref", "model-a", [0.5, 0.4, 0.3, 0.2])
    cand = _graded_rows("run-cand", "model-b", [0.6, 0.6, 0.6, 0.6])
    del cand[3]  # item-03 missing from the candidate
    ref[2]["item_score"] = None  # item-02 unobserved on the reference
    member = _compare(ref, cand)
    assert member["paired_n"] == 2
    assert member["paired_item_ids"] == ["item-00", "item-01"]
    assert member["unpaired_items"] == [
        {"item_id": "item-02", "missing_from": "reference"},
        {"item_id": "item-03", "missing_from": "candidate"},
    ]
    assert member["unpaired_count"] == 2


def test_no_paired_item_is_not_comparable() -> None:
    ref = _binary_rows("run-ref", "model-a", [True])
    cand = [_row("run-cand", "model-b", "item-99")]
    member = _compare(ref, cand)
    assert member["paired_n"] == 0
    assert member["result"]["p_value_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM
    assert member["verdict"] == comparison.VERDICT_NOT_COMPARABLE


def test_a_gpu_against_cpu_only_row_of_one_model_is_an_observation() -> None:
    ref, cand = _pairs_outcomes(14, 1, 4, 1)
    member = compare_sides(
        _binary_rows("run-ref", "model-a", ref, compute_mode="gpu"),
        _binary_rows("run-cand", "model-a", cand, compute_mode="cpu_only"),
        Side("run-ref"),
        Side("run-cand"),
    )
    assert member["differing_fields"] == ["compute_mode"]
    assert member["comparison_kind"] == comparison.KIND_OBSERVATION
    assert "key field" in member["observation_reason"]
    assert member["result"]["p_value"] == 0.375
    assert member["verdict"] == comparison.VERDICT_NOT_COMPARABLE


def test_a_confound_outside_the_dimension_makes_an_observation() -> None:
    ref, cand = _pairs_outcomes(10, 0, 10, 0)
    member = _compare(
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", "model-b", cand, compute_mode="cpu_only"),
    )
    assert member["comparison_kind"] == comparison.KIND_OBSERVATION
    assert member["confounds"] == ["compute_mode"]
    assert "outside" in member["observation_reason"]
    # A significant p on a confounded pair never reads as a finding.
    assert member["result"]["p_value"] <= 0.05
    assert member["verdict"] == comparison.VERDICT_NOT_COMPARABLE


def test_a_prompt_variant_dimension_is_a_clean_test() -> None:
    ref, cand = _pairs_outcomes(14, 1, 4, 1)
    member = compare_sides(
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", "model-a", cand, prompt_variant_id="terse"),
        Side("run-ref"),
        Side("run-cand"),
        dimension="prompt_variant",
    )
    assert member["comparison_kind"] == comparison.KIND_TEST
    assert member["differing_fields"] == ["prompt_variant_id"]


def test_inputs_that_cannot_make_a_record_raise() -> None:
    rows = _binary_rows("run-ref", "model-a", [True])
    with pytest.raises(ComparisonInputError, match="reference"):
        _compare([], rows)
    with pytest.raises(ComparisonInputError, match="candidate"):
        _compare(rows, [])
    with pytest.raises(ComparisonInputError, match="twice"):
        _compare(rows + rows, rows)


def test_a_family_of_one_states_its_adjusted_p_and_is_deterministic() -> None:
    ref, cand = _pairs_outcomes(14, 1, 4, 1)
    rows = (
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", "model-b", cand),
    )
    first = comparison.build_family_record(
        [_compare(*rows)], alpha=0.05, rows_source="x"
    )
    second = comparison.build_family_record(
        [_compare(*rows)], alpha=0.05, rows_source="x"
    )
    assert comparison.record_text(first) == comparison.record_text(second)
    assert first["family_size"] == 1
    assert first["members"][0]["adjusted_p_value"] == 0.375
    assert first["members"][0]["raw_p_value"] == 0.375
    assert first["multiplicity_correction"]["adjustment_size"] == 1
    assert first["supersedes"] == []
    assert first["multiplicity_correction"]["method"] == "holm"
    assert len(first["family_id"]) == 64


# --------------------------------------------------------------------------
# The analysis command


def _bundle_args(run_id: str, output: Path, *extra: str) -> list[str]:
    return [
        "--reference",
        run_id,
        "--reference-where",
        "model_id=Qwen3.6-35B-A3B",
        "--candidate",
        run_id,
        "--candidate-where",
        "model_id=mistral-small-2603",
        "--records-dir",
        str(output.parent / "records"),
        "--output",
        str(output),
        *extra,
    ]


def test_the_command_refuses_the_committed_pair_on_thinking_policy(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "record.json"
    assert comparison.main(_bundle_args(RUN_5E, output)) == 0
    record = json.loads(output.read_text(encoding="utf-8"))
    member = record["members"][0]
    assert member["refusal"] == [
        {
            "field": "thinking_policy",
            "reason": "absent",
            "reference_value": None,
            "candidate_value": None,
        }
    ]
    assert member["reference_row_count"] == member["candidate_row_count"] == 20
    assert member["verdict"] == comparison.VERDICT_NOT_COMPARABLE
    assert "refused on thinking_policy (absent)" in capsys.readouterr().out

    first = output.read_bytes()
    assert comparison.main(_bundle_args(RUN_5E, output)) == 0
    assert output.read_bytes() == first


@pytest.mark.parametrize(
    ("run_prefix", "reference_only", "candidate_only", "expected_p"),
    [("5e13166d", 1, 4, 0.375), ("d20afbda", 2, 4, 0.6875)],
)
def test_the_committed_pairs_with_their_constraint_present_reproduce_the_epic(
    run_prefix: str, reference_only: int, candidate_only: int, expected_p: float
) -> None:
    # The same per-item outcomes as the published rows, with the one field
    # they predate supplied: the arithmetic the epic states for them.
    rows = [
        {**json.loads(line), "thinking_policy": "disabled"}
        for line in REFERENCE_BUNDLE.read_text(encoding="utf-8").splitlines()
    ]
    run_id = next(row["run_id"] for row in rows if row["run_id"].startswith(run_prefix))
    reference = Side(run_id, {"model_id": "Qwen3.6-35B-A3B"})
    candidate = Side(run_id, {"model_id": "mistral-small-2603"})
    member = compare_sides(
        comparison.select_side(rows, reference),
        comparison.select_side(rows, candidate),
        reference,
        candidate,
    )
    contingency = member["result"]["contingency"]
    assert contingency["reference_only_correct"] == reference_only
    assert contingency["candidate_only_correct"] == candidate_only
    assert member["result"]["p_value"] == expected_p
    assert member["comparison_kind"] == comparison.KIND_TEST
    assert member["verdict"] == comparison.VERDICT_NOT_DISTINGUISHABLE


def test_the_command_refuses_to_overwrite_a_different_record(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    output = tmp_path / "record.json"
    output.write_text("{}\n", encoding="utf-8")
    assert comparison.main(_bundle_args(RUN_5E, output)) == 1
    assert output.read_text(encoding="utf-8") == "{}\n"
    assert "immutable" in capsys.readouterr().err


def test_the_command_writes_to_the_default_comparisons_dir(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = tmp_path / "rows.jsonl"
    rows.write_text(REFERENCE_BUNDLE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.setattr(comparison, "COMPARISONS_DIR", tmp_path / "comparisons")
    args = _bundle_args(RUN_5E, tmp_path / "unused")[:-4] + ["--rows", str(rows)]
    assert comparison.main(args) == 0
    written = list((tmp_path / "comparisons").glob("*.json"))
    assert len(written) == 1
    assert written[0].name.startswith("classification-support-routing@2.model.")


@pytest.mark.parametrize(
    ("args", "message"),
    [
        (["--alpha", "1.5"], "--alpha"),
        (["--reference-where", "model_id"], "field=value"),
        (["--rows", "missing.jsonl"], "cannot read"),
        (["--candidate-where", "model_id=nobody"], "candidate side"),
    ],
)
def test_the_command_exits_1_on_unusable_input(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    args: list[str],
    message: str,
) -> None:
    output = tmp_path / "record.json"
    base = _bundle_args(RUN_5E, output)
    assert comparison.main([*base, *args]) == 1
    assert message in capsys.readouterr().err
    assert not output.exists()


def test_the_command_refuses_a_file_that_is_not_json_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = tmp_path / "rows.jsonl"
    rows.write_text("not json\n", encoding="utf-8")
    args = [*_bundle_args(RUN_5E, tmp_path / "out.json"), "--rows", str(rows)]
    assert comparison.main(args) == 1
    assert "JSON lines" in capsys.readouterr().err


def test_a_record_over_mixed_suites_is_named_as_such() -> None:
    ref, cand = _pairs_outcomes(1, 0, 0, 0)
    member = _compare(
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", "model-b", cand, suite_id="other-suite"),
    )
    record = comparison.build_family_record([member], alpha=0.05, rows_source="x")
    assert comparison.default_output_path(record).name.startswith("mixed-suites.model.")


PUBLISHED_DIR = Path("aidd_docs/results/comparisons")
PUBLISHED_RECORDS = sorted(PUBLISHED_DIR.glob("*.json"))


def _load(path: Path) -> dict[str, Any]:
    record: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return record


def _declaration(members: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            side: {
                "run_id": member[f"{side}_run_id"],
                "where": member[f"{side}_selector"],
            }
            for side in ("reference", "candidate")
        }
        for member in members
    ]


@pytest.mark.parametrize("published", PUBLISHED_RECORDS, ids=lambda path: path.name)
def test_a_published_record_recomputes_or_is_unedited(
    published: Path, tmp_path: Path
) -> None:
    record = _load(published)
    if record["record_version"] == "1":
        # Superseded and kept: its own content still hashes to its id.
        body = {key: value for key, value in record.items() if key != "family_id"}
        digest = hashlib.sha256(comparison.record_text(body).encode()).hexdigest()
        assert digest == record["family_id"]
        assert comparison.record_text(record) == published.read_text(encoding="utf-8")
        return
    # Recomputed from the bundle with only the records it supersedes on file,
    # so the command cannot simply re-emit the published one.
    records_dir = tmp_path / "records"
    records_dir.mkdir()
    by_id = {_load(path)["family_id"]: path for path in PUBLISHED_RECORDS}
    for family_id in comparison.superseded_ids(record):
        source = by_id[family_id]
        (records_dir / source.name).write_bytes(source.read_bytes())
    declaration = tmp_path / "comparisons.json"
    declaration.write_text(json.dumps(_declaration(record["members"])), "utf-8")
    output = tmp_path / published.name
    args = [
        "--rows",
        record["rows_source"],
        "--alpha",
        str(record["alpha"]),
        "--dimension",
        record["family_definition"]["compared_dimension"],
        "--comparisons",
        str(declaration),
        "--records-dir",
        str(records_dir),
        "--output",
        str(output),
    ]
    assert comparison.main(args) == 0
    assert output.read_text(encoding="utf-8") == published.read_text(encoding="utf-8")


def test_the_bundle_publishes_one_current_family_holding_both_pairs() -> None:
    records = [_load(path) for path in PUBLISHED_RECORDS]
    current = [
        record for record in records if record["family_id"] in comparison.heads(records)
    ]
    (head,) = current
    assert head["record_version"] == comparison.RECORD_VERSION
    assert head["family_size"] == 2
    assert (head["tested_count"], head["refused_count"]) == (0, 2)
    superseded = sorted(
        record["family_id"] for record in records if record["record_version"] == "1"
    )
    assert comparison.superseded_ids(head) == superseded
    assert len(superseded) == 2


def test_two_spellings_of_one_rows_file_give_one_family_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rows = tmp_path / "data" / "rows.jsonl"
    rows.parent.mkdir()
    rows.write_text(REFERENCE_BUNDLE.read_text(encoding="utf-8"), encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    spellings = ["data/rows.jsonl", "./data/../data/rows.jsonl", str(rows)]
    texts = []
    for index, spelling in enumerate(spellings):
        output = tmp_path / f"out-{index}.json"
        args = [*_bundle_args(RUN_5E, output), "--rows", spelling]
        assert comparison.main(args) == 0
        texts.append(output.read_text(encoding="utf-8"))
    assert texts[0] == texts[1] == texts[2]
    assert json.loads(texts[0])["rows_source"] == "data/rows.jsonl"


def test_a_rows_file_outside_the_working_directory_is_named_absolutely(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    rows = tmp_path / "rows.jsonl"
    assert comparison.rows_source_name(rows) == rows.resolve().as_posix()


# --------------------------------------------------------------------------
# Holm and the family


def test_holm_reproduces_the_published_worked_example() -> None:
    # Wikipedia, "Holm-Bonferroni method", Example: H1 and H4 rejected at 0.05.
    adjusted = holm_adjust([0.01, 0.04, 0.03, 0.005])
    assert adjusted == [0.03, 0.06, 0.06, 0.02]
    assert [p <= 0.05 for p in adjusted] == [True, False, False, True]


def test_holm_matches_a_hand_computed_fixture_with_a_tie_and_a_cap() -> None:
    # m = 5, ascending 0.01, 0.04, 0.25, 0.25, 0.75: 5 * 0.01 = 0.05,
    # 4 * 0.04 = 0.16, 3 * 0.25 = 0.75, then 0.5 and 0.75 under the running
    # maximum 0.75, so the tie shares one value.
    assert holm_adjust([0.25, 0.01, 0.25, 0.75, 0.04]) == [
        0.75,
        0.05,
        0.75,
        0.75,
        0.16,
    ]
    assert holm_adjust([0.6, 0.7]) == [1.0, 1.0]
    assert holm_adjust([0.375]) == [0.375]
    assert holm_adjust([]) == []


def _candidate_member(
    model_id: str, candidate_only: int, **overrides: Any
) -> dict[str, Any]:
    """`model-a` against `model_id`: `candidate_only` items only the candidate gets."""
    ref, cand = _pairs_outcomes(10, 0, candidate_only, 10 - candidate_only)
    candidate = Side("run-cand", {"model_id": model_id})
    return compare_sides(
        _binary_rows("run-ref", "model-a", ref),
        _binary_rows("run-cand", model_id, cand, **overrides),
        REFERENCE,
        candidate,
    )


def test_each_verdict_reads_its_holm_adjusted_p_with_the_raw_p_beside_it() -> None:
    # Raw McNemar p: 8 one-way discordant pairs 2/2^8, 6 pairs 2/2^6, 5 pairs
    # 2/2^5; Holm over three: 0.0234375, 0.0625, 0.0625.
    members = [
        _candidate_member("model-b", 8),
        _candidate_member("model-c", 6),
        _candidate_member("model-d", 5),
    ]
    record = comparison.build_family_record(members, alpha=0.05, rows_source="x")
    by_model = {m["candidate_selector"]["model_id"]: m for m in record["members"]}
    assert [by_model[k]["raw_p_value"] for k in ("model-b", "model-c", "model-d")] == [
        0.0078125,
        0.03125,
        0.0625,
    ]
    assert [
        by_model[k]["adjusted_p_value"] for k in ("model-b", "model-c", "model-d")
    ] == [0.0234375, 0.0625, 0.0625]
    assert by_model["model-b"]["verdict"] == comparison.VERDICT_DISTINGUISHABLE
    # Distinguishable alone (raw 0.03125 <= 0.05), not once adjusted.
    assert by_model["model-c"]["verdict"] == comparison.VERDICT_NOT_DISTINGUISHABLE
    assert record["family_size"] == record["tested_count"] == 3
    assert record["refused_count"] == 0
    assert record["multiplicity_correction"]["adjustment_size"] == 3
    assert record["family_definition"]["rule"] == comparison.FAMILY_RULE
    reordered = comparison.build_family_record(
        members[::-1], alpha=0.05, rows_source="x"
    )
    assert comparison.record_text(reordered) == comparison.record_text(record)


def test_a_refused_member_is_listed_and_enters_no_count() -> None:
    members = [
        _candidate_member("model-b", 8),
        _candidate_member("model-c", 6),
        _candidate_member("model-d", 5),
        _candidate_member("model-e", 8, max_output_tokens=64),
    ]
    record = comparison.build_family_record(members, alpha=0.05, rows_source="x")
    refused = next(
        m for m in record["members"] if m["candidate_selector"]["model_id"] == "model-e"
    )
    assert refused["comparison_kind"] == comparison.KIND_REFUSAL
    assert [entry["field"] for entry in refused["refusal"]] == ["max_output_tokens"]
    assert refused["raw_p_value"] is None
    assert refused["adjusted_p_value"] is None
    assert refused["adjusted_p_value_null_reason"] == NULL_COMPARISON_REFUSED
    assert refused["verdict"] == comparison.VERDICT_NOT_COMPARABLE
    assert (record["family_size"], record["tested_count"]) == (4, 3)
    assert record["refused_count"] == 1
    assert record["multiplicity_correction"]["adjustment_size"] == 3
    adjusted = sorted(
        m["adjusted_p_value"] for m in record["members"] if m is not refused
    )
    assert adjusted == [0.0234375, 0.0625, 0.0625]


def test_an_observation_is_adjusted_and_a_null_p_counts_as_one() -> None:
    observation = _candidate_member("model-b", 8, compute_mode="cpu_only")
    no_discordant = _candidate_member("model-c", 0)
    record = comparison.build_family_record(
        [observation, no_discordant, _candidate_member("model-d", 6)],
        alpha=0.05,
        rows_source="x",
    )
    by_model = {m["candidate_selector"]["model_id"]: m for m in record["members"]}
    # m = 3 = tested_count: model-c has no p and enters as p = 1, so the
    # others are adjusted as one of three (0.0078125 * 3, then 0.03125 * 2).
    assert record["multiplicity_correction"]["adjustment_size"] == 3
    assert record["tested_count"] == 3
    assert by_model["model-b"]["comparison_kind"] == comparison.KIND_OBSERVATION
    assert by_model["model-b"]["adjusted_p_value"] == 0.0234375
    assert by_model["model-b"]["verdict"] == comparison.VERDICT_NOT_COMPARABLE
    assert by_model["model-c"]["adjusted_p_value"] is None
    assert by_model["model-c"]["adjusted_p_value_null_reason"] == (
        NULL_NO_DISCORDANT_PAIRS
    )
    assert by_model["model-d"]["adjusted_p_value"] == 0.0625


def test_comparisons_that_cannot_form_one_family_are_refused() -> None:
    member = _candidate_member("model-b", 8)
    with pytest.raises(FamilyError, match="at least one"):
        comparison.build_family_record([], alpha=0.05, rows_source="x")
    with pytest.raises(FamilyError, match="declared twice"):
        comparison.build_family_record([member, member], alpha=0.05, rows_source="x")
    other_suite = _candidate_member("model-c", 6)
    other_suite["suite_id"] = "translation-business-short-form"
    with pytest.raises(FamilyError, match="more than one suite"):
        comparison.build_family_record(
            [member, other_suite], alpha=0.05, rows_source="x"
        )
    other_axis = {**_candidate_member("model-c", 6), "compared_dimension": "x"}
    with pytest.raises(FamilyError, match="compared dimension"):
        comparison.build_family_record(
            [member, other_axis], alpha=0.05, rows_source="x"
        )


def test_a_member_refused_on_suite_identity_stays_in_its_family() -> None:
    refused = _candidate_member("model-c", 6, suite_id="other-suite")
    record = comparison.build_family_record(
        [_candidate_member("model-b", 8), refused], alpha=0.05, rows_source="x"
    )
    assert record["family_definition"]["suite_id"] == "classification-support-routing"
    assert record["refused_count"] == 1


def _growing_rows(tmp_path: Path, candidates: int) -> Path:
    ref, _ = _pairs_outcomes(10, 0, 0, 10)
    rows = _binary_rows("run-1", "model-ref", ref)
    for index in range(candidates):
        discordant = index % 9 + 1
        _, cand = _pairs_outcomes(10, 0, discordant, 10 - discordant)
        rows += _binary_rows("run-1", f"model-{index:02d}", cand)
    path = tmp_path / "rows.jsonl"
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), "utf-8")
    return path


def _declare(tmp_path: Path, count: int) -> Path:
    declaration = [
        {
            "reference": {"run_id": "run-1", "where": {"model_id": "model-ref"}},
            "candidate": {"run_id": "run-1", "where": {"model_id": f"model-{i:02d}"}},
        }
        for i in range(count)
    ]
    path = tmp_path / f"declare-{count}.json"
    path.write_text(json.dumps(declaration), "utf-8")
    return path


def test_a_family_of_eleven_grown_to_twelve_is_superseded_not_edited(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = _growing_rows(tmp_path, 12)
    records = tmp_path / "records"

    def run(count: int) -> int:
        return comparison.main(
            [
                "--rows",
                str(rows),
                "--comparisons",
                str(_declare(tmp_path, count)),
                "--records-dir",
                str(records),
            ]
        )

    assert run(11) == 0
    (eleven_path,) = records.glob("*.json")
    eleven_bytes = eleven_path.read_bytes()
    eleven = json.loads(eleven_bytes)
    assert eleven["family_size"] == 11
    assert eleven["supersedes"] == []

    assert run(12) == 0
    (twelve_path,) = set(records.glob("*.json")) - {eleven_path}
    twelve = _load(twelve_path)
    assert twelve["family_size"] == 12
    assert twelve["multiplicity_correction"]["adjustment_size"] == 12
    assert twelve["supersedes"] == [{"family_id": eleven["family_id"]}]
    assert eleven_path.read_bytes() == eleven_bytes
    assert "supersedes " + eleven["family_id"][:12] in capsys.readouterr().out

    # The same bundle and definition, re-run: the identical record, nothing new.
    twelve_bytes = twelve_path.read_bytes()
    assert run(12) == 0
    assert run(11) == 0
    assert sorted(records.glob("*.json")) == sorted([eleven_path, twelve_path])
    assert twelve_path.read_bytes() == twelve_bytes
    assert eleven_path.read_bytes() == eleven_bytes
    out = capsys.readouterr().out
    assert "identical to a published record" in out
    assert "superseded by " + twelve["family_id"][:12] in out


@pytest.mark.parametrize(
    ("first", "second", "missing"),
    [
        # A shrink: twelve, then the one favourable pair alone.
        (range(12), [3], "model-00"),
        # Disjoint: two pairs, then a third pair in their place.
        (range(2), [2], "model-01"),
    ],
    ids=["shrinking", "disjoint"],
)
def test_a_declaration_dropping_a_current_comparison_is_refused(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    first: range | list[int],
    second: list[int],
    missing: str,
) -> None:
    rows = _growing_rows(tmp_path, 12)
    records = tmp_path / "records"

    def run(indexes: range | list[int], name: str) -> int:
        declaration = [
            {
                "reference": {"run_id": "run-1", "where": {"model_id": "model-ref"}},
                "candidate": {
                    "run_id": "run-1",
                    "where": {"model_id": f"model-{i:02d}"},
                },
            }
            for i in indexes
        ]
        path = tmp_path / name
        path.write_text(json.dumps(declaration), "utf-8")
        args = ["--rows", str(rows), "--comparisons", str(path)]
        return comparison.main([*args, "--records-dir", str(records)])

    assert run(first, "first.json") == 0
    (head,) = records.glob("*.json")
    head_bytes = head.read_bytes()
    capsys.readouterr()
    assert run(second, "second.json") == 1
    error = capsys.readouterr().err
    assert "does not declare" in error
    assert missing in error
    assert list(records.glob("*.json")) == [head]
    assert head.read_bytes() == head_bytes


def test_a_record_of_another_family_is_not_superseded(tmp_path: Path) -> None:
    rows = _growing_rows(tmp_path, 2)
    records = tmp_path / "records"
    base = ["--rows", str(rows), "--comparisons", str(_declare(tmp_path, 2))]
    assert comparison.main([*base, "--records-dir", str(records)]) == 0
    args = [*base, "--records-dir", str(records), "--dimension", "prompt_variant"]
    assert comparison.main(args) == 0
    assert all(_load(path)["supersedes"] == [] for path in records.glob("*.json"))


@pytest.mark.parametrize(
    ("content", "extra", "message"),
    [
        ("[]", [], "non-empty array"),
        ("{", [], "is not JSON"),
        ("[1]", [], "comparison 1 is not an object"),
        ('[{"reference": {"run_id": 1}}]', [], "comparison 1: reference"),
        (
            (
                '[{"reference": {"run_id": "run-1"}, "candidate": {"run_id": "r", '
                '"where": {"model_id": 3}}}]'
            ),
            [],
            "comparison 1: candidate",
        ),
        (None, [], "cannot read comparisons"),
        ("[]", ["--reference", "run-1"], "replaces --reference"),
    ],
)
def test_a_malformed_declaration_exits_1_writing_nothing(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    content: str | None,
    extra: list[str],
    message: str,
) -> None:
    declaration = tmp_path / "declare.json"
    if content is not None:
        declaration.write_text(content, "utf-8")
    records = tmp_path / "records"
    args = [
        "--rows",
        str(_growing_rows(tmp_path, 1)),
        "--comparisons",
        str(declaration),
        "--records-dir",
        str(records),
        *extra,
    ]
    assert comparison.main(args) == 1
    assert message in capsys.readouterr().err
    assert not records.exists()


def test_an_invocation_needs_its_comparisons_declared(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert comparison.main(["--reference", "run-1"]) == 1
    assert "or --comparisons" in capsys.readouterr().err


def test_an_invocation_spanning_two_suites_writes_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    rows = _growing_rows(tmp_path, 1)
    extra = _binary_rows(
        "run-2", "model-x", [True] * 20, suite_id="translation-x"
    ) + _binary_rows("run-2", "model-y", [False] * 20, suite_id="translation-x")
    with rows.open("a", encoding="utf-8") as handle:
        handle.write("".join(json.dumps(row) + "\n" for row in extra))
    declaration = json.loads(_declare(tmp_path, 1).read_text("utf-8"))
    declaration.append(
        {
            "reference": {"run_id": "run-2", "where": {"model_id": "model-x"}},
            "candidate": {"run_id": "run-2", "where": {"model_id": "model-y"}},
        }
    )
    path = tmp_path / "two-suites.json"
    path.write_text(json.dumps(declaration), "utf-8")
    records = tmp_path / "records"
    args = ["--rows", str(rows), "--comparisons", str(path)]
    assert comparison.main([*args, "--records-dir", str(records)]) == 1
    assert "more than one suite" in capsys.readouterr().err
    assert not records.exists()


def test_the_records_dir_skips_other_json_and_refuses_broken_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    records = tmp_path / "records"
    records.mkdir()
    (records / "notes.json").write_text('{"record_type": "other"}', "utf-8")
    rows = _growing_rows(tmp_path, 1)
    args = ["--rows", str(rows), "--comparisons", str(_declare(tmp_path, 1))]
    assert comparison.main([*args, "--records-dir", str(records)]) == 0
    assert len(list(records.glob("*.json"))) == 2
    (records / "broken.json").write_text("{", "utf-8")
    assert comparison.main([*args, "--records-dir", str(records)]) == 1
    assert "broken.json is not JSON" in capsys.readouterr().err
