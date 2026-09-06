"""Agreement between two judges: the two kappas, the raw rates beside them,
the contested rule, and the headline that excludes contested items and says so.

`κ = 1 − ΣΣ W(i,j)·Õ(i,j) / ΣΣ W(i,j)·Ẽ(i,j)`, with `Õ` the confusion matrix
normalized by N and `Ẽ` the outer product of the two raters' marginals.
Quadratic weighting is `W(i,j) = (i−j)²` over the rubric's ordered points,
unweighted is `W(i,j) = 0 if i == j else 1`. The conventional `/(k−1)²`
normalization of the quadratic weights is deliberately omitted: it scales
numerator and denominator alike and cancels out of the ratio.

Pure arithmetic: no provider, no network, no rubric text. It takes a `Rubric`
only to read which kind of scale it declares.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TypedDict

from wave_local_ai_v2 import judge_protocol, settings
from wave_local_ai_v2.judge_protocol import (
    RUBRIC_KIND_ORDINAL_1_5,
    Rubric,
)

# One judge's score for one item: an ordinal point, a category label, or the
# absence of a judgement (`judge.run_judge_call` on a failed parse).
JudgeScore = int | str

AGREEMENT_STATISTIC_KAPPA_QUADRATIC = "cohens_kappa_quadratic_weighted"
AGREEMENT_STATISTIC_KAPPA_UNWEIGHTED = "cohens_kappa_unweighted"

KAPPA_NULL_ZERO_VARIANCE = "zero_variance"
KAPPA_NULL_ZERO_EXPECTED_DISAGREEMENT = "zero_expected_disagreement"

CONTESTED_REASON_ORDINAL_DELTA = "ordinal_delta_above_threshold"
CONTESTED_REASON_CATEGORY_MISMATCH = "category_mismatch"


class Agreement(TypedDict):
    """What a judged suite publishes about how far its two judges agreed."""

    statistic: str
    value: float | None
    value_null_reason: str | None
    exact_match_rate: float
    within_one_rate: float | None
    n_items: int
    n_items_excluded: int


class Headline(TypedDict):
    """The judged headline score and how many items it left out."""

    score: float | None
    n_included: int
    n_excluded: int


def cohens_kappa(
    scores_a: Sequence[JudgeScore],
    scores_b: Sequence[JudgeScore],
    *,
    categories: Sequence[JudgeScore],
    weighted: bool,
) -> tuple[float | None, str | None]:
    """Cohen's kappa over two judges' scores, or `None` with a named reason.

    Returns `(value, null_reason)` with exactly one of them non-null. The
    confusion matrix is built over `categories` in the order given, so an
    unobserved category still occupies a row and a column and the quadratic
    weights read the rubric's own ordering.

    Two null cases, checked in this order. `zero_variance` when either judge
    scored every item the same: mathematically a constant judge against a
    varying one yields a defined `κ = 0`, and publishing that `0` would read
    as chance-level disagreement when the two may have agreed on every single
    item. That is the fabricated-figure failure `cost.total_or_none` and
    `aggregation.spread` already refuse, so it is refused here too, stricter
    than the mathematics requires and named as its own reason.
    `zero_expected_disagreement` is the textbook undefined case, a zero
    denominator, kept separate so the two are never confused for each other.
    """
    if len(scores_a) != len(scores_b):
        raise ValueError(
            f"cohens_kappa needs one score per judge per item: got "
            f"{len(scores_a)} and {len(scores_b)}"
        )

    # `< 2` rather than `== 1`: an empty score set has no variance to speak
    # of either, and returning a kappa over nothing would be the same lie.
    if len(set(scores_a)) < 2 or len(set(scores_b)) < 2:
        return None, KAPPA_NULL_ZERO_VARIANCE

    position = {category: index for index, category in enumerate(categories)}
    unknown = sorted(
        str(score) for score in set(scores_a) | set(scores_b) if score not in position
    )
    if unknown:
        raise ValueError(
            f"cohens_kappa was given score(s) outside the declared categories: "
            f"{', '.join(unknown)} (categories: {categories!r})"
        )

    size = len(categories)
    n_items = len(scores_a)
    observed = [[0] * size for _ in range(size)]
    for score_a, score_b in zip(scores_a, scores_b, strict=True):
        observed[position[score_a]][position[score_b]] += 1

    marginal_a = [sum(row) / n_items for row in observed]
    marginal_b = [
        sum(observed[i][j] for i in range(size)) / n_items for j in range(size)
    ]

    def weight(i: int, j: int) -> float:
        return float((i - j) ** 2) if weighted else float(i != j)

    numerator = sum(
        weight(i, j) * observed[i][j] / n_items
        for i in range(size)
        for j in range(size)
    )
    denominator = sum(
        weight(i, j) * marginal_a[i] * marginal_b[j]
        for i in range(size)
        for j in range(size)
    )
    if denominator == 0:
        return None, KAPPA_NULL_ZERO_EXPECTED_DISAGREEMENT

    return 1 - numerator / denominator, None


def exact_match_rate(
    scores_a: Sequence[JudgeScore], scores_b: Sequence[JudgeScore]
) -> float:
    """The share of items the two judges scored identically.

    `0.0` over an empty input rather than a `ZeroDivisionError`, the same
    convention `scoring.score_suite` applies to an empty item list. The
    `Agreement` that publishes this figure carries `n_items` beside it, which
    is what tells a reader the rate is over nothing.
    """
    if not scores_a:
        return 0.0
    matches = sum(1 for a, b in zip(scores_a, scores_b, strict=True) if a == b)
    return matches / len(scores_a)


def within_one_rate(
    scores_a: Sequence[JudgeScore], scores_b: Sequence[JudgeScore]
) -> float | None:
    """The share of items the two judges scored at most one point apart.

    `None` when either judge's scores are not ordinal points: category labels
    are unordered, so "within one" would be a number inviting an ordering the
    rubric never declared.
    """
    if not scores_a:
        return None
    if not all(
        isinstance(score, int) and not isinstance(score, bool)
        for score in (*scores_a, *scores_b)
    ):
        return None
    close = sum(
        1
        for a, b in zip(scores_a, scores_b, strict=True)
        if isinstance(a, int) and isinstance(b, int) and abs(a - b) <= 1
    )
    return close / len(scores_a)


def agreement_for_rubric(
    rubric: Rubric, pairs: Sequence[tuple[JudgeScore | None, JudgeScore | None]]
) -> Agreement:
    """Agreement over one suite's `(judge_a, judge_b)` score pairs.

    A pair with a `None` on either side is a judge whose call did not parse
    (`judge.run_judge_call`): it is dropped from the statistic and counted in
    `n_items_excluded`, never coerced to a score. `n_items` is what the
    statistic was actually computed over, not what was handed in.
    """
    usable = [(a, b) for a, b in pairs if a is not None and b is not None]
    scores_a = [a for a, _ in usable]
    scores_b = [b for _, b in usable]

    ordinal = rubric.kind == RUBRIC_KIND_ORDINAL_1_5
    if ordinal and rubric.scale is not None:
        categories: Sequence[JudgeScore] = rubric.scale
    else:
        # Sorted for a stable matrix ordering; with unweighted weights the
        # order cannot change the result, so any total order will do.
        categories = sorted(rubric.categories or frozenset())

    value, null_reason = cohens_kappa(
        scores_a, scores_b, categories=categories, weighted=ordinal
    )
    return Agreement(
        statistic=(
            AGREEMENT_STATISTIC_KAPPA_QUADRATIC
            if ordinal
            else AGREEMENT_STATISTIC_KAPPA_UNWEIGHTED
        ),
        value=value,
        value_null_reason=null_reason,
        exact_match_rate=exact_match_rate(scores_a, scores_b),
        within_one_rate=within_one_rate(scores_a, scores_b) if ordinal else None,
        n_items=len(usable),
        n_items_excluded=len(pairs) - len(usable),
    )


@dataclass(frozen=True)
class ContestedThreshold:
    """How far two judges may sit apart on one item before it is contested.

    Ordinal only: a categorical rubric ignores `max_ordinal_delta` entirely
    and treats any mismatch as contested, because unordered labels have no
    distance for a threshold to sit on.
    """

    max_ordinal_delta: int


DEFAULT_CONTESTED_THRESHOLD = ContestedThreshold(
    max_ordinal_delta=settings.DEFAULT_CONTESTED_ORDINAL_MAX_DELTA
)


def is_contested(
    rubric_kind: str,
    score_a: JudgeScore | None,
    score_b: JudgeScore | None,
    threshold: ContestedThreshold,
) -> tuple[bool, str | None]:
    """Whether one item's two judge scores disagree far enough to be contested.

    A pair with a `None` on either side is **not** contested: that is a
    missing judgement, which the judged row reports as a failure reason and a
    single-judge flag. Publishing it as a disagreement would turn an unjudged
    item into evidence of two judges falling out.
    """
    if score_a is None or score_b is None:
        return False, None

    if rubric_kind == RUBRIC_KIND_ORDINAL_1_5:
        if not isinstance(score_a, int) or not isinstance(score_b, int):
            raise ValueError(
                f"an ordinal rubric's scores must be integers, got "
                f"{score_a!r} and {score_b!r}"
            )
        if abs(score_a - score_b) > threshold.max_ordinal_delta:
            return True, CONTESTED_REASON_ORDINAL_DELTA
        return False, None

    if rubric_kind == judge_protocol.RUBRIC_KIND_CATEGORICAL:
        if score_a != score_b:
            return True, CONTESTED_REASON_CATEGORY_MISMATCH
        return False, None

    raise ValueError(f"unrecognised rubric kind: {rubric_kind!r}")


def headline_score(
    item_scores: Sequence[Sequence[JudgeScore | None]],
    contested_flags: Sequence[bool],
) -> Headline:
    """Average each non-contested item's judge scores, and say what was left out.

    An item is excluded when it is contested, or when no judge left a numeric
    score on it -- a categorical rubric therefore has no headline mean, which
    is the honest answer for labels that were never a quantity. `score` is
    `None` when nothing survives inclusion, never `0.0`.
    """
    if len(item_scores) != len(contested_flags):
        raise ValueError(
            f"headline_score needs one contested flag per item: got "
            f"{len(item_scores)} items and {len(contested_flags)} flags"
        )

    means: list[float] = []
    n_excluded = 0
    for scores, contested in zip(item_scores, contested_flags, strict=True):
        usable = [
            score
            for score in scores
            if isinstance(score, int) and not isinstance(score, bool)
        ]
        if contested or not usable:
            n_excluded += 1
            continue
        means.append(sum(usable) / len(usable))

    if not means:
        return Headline(score=None, n_included=0, n_excluded=n_excluded)
    return Headline(
        score=sum(means) / len(means),
        n_included=len(means),
        n_excluded=n_excluded,
    )
