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
    score_graded_suite,
    score_graded_suite_by_language,
    score_item,
    score_suite,
    score_suite_by_language,
    score_translation_item,
)

ScoringRule = Callable[..., tuple[list[dict[str, Any]], dict[str, Any]]]
"""`(items, completions, *, max_output_tokens) -> (per_item_fields, batch_fields)`."""


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
    suite_score = score_suite(scored_items)
    per_item = [
        {
            "expected_label": scored["expected_label"],
            "predicted_label": scored["predicted_label"],
            "correct": scored["correct"],
            "failure_reason": scored["failure_reason"],
        }
        for scored in scored_items
    ]
    batch = {
        "suite_accuracy": suite_score["accuracy"],
        "language_breakdown": score_suite_by_language(items, scored_items),
        "failure_counts": dict(suite_score["failure_counts"]),
    }
    return per_item, batch


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
    suite_score = score_graded_suite(graded_items)
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
    batch = {
        "suite_accuracy": None,
        "language_breakdown": None,
        "suite_score": suite_score["suite_score"],
        "score_breakdown": score_graded_suite_by_language(items, graded_items),
        "failure_counts": dict(suite_score["failure_counts"]),
    }
    return per_item, batch


SCORING_RULES: dict[str, ScoringRule] = {
    "exact_label_match": exact_label_match,
    "chrf_against_reference": chrf_against_reference,
}
