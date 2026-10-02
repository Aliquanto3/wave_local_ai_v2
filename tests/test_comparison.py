"""Tests for the paired comparison: the two tests, the refusals, the record."""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import pytest
from scipy import stats

from wave_local_ai_v2 import comparison
from wave_local_ai_v2.comparison import (
    NULL_ALL_DIFFERENCES_ZERO,
    NULL_NO_DISCORDANT_PAIRS,
    NULL_ODDS_RATIO_EMPTY_CELL,
    NULL_PAIRED_N_BELOW_MINIMUM,
    ComparisonInputError,
    Side,
    compare_sides,
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
    first = comparison.build_family_record(_compare(*rows), alpha=0.05, rows_source="x")
    second = comparison.build_family_record(
        _compare(*rows), alpha=0.05, rows_source="x"
    )
    assert comparison.record_text(first) == comparison.record_text(second)
    assert first["family_size"] == 1
    assert first["members"][0]["adjusted_p_value"] == 0.375
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
    args = _bundle_args(RUN_5E, tmp_path / "unused")[:-2] + ["--rows", str(rows)]
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
    record = comparison.build_family_record(member, alpha=0.05, rows_source="x")
    assert comparison.default_output_path(record).name.startswith("mixed-suites.model.")


PUBLISHED_RECORDS = sorted(Path("aidd_docs/results/comparisons").glob("*.json"))


@pytest.mark.parametrize("published", PUBLISHED_RECORDS, ids=lambda path: path.name)
def test_a_published_record_recomputes_from_the_bundle_alone(
    published: Path, tmp_path: Path
) -> None:
    record = json.loads(published.read_text(encoding="utf-8"))
    (member,) = record["members"]
    args = ["--rows", record["rows_source"], "--alpha", str(record["alpha"])]
    for side in ("reference", "candidate"):
        args += [f"--{side}", member[f"{side}_run_id"]]
        for key, value in member[f"{side}_selector"].items():
            args += [f"--{side}-where", f"{key}={value}"]
    args += ["--dimension", member["compared_dimension"]]
    output = tmp_path / published.name
    assert comparison.main([*args, "--output", str(output)]) == 0
    assert output.read_text(encoding="utf-8") == published.read_text(encoding="utf-8")


def test_the_bundle_publishes_one_record_per_committed_pair() -> None:
    assert len(PUBLISHED_RECORDS) == 2


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
