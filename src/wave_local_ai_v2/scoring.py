"""Deterministic scoring: exact label match, and a graded reference score.

Two scorers live here, both deterministic and both sharing one failure
taxonomy. The exact-match one is the classification suite's: a completion is
normalized to a label and either matches the expected one or does not. The
graded one is any reference-scored suite's -- today the translation suite's
-- where a completion is scored against a written reference by `chrf.py` and
lands anywhere on `0..1`. They are kept apart deliberately: a chrF mean is
not an accuracy, and one function returning either would publish a graded
score under an exact-match name (plan.md's D4).

No network, no randomness: given the same raw completion and the same caller-
supplied truncation facts, both scorers always return the same result. This
is what makes the quality scores this module produces reproducible (same
model + same prompt + same completion => same score), unlike the runtime
metrics in `timings.py`, which are hardware-bound and never claimed to be
reproducible across machines. Both decide the four-way failure taxonomy
themselves, but stay provider-agnostic: they take only
`truncated`/`generated_tokens`/`max_output_tokens` as plain facts, never a
provider's raw response shape -- that mapping belongs to each provider's own
caller (`quality_cli.py`).
"""

from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TypedDict

from wave_local_ai_v2.chrf import chrf
from wave_local_ai_v2.classification_suite import LABELS, ClassificationItem
from wave_local_ai_v2.suite_gate import LANGUAGES, MIN_PER_LANGUAGE_CELL_ITEMS
from wave_local_ai_v2.translation_suite import TranslationItem

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


def _truncation_reason(
    *,
    truncation_reason: str | None,
    generated_tokens: int,
    max_output_tokens: int,
) -> str:
    """Which truncation the caller is reporting, validated.

    Shared by both scorers so the two never drift on which reason a set of
    facts maps to. A caller-supplied reason is used as-is and must be one of
    the two truncation members of the taxonomy; anything else is a caller
    bug and raises rather than being silently coerced.
    """
    if truncation_reason is None:
        return (
            FAILURE_REASON_TRUNCATED_MAX_TOKENS
            if generated_tokens >= max_output_tokens
            else FAILURE_REASON_TRUNCATED_CONTEXT
        )
    if truncation_reason not in (
        FAILURE_REASON_TRUNCATED_MAX_TOKENS,
        FAILURE_REASON_TRUNCATED_CONTEXT,
    ):
        raise ValueError(
            f"truncation_reason must be "
            f"{FAILURE_REASON_TRUNCATED_MAX_TOKENS!r} or "
            f"{FAILURE_REASON_TRUNCATED_CONTEXT!r}, got {truncation_reason!r}"
        )
    return truncation_reason


def score_item(
    item: ClassificationItem,
    raw_completion: str,
    *,
    truncated: bool,
    generated_tokens: int,
    max_output_tokens: int,
    truncation_reason: str | None = None,
) -> ScoredItem:
    """Score one completion, naming why it failed when it did.

    A generation fails one of four ways, checked in order: empty output,
    truncation (at the suite's own cap when `generated_tokens` reached
    `max_output_tokens`, otherwise at the model's own context limit), or
    label-free prose the completion could not be parsed into. A failed item
    is `correct=False` with `predicted_label=None` but stays in the suite's
    denominator -- it is scored, not dropped.

    `truncation_reason`, when given and `truncated` is True, is used as-is
    instead of the `generated_tokens >= max_output_tokens` comparison -- it
    must be `FAILURE_REASON_TRUNCATED_MAX_TOKENS` or
    `FAILURE_REASON_TRUNCATED_CONTEXT`, anything else is a caller bug. Some
    providers (Google) report fewer generated tokens than the cap they
    actually enforced, which makes the token-count comparison alone
    misclassify a cap-truncated item as context-truncated; a caller that
    already knows the cause from its own response shape passes it directly.
    Every existing call site (Mistral, local) passes nothing and keeps
    today's comparison unchanged.
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
        reason = _truncation_reason(
            truncation_reason=truncation_reason,
            generated_tokens=generated_tokens,
            max_output_tokens=max_output_tokens,
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


class GradedItem(TypedDict):
    """One reference-scored item's outcome for one model.

    Deliberately carries no `correct` and no `predicted_label`: `correct` is
    a boolean and a chrF is not, and there is no label to predict on a
    reference-scored suite (plan.md's D4). A row built from this nulls both.
    """

    item_id: str
    item_score: float
    failure_reason: str | None


class GradedSuiteScore(TypedDict):
    """A suite's mean score plus the failure counts it was aggregated over."""

    suite_score: float
    failure_counts: dict[str, int]


class GradedLanguageCell(TypedDict):
    """One language's slice of a graded suite score: score, sample size, mark.

    The key is `score`, not `accuracy`. A chrF mean and an exact-match rate
    are different statistics, and one key that held either would be
    unnameable in a store that publishes both.
    """

    score: float
    n: int
    indicative: bool


def score_translation_item(
    item: TranslationItem,
    raw_completion: str,
    *,
    truncated: bool,
    generated_tokens: int,
    max_output_tokens: int,
    truncation_reason: str | None = None,
) -> GradedItem:
    """Score one completion against its reference translation, on `0..1`.

    The same checks in the same order as `score_item`: empty output first,
    then truncation (at the suite's own cap when `generated_tokens` reached
    `max_output_tokens`, otherwise at the model's own context limit, with the
    same caller-supplied-reason override), then the score itself. A failed
    generation is `item_score=0.0` with its named reason and stays in the
    suite's denominator -- it is scored, not dropped.

    There is no `unparseable` branch, and the absence is deliberate: that
    reason names a completion no member of a closed label set could be found
    in, and a translation has no closed set. The raw completion is handed to
    `chrf` after whitespace normalisation only, with no preamble stripped and
    no paragraph selected (plan.md's Decisions) -- any such extraction rule
    would be a scoring choice invented here that sacreBLEU would not
    reproduce, so a model that answers "Sure! Here it is: ..." is genuinely
    worse at the instruction and its score says so.
    """
    if raw_completion.strip() == "":
        return GradedItem(
            item_id=item["item_id"],
            item_score=0.0,
            failure_reason=FAILURE_REASON_EMPTY,
        )

    if truncated:
        return GradedItem(
            item_id=item["item_id"],
            item_score=0.0,
            failure_reason=_truncation_reason(
                truncation_reason=truncation_reason,
                generated_tokens=generated_tokens,
                max_output_tokens=max_output_tokens,
            ),
        )

    return GradedItem(
        item_id=item["item_id"],
        item_score=chrf(item["reference"], raw_completion),
        failure_reason=None,
    )


def score_graded_suite(graded_items: list[GradedItem]) -> GradedSuiteScore:
    """Return the mean item score and the failure-reason counts over a batch.

    The mean is arithmetic over *every* item, failures included as their
    0.0 -- dropping them would let a model raise its published score by
    failing to answer. `suite_score` is 0.0 for an empty list rather than
    dividing by zero, and `failure_counts` always carries all four taxonomy
    keys, 0 when absent, mirroring `score_suite`.
    """
    failure_counts: dict[str, int] = dict.fromkeys(_FAILURE_REASONS, 0)
    for graded in graded_items:
        reason = graded["failure_reason"]
        if reason is not None:
            failure_counts[reason] += 1

    if not graded_items:
        suite_score = 0.0
    else:
        suite_score = sum(graded["item_score"] for graded in graded_items) / len(
            graded_items
        )

    return GradedSuiteScore(suite_score=suite_score, failure_counts=failure_counts)


def score_graded_suite_by_language(
    items: Sequence[TranslationItem], graded_items: list[GradedItem]
) -> dict[str, GradedLanguageCell]:
    """Score, n and the indicative mark per language, one cell per language.

    How Methodology 4's per-language requirement is met on a graded suite:
    the headline number is broken down by the item's source `language`, and a
    cell too small to trust says so rather than being dropped or silently
    reported as if it were the same evidence as a full one.

    `items` and `graded_items` are zipped by position with `strict=True` --
    the same convention `score_suite_by_language` uses -- and `indicative`
    reuses `suite_gate.MIN_PER_LANGUAGE_CELL_ITEMS` rather than redeclaring
    the threshold, so the gate and the per-language score agree on what
    counts as too small a sample.
    """
    by_language: dict[str, list[GradedItem]] = {lang: [] for lang in LANGUAGES}
    for item, graded in zip(items, graded_items, strict=True):
        by_language[item["language"]].append(graded)

    cells: dict[str, GradedLanguageCell] = {}
    for lang in LANGUAGES:
        lang_items = by_language[lang]
        n = len(lang_items)
        if n == 0:
            score = 0.0
        else:
            score = sum(graded["item_score"] for graded in lang_items) / n
        cells[lang] = GradedLanguageCell(
            score=score, n=n, indicative=n < MIN_PER_LANGUAGE_CELL_ITEMS
        )
    return cells
