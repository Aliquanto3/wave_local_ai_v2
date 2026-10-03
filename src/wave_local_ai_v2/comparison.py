"""Paired comparison of two published configurations on the same items.

A claim that one configuration beats another is published here as a
comparison record, never computed at read time: `main` reads the published
quality rows, runs every declared comparison (a reference side against a
candidate side) and writes one immutable family record
(`aidd_docs/results/comparisons/`) holding each one as a paired test or a
refusal naming why its two sides cannot be compared, with Holm-adjusted
p-values over that closed family (PRD Methodology 24). A family that grows is
a new record superseding the old one by id; no published record is rewritten.
`--leader-sets` runs the leader-set derivation (`leader_set.py`) instead of
a declared family.

The test is chosen by the rows' scoring kind, never by the caller: a binary
exact-match score (`correct`) gets McNemar's exact test over the discordant
pairs, a graded score (`item_score`) gets the Wilcoxon signed-rank test over
the per-item differences. Every difference is candidate minus reference.

The compared quantity is the score by default. A per-item measurement --
the item's own tokens in or out, or its engine-reported first-token time
(schema "18") -- is a continuous quantity and gets the Wilcoxon signed-rank
test over the same item ids. Energy is measured per batch, never per item, so
an energy difference is published as an observation that says why it carries
no paired test (owner decision Q24 (a)).

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

from wave_local_ai_v2 import field_doc, harness, row_contract, settings
from wave_local_ai_v2.field_doc import FieldDoc

RECORD_TYPE = "comparison_family"
RECORD_VERSION = "2"
DEFAULT_ALPHA = 0.05
COMPARISONS_DIR = Path(settings.DEFAULT_COMPARISONS_DIR)

SCORING_KIND_BINARY = "binary"
SCORING_KIND_GRADED = "graded"
# A per-item measurement rather than a score: tokens, or a first-token time.
SCORING_KIND_CONTINUOUS = "continuous_measurement"
# A per-batch measurement: one value per side, no per-item pairing at all.
SCORING_KIND_BATCH = "batch_measurement"

# What a comparison compares. `score` is the rows' own score, its field
# chosen by their scoring kind; the rest name the row field itself.
QUANTITY_SCORE = "score"
MEASUREMENT_QUANTITIES: tuple[str, ...] = (
    "item_tokens_in",
    "item_tokens_out",
    "item_ttft_ms",
)
QUANTITY_ENERGY = "energy_kwh"
QUANTITIES: tuple[str, ...] = (QUANTITY_SCORE, *MEASUREMENT_QUANTITIES, QUANTITY_ENERGY)

# The row labels a per-item measurement is only one quantity under: two sides
# whose non-null labels differ measured two different things.
MEASUREMENT_LABEL_FIELDS: dict[str, tuple[str, ...]] = {
    "item_tokens_in": ("item_measurement_kind",),
    "item_tokens_out": ("item_measurement_kind",),
    "item_ttft_ms": ("item_measurement_kind", "item_ttft_source"),
}

ENERGY_NO_PAIRED_TEST_REASON = (
    "energy is measured per batch, never per item: per-item energy on items "
    "of a few dozen tokens sits below what the tracker can resolve, so there "
    "is no per-item value to pair and a per-batch energy difference is "
    "published as an observation (owner decision Q24 (a))"
)

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
    SCORING_KIND_CONTINUOUS: TEST_WILCOXON,
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

# Why the test fits, per scoring kind: one test can serve two kinds for two
# different reasons.
CHOSEN_BECAUSE_BY_SCORING_KIND: dict[str, str] = {
    SCORING_KIND_BINARY: TEST_CHOSEN_BECAUSE[TEST_MCNEMAR],
    SCORING_KIND_GRADED: TEST_CHOSEN_BECAUSE[TEST_WILCOXON],
    SCORING_KIND_CONTINUOUS: (
        "the compared quantity is a continuous per-item measurement (tokens or "
        "an engine-reported first-token time): per-item differences carry "
        "magnitude and no normality is assumed, so the Wilcoxon signed-rank "
        "test ranks them"
    ),
}

# Named null reasons: a statistic that is undefined publishes one of these in
# place of a number, on `agreement.py`'s value-plus-one-reason shape.
NULL_PAIRED_N_BELOW_MINIMUM = "paired_n_below_minimum"
NULL_NO_DISCORDANT_PAIRS = "no_discordant_pairs"
NULL_ODDS_RATIO_EMPTY_CELL = "odds_ratio_empty_cell"
NULL_ALL_DIFFERENCES_ZERO = "all_differences_zero"
# A refused member carries no p-value, so none is adjusted.
NULL_COMPARISON_REFUSED = "comparison_refused"
# A per-batch quantity has nothing to pair, so no test ran.
NULL_NO_PAIRED_TEST = "no_paired_test"
# A side whose rows repeat no single per-batch value has no batch value.
NULL_NO_SINGLE_BATCH_VALUE = "no_single_batch_value_on_a_side"

# Both tests' own minimum: one paired item. Below it nothing is compared.
MIN_PAIRED_N = 1

WILCOXON_ZERO_METHOD = "pratt"
WILCOXON_EXACT_MAX_NONZERO = 50
WILCOXON_CONTINUITY_CORRECTION = False

VERDICT_DISTINGUISHABLE = "distinguishable"
VERDICT_NOT_DISTINGUISHABLE = "not distinguishable"
VERDICT_NOT_COMPARABLE = "not comparable"
VERDICT_RULE = (
    "distinguishable when the Holm-adjusted p over the family "
    "(adjusted_p_value) <= alpha; not distinguishable "
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
        "retry_budget",
        "partial_failure",
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
        # measurements: the item's own generation figures (schema "18")
        "item_tokens_in",
        "item_tokens_in_null_reason",
        "item_tokens_out",
        "item_tokens_out_null_reason",
        "item_ttft_ms",
        "item_ttft_ms_null_reason",
        "item_ttft_source",
        "item_prompt_tokens_cached",
        "item_prompt_tokens_cached_null_reason",
        "item_measurement_kind",
        "item_first_in_batch",
        # a measurement: the tokens the harness added around the item's own
        # prompt (schema "20"). The harness id and version are configuration
        # and stay compared.
        "harness_prompt_overhead",
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
                # A function of `provider` (`row_contract.subject_egress_for`),
                # so it moves with the model axis and is never a confound.
                "subject_egress",
                # The subject's family and size class (schema "19"): properties
                # of the model, so they move with the model axis too.
                "family",
                "size_class",
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

# The engine that produced a row and its build (schema "22"), and the
# declared machine and compute mode it ran under (schema "23"). Along `model`
# they move with the axis only where they differ by construction: one side's
# subject was served by a local engine and the other's by a cloud provider,
# whose rows state that none of the four applies. Between two locally served
# sides a different engine, build, machine or mode is a confound, not part of
# what a model comparison compares.
ENGINE_FIELDS: frozenset[str] = frozenset(
    {"engine_id", "engine_build", "machine_id", "compute_mode"}
)


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
    *,
    quantity: str = QUANTITY_SCORE,
) -> list[dict[str, Any]]:
    """Every field that makes the two sides incomparable, in declaration order.

    On a measurement quantity the score's own derived kind is not what is
    compared: the quantity's field must be carried by every row of both sides
    (a row below schema "18" does not carry the per-item ones), and its labels
    must name one measurement on both.
    """
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

    if quantity != QUANTITY_SCORE:
        found.extend(_measurement_refusals(reference_rows, candidate_rows, quantity))
        return found

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


def _measurement_refusals(
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    quantity: str,
) -> list[dict[str, Any]]:
    """The quantity's field absent from a row, or its labels disagreeing.

    A label is read over the rows that carry a non-null one: a null TTFT has
    no source, which is not a second source.
    """
    sides = (reference_rows, candidate_rows)
    found: list[dict[str, Any]] = []
    for key in (quantity, *MEASUREMENT_LABEL_FIELDS.get(quantity, ())):
        carried = all(key in row for rows in sides for row in rows)
        reference_labels, candidate_labels = (
            {
                json.dumps(row[key], sort_keys=True)
                for row in rows
                if row.get(key) is not None
            }
            for rows in sides
        )
        if not carried:
            reason = REFUSAL_ABSENT
        elif key == quantity:
            continue
        elif len(reference_labels) > 1 or len(candidate_labels) > 1:
            reason = REFUSAL_VARIES_WITHIN_SIDE
        elif reference_labels != candidate_labels:
            reason = REFUSAL_DIFFERS
        else:
            continue
        found.append(
            {
                "field": key,
                "reason": reason,
                "reference_value": _one_label(reference_labels),
                "candidate_value": _one_label(candidate_labels),
            }
        )
    return found


def _one_label(labels: set[str]) -> Any:
    """The one value a side's labels take, or `None` when none or several."""
    return json.loads(next(iter(labels))) if len(labels) == 1 else None


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
    rows = [*reference_rows, *candidate_rows]
    keys = {key for row in rows for key in row}
    excluded = EXCLUDED_FROM_DIFFERING
    if all(row.get("harness_id") == harness.HARNESS_DIRECT for row in rows):
        # `direct`'s version is its HTTP client's (`requests`): a routine bump
        # changes no prompt the engine receives, so between two `direct` sides
        # it is not a configuration difference. Any other harness's version is
        # the framework itself and stays compared.
        excluded = excluded | {"harness_version"}
    return sorted(
        key
        for key in keys - excluded
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


def _partial_sides(
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> list[str]:
    """The sides whose batch never completed: no row has `partial_failure` null.

    A batch completed by `--resume` holds partial rows beside complete ones
    and is complete. A row predating `partial_failure` carries no such key
    and was written by a batch that wrote nothing unless it completed.
    """
    return [
        side
        for side, rows in (("reference", reference_rows), ("candidate", candidate_rows))
        if rows and all(row.get("partial_failure") is not None for row in rows)
    ]


def _axis(
    dimension: str,
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
) -> Dimension:
    """`dimension`'s axis for these two sides, with the local-producer rule
    (engine, machine, mode) applied."""
    axis = DIMENSIONS[dimension]
    if dimension != DEFAULT_DIMENSION:
        return axis

    def served_locally(rows: Sequence[Mapping[str, Any]]) -> set[bool]:
        return {
            row.get("provider") == row_contract.SUBJECT_PROVIDER_LOCAL for row in rows
        }

    if served_locally(reference_rows) != served_locally(candidate_rows):
        return Dimension(fields=axis.fields | ENGINE_FIELDS, key_fields=axis.key_fields)
    return axis


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


def _verdict(
    kind: str,
    result: Mapping[str, Any] | None,
    adjusted_p_value: float | None,
    alpha: float,
) -> str:
    """The reader-facing verdict of a member, read against its adjusted p.

    An observation reads `not comparable`: a reader of the verdict alone must
    never take a confounded pair for a finding. Its p stays in `result`, where
    a significant one reads as the bug signal it is.
    """
    if kind in (KIND_REFUSAL, KIND_OBSERVATION) or result is None:
        return VERDICT_NOT_COMPARABLE
    if result["p_value_null_reason"] == NULL_PAIRED_N_BELOW_MINIMUM:
        return VERDICT_NOT_COMPARABLE
    if adjusted_p_value is not None and adjusted_p_value <= alpha:
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
    quantity: str = QUANTITY_SCORE,
) -> dict[str, Any]:
    """One comparison member: a paired test, an observation, or a refusal.

    `quantity` is what is compared: the score (default), a per-item
    measurement (Wilcoxon over the same item ids), or the per-batch energy
    (always an observation, never a test).
    """
    if not reference_rows:
        raise ComparisonInputError(f"no row selects the reference side {reference}")
    if not candidate_rows:
        raise ComparisonInputError(f"no row selects the candidate side {candidate}")
    if quantity not in QUANTITIES:
        raise ComparisonInputError(
            f"unknown compared quantity {quantity!r}: one of {', '.join(QUANTITIES)}"
        )
    axis = _axis(dimension, reference_rows, candidate_rows)
    refused = refusals(reference_rows, candidate_rows, quantity=quantity)
    differing = differing_fields(reference_rows, candidate_rows)
    if quantity == QUANTITY_SCORE:
        kinds = {scoring_kind(row) for row in [*reference_rows, *candidate_rows]}
        kind = next(iter(kinds)) if len(kinds) == 1 else None
        compared_field = COMPARED_FIELD_BY_SCORING_KIND.get(kind) if kind else None
    else:
        kind = (
            SCORING_KIND_BATCH
            if quantity == QUANTITY_ENERGY
            else SCORING_KIND_CONTINUOUS
        )
        compared_field = quantity

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
        "compared_field": compared_field,
        "refusal": refused,
        "differing_fields": differing,
        "difference_convention": "candidate minus reference",
    }
    if quantity != QUANTITY_SCORE:
        # Only off the default, so a score record keeps its published shape.
        member["compared_quantity"] = quantity
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
            "raw_p_value": None,
            "adjusted_p_value": None,
            "adjusted_p_value_null_reason": NULL_COMPARISON_REFUSED,
            "verdict": VERDICT_NOT_COMPARABLE,
        }

    assert kind is not None and compared_field is not None  # else refused above
    comparison_kind, confounds, observation_reason = _comparison_kind(differing, axis)
    if kind == SCORING_KIND_BATCH:
        return {
            **member,
            **_batch_observation(
                reference_rows, candidate_rows, compared_field, observation_reason
            ),
            "confounds": confounds,
        }
    compared = compared_field
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
    partial_sides = _partial_sides(reference_rows, candidate_rows)
    if partial_sides:
        # A partially observed row set shrinks the paired n, but a batch left
        # partial by a failure is a prefix of the suite in run order, not a
        # random subset of it: its p is kept in `result` and never read as a
        # test.
        partial_reason = (
            f"the {' and '.join(partial_sides)} side's batch is partial "
            "(every row carries a partial_failure): its items are the ones "
            "answered before a failure, not the suite"
        )
        comparison_kind = KIND_OBSERVATION
        observation_reason = (
            partial_reason
            if observation_reason is None
            else f"{observation_reason}; {partial_reason}"
        )
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
        "test_chosen_because": CHOSEN_BECAUSE_BY_SCORING_KIND[kind],
        "result": result,
        "raw_p_value": result["p_value"],
        # Alone, a member is a family of one: Holm's adjusted p is the raw p.
        # `build_family_record` re-reads both over the family it belongs to.
        "adjusted_p_value": result["p_value"],
        "adjusted_p_value_null_reason": result["p_value_null_reason"],
        "verdict": _verdict(comparison_kind, result, result["p_value"], alpha),
    }


def _batch_observation(
    reference_rows: Sequence[Mapping[str, Any]],
    candidate_rows: Sequence[Mapping[str, Any]],
    field_name: str,
    dimension_reason: str | None,
) -> dict[str, Any]:
    """A per-batch quantity's member body: two values, their difference, no test.

    Each side's value is the one its rows repeat; a side whose rows carry two
    (a batch completed by `--resume`, each run measuring its own span) or none
    has no single batch value, and the difference is null with that reason.
    """
    reference_value = _single_value(reference_rows, field_name)
    candidate_value = _single_value(candidate_rows, field_name)
    known = (
        reference_value is not _ABSENT
        and candidate_value is not _ABSENT
        and isinstance(reference_value, int | float)
        and isinstance(candidate_value, int | float)
    )
    return {
        "comparison_kind": KIND_OBSERVATION,
        "observation_reason": (
            ENERGY_NO_PAIRED_TEST_REASON
            if dimension_reason is None
            else f"{ENERGY_NO_PAIRED_TEST_REASON}; {dimension_reason}"
        ),
        "batch_values": {
            "reference": _shown(reference_value),
            "candidate": _shown(candidate_value),
            "difference": candidate_value - reference_value if known else None,
            "difference_null_reason": None if known else NULL_NO_SINGLE_BATCH_VALUE,
        },
        "paired_item_ids": None,
        "paired_n": None,
        "paired_values": None,
        "unpaired_items": None,
        "unpaired_count": None,
        "test": None,
        "test_chosen_because": None,
        "result": None,
        "raw_p_value": None,
        "adjusted_p_value": None,
        "adjusted_p_value_null_reason": NULL_NO_PAIRED_TEST,
        "verdict": VERDICT_NOT_COMPARABLE,
    }


# --------------------------------------------------------------------------
# The family


FAMILY_RULE = (
    "one suite crossed with one compared dimension, closed at analysis time: "
    "every comparison this invocation declared, which must include every "
    "comparison of the family's current record, so a family only grows and "
    "each growth is a new record superseding the old by id (PRD Methodology 24)"
)
HOLM_FORMULA = (
    "adjusted p_(i) = max over j <= i of min(1, (m - j + 1) * p_(j)), the m raw "
    "p-values sorted ascending; computed exactly, so tied raw p-values share "
    "one adjusted value and with m = 1 the adjusted p equals the raw p"
)
HOLM_ADJUSTED_OVER = (
    "every member that was not refused, tests and observations alike, so "
    "adjustment_size equals tested_count; a member whose p is left null with a "
    "named reason enters as p = 1, which never lowers another member's "
    "adjusted p, and keeps its own adjusted p null with that reason; a refused "
    "member carries no p and enters no count"
)


class FamilyError(ComparisonInputError):
    """The declared comparisons cannot form one family record."""


def holm_adjust(p_values: Sequence[float]) -> list[float]:
    """Holm's step-down adjusted p-values, in the order given.

    `p~(i) = max_{j <= i} min(1, (m - j + 1) * p(j))` over the ascending raw
    p-values, computed in `Fraction` from each float so the arithmetic adds no
    rounding of its own.
    """
    m = len(p_values)
    order = sorted(range(m), key=lambda index: p_values[index])
    adjusted = [0.0] * m
    running = Fraction(0)
    for rank, index in enumerate(order):
        scaled = min(Fraction(1), (m - rank) * Fraction(p_values[index]))
        running = max(running, scaled)
        adjusted[index] = float(running)
    return adjusted


def member_key(member: Mapping[str, Any]) -> tuple[str, str, str, str]:
    """A member's identity: its two sides, run id plus selector."""
    return (
        member["reference_run_id"],
        json.dumps(member["reference_selector"], sort_keys=True),
        member["candidate_run_id"],
        json.dumps(member["candidate_selector"], sort_keys=True),
    )


def _member_quantity(member: Mapping[str, Any]) -> str:
    """What a member compares; a member without the key compares the score."""
    quantity: str = member.get("compared_quantity", QUANTITY_SCORE)
    return quantity


def _family_definition(members: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """One suite by one dimension by one quantity; a member refused on suite
    identity joins it.

    The quantity is named only off the default, so a score family's
    definition keeps the shape every published record has.
    """
    dimensions = {member["compared_dimension"] for member in members}
    if len(dimensions) != 1:
        raise FamilyError(
            "the comparisons span more than one compared dimension: "
            + ", ".join(sorted(dimensions))
        )
    quantities = {_member_quantity(member) for member in members}
    if len(quantities) != 1:
        raise FamilyError(
            "the comparisons span more than one compared quantity: "
            + ", ".join(sorted(quantities))
        )
    suites = {
        (member["suite_id"], member["suite_version"])
        for member in members
        if member["suite_id"] is not None and member["suite_version"] is not None
    }
    if len(suites) > 1:
        raise FamilyError(
            "the comparisons span more than one suite, so more than one family: "
            + ", ".join(f"{suite_id}@{version}" for suite_id, version in sorted(suites))
            + "; one invocation writes one family record"
        )
    suite_id, suite_version = next(iter(suites)) if suites else (None, None)
    definition: dict[str, Any] = {
        "suite_id": suite_id,
        "suite_version": suite_version,
        "compared_dimension": next(iter(dimensions)),
        "rule": FAMILY_RULE,
    }
    quantity = next(iter(quantities))
    if quantity != QUANTITY_SCORE:
        definition["compared_quantity"] = quantity
    return definition


def family_key(record: Mapping[str, Any]) -> tuple[Any, Any, Any, Any]:
    """The family a record belongs to, whatever its record version.

    A record without a compared quantity compares the score: a token family
    and a score family over one suite and dimension are two families, and Holm
    never adjusts one over the other.
    """
    definition = record["family_definition"]
    return (
        definition["suite_id"],
        definition["suite_version"],
        definition["compared_dimension"],
        definition.get("compared_quantity", QUANTITY_SCORE),
    )


def _canonical(record: Mapping[str, Any]) -> str:
    return json.dumps(record, indent=2, sort_keys=True) + "\n"


def superseded_ids(record: Mapping[str, Any]) -> list[str]:
    """The family ids a record supersedes; none on a record that predates it."""
    return [entry["family_id"] for entry in record.get("supersedes", [])]


def _identified(body: Mapping[str, Any], supersedes: Sequence[str]) -> dict[str, Any]:
    # Each id sits under its own `family_id` key, so it reads as an id.
    record = {
        **body,
        "supersedes": [{"family_id": family_id} for family_id in sorted(supersedes)],
    }
    record["family_id"] = hashlib.sha256(_canonical(record).encode()).hexdigest()
    return record


def build_family_record(
    members: Sequence[Mapping[str, Any]],
    *,
    alpha: float,
    rows_source: str,
    supersedes: Sequence[str] = (),
) -> dict[str, Any]:
    """One closed family: every member, Holm over their raw p, one id.

    Members are put in a canonical order, so the record does not depend on
    the order they were declared in; each verdict is re-read against the
    member's adjusted p. `family_id` hashes the content, `supersedes`
    included.
    """
    if not members:
        raise FamilyError("a family holds at least one comparison")
    ordered = sorted((dict(member) for member in members), key=member_key)
    keys = [member_key(member) for member in ordered]
    duplicates = sorted({key for key in keys if keys.count(key) > 1})
    if duplicates:
        raise FamilyError(
            "a comparison is declared twice: "
            + "; ".join(f"{key[0]} {key[1]} vs {key[2]} {key[3]}" for key in duplicates)
        )
    definition = _family_definition(ordered)
    adjusted_indexes = [
        index
        for index, member in enumerate(ordered)
        if member["comparison_kind"] != KIND_REFUSAL
    ]
    # A tested member without a p counts as p = 1: the conservative reading.
    adjusted = holm_adjust(
        [
            1.0
            if ordered[index]["raw_p_value"] is None
            else ordered[index]["raw_p_value"]
            for index in adjusted_indexes
        ]
    )
    for index, value in zip(adjusted_indexes, adjusted, strict=True):
        if ordered[index]["raw_p_value"] is not None:
            ordered[index]["adjusted_p_value"] = value
            ordered[index]["adjusted_p_value_null_reason"] = None
    for member in ordered:
        member["verdict"] = _verdict(
            member["comparison_kind"],
            member["result"],
            member["adjusted_p_value"],
            alpha,
        )
    refused = sum(1 for member in ordered if member["comparison_kind"] == KIND_REFUSAL)
    body: dict[str, Any] = {
        "record_type": RECORD_TYPE,
        "record_version": RECORD_VERSION,
        "family_definition": definition,
        "family_size": len(ordered),
        "tested_count": len(ordered) - refused,
        "refused_count": refused,
        "alpha": alpha,
        "multiplicity_correction": {
            "method": "holm",
            "formula": HOLM_FORMULA,
            "adjusted_over": HOLM_ADJUSTED_OVER,
            "adjustment_size": len(adjusted_indexes),
        },
        "verdict_rule": VERDICT_RULE,
        "rows_source": rows_source,
        "members": ordered,
    }
    return _identified(body, supersedes)


def same_content(first: Mapping[str, Any], second: Mapping[str, Any]) -> bool:
    """Two records equal but for their id and the ids they supersede."""
    ignored = ("family_id", "supersedes")

    def body(record: Mapping[str, Any]) -> dict[str, Any]:
        return {key: value for key, value in record.items() if key not in ignored}

    return body(first) == body(second)


def heads(records: Sequence[Mapping[str, Any]]) -> list[str]:
    """The ids no other record supersedes: the current record(s) of a family."""
    superseded = {
        family_id for record in records for family_id in superseded_ids(record)
    }
    return sorted(
        record["family_id"]
        for record in records
        if record["family_id"] not in superseded
    )


def record_text(record: Mapping[str, Any]) -> str:
    """The exact text a family record file holds."""
    return _canonical(record)


def default_output_path(
    record: Mapping[str, Any], directory: Path | None = None
) -> Path:
    definition = record["family_definition"]
    suite = (
        f"{definition['suite_id']}@{definition['suite_version']}"
        if definition["suite_id"] is not None
        else "mixed-suites"
    )
    quantity = definition.get("compared_quantity")
    axis = definition["compared_dimension"] + (f".{quantity}" if quantity else "")
    name = f"{suite}.{axis}.{record['family_id'][:12]}.json"
    return (COMPARISONS_DIR if directory is None else directory) / name


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


def _side_from_declaration(entry: Any, role: str, position: int) -> Side:
    where = entry.get("where", {}) if isinstance(entry, dict) else None
    if (
        not isinstance(entry, dict)
        or not isinstance(entry.get("run_id"), str)
        or not isinstance(where, dict)
        or not all(isinstance(value, str) for value in where.values())
    ):
        raise ComparisonInputError(
            f"comparison {position}: {role} is not "
            '{"run_id": "...", "where": {"field": "value"}}'
        )
    return Side(entry["run_id"], dict(where))


def read_declaration(path: Path) -> list[tuple[Side, Side]]:
    """The comparisons a declaration file names, as (reference, candidate) sides.

    The file is a JSON array of `{"reference": {"run_id", "where"},
    "candidate": {...}}` objects; `where` is optional.
    """
    try:
        declared = json.loads(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise ComparisonInputError(
            f"cannot read comparisons from {path}: {error}"
        ) from error
    except json.JSONDecodeError as error:
        raise ComparisonInputError(f"{path} is not JSON: {error}") from error
    if not isinstance(declared, list) or not declared:
        raise ComparisonInputError(
            f"{path} does not hold a non-empty array of comparisons"
        )
    pairs = []
    for position, entry in enumerate(declared, start=1):
        if not isinstance(entry, dict):
            raise ComparisonInputError(f"comparison {position} is not an object")
        pairs.append(
            (
                _side_from_declaration(entry.get("reference"), "reference", position),
                _side_from_declaration(entry.get("candidate"), "candidate", position),
            )
        )
    return pairs


def read_family_records(directory: Path) -> list[dict[str, Any]]:
    """Every family record published under `directory`, any record version."""
    records = []
    for path in sorted(directory.glob("*.json")) if directory.is_dir() else []:
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ComparisonInputError(f"{path} is not JSON: {error}") from error
        if isinstance(record, dict) and record.get("record_type") == RECORD_TYPE:
            records.append(record)
    return records


def resolve_family_record(
    members: Sequence[Mapping[str, Any]],
    published: Sequence[Mapping[str, Any]],
    *,
    alpha: float,
    rows_source: str,
) -> tuple[dict[str, Any], list[str] | None]:
    """The record this analysis publishes, and what supersedes it if published.

    A published record of the same family whose content equals this analysis
    but for its id is returned as is, with the ids of the records superseding
    it (empty when it is current): the same bundle and definition give the
    identical record, even after the family grew. Otherwise the new record
    supersedes every current record of its family by id, and only when it
    holds every comparison they hold: a family grows, it never shrinks, so no
    comparison can leave the current record to escape the adjustment. None is
    ever edited. `None` in second place means the record is new.
    """
    fresh = build_family_record(members, alpha=alpha, rows_source=rows_source)
    comparable = json.loads(record_text(fresh))
    family = [record for record in published if family_key(record) == family_key(fresh)]
    for record in family:
        if same_content(record, comparable):
            successors = sorted(
                other["family_id"]
                for other in family
                if record["family_id"] in superseded_ids(other)
            )
            return dict(record), successors
    current = heads(family)
    declared = {member_key(member) for member in members}
    missing = sorted(
        {
            member_key(member)
            for record in family
            if record["family_id"] in current
            for member in record["members"]
        }
        - declared
    )
    if missing:
        raise FamilyError(
            "the current record of this family holds comparisons this invocation "
            "does not declare: "
            + "; ".join(f"{key[0]} {key[1]} vs {key[2]} {key[3]}" for key in missing)
            + "; a family only grows, so declare every one of them"
        )
    superseding = build_family_record(
        members, alpha=alpha, rows_source=rows_source, supersedes=current
    )
    return superseding, None


# --------------------------------------------------------------------------
# The record's field definitions
#
# What each field of a family record, and of each comparison it holds, means,
# its unit, and what a null in it means: the definitions the published tables
# read (`bundle_export` reads them into its column dictionary and never
# redefines them). `empty` says when, and why, a field holds null.


def _listed(*values: str) -> str:
    return ", ".join(values)


_KINDS = _listed(KIND_TEST, KIND_OBSERVATION, KIND_REFUSAL)
_VERDICTS = _listed(
    VERDICT_DISTINGUISHABLE, VERDICT_NOT_DISTINGUISHABLE, VERDICT_NOT_COMPARABLE
)
_SCORING_KINDS = _listed(
    SCORING_KIND_BINARY,
    SCORING_KIND_GRADED,
    SCORING_KIND_CONTINUOUS,
    SCORING_KIND_BATCH,
)
_DIRECTIONS = _listed(
    DIRECTION_CANDIDATE_HIGHER, DIRECTION_REFERENCE_HIGHER, DIRECTION_NONE
)
_REFUSAL_REASONS = _listed(REFUSAL_DIFFERS, REFUSAL_ABSENT, REFUSAL_VARIES_WITHIN_SIDE)
_OTHER_QUANTITIES = _listed(*MEASUREMENT_QUANTITIES, QUANTITY_ENERGY)
_NO_RESULT = (
    "Null when no test ran: a refusal, or a per-batch quantity "
    f"(adjusted_p_value_null_reason {NULL_COMPARISON_REFUSED} or "
    f"{NULL_NO_PAIRED_TEST})."
)
_NO_PAIRS = "Null when nothing was paired: a refusal or a per-batch quantity."
_BELOW_MINIMUM = (
    f"Null when the paired n is below the minimum ({NULL_PAIRED_N_BELOW_MINIMUM})."
)
_SHARED_NULL = "Null when the two sides differ on it or either does not carry it."
_COMPARED_UNIT = "compared field's unit"

FAMILY_RECORD_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("record_type",): FieldDoc(
        f"Record type the file declares: {RECORD_TYPE}.", field_doc.ID
    ),
    ("record_version",): FieldDoc(
        "Version of the family-record shape. Version 1 predates tested_count, "
        "refused_count, raw_p_value and a refusal's adjusted p-value reason.",
        field_doc.ID,
    ),
    ("family_id",): FieldDoc(
        "SHA-256 of the record's canonical JSON, the ids it supersedes "
        "included: the record's identity. A comparison row carries the id of "
        "the family holding it.",
        field_doc.SHA,
    ),
    ("family_definition", "suite_id"): FieldDoc(
        "Suite the family covers: one suite per family.",
        field_doc.ID,
        "Null when every member is refused on suite identity.",
    ),
    ("family_definition", "suite_version"): FieldDoc(
        "Version of the suite the family covers.",
        field_doc.ID,
        "Null when every member is refused on suite identity.",
    ),
    ("family_definition", "compared_dimension"): FieldDoc(
        f"Configuration axis the family compares along: {_listed(*DIMENSIONS)}.",
        field_doc.ID,
    ),
    ("family_definition", "compared_quantity"): FieldDoc(
        f"Quantity compared when it is not the score: {_OTHER_QUANTITIES}. A "
        "score family does not carry the field.",
        field_doc.ID,
    ),
    ("family_definition", "rule"): FieldDoc(
        "The family rule, as the record states it: one suite by one "
        "dimension, closed at analysis time, grown only by supersession.",
        field_doc.TEXT,
    ),
    ("family_size",): FieldDoc(
        "Comparisons the family holds, refused ones included.", field_doc.COUNT
    ),
    ("tested_count",): FieldDoc(
        "Comparisons not refused (tests and observations): the ones the "
        "multiplicity correction runs over.",
        field_doc.COUNT,
    ),
    ("refused_count",): FieldDoc(
        "Comparisons refused: listed, and in no adjustment.", field_doc.COUNT
    ),
    ("alpha",): FieldDoc(
        "Significance level every verdict is read against.", field_doc.PROBABILITY
    ),
    ("multiplicity_correction", "method"): FieldDoc(
        "Multiplicity correction applied over the family: holm (Holm's step-down).",
        field_doc.ID,
    ),
    ("multiplicity_correction", "formula"): FieldDoc(
        "The correction's formula, as the record states it.", field_doc.TEXT
    ),
    ("multiplicity_correction", "adjusted_over"): FieldDoc(
        "Which comparisons the adjustment runs over and how a null p enters "
        "it (as p = 1), as the record states it.",
        field_doc.TEXT,
    ),
    ("multiplicity_correction", "adjustment_size"): FieldDoc(
        "Number of p-values the adjustment ran over (m); equals tested_count.",
        field_doc.COUNT,
    ),
    ("multiplicity_correction", "note"): FieldDoc(
        "A note an earlier record version adds on the correction.", field_doc.TEXT
    ),
    ("verdict_rule",): FieldDoc(
        "How each comparison's verdict is read from its adjusted p-value, as "
        "the record states it.",
        field_doc.TEXT,
    ),
    ("rows_source",): FieldDoc(
        "Quality rows file the family was computed from, as the record names it.",
        field_doc.TEXT,
    ),
    ("supersedes",): FieldDoc(
        "Family records this one supersedes, as the record lists them "
        '([{"family_id": ...}]). Each named record is an earlier version of '
        "the same family and stays published; a record no other record names "
        "here is current.",
        field_doc.JSON_ARRAY,
    ),
}

COMPARISON_RECORD_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("reference_run_id",): FieldDoc(
        "run_id of the reference side's rows.", field_doc.ID
    ),
    ("reference_selector",): FieldDoc(
        "Row fields selecting the reference side within its run; {} when the "
        "run id alone selects it.",
        field_doc.JSON_OBJECT,
    ),
    ("reference_selector", "*"): FieldDoc(
        "Value, as text, a reference-side row carries in the field the column "
        "suffix names.",
        field_doc.TEXT,
    ),
    ("reference_row_count",): FieldDoc(
        "Rows the reference side selects.", field_doc.COUNT
    ),
    ("candidate_run_id",): FieldDoc(
        "run_id of the candidate side's rows.", field_doc.ID
    ),
    ("candidate_selector",): FieldDoc(
        "Row fields selecting the candidate side within its run; {} when the "
        "run id alone selects it.",
        field_doc.JSON_OBJECT,
    ),
    ("candidate_selector", "*"): FieldDoc(
        "Value, as text, a candidate-side row carries in the field the column "
        "suffix names.",
        field_doc.TEXT,
    ),
    ("candidate_row_count",): FieldDoc(
        "Rows the candidate side selects.", field_doc.COUNT
    ),
    ("suite_id",): FieldDoc("Suite both sides share.", field_doc.ID, _SHARED_NULL),
    ("suite_version",): FieldDoc(
        "Suite version both sides share.", field_doc.ID, _SHARED_NULL
    ),
    ("suite_level",): FieldDoc(
        "Suite level both sides share.", field_doc.ID, _SHARED_NULL
    ),
    ("compared_dimension",): FieldDoc(
        f"Axis this comparison is along: {_listed(*DIMENSIONS)}.", field_doc.ID
    ),
    ("scoring_kind",): FieldDoc(
        f"Kind of the compared value: {_SCORING_KINDS}.",
        field_doc.ID,
        "Null when the two sides' rows do not agree on one scoring kind.",
    ),
    ("compared_field",): FieldDoc(
        "Row field compared: correct, item_score, or the measurement field.",
        field_doc.ID,
        "Null when the scoring kind is null.",
    ),
    ("compared_quantity",): FieldDoc(
        f"Quantity compared when it is not the score: {_OTHER_QUANTITIES}. A "
        "score comparison does not carry the field.",
        field_doc.ID,
    ),
    ("refusal",): FieldDoc(
        "Why the comparison is refused, one entry per field: field, reason "
        f"({_REFUSAL_REASONS}), reference_value, candidate_value; [] when not "
        "refused.",
        field_doc.JSON_ARRAY,
    ),
    ("differing_fields",): FieldDoc(
        "Row fields on which the two sides differ.", field_doc.JSON_ARRAY
    ),
    ("difference_convention",): FieldDoc(
        "Sign convention of every difference: candidate minus reference.",
        field_doc.TEXT,
    ),
    ("comparison_kind",): FieldDoc(
        f"{_KINDS}. An observation attributes no difference: the sides differ "
        "outside the compared dimension or not on it, a side's batch is "
        "partial, or the quantity is per batch.",
        field_doc.ID,
    ),
    ("confounds",): FieldDoc(
        "Fields outside the compared dimension on which the sides differ.",
        field_doc.JSON_ARRAY,
    ),
    ("observation_reason",): FieldDoc(
        "Why the comparison is an observation.",
        field_doc.TEXT,
        "Null when the comparison is a test or a refusal.",
    ),
    ("paired_item_ids",): FieldDoc(
        "Item ids both sides answered with a value.", field_doc.JSON_ARRAY, _NO_PAIRS
    ),
    ("paired_n",): FieldDoc("Number of paired items.", field_doc.COUNT, _NO_PAIRS),
    ("paired_values",): FieldDoc(
        "Each paired item's compared value on both sides (item_id, reference, "
        "candidate): the data the test ran over.",
        field_doc.JSON_ARRAY,
        _NO_PAIRS,
    ),
    ("unpaired_items",): FieldDoc(
        "Items only one side answered with a value (item_id, missing_from).",
        field_doc.JSON_ARRAY,
        _NO_PAIRS,
    ),
    ("unpaired_count",): FieldDoc(
        "Number of unpaired items.", field_doc.COUNT, _NO_PAIRS
    ),
    ("test",): FieldDoc(
        f"Paired test run: {TEST_MCNEMAR} for a binary score, {TEST_WILCOXON} "
        "for a graded score or a per-item measurement; chosen from the rows' "
        "shape, never by flag.",
        field_doc.ID,
        _NO_RESULT,
    ),
    ("test_chosen_because",): FieldDoc(
        "Why that test, as the record states it.", field_doc.TEXT, _NO_RESULT
    ),
    ("result",): FieldDoc(
        "The test's result block.", field_doc.JSON_OBJECT, _NO_RESULT
    ),
    ("result", "test"): FieldDoc("Test the result block belongs to.", field_doc.ID),
    ("result", "contingency", "both_correct"): FieldDoc(
        "McNemar: paired items both sides got right.", field_doc.COUNT
    ),
    ("result", "contingency", "reference_only_correct"): FieldDoc(
        "McNemar: paired items only the reference got right (b).", field_doc.COUNT
    ),
    ("result", "contingency", "candidate_only_correct"): FieldDoc(
        "McNemar: paired items only the candidate got right (c).", field_doc.COUNT
    ),
    ("result", "contingency", "both_wrong"): FieldDoc(
        "McNemar: paired items both sides got wrong.", field_doc.COUNT
    ),
    ("result", "discordant_n"): FieldDoc(
        "McNemar: discordant pairs (b + c).", field_doc.COUNT
    ),
    ("result", "conventions", "zero_method"): FieldDoc(
        f"Wilcoxon: how zero differences are handled ({WILCOXON_ZERO_METHOD}).",
        field_doc.ID,
    ),
    ("result", "conventions", "zero_method_definition"): FieldDoc(
        "Wilcoxon: the zero method, as the record states it.", field_doc.TEXT
    ),
    ("result", "conventions", "exact_rule"): FieldDoc(
        "Wilcoxon: when the exact p is used, as the record states it.",
        field_doc.TEXT,
    ),
    ("result", "conventions", "exact_max_nonzero"): FieldDoc(
        "Wilcoxon: largest non-zero difference count given an exact p.",
        field_doc.COUNT,
    ),
    ("result", "conventions", "continuity_correction"): FieldDoc(
        "Wilcoxon: whether a continuity correction is applied.", field_doc.BOOL
    ),
    ("result", "conventions", "tie_handling"): FieldDoc(
        "Wilcoxon: how tied magnitudes are ranked.", field_doc.TEXT
    ),
    ("result", "statistic_name"): FieldDoc(
        "What the statistic is: min(b, c) for McNemar, W+ for Wilcoxon.",
        field_doc.TEXT,
    ),
    ("result", "statistic"): FieldDoc(
        "The test statistic, named by statistic_name.",
        "test statistic",
        _BELOW_MINIMUM,
    ),
    ("result", "w_minus"): FieldDoc(
        "Wilcoxon: sum of the ranks of negative differences.",
        "rank sum",
        _BELOW_MINIMUM,
    ),
    ("result", "p_value"): FieldDoc(
        "The test's two-sided p-value, unadjusted. McNemar: exact binomial "
        "over the discordant pairs at 0.5, min(1, 2 * sum over k <= min(b, c) "
        "of C(b + c, k) / 2^(b + c)).",
        field_doc.PROBABILITY,
        "Null with its reason in p_value_null_reason.",
    ),
    ("result", "p_value_null_reason"): FieldDoc(
        "Why the p-value is null: "
        + _listed(
            NULL_PAIRED_N_BELOW_MINIMUM,
            NULL_NO_DISCORDANT_PAIRS,
            NULL_ALL_DIFFERENCES_ZERO,
        )
        + ".",
        field_doc.ID,
        "Null when the p-value is a number.",
    ),
    ("result", "p_value_method"): FieldDoc(
        "Wilcoxon: how the p-value was computed, exact_sign_flip or "
        "normal_approximation.",
        field_doc.ID,
        "Null when the p-value is null.",
    ),
    ("result", "effect_size_name"): FieldDoc(
        "Which effect size is reported: discordant_pair_odds_ratio (McNemar) "
        "or rank_biserial (Wilcoxon).",
        field_doc.ID,
    ),
    ("result", "effect_size_formula"): FieldDoc(
        "The effect size's formula, as the record states it.", field_doc.TEXT
    ),
    ("result", "effect_size"): FieldDoc(
        "The effect size, named by effect_size_name.",
        "effect size",
        "Null with its reason in effect_size_null_reason.",
    ),
    ("result", "effect_size_null_reason"): FieldDoc(
        "Why the effect size is null: "
        + _listed(
            NULL_PAIRED_N_BELOW_MINIMUM,
            NULL_ODDS_RATIO_EMPTY_CELL,
            NULL_ALL_DIFFERENCES_ZERO,
        )
        + ".",
        field_doc.ID,
        "Null when the effect size is a number.",
    ),
    ("result", "direction"): FieldDoc(
        f"Which side scored higher: {_DIRECTIONS}.", field_doc.ID, _BELOW_MINIMUM
    ),
    ("result", "mean_difference"): FieldDoc(
        "Mean candidate-minus-reference difference over the paired items.",
        _COMPARED_UNIT,
        _BELOW_MINIMUM,
    ),
    ("result", "tie_count"): FieldDoc("Tied differences.", field_doc.COUNT),
    ("result", "zero_difference_count"): FieldDoc("Zero differences.", field_doc.COUNT),
    ("batch_values", "reference"): FieldDoc(
        "Reference side's per-batch value.",
        _COMPARED_UNIT,
        "Null when the side's rows carry no single batch value.",
    ),
    ("batch_values", "candidate"): FieldDoc(
        "Candidate side's per-batch value.",
        _COMPARED_UNIT,
        "Null when the side's rows carry no single batch value.",
    ),
    ("batch_values", "difference"): FieldDoc(
        "Candidate minus reference per-batch value.",
        _COMPARED_UNIT,
        "Null with its reason in batch_values.difference_null_reason.",
    ),
    ("batch_values", "difference_null_reason"): FieldDoc(
        f"Why the per-batch difference is null: {NULL_NO_SINGLE_BATCH_VALUE}.",
        field_doc.ID,
        "Null when the difference is a number.",
    ),
    ("raw_p_value",): FieldDoc(
        "The comparison's p-value before the family adjustment (result.p_value).",
        field_doc.PROBABILITY,
        f"{_NO_RESULT} Otherwise null with result.p_value_null_reason.",
    ),
    ("adjusted_p_value",): FieldDoc(
        "The comparison's p-value after the family's multiplicity correction; "
        "the verdict reads it.",
        field_doc.PROBABILITY,
        "Null with its reason in adjusted_p_value_null_reason.",
    ),
    ("adjusted_p_value_null_reason",): FieldDoc(
        f"Why the adjusted p-value is null: {NULL_COMPARISON_REFUSED} (a "
        f"refusal), {NULL_NO_PAIRED_TEST} (a per-batch quantity), or the "
        "result's p_value_null_reason.",
        field_doc.ID,
        "Null when the adjusted p-value is a number, and on a version-1 "
        "record's refusal (whose reasons are in refusal).",
    ),
    ("verdict",): FieldDoc(
        f"{_VERDICTS}: read from adjusted_p_value against the family's alpha "
        "by the record's verdict_rule.",
        field_doc.ID,
    ),
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-compare",
        description=(
            "Compare published configurations on the same items: write one "
            "family record holding every declared comparison, each a paired "
            "test or a refusal, with Holm-adjusted p-values over the family."
        ),
    )
    parser.add_argument(
        "--rows",
        default=settings.DEFAULT_QUALITY_REFERENCE_PATH,
        help="published quality rows (default: the reference bundle)",
    )
    parser.add_argument("--reference", help="reference run_id (one comparison)")
    parser.add_argument("--candidate", help="candidate run_id (one comparison)")
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
        "--comparisons",
        default=None,
        metavar="JSON",
        help=(
            "declaration file: a JSON array of {reference: {run_id, where}, "
            "candidate: {...}}; replaces --reference/--candidate"
        ),
    )
    parser.add_argument(
        "--dimension", choices=sorted(DIMENSIONS), default=DEFAULT_DIMENSION
    )
    parser.add_argument(
        "--quantity",
        choices=QUANTITIES,
        default=QUANTITY_SCORE,
        help=(
            "what is compared: the score (default), a per-item measurement "
            "(Wilcoxon over the same item ids), or the per-batch energy "
            "(an observation, never a test)"
        ),
    )
    parser.add_argument("--alpha", type=float, default=DEFAULT_ALPHA)
    parser.add_argument(
        "--records-dir",
        default=None,
        help=(
            "published family records a new record supersedes "
            "(default: aidd_docs/results/comparisons/)"
        ),
    )
    parser.add_argument(
        "--output",
        default=None,
        help="record path (default: <records-dir>/<name>.json)",
    )
    parser.add_argument(
        "--leader-sets",
        action="store_true",
        help=(
            "publish the leader set of every suite and machine class: grow "
            "each suite's model family by the comparisons against its best "
            "local subject and write one leader-set record per group; "
            "replaces the declared comparisons"
        ),
    )
    parser.add_argument(
        "--leader-sets-dir",
        default=None,
        help="leader-set records (default: aidd_docs/results/leader-sets/)",
    )
    parser.add_argument(
        "--fiche-registry-dir",
        default=settings.DEFAULT_FICHE_REGISTRY_DIR,
        help="fiches the rows cite, read for the machine class",
    )
    return parser


def _declared_pairs(args: argparse.Namespace) -> list[tuple[Side, Side]]:
    if args.comparisons is not None:
        if (
            args.reference is not None
            or args.candidate is not None
            or args.reference_where
            or args.candidate_where
        ):
            raise ComparisonInputError(
                "--comparisons replaces --reference/--candidate and their "
                "selectors; give one or the other"
            )
        return read_declaration(Path(args.comparisons))
    if args.reference is None or args.candidate is None:
        raise ComparisonInputError("give --reference and --candidate, or --comparisons")
    return [
        (
            Side(args.reference, _parse_selector(args.reference_where)),
            Side(args.candidate, _parse_selector(args.candidate_where)),
        )
    ]


def _member_line(member: Mapping[str, Any]) -> str:
    refused = ", ".join(
        f"{entry['field']} ({entry['reason']})" for entry in member["refusal"]
    )
    sides = " vs ".join(
        member[f"{side}_run_id"][:8]
        + "".join(
            f" {key}={value}" for key, value in member[f"{side}_selector"].items()
        )
        for side in ("reference", "candidate")
    )
    return f"  {sides}: {member['comparison_kind']}, verdict {member['verdict']}" + (
        f"; refused on {refused}" if refused else ""
    )


def _leader_sets(args: argparse.Namespace) -> int:
    """`--leader-sets`: the families and leader-set records over the rows."""
    # Imported here: `leader_set` builds on this module.
    from wave_local_ai_v2 import leader_set

    try:
        if not 0 < args.alpha < 1:
            raise ComparisonInputError(f"--alpha {args.alpha} is not in (0, 1)")
        named = [
            flag
            for flag, value in (
                ("--reference", args.reference),
                ("--candidate", args.candidate),
                ("--reference-where", args.reference_where or None),
                ("--candidate-where", args.candidate_where or None),
                ("--comparisons", args.comparisons),
                ("--output", args.output),
            )
            if value is not None
        ]
        if args.dimension != leader_set.LEADER_DIMENSION:
            named.append("--dimension")
        if args.quantity != QUANTITY_SCORE:
            named.append("--quantity")
        if named:
            raise ComparisonInputError(
                "--leader-sets declares its own comparisons on the model score: "
                + ", ".join(named)
                + " cannot be given with it"
            )
        rows_path = Path(args.rows)
        rows = _read_rows(rows_path)
    except ComparisonInputError as error:
        print(str(error), file=sys.stderr)
        return 1
    return leader_set.publish(
        rows,
        rows_source=rows_source_name(rows_path),
        records_dir=(
            Path(args.records_dir) if args.records_dir is not None else COMPARISONS_DIR
        ),
        leader_sets_dir=(
            Path(args.leader_sets_dir)
            if args.leader_sets_dir is not None
            else leader_set.LEADER_SETS_DIR
        ),
        fiche_registry_dir=Path(args.fiche_registry_dir),
        alpha=args.alpha,
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the declared comparisons and write their one family record.

    Exits 0 when the record is written or already published byte for byte
    (a refusal is a published record, not an error), 1 on unusable input,
    comparisons spanning two families, or an existing file with different
    content. No published record is ever rewritten.
    """
    args = _parser().parse_args(argv)
    if args.leader_sets:
        return _leader_sets(args)
    try:
        if not 0 < args.alpha < 1:
            raise ComparisonInputError(f"--alpha {args.alpha} is not in (0, 1)")
        pairs = _declared_pairs(args)
        rows_path = Path(args.rows)
        rows = _read_rows(rows_path)
        members = [
            compare_sides(
                select_side(rows, reference),
                select_side(rows, candidate),
                reference,
                candidate,
                dimension=args.dimension,
                alpha=args.alpha,
                quantity=args.quantity,
            )
            for reference, candidate in pairs
        ]
        records_dir = (
            Path(args.records_dir) if args.records_dir is not None else COMPARISONS_DIR
        )
        record, successors = resolve_family_record(
            members,
            read_family_records(records_dir),
            alpha=args.alpha,
            rows_source=rows_source_name(rows_path),
        )
    except ComparisonInputError as error:
        print(str(error), file=sys.stderr)
        return 1
    text = record_text(record)
    out_path = (
        Path(args.output) if args.output else default_output_path(record, records_dir)
    )
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
    supersedes = ", ".join(family_id[:12] for family_id in superseded_ids(record))
    print(
        f"{out_path} {status}: family {record['family_id'][:12]} of "
        f"{record['family_size']} ({record['tested_count']} tested, "
        f"{record['refused_count']} refused, Holm over "
        f"{record['multiplicity_correction']['adjustment_size']})"
        + (f"; supersedes {supersedes}" if supersedes else "")
        + ("; identical to a published record" if successors is not None else "")
        + (
            "; superseded by " + ", ".join(i[:12] for i in successors)
            if successors
            else ""
        )
    )
    for member in record["members"]:
        print(_member_line(member))
    return 0


if __name__ == "__main__":
    sys.exit(main())
