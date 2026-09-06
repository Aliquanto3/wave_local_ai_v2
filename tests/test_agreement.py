import pytest

from wave_local_ai_v2.agreement import (
    DEFAULT_CONTESTED_THRESHOLD,
    ContestedThreshold,
    agreement_for_rubric,
    cohens_kappa,
    exact_match_rate,
    headline_score,
    is_contested,
    within_one_rate,
)
from wave_local_ai_v2.judge_protocol import (
    OPEN_ENDED_QUALITY_1_TO_5,
    RUBRIC_KIND_CATEGORICAL,
    RUBRIC_KIND_ORDINAL_1_5,
    Rubric,
)

ORDINAL_POINTS = (1, 2, 3, 4, 5)
CATEGORIES = frozenset({"adequate", "partial", "inadequate"})

CATEGORICAL_RUBRIC = Rubric(
    rubric_id="test-categorical",
    version="1",
    kind=RUBRIC_KIND_CATEGORICAL,
    scale=None,
    categories=CATEGORIES,
    text={"en": "Answer with exactly one of: adequate, partial, inadequate."},
)

# The one hand-computed matrix every kappa assertion below reads.
SCORES_A = [1, 2, 3, 4, 5]
SCORES_B = [1, 2, 3, 4, 4]


def test_quadratic_weighted_kappa_on_the_fixed_matrix() -> None:
    # Observed disagreement = W(5,4)*1/5 = 1/5 = 0.2.
    # Marginals: A uniform 0.2 each; B = (0.2, 0.2, 0.2, 0.4, 0.0).
    # Expected = 0.2 * sum_j pB_j * sum_i (i-j)^2
    #          = 0.2 * (0.2*30 + 0.2*15 + 0.2*10 + 0.4*15 + 0.0*30) = 0.2*17 = 3.4
    # kappa = 1 - 0.2/3.4 = 16/17.
    value, null_reason = cohens_kappa(
        SCORES_A, SCORES_B, categories=ORDINAL_POINTS, weighted=True
    )

    assert null_reason is None
    assert value == pytest.approx(16 / 17)


def test_unweighted_kappa_on_the_same_matrix() -> None:
    # po = 4/5 = 0.8; pe = sum_i pA_i * pB_i = 0.2*(0.2+0.2+0.2+0.4+0.0) = 0.2.
    # kappa = (0.8 - 0.2) / (1 - 0.2) = 0.75.
    value, null_reason = cohens_kappa(
        SCORES_A, SCORES_B, categories=ORDINAL_POINTS, weighted=False
    )

    assert null_reason is None
    assert value == pytest.approx(0.75)


def test_both_judges_constant_is_null_with_zero_variance() -> None:
    value, null_reason = cohens_kappa(
        [3, 3, 3], [3, 3, 3], categories=ORDINAL_POINTS, weighted=True
    )

    assert value is None
    assert null_reason == "zero_variance"


def test_one_judge_constant_is_null_rather_than_the_defined_zero() -> None:
    # The unweighted mathematics returns a defined kappa of 0 here (expected
    # disagreement equals observed), which would read as chance-level
    # disagreement even though the judges may have agreed on every item.
    value, null_reason = cohens_kappa(
        [3, 3, 3], [1, 2, 3], categories=ORDINAL_POINTS, weighted=False
    )

    assert value is None
    assert null_reason == "zero_variance"


def test_mismatched_score_lengths_are_refused() -> None:
    with pytest.raises(ValueError, match="one score per judge per item"):
        cohens_kappa([1, 2], [1], categories=ORDINAL_POINTS, weighted=True)


def test_a_score_outside_the_declared_categories_is_refused() -> None:
    with pytest.raises(ValueError, match="outside the declared categories"):
        cohens_kappa([1, 9], [1, 2], categories=ORDINAL_POINTS, weighted=True)


def test_an_ordinal_agreement_names_the_quadratic_statistic() -> None:
    result = agreement_for_rubric(
        OPEN_ENDED_QUALITY_1_TO_5, list(zip(SCORES_A, SCORES_B, strict=True))
    )

    assert result["statistic"] == "cohens_kappa_quadratic_weighted"
    assert result["value"] == pytest.approx(16 / 17)
    assert result["exact_match_rate"] == pytest.approx(0.8)
    assert result["within_one_rate"] == pytest.approx(1.0)
    assert result["n_items"] == 5
    assert result["n_items_excluded"] == 0


def test_a_categorical_agreement_names_the_unweighted_statistic() -> None:
    pairs = [
        ("adequate", "adequate"),
        ("partial", "partial"),
        ("inadequate", "inadequate"),
        ("adequate", "partial"),
    ]

    result = agreement_for_rubric(CATEGORICAL_RUBRIC, pairs)

    assert result["statistic"] == "cohens_kappa_unweighted"
    assert result["within_one_rate"] is None
    assert result["exact_match_rate"] == pytest.approx(0.75)


def test_a_pair_with_a_missing_judgement_is_excluded_not_scored() -> None:
    pairs = list(zip(SCORES_A, SCORES_B, strict=True))
    with_missing = [*pairs, (4, None)]

    baseline = agreement_for_rubric(OPEN_ENDED_QUALITY_1_TO_5, pairs)
    result = agreement_for_rubric(OPEN_ENDED_QUALITY_1_TO_5, with_missing)

    assert result["n_items"] == baseline["n_items"]
    assert result["n_items_excluded"] == 1
    assert result["value"] == pytest.approx(baseline["value"])


def test_an_empty_pair_list_is_null_with_a_reason_and_raises_nothing() -> None:
    result = agreement_for_rubric(OPEN_ENDED_QUALITY_1_TO_5, [])

    assert result["value"] is None
    assert result["value_null_reason"] == "zero_variance"
    assert result["n_items"] == 0


def test_exact_match_rate_over_an_empty_input_is_zero() -> None:
    assert exact_match_rate([], []) == 0.0


def test_within_one_rate_is_none_for_unordered_labels() -> None:
    assert within_one_rate(["adequate"], ["partial"]) is None


def test_within_one_rate_counts_a_one_point_gap() -> None:
    assert within_one_rate([1, 2, 3], [2, 2, 5]) == pytest.approx(2 / 3)


def test_a_one_point_gap_is_not_contested_and_two_points_is() -> None:
    assert is_contested(RUBRIC_KIND_ORDINAL_1_5, 3, 4, DEFAULT_CONTESTED_THRESHOLD) == (
        False,
        None,
    )
    assert is_contested(RUBRIC_KIND_ORDINAL_1_5, 2, 4, DEFAULT_CONTESTED_THRESHOLD) == (
        True,
        "ordinal_delta_above_threshold",
    )


def test_a_category_mismatch_is_contested() -> None:
    assert is_contested(
        RUBRIC_KIND_CATEGORICAL, "adequate", "partial", DEFAULT_CONTESTED_THRESHOLD
    ) == (True, "category_mismatch")
    assert is_contested(
        RUBRIC_KIND_CATEGORICAL, "adequate", "adequate", DEFAULT_CONTESTED_THRESHOLD
    ) == (False, None)


def test_the_threshold_is_read_not_hardcoded_at_the_call_site() -> None:
    lenient = ContestedThreshold(max_ordinal_delta=2)

    assert is_contested(RUBRIC_KIND_ORDINAL_1_5, 2, 4, lenient) == (False, None)


def test_a_missing_judge_score_is_not_contested() -> None:
    assert is_contested(
        RUBRIC_KIND_ORDINAL_1_5, 4, None, DEFAULT_CONTESTED_THRESHOLD
    ) == (False, None)


def test_a_non_integer_score_on_an_ordinal_rubric_is_refused() -> None:
    with pytest.raises(ValueError, match="must be integers"):
        is_contested(
            RUBRIC_KIND_ORDINAL_1_5, "adequate", 4, DEFAULT_CONTESTED_THRESHOLD
        )


def test_an_unrecognised_rubric_kind_is_refused() -> None:
    with pytest.raises(ValueError, match="ternary"):
        is_contested("ternary", 1, 2, DEFAULT_CONTESTED_THRESHOLD)


def test_the_headline_excludes_the_contested_item_and_counts_it() -> None:
    item_scores = [[4, 4], [5, 5], [1, 5], [3, 3], [2, 2]]
    contested = [False, False, True, False, False]

    headline = headline_score(item_scores, contested)

    assert headline["score"] == pytest.approx((4 + 5 + 3 + 2) / 4)
    assert headline["n_included"] == 4
    assert headline["n_excluded"] == 1


def test_un_flagging_the_contested_item_moves_the_headline() -> None:
    item_scores = [[4, 4], [5, 5], [1, 5], [3, 3], [2, 2]]

    excluded = headline_score(item_scores, [False, False, True, False, False])
    included = headline_score(item_scores, [False] * 5)

    assert included["score"] != pytest.approx(excluded["score"])
    assert included["n_included"] == 5
    assert included["n_excluded"] == 0


def test_all_contested_leaves_no_headline_rather_than_zero() -> None:
    headline = headline_score([[4, 4], [5, 5], [1, 5], [3, 3], [2, 2]], [True] * 5)

    assert headline["score"] is None
    assert headline["n_included"] == 0
    assert headline["n_excluded"] == 5


def test_an_item_with_no_numeric_score_is_excluded() -> None:
    headline = headline_score([[None, None], [4, 4]], [False, False])

    assert headline["score"] == pytest.approx(4.0)
    assert headline["n_included"] == 1
    assert headline["n_excluded"] == 1


def test_headline_needs_one_flag_per_item() -> None:
    with pytest.raises(ValueError, match="one contested flag per item"):
        headline_score([[4, 4]], [])
