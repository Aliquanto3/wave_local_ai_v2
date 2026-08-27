"""Deterministic label normalization and exact-match scoring.

No network, no randomness: given the same raw completion and the same caller-
supplied truncation facts, `normalize_label` and `score_item` always return
the same result. This is what makes the quality scores this module produces
reproducible (same model + same prompt + same completion => same score),
unlike the runtime metrics in `timings.py`, which are hardware-bound and
never claimed to be reproducible across machines. `score_item` decides the
four-way failure taxonomy itself, but stays provider-agnostic: it takes only
`truncated`/`generated_tokens`/`max_output_tokens` as plain facts, never a
provider's raw response shape -- that mapping belongs to each provider's own
caller (`quality_cli.py`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TypedDict

from wave_local_ai_v2.classification_suite import LABELS, ClassificationItem
from wave_local_ai_v2.suite_gate import LANGUAGES, MIN_PER_LANGUAGE_CELL_ITEMS

_TOKEN_RE = re.compile(r"[a-z]+")

FAILURE_REASON_EMPTY = "empty"
FAILURE_REASON_UNPARSEABLE = "unparseable"
FAILURE_REASON_TRUNCATED_MAX_TOKENS = "truncated_max_tokens"
FAILURE_REASON_TRUNCATED_CONTEXT = "truncated_context"

_FAILURE_REASONS = (
    FAILURE_REASON_EMPTY,
    FAILURE_REASON_UNPARSEABLE,
    FAILURE_REASON_TRUNCATED_MAX_TOKENS,
    FAILURE_REASON_TRUNCATED_CONTEXT,
)


def normalize_label(raw_completion: str, labels: frozenset[str]) -> str | None:
    """Extract a member of `labels` from free-text model output, or None.

    Lowercases, strips punctuation/whitespace, and returns the first
    whitespace/punctuation-delimited token that exactly matches a member of
    `labels`. Never raises on malformed input.
    """
    for token in _TOKEN_RE.findall(raw_completion.lower()):
        if token in labels:
            return token
    return None


class ScoredItem(TypedDict):
    """One task-suite item's outcome for one model."""

    item_id: str
    expected_label: str
    predicted_label: str | None
    correct: bool
    failure_reason: str | None


class SuiteScore(TypedDict):
    """A suite's accuracy plus the failure counts it was aggregated over."""

    accuracy: float
    failure_counts: dict[str, int]


class LanguageCell(TypedDict):
    """One language's slice of a suite score: accuracy, sample size, mark."""

    accuracy: float
    n: int
    indicative: bool


def score_item(
    item: ClassificationItem,
    raw_completion: str,
    *,
    truncated: bool,
    generated_tokens: int,
    max_output_tokens: int,
) -> ScoredItem:
    """Score one completion, naming why it failed when it did.

    A generation fails one of four ways, checked in order: empty output,
    truncation (at the suite's own cap when `generated_tokens` reached
    `max_output_tokens`, otherwise at the model's own context limit), or
    label-free prose the completion could not be parsed into. A failed item
    is `correct=False` with `predicted_label=None` but stays in the suite's
    denominator -- it is scored, not dropped.
    """
    if raw_completion.strip() == "":
        return ScoredItem(
            item_id=item["item_id"],
            expected_label=item["expected_label"],
            predicted_label=None,
            correct=False,
            failure_reason=FAILURE_REASON_EMPTY,
        )

    if truncated:
        reason = (
            FAILURE_REASON_TRUNCATED_MAX_TOKENS
            if generated_tokens >= max_output_tokens
            else FAILURE_REASON_TRUNCATED_CONTEXT
        )
        return ScoredItem(
            item_id=item["item_id"],
            expected_label=item["expected_label"],
            predicted_label=None,
            correct=False,
            failure_reason=reason,
        )

    predicted_label = normalize_label(raw_completion, LABELS)
    if predicted_label is None:
        return ScoredItem(
            item_id=item["item_id"],
            expected_label=item["expected_label"],
            predicted_label=None,
            correct=False,
            failure_reason=FAILURE_REASON_UNPARSEABLE,
        )

    return ScoredItem(
        item_id=item["item_id"],
        expected_label=item["expected_label"],
        predicted_label=predicted_label,
        correct=predicted_label == item["expected_label"],
        failure_reason=None,
    )


def score_suite(scored_items: list[ScoredItem]) -> SuiteScore:
    """Return accuracy and the failure-reason counts over a list of scored items.

    Accuracy is 0.0 for an empty list rather than dividing by zero.
    `failure_counts` always carries all four taxonomy keys, 0 when absent.
    """
    failure_counts: dict[str, int] = dict.fromkeys(_FAILURE_REASONS, 0)
    for scored in scored_items:
        reason = scored["failure_reason"]
        if reason is not None:
            failure_counts[reason] += 1

    if not scored_items:
        accuracy = 0.0
    else:
        correct_count = sum(1 for item in scored_items if item["correct"])
        accuracy = correct_count / len(scored_items)

    return SuiteScore(accuracy=accuracy, failure_counts=failure_counts)


def score_suite_by_language(
    items: Sequence[ClassificationItem], scored_items: list[ScoredItem]
) -> dict[str, LanguageCell]:
    """Accuracy, n and the indicative mark per language, one cell per language.

    `items` and `scored_items` are zipped by position -- the same convention
    `quality_cli._score_and_write` already uses to pair a suite item with its
    scored outcome. `indicative` reuses `suite_gate.MIN_PER_LANGUAGE_CELL_ITEMS`
    rather than redeclaring the threshold, so the gate and the per-language
    score agree on what counts as too small a sample to trust.
    """
    by_language: dict[str, list[ScoredItem]] = {lang: [] for lang in LANGUAGES}
    for item, scored in zip(items, scored_items, strict=True):
        by_language[item["language"]].append(scored)

    cells: dict[str, LanguageCell] = {}
    for lang in LANGUAGES:
        lang_items = by_language[lang]
        n = len(lang_items)
        if n == 0:
            accuracy = 0.0
        else:
            correct_count = sum(1 for scored in lang_items if scored["correct"])
            accuracy = correct_count / n
        cells[lang] = LanguageCell(
            accuracy=accuracy, n=n, indicative=n < MIN_PER_LANGUAGE_CELL_ITEMS
        )
    return cells
