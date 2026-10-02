"""Paired comparison of two published configurations on the same items.

A claim that one configuration beats another is published here as a
comparison record, never computed at read time: `main` reads the published
quality rows, selects a reference side and a candidate side, and writes one
immutable family record (`aidd_docs/results/comparisons/`) holding either a
paired test or a refusal naming why the two sides cannot be compared (PRD
Methodology 24).

The test is chosen by the rows' scoring kind, never by the caller: a binary
exact-match score (`correct`) gets McNemar's exact test over the discordant
pairs, a graded score (`item_score`) gets the Wilcoxon signed-rank test over
the per-item differences. Every difference is candidate minus reference.

Everything runs on the standard library. scipy is a dev-only oracle the tests
compare against, never an import here.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from fractions import Fraction
from pathlib import Path
from statistics import NormalDist
from typing import Any

from wave_local_ai_v2 import settings

RECORD_TYPE = "comparison_family"
RECORD_VERSION = "1"
DEFAULT_ALPHA = 0.05
COMPARISONS_DIR = Path("aidd_docs/results/comparisons")

SCORING_KIND_BINARY = "binary"
SCORING_KIND_GRADED = "graded"

# The per-item value each scoring kind is compared on, on `verdict.py`'s
# `compared_field` meaning.
COMPARED_FIELD_BY_SCORING_KIND: dict[str, str] = {
    SCORING_KIND_BINARY: "correct",
    SCORING_KIND_GRADED: "item_score",
}

TEST_MCNEMAR = "mcnemar_exact"
TEST_WILCOXON = "wilcoxon_signed_rank"

# The one place a test is chosen: by scoring kind, never per call site.
TEST_BY_SCORING_KIND: dict[str, str] = {
    SCORING_KIND_BINARY: TEST_MCNEMAR,
    SCORING_KIND_GRADED: TEST_WILCOXON,
}

TEST_CHOSEN_BECAUSE: dict[str, str] = {
    TEST_MCNEMAR: (
        "the score is binary (exact match): every non-zero paired difference "
        "is +1 or -1, so the information is in the discordant pairs, and "
        "McNemar's exact test is the two-sided binomial over them"
    ),
    TEST_WILCOXON: (
        "the score is graded: per-item differences carry magnitude, so the "
        "Wilcoxon signed-rank test ranks them"
    ),
}

# Named null reasons: a statistic that is undefined publishes one of these in
# place of a number, on `agreement.py`'s value-plus-one-reason shape.
NULL_PAIRED_N_BELOW_MINIMUM = "paired_n_below_minimum"
NULL_NO_DISCORDANT_PAIRS = "no_discordant_pairs"
NULL_ODDS_RATIO_EMPTY_CELL = "odds_ratio_empty_cell"
NULL_ALL_DIFFERENCES_ZERO = "all_differences_zero"

# Both tests' own minimum: one paired item. Below it nothing is compared.
MIN_PAIRED_N = 1

WILCOXON_ZERO_METHOD = "pratt"
WILCOXON_EXACT_MAX_NONZERO = 50
WILCOXON_CONTINUITY_CORRECTION = False

VERDICT_DISTINGUISHABLE = "distinguishable"
VERDICT_NOT_DISTINGUISHABLE = "not distinguishable"
VERDICT_NOT_COMPARABLE = "not comparable"
VERDICT_RULE = (
    "distinguishable when adjusted_p_value <= alpha; not distinguishable "
    "otherwise, including a p left null because the sides never disagree; "
    "not comparable for a refusal, an observation (the sides differ outside "
    "the compared dimension or not on it, so no difference is attributable "
    "to it; its p stays in result) or a paired n below the test's minimum"
)

DIRECTION_CANDIDATE_HIGHER = "candidate_higher"
DIRECTION_REFERENCE_HIGHER = "reference_higher"
DIRECTION_NONE = "no_difference"

KIND_TEST = "test"
KIND_OBSERVATION = "observation"
KIND_REFUSAL = "refusal"

REFUSAL_DIFFERS = "differs"
REFUSAL_ABSENT = "absent"
REFUSAL_VARIES_WITHIN_SIDE = "varies_within_side"

# Refused when null or missing on either side, even on both: two unknown
# values never count as a match (Methodology 8, owner answer Q4 (a)). The
# suite identity of Methodology 2 and the four generation constraints of
# Methodology 3.
_ABSENCE_REFUSAL_FIELDS = (
    "suite_id",
    "suite_version",
    "prompt_set_hash",
    "max_output_tokens",
    "stop_sequences",
    "context_length",
    "thinking_policy",
)
# The metric identity, held to the same rule when either side is graded.
_METRIC_REFUSAL_FIELDS = ("metric_id", "metric_version", "metric_params")
# Refused only when the two sides declare different values: two rows that
# predate the level both declare none, which is not two different levels.
_VALUE_REFUSAL_FIELDS = ("suite_level",)

# Row fields that never describe a configuration, so never enter the
# differing-field set: bookkeeping, per-item content, and outcomes or
# measurements a configuration produces rather than is.
EXCLUDED_FROM_DIFFERING: frozenset[str] = frozenset(
    {
        # bookkeeping
        "schema_version",
        "run_id",
        "captured_at",
        "release_version",
        "commit_sha",
        "tree_dirty",
        "retries",
        "resumed",
        "verdict",
        # per item
        "item_id",
        "prompt",
        "prompt_before_template",
        "expected_label",
        "predicted_label",
        "correct",
        "item_score",
        "subject_output",
        "reference_output",
        "language",
        "failure_reason",
        "provenance",
        "contamination_risk",
        "item_licence",
        "item_source",
        "item_source_revision",
        # outcomes
        "suite_accuracy",
        "language_breakdown",
        "suite_score",
        "score_breakdown",
        "failure_counts",
        "judges",
        "agreement",
        "agreement_statistic",
        "single_judge",
        "single_judge_reason",
        "contested",
        "contested_reason",
        "judged_headline_score",
        "judged_headline_excluded_n",
        "judge_egress",
        "judge_cost",
        # measurements: energy, emissions, cost
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
    }
)


@dataclass(frozen=True)
class Dimension:
    """One configuration axis a family compares along.

    `fields` are the row fields that belong to the axis; `key_fields` are the
    ones that must differ for the two sides to sit on two points of it.
    """

    fields: frozenset[str]
    key_fields: tuple[str, ...]


DIMENSIONS: dict[str, Dimension] = {
    # A subject's call path and sampling parameters are recorded per provider
    # (Methodology 1 and 2), so a local and a cloud subject differ on all of
    # them by construction. `fiche_hash` names the model and the machine
    # together; a machine change it alone carries is not separable here.
    "model": Dimension(
        fields=frozenset(
            {
                "model_id",
                "provider",
                "roster_entry_id",
                "roster_version",
                "endpoint",
                "prompt_template_id",
                "prompt_template_hash",
                "prompt_capture",
                "sampling",
                "fiche_hash",
            }
        ),
        key_fields=("model_id",),
    ),
    "prompt_variant": Dimension(
        fields=frozenset({"prompt_variant_id", "prompt_variant_version"}),
        key_fields=("prompt_variant_id", "prompt_variant_version"),
    ),
}
DEFAULT_DIMENSION = "model"


class ComparisonInputError(ValueError):
    """The inputs cannot produce any record: an empty side, a duplicate item."""


# --------------------------------------------------------------------------
# The two tests


def _direction(delta: float) -> str:
    if delta > 0:
        return DIRECTION_CANDIDATE_HIGHER
    if delta < 0:
        return DIRECTION_REFERENCE_HIGHER
    return DIRECTION_NONE


def _tie_count(differences: Sequence[float]) -> int:
    """Non-zero pairs whose absolute difference another non-zero pair shares."""
    magnitudes = [abs(d) for d in differences if d != 0]
    return sum(1 for m in magnitudes if magnitudes.count(m) > 1)


def mcnemar_exact(pairs: Sequence[tuple[bool, bool]]) -> dict[str, Any]:
    """McNemar's exact test over `(reference_correct, candidate_correct)` pairs.

    Two-sided binomial over the discordant pairs at 0.5, computed exactly in
    integers: `p = min(1, 2 * sum_{k <= min(b, c)} C(b + c, k) / 2^(b + c))`.
    """
    n = len(pairs)
    reference_only = sum(1 for r, c in pairs if r and not c)
    candidate_only = sum(1 for r, c in pairs if c and not r)
    both_correct = sum(1 for r, c in pairs if r and c)
    both_wrong = n - reference_only - candidate_only - both_correct
    discordant = reference_only + candidate_only
    differences = [float(int(c) - int(r)) for r, c in pairs]
    result: dict[str, Any] = {
        "test": TEST_MCNEMAR,
        "contingency": {
            "both_correct": both_correct,
            "reference_only_correct": reference_only,
            "candidate_only_correct": candidate_only,
            "both_wrong": both_wrong,
        },
        "discordant_n": discordant,
        "statistic_name": (
            "min(b, c): the smaller of the two discordant counts "
            "(b = reference only correct, c = candidate only correct)"
        ),
        "effect_size_name": "discordant_pair_odds_ratio",
        "effect_size_formula": (
            "c / b: pairs only the candidate got right over pairs only the "
            "reference got right; above 1 favours the candidate"
        ),
        "tie_count": _tie_count(differences),
        "zero_difference_count": both_correct + both_wrong,
    }
    if n < MIN_PAIRED_N:
        return {
            **result,
            "statistic": None,
            "p_value": None,
            "p_value_null_reason": NULL_PAIRED_N_BELOW_MINIMUM,
            "effect_size": None,
            "effect_size_null_reason": NULL_PAIRED_N_BELOW_MINIMUM,
            "direction": None,
            "mean_difference": None,
        }
    smaller = min(reference_only, candidate_only)
    if discordant == 0:
        p_value: float | None = None
        p_reason: str | None = NULL_NO_DISCORDANT_PAIRS
    else:
        tail = sum(math.comb(discordant, k) for k in range(smaller + 1))
        p_value = float(min(Fraction(1), Fraction(2 * tail, 2**discordant)))
        p_reason = None
    if reference_only == 0 or candidate_only == 0:
        effect: float | None = None
        effect_reason: str | None = NULL_ODDS_RATIO_EMPTY_CELL
    else:
        effect = candidate_only / reference_only
        effect_reason = None
    return {
        **result,
        "statistic": smaller,
        "p_value": p_value,
        "p_value_null_reason": p_reason,
        "effect_size": effect,
        "effect_size_null_reason": effect_reason,
        "direction": _direction(candidate_only - reference_only),
        "mean_difference": (candidate_only - reference_only) / n,
    }


def _average_ranks(values: Sequence[float]) -> list[float]:
    """1-based ranks of `values` ascending, ties given their average rank."""
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(order):
        end = start
        while end + 1 < len(order) and values[order[end + 1]] == values[order[start]]:
            end += 1
        average = (start + end) / 2 + 1
        for position in range(start, end + 1):
            ranks[order[position]] = average
        start = end + 1
    return ranks


def _exact_sign_flip_p(nonzero_ranks: Sequence[float], w_plus: float) -> float:
    """Two-sided p from every sign assignment over the observed ranks.

    Average ranks are multiples of one half, so doubling them makes every
    sum an integer and the count table exact.
    """
    doubled = [round(2 * rank) for rank in nonzero_ranks]
    counts = [1] + [0] * sum(doubled)
    reach = 0
    for step in doubled:
        reach += step
        for total in range(reach, step - 1, -1):
            counts[total] += counts[total - step]
    observed = round(2 * w_plus)
    lower = sum(counts[: observed + 1])
    upper = sum(counts[observed:])
    two_sided = Fraction(2 * min(lower, upper), 2 ** len(doubled))
    return float(min(Fraction(1), two_sided))


def _normal_approximation_p(
    n: int, zero_count: int, nonzero_magnitudes: Sequence[float], w_plus: float
) -> float:
    """Two-sided p under the normal approximation, Pratt-adjusted.

    Cureton's zero adjustment to the mean and variance, the tie correction
    over the non-zero magnitudes, no continuity correction.
    """
    mean = (n * (n + 1) - zero_count * (zero_count + 1)) / 4
    variance_24 = float(
        n * (n + 1) * (2 * n + 1) - zero_count * (zero_count + 1) * (2 * zero_count + 1)
    )
    groups: dict[float, int] = {}
    for magnitude in nonzero_magnitudes:
        groups[magnitude] = groups.get(magnitude, 0) + 1
    variance_24 -= sum(t**3 - t for t in groups.values()) / 2
    z = (w_plus - mean) / math.sqrt(variance_24 / 24)
    return min(1.0, 2 * NormalDist().cdf(-abs(z)))


def wilcoxon_signed_rank(differences: Sequence[float]) -> dict[str, Any]:
    """Wilcoxon signed-rank test over candidate-minus-reference differences.

    Pratt's zero method: every difference, zeros included, is ranked by
    magnitude, and the zeros' ranks are then left out of both sums, so an
    item both sides failed stays in the ranking rather than being dropped.
    """
    n = len(differences)
    result: dict[str, Any] = {
        "test": TEST_WILCOXON,
        "conventions": {
            "zero_method": WILCOXON_ZERO_METHOD,
            "zero_method_definition": (
                "zero differences are ranked with the others, then their "
                "ranks are excluded from W+ and W-"
            ),
            "exact_rule": (
                "exact two-sided p from all 2^m sign assignments over the "
                "observed tie-averaged ranks when the non-zero count m is at "
                "most the threshold; normal approximation above it, with "
                "Cureton's zero adjustment and the tie correction"
            ),
            "exact_max_nonzero": WILCOXON_EXACT_MAX_NONZERO,
            "continuity_correction": WILCOXON_CONTINUITY_CORRECTION,
            "tie_handling": "average ranks",
        },
        "statistic_name": "W+: the sum of the ranks of positive differences",
        "effect_size_name": "rank_biserial",
        "effect_size_formula": (
            "(W+ - W-) / (W+ + W-), over the ranks of the non-zero differences"
        ),
        "zero_difference_count": sum(1 for d in differences if d == 0),
        "tie_count": _tie_count(differences),
    }
    if n < MIN_PAIRED_N:
        return {
            **result,
            "statistic": None,
            "w_minus": None,
            "p_value": None,
            "p_value_null_reason": NULL_PAIRED_N_BELOW_MINIMUM,
            "p_value_method": None,
            "effect_size": None,
            "effect_size_null_reason": NULL_PAIRED_N_BELOW_MINIMUM,
            "direction": None,
            "mean_difference": None,
        }
    ranks = _average_ranks([abs(d) for d in differences])
    w_plus = sum(r for r, d in zip(ranks, differences, strict=True) if d > 0)
    w_minus = sum(r for r, d in zip(ranks, differences, strict=True) if d < 0)
    nonzero_ranks = [r for r, d in zip(ranks, differences, strict=True) if d != 0]
    zero_count = n - len(nonzero_ranks)
    common = {
        **result,
        "statistic": w_plus,
        "w_minus": w_minus,
        "direction": _direction(w_plus - w_minus),
        "mean_difference": sum(differences) / n,
    }
    if not nonzero_ranks:
        return {
            **common,
            "p_value": None,
            "p_value_null_reason": NULL_ALL_DIFFERENCES_ZERO,
            "p_value_method": None,
            "effect_size": None,
            "effect_size_null_reason": NULL_ALL_DIFFERENCES_ZERO,
        }
    if len(nonzero_ranks) <= WILCOXON_EXACT_MAX_NONZERO:
        p_value = _exact_sign_flip_p(nonzero_ranks, w_plus)
        method = "exact_sign_flip"
    else:
        magnitudes = [abs(d) for d in differences if d != 0]
        p_value = _normal_approximation_p(n, zero_count, magnitudes, w_plus)
        method = "normal_approximation"
    return {
        **common,
        "p_value": p_value,
        "p_value_null_reason": None,
        "p_value_method": method,
        "effect_size": (w_plus - w_minus) / (w_plus + w_minus),
        "effect_size_null_reason": None,
    }


# --------------------------------------------------------------------------
# Sides, refusals and the record


@dataclass(frozen=True)
class Side:
    """A run id plus the further row fields that select a side within it."""

    run_id: str
    selector: Mapping[str, str] = field(default_factory=dict)


def _as_text(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, sort_keys=True)


def select_side(rows: Sequence[Mapping[str, Any]], side: Side) -> list[dict[str, Any]]:
    """The rows of `side`: its run id, and every selector field matching as text."""
    return [
        dict(row)
        for row in rows
        if row.get("run_id") == side.run_id
        and all(
            key in row and _as_text(row[key]) == value
            for key, value in side.selector.items()
        )
    ]


def scoring_kind(row: Mapping[str, Any]) -> str | None:
    """The row's scoring kind from its shape, or `None` when it has none.

    The graded block's presence is the discriminator (`row_contract`): a row
    carrying it is graded; a row whose `correct` is a boolean is binary.
    """
    if "metric_id" in row:
        return SCORING_KIND_GRADED
    if isinstance(row.get("correct"), bool):
        return SCORING_KIND_BINARY
    return None


_ABSENT = object()


def _side_values(rows: Sequence[Mapping[str, Any]], key: str) -> set[str]:
    """Each distinct value `key` takes on a side, canonical JSON, `<absent>` if missing."""
    return {
        json.dumps(row[key], sort_keys=True) if key in row else "<absent>"
        for row in rows
    }


def _single_value(rows: Sequence[Mapping[str, Any]], key: str) -> Any:
    """The one value `key` takes across `rows`, `_ABSENT` if missing or mixed."""
    values = _side_values(rows, key)
    if len(values) != 1 or values == {"<absent>"}:
        return _ABSENT
    return rows[0][key]


def _shown(value: Any) -> Any:
    return None if value is _ABSENT else value


def _derived_values(rows: Sequence[Mapping[str, Any]]) -> dict[str, set[str]]:
    kinds = {scoring_kind(row) for row in rows}
    fields = {
        COMPARED_FIELD_BY_SCORING_KIND.get(kind) if kind else None for kind in kinds
    }
    return {
        "scoring_kind": {json.dumps(kind) for kind in kinds},
        "compared_field": {json.dumps(name) for name in fields},
    }


def refusals(
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Every field that makes the two sides incomparable, in declaration order."""
    found: list[dict[str, Any]] = []

    def refuse(key: str, reason: str, reference: Any, candidate: Any) -> None:
        found.append(
            {
                "field": key,
                "reason": reason,
                "reference_value": _shown(reference),
                "candidate_value": _shown(candidate),
            }
        )

    def check(key: str, *, absence_refuses: bool) -> None:
        ref_values = _side_values(reference_rows, key)
        cand_values = _side_values(candidate_rows, key)
        reference = _single_value(reference_rows, key)
        candidate = _single_value(candidate_rows, key)
        if len(ref_values) > 1 or len(cand_values) > 1:
            refuse(key, REFUSAL_VARIES_WITHIN_SIDE, reference, candidate)
        elif absence_refuses and (
            reference is _ABSENT
            or candidate is _ABSENT
            or reference is None
            or candidate is None
        ):
            refuse(key, REFUSAL_ABSENT, reference, candidate)
        elif ref_values != cand_values:
            refuse(key, REFUSAL_DIFFERS, reference, candidate)

    for key in _ABSENCE_REFUSAL_FIELDS:
        check(key, absence_refuses=True)
    for key in _VALUE_REFUSAL_FIELDS:
        check(key, absence_refuses=False)
    kinds = {scoring_kind(row) for row in [*reference_rows, *candidate_rows]}
    if SCORING_KIND_GRADED in kinds:
        for key in _METRIC_REFUSAL_FIELDS:
            check(key, absence_refuses=True)

    reference_derived = _derived_values(reference_rows)
    candidate_derived = _derived_values(candidate_rows)
    for key in ("scoring_kind", "compared_field"):
        ref_values = reference_derived[key]
        cand_values = candidate_derived[key]
        reference = json.loads(next(iter(ref_values))) if len(ref_values) == 1 else None
        candidate = (
            json.loads(next(iter(cand_values))) if len(cand_values) == 1 else None
        )
        if len(ref_values) > 1 or len(cand_values) > 1:
            refuse(key, REFUSAL_VARIES_WITHIN_SIDE, reference, candidate)
        elif reference is None or candidate is None:
            refuse(key, REFUSAL_ABSENT, reference, candidate)
        elif reference != candidate:
            refuse(key, REFUSAL_DIFFERS, reference, candidate)
    return found


def differing_fields(
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    """The configuration fields on which the two sides differ, computed from rows.

    Every row field outside `EXCLUDED_FROM_DIFFERING` is compared as the set
    of values each side carries, so a field the contract does not hold yet
    (`compute_mode`) still surfaces. Sorted, on `verdict.py`'s
    `differing_fields` shape.
    """
    keys = {key for row in [*reference_rows, *candidate_rows] for key in row}
    return sorted(
        key
        for key in keys - EXCLUDED_FROM_DIFFERING
        if _side_values(reference_rows, key) != _side_values(candidate_rows, key)
    )


def _per_item_values(
    rows: Sequence[Mapping[str, Any]], compared: str
) -> dict[str, Any]:
    """`item_id` to the compared value; a null value is an unobserved item."""
    seen: set[str] = set()
    values: dict[str, Any] = {}
    for row in rows:
        item_id = str(row.get("item_id"))
        if item_id in seen:
            raise ComparisonInputError(
                f"item_id {item_id!r} appears twice on one side: a side must be "
                "one batch; narrow it with a selector field"
            )
        seen.add(item_id)
        if row.get(compared) is not None:
            values[item_id] = row[compared]
    return values


def _comparison_kind(
    differing: Sequence[str], dimension: Dimension
) -> tuple[str, list[str], str | None]:
    confounds = sorted(key for key in differing if key not in dimension.fields)
    if not any(key in differing for key in dimension.key_fields):
        return (
            KIND_OBSERVATION,
            confounds,
            "the sides do not differ on the compared dimension's key field(s) "
            + ", ".join(dimension.key_fields),
        )
    if confounds:
        return (
            KIND_OBSERVATION,
            confounds,
            (
                "the sides differ outside the compared dimension, so a "
                "difference cannot be attributed to it"
            ),
        )
    return KIND_TEST, confounds, None


def _verdict(kind: str, result: Mapping[str, Any], alpha: float) -> str:
    """The reader-facing verdict of a member that was not refused.

    An observation reads `not comparable`: a reader of the verdict alone must
    never take a confounded pair for a finding. Its p stays in `result`, where
    a significant one reads as the bug signal it is.
    """
    if kind == KIND_OBSERVATION:
        return VERDICT_NOT_COMPARABLE
    if result["p_value_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM:
        return VERDICT_NOT_COMPARABLE
    p_value = result["p_value"]
    if p_value is not None and p_value <= alpha:
        return VERDICT_DISTINGUISHABLE
    return VERDICT_NOT_DISTINGUISHABLE


def compare_sides(
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    reference: Side,
    candidate: Side,
    *,
    dimension: str = DEFAULT_DIMENSION,
    alpha: float = DEFAULT_ALPHA,
) -> dict[str, Any]:
    """One comparison member: a paired test, an observation, or a refusal."""
    if not reference_rows:
        raise ComparisonInputError(f"no row selects the reference side {reference}")
    if not candidate_rows:
        raise ComparisonInputError(f"no row selects the candidate side {candidate}")
    axis = DIMENSIONS[dimension]
    refused = refusals(reference_rows, candidate_rows)
    differing = differing_fields(reference_rows, candidate_rows)
    kinds = {scoring_kind(row) for row in [*reference_rows, *candidate_rows]}
    kind = next(iter(kinds)) if len(kinds) == 1 else None

    def shared(key: str) -> Any:
        reference_value = _single_value(reference_rows, key)
        if reference_value is _ABSENT:
            return None
        if _single_value(candidate_rows, key) != reference_value:
            return None
        return reference_value

    member: dict[str, Any] = {
        "reference_run_id": reference.run_id,
        "reference_selector": dict(reference.selector),
        "reference_row_count": len(reference_rows),
        "candidate_run_id": candidate.run_id,
        "candidate_selector": dict(candidate.selector),
        "candidate_row_count": len(candidate_rows),
        "suite_id": shared("suite_id"),
        "suite_version": shared("suite_version"),
        "suite_level": shared("suite_level"),
        "compared_dimension": dimension,
        # Named whenever both sides agree on it, a refusal included.
        "scoring_kind": kind,
        "compared_field": COMPARED_FIELD_BY_SCORING_KIND.get(kind) if kind else None,
        "refusal": refused,
        "differing_fields": differing,
        "difference_convention": "candidate minus reference",
    }
    if refused:
        return {
            **member,
            "comparison_kind": KIND_REFUSAL,
            "confounds": [],
            "observation_reason": None,
            "paired_item_ids": None,
            "paired_n": None,
            "paired_values": None,
            "unpaired_items": None,
            "unpaired_count": None,
            "test": None,
            "test_chosen_because": None,
            "result": None,
            "adjusted_p_value": None,
            "adjusted_p_value_null_reason": None,
            "verdict": VERDICT_NOT_COMPARABLE,
        }

    assert kind is not None  # a missing scoring kind is a refusal above
    compared = COMPARED_FIELD_BY_SCORING_KIND[kind]
    reference_values = _per_item_values(reference_rows, compared)
    candidate_values = _per_item_values(candidate_rows, compared)
    paired_ids = sorted(reference_values.keys() & candidate_values.keys())
    unpaired = sorted(
        [
            {"item_id": item_id, "missing_from": "candidate"}
            for item_id in reference_values.keys() - candidate_values.keys()
        ]
        + [
            {"item_id": item_id, "missing_from": "reference"}
            for item_id in candidate_values.keys() - reference_values.keys()
        ],
        key=lambda entry: entry["item_id"],
    )
    test = TEST_BY_SCORING_KIND[kind]
    if test == TEST_MCNEMAR:
        result = mcnemar_exact(
            [(reference_values[i], candidate_values[i]) for i in paired_ids]
        )
    else:
        result = wilcoxon_signed_rank(
            [candidate_values[i] - reference_values[i] for i in paired_ids]
        )
    comparison_kind, confounds, observation_reason = _comparison_kind(differing, axis)
    return {
        **member,
        "comparison_kind": comparison_kind,
        "confounds": confounds,
        "observation_reason": observation_reason,
        "paired_item_ids": paired_ids,
        "paired_n": len(paired_ids),
        "paired_values": [
            {
                "item_id": item_id,
                "reference": reference_values[item_id],
                "candidate": candidate_values[item_id],
            }
            for item_id in paired_ids
        ],
        "unpaired_items": unpaired,
        "unpaired_count": len(unpaired),
        "test": test,
        "test_chosen_because": TEST_CHOSEN_BECAUSE[test],
        "result": result,
        # A family of one: Holm's adjusted p is the raw p.
        "adjusted_p_value": result["p_value"],
        "adjusted_p_value_null_reason": result["p_value_null_reason"],
        "verdict": _verdict(comparison_kind, result, alpha),
    }


def _canonical(record: Mapping[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def build_family_record(
    member: Mapping[str, Any], *, alpha: float, rows_source: str
) -> dict[str, Any]:
    """Wrap one comparison as a family of one, identified by its own content."""
    record: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "family_definition": {
            "suite_id": member["suite_id"],
            "suite_version": member["suite_version"],
            "compared_dimension": member["compared_dimension"],
        },
        "family_size": 1,
        "alpha": alpha,
        "multiplicity_correction": {
            "method": "holm",
            "note": "a family of one: each adjusted p equals its raw p",
        },
        "verdict_rule": VERDICT_RULE,
        "rows_source": rows_source,
        "members": [dict(member)],
    }
    record["family_id"] = hashlib.sha256(_canonical(record).encode()).hexdigest()
    return record


def record_text(record: Mapping[str, Any]) -> str:
    """The exact text a family record file holds."""
    return _canonical(record)


def default_output_path(record: Mapping[str, Any]) -> Path:
    definition = record["family_definition"]
    suite = (
        f"{definition['suite_id']}@{definition['suite_version']}"
        if definition["suite_id"] is not None
        else "mixed-suites"
    )
    name = f"{suite}.{definition['compared_dimension']}.{record['family_id'][:12]}.json"
    return COMPARISONS_DIR / name


# --------------------------------------------------------------------------
# The analysis command


def rows_source_name(path: Path) -> str:
    """One spelling per rows file, so one file never yields two family ids.

    Relative to the working directory (the repository root the defaults
    assume) when the file lies under it, else the resolved absolute path;
    POSIX separators either way.
    """
    resolved = path.resolve()
    try:
        return resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return resolved.as_posix()


def _parse_selector(entries: Sequence[str]) -> dict[str, str]:
    selector: dict[str, str] = {}
    for entry in entries:
        key, sep, value = entry.partition("=")
        if not sep or not key:
            raise ComparisonInputError(
                f"selector {entry!r} is not field=value (for example model_id=X)"
            )
        selector[key] = value
    return selector


def _read_rows(path: Path) -> list[dict[str, Any]]:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise ComparisonInputError(f"cannot read rows from {path}: {error}") from error
    try:
        return [json.loads(line) for line in lines if line.strip()]
    except json.JSONDecodeError as error:
        raise ComparisonInputError(f"{path} is not JSON lines: {error}") from error


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-compare",
        description=(
            "Compare two published configurations on the same items: write a "
            "family record holding a paired test or a refusal."
        ),
    )
    parser.add_argument(
        "--rows",
        default=settings.DEFAULT_QUALITY_REFERENCE_PATH,
        help="published quality rows (default: the reference bundle)",
    )
    parser.add_argument("--reference", required=True, help="reference run_id")
    parser.add_argument("--candidate", required=True, help="candidate run_id")
    parser.add_argument(
        "--reference-where",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="row field selecting the reference side within its run (repeatable)",
    )
    parser.add_argument(
        "--candidate-where",
        action="append",
        default=[],
        metavar="FIELD=VALUE",
        help="row field selecting the candidate side within its run (repeatable)",
    )
    parser.add_argument(
        "--dimension", choices=sorted(DIMENSIONS), default=DEFAULT_DIMENSION
    )
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument(
        "--output",
        default=None,
        help="record path (default: aidd_docs/results/comparisons/<name>.json)",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Run one comparison and write its family record, write-once.

    Exits 0 when the record is written or already published byte for byte
    (a refusal is a published record, not an error), 1 on unusable input or
    an existing file with different content.
    """
    args = _parser().parse_args(argv)
    try:
        if not 0 < args.alpha < 1:
            raise ComparisonInputError(f"--alpha {args.alpha} is not in (0, 1)")
        reference = Side(args.reference, _parse_selector(args.reference_where))
        candidate = Side(args.candidate, _parse_selector(args.candidate_where))
        rows_path = Path(args.rows)
        rows = _read_rows(rows_path)
        member = compare_sides(
            select_side(rows, reference),
            select_side(rows, candidate),
            reference,
            candidate,
            dimension=args.dimension,
            alpha=args.alpha,
        )
    except ComparisonInputError as error:
        print(str(error), file=sys.stderr)
        return 1
    record = build_family_record(
        member, alpha=args.alpha, rows_source=rows_source_name(rows_path)
    )
    text = record_text(record)
    out_path = Path(args.output) if args.output else default_output_path(record)
    if out_path.exists():
        if out_path.read_text(encoding="utf-8") != text:
            print(
                f"{out_path} is already published with different content: a "
                "family record is immutable; write a new one",
                file=sys.stderr,
            )
            return 1
        status = "unchanged"
    else:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8", newline="\n")
        status = "written"
    refused = ", ".join(
        f"{entry['field']} ({entry['reason']})" for entry in member["refusal"]
    )
    print(
        f"{out_path} {status}: {member['comparison_kind']}, verdict "
        f"{member['verdict']}" + (f"; refused on {refused}" if refused else "")
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
