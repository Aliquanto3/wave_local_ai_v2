"""Deterministic label normalization and exact-match scoring.

No network, no randomness: given the same raw completion, `normalize_label` and
`score_item` always return the same result. This is what makes the quality
scores this module produces reproducible (same model + same prompt + same
completion => same score), unlike the runtime metrics in `timings.py`, which are
hardware-bound and never claimed to be reproducible across machines.
"""

from __future__ import annotations

import re
from typing import TypedDict

from wave_local_ai_v2.classification_suite import LABELS, ClassificationItem

_TOKEN_RE = re.compile(r"[a-z]+")


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


def score_item(item: ClassificationItem, raw_completion: str) -> ScoredItem:
    """Score one completion against its task-suite item's expected label."""
    predicted_label = normalize_label(raw_completion, LABELS)
    return ScoredItem(
        item_id=item["item_id"],
        expected_label=item["expected_label"],
        predicted_label=predicted_label,
        correct=predicted_label == item["expected_label"],
    )


def score_suite(scored_items: list[ScoredItem]) -> float:
    """Return accuracy (fraction correct) over a list of scored items.

    Returns 0.0 for an empty list rather than dividing by zero.
    """
    if not scored_items:
        return 0.0
    correct_count = sum(1 for item in scored_items if item["correct"])
    return correct_count / len(scored_items)
