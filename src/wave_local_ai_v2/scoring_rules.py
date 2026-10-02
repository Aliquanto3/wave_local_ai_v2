"""The named scoring rules a suite definition selects by name.

A suite definition is data (`suite_registry.py`); how its completions are
scored is not, so each definition names one rule from `SCORING_RULES` and the
registry refuses a name this table does not hold. A further suite whose
scoring matches an existing rule names that rule; one whose scoring differs
adds a rule here, never a branch in the CLI.

Every rule has one signature: the suite's items and the batch's completions
in, one dict of row fields per item plus one dict shared by the whole batch
out. The suite's declared `max_output_tokens` is passed in rather than read
from a module constant, so truncation is judged against the cap the
definition itself declares. A completion is any mapping exposing `content`,
`truncated`, `generated_tokens` and `truncation_reason` -- the CLI's
`_Completion` shape, duck-typed so this module never imports the CLI.

Two rules publish two different score shapes on purpose: `exact_label_match`
publishes `correct` and `suite_accuracy`, `chrf_against_reference` publishes
the graded block and nulls the exact-match fields. `row_contract` refuses a
row carrying both.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any

from wave_local_ai_v2 import chrf
from wave_local_ai_v2.scoring import (
    GradedItem,
    ScoredItem,
    score_graded_suite,
    score_graded_suite_by_language,
    score_item,
    score_suite,
    score_suite_by_language,
    score_translation_item,
)

ScoringRule = Callable[..., tuple[list[dict[str, Any]], dict[str, Any]]]
"""`(items, completions, *, max_output_tokens) -> (per_item_fields, batch_fields)`."""

BatchAggregate = Callable[[Sequence[Any], Sequence[Mapping[str, Any]]], dict[str, Any]]
"""`(items, per_item_fields) -> batch_fields`: a rule's suite-level fields,
computed from its per-item fields alone.

Split out so a batch completed by `--resume` -- whose earlier items exist only
as rows, never as completions -- reaches its suite-level score through the
same function an uninterrupted batch does. Every input it reads is a field
the rows carry.
"""


def aggregate_exact_label_match(
    items: Sequence[Any], per_item: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The exact-match batch fields over `items`, paired by position with `per_item`."""
    scored_items = [
        ScoredItem(
            item_id=item["item_id"],
            expected_label=fields["expected_label"],
            predicted_label=fields["predicted_label"],
            correct=fields["correct"],
            failure_reason=fields["failure_reason"],
        )
        for item, fields in zip(items, per_item, strict=True)
    ]
    suite_score = score_suite(scored_items)
    return {
        "suite_accuracy": suite_score["accuracy"],
        "language_breakdown": score_suite_by_language(items, scored_items),
        "failure_counts": dict(suite_score["failure_counts"]),
    }


def aggregate_chrf_against_reference(
    items: Sequence[Any], per_item: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The graded batch fields over `items`, paired by position with `per_item`."""
    graded_items = [
        GradedItem(
            item_id=item["item_id"],
            item_score=fields["item_score"],
            failure_reason=fields["failure_reason"],
        )
        for item, fields in zip(items, per_item, strict=True)
    ]
    suite_score = score_graded_suite(graded_items)
    return {
        "suite_accuracy": None,
        "language_breakdown": None,
        "suite_score": suite_score["suite_score"],
        "score_breakdown": score_graded_suite_by_language(items, graded_items),
        "failure_counts": dict(suite_score["failure_counts"]),
    }


def exact_label_match(
    items: Sequence[Any],
    completions: Sequence[Mapping[str, Any]],
    *,
    max_output_tokens: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exact-label-match scoring: the exact-match fields, and no graded block."""
    scored_items = [
        score_item(
            item,
            completion["content"],
            truncated=completion["truncated"],
            generated_tokens=completion["generated_tokens"],
            max_output_tokens=max_output_tokens,
            truncation_reason=completion["truncation_reason"],
        )
        for item, completion in zip(items, completions, strict=True)
    ]
    per_item = [
        {
            "expected_label": scored["expected_label"],
            "predicted_label": scored["predicted_label"],
            "correct": scored["correct"],
            "failure_reason": scored["failure_reason"],
        }
        for scored in scored_items
    ]
    return per_item, aggregate_exact_label_match(items, per_item)


def chrf_against_reference(
    items: Sequence[Any],
    completions: Sequence[Mapping[str, Any]],
    *,
    max_output_tokens: int,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """chrF scoring against each item's written reference.

    Every row carries `reference_output` beside its `subject_output` and the
    metric parameters the score ran under, so a reader who disputes a number
    can recompute it with sacreBLEU rather than take it on trust. The
    exact-match fields are explicitly nulled: `correct` is a boolean, a chrF
    is not, and `suite_accuracy` names an exact-match rate this rule never
    computed.
    """
    graded_items = [
        score_translation_item(
            item,
            completion["content"],
            truncated=completion["truncated"],
            generated_tokens=completion["generated_tokens"],
            max_output_tokens=max_output_tokens,
            truncation_reason=completion["truncation_reason"],
        )
        for item, completion in zip(items, completions, strict=True)
    ]
    per_item = [
        {
            "expected_label": None,
            "predicted_label": None,
            "correct": None,
            "failure_reason": graded["failure_reason"],
            "item_score": graded["item_score"],
            "subject_output": completion["content"],
            "reference_output": item["reference"],
            "metric_id": chrf.METRIC_ID,
            "metric_version": chrf.METRIC_VERSION,
            # Copied, never shared: `chrf.METRIC_PARAMS` is one frozen object
            # and each row owns its own plain dict of it.
            "metric_params": dict(chrf.METRIC_PARAMS),
        }
        for item, completion, graded in zip(
            items, completions, graded_items, strict=True
        )
    ]
    return per_item, aggregate_chrf_against_reference(items, per_item)


SCORING_RULES: dict[str, ScoringRule] = {
    "exact_label_match": exact_label_match,
    "chrf_against_reference": chrf_against_reference,
}

# One aggregate per rule, keyed by the same name: the registry refuses a rule
# that has none, so every registered suite can complete a batch by resume.
BATCH_AGGREGATES: dict[str, BatchAggregate] = {
    "exact_label_match": aggregate_exact_label_match,
    "chrf_against_reference": aggregate_chrf_against_reference,
}
