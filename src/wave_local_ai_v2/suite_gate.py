"""The suite gate: refuses an internally inconsistent suite, marks an
under-sized or language-imbalanced one indicative rather than passing or
failing it outright.

Duck-typed against any object exposing `item_id`, `language`, `provenance`,
`contamination_risk` -- not `isinstance` against `classification_suite`'s
`ClassificationItem` shape, per the story's "validates fields, not a suite
shape" and the epic's boundary that the suite-shape/registry work belongs to
a sibling epic.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TypedDict

MIN_SUITE_ITEMS = 20
MIN_LANGUAGE_SHARE = 0.25
MIN_PER_LANGUAGE_CELL_ITEMS = 10
LANGUAGES = ("en", "fr", "de")

_VALID_PROVENANCE = {"hand_written", "licensed", "public"}


class SuiteGateError(ValueError):
    """Raised when an item's language or provenance/contamination_risk
    declaration is missing, out of range, or internally inconsistent."""


class SuiteGateResult(TypedDict):
    item_count: int
    language_counts: dict[str, int]
    language_shares: dict[str, float]
    indicative: bool
    indicative_reasons: list[str]
    per_language_indicative: dict[str, bool]


def gate_suite(items: Iterable[Mapping[str, object]]) -> SuiteGateResult:
    """Validate every item's declaration, then compute counts, shares and verdict.

    Raises `SuiteGateError` on the first item whose language is missing or
    outside `LANGUAGES`, or whose provenance/contamination_risk declaration is
    missing or self-inconsistent -- this step checks the declaration's presence
    and internal consistency only, never its truth.
    """
    items = list(items)
    for item in items:
        _check_item_declaration(item)

    item_count = len(items)
    language_counts = {
        lang: sum(1 for item in items if item.get("language") == lang)
        for lang in LANGUAGES
    }
    language_shares = {
        lang: (count / item_count if item_count else 0.0)
        for lang, count in language_counts.items()
    }

    indicative_reasons: list[str] = []
    if item_count < MIN_SUITE_ITEMS:
        indicative_reasons.append(
            f"item_count {item_count} is below the minimum of {MIN_SUITE_ITEMS}"
        )
    for lang in LANGUAGES:
        share = language_shares[lang]
        if share < MIN_LANGUAGE_SHARE:
            indicative_reasons.append(
                f"language {lang!r} share {share:.0%} is below the minimum of "
                f"{MIN_LANGUAGE_SHARE:.0%}"
            )

    per_language_indicative = {
        lang: language_counts[lang] < MIN_PER_LANGUAGE_CELL_ITEMS for lang in LANGUAGES
    }

    return SuiteGateResult(
        item_count=item_count,
        language_counts=language_counts,
        language_shares=language_shares,
        indicative=bool(indicative_reasons),
        indicative_reasons=indicative_reasons,
        per_language_indicative=per_language_indicative,
    )


def _check_item_declaration(item: Mapping[str, object]) -> None:
    item_id = item.get("item_id", "<unknown>")

    # Refused, not counted-and-ignored: an item outside `LANGUAGES` still adds
    # to `item_count` while entering no bucket, so the shares below would sum to
    # less than 1 and a suite could report a compliant mix while a slice of it
    # was invisible to the check.
    if "language" not in item:
        raise SuiteGateError(f"item {item_id!r} is missing 'language'")
    language = item["language"]
    if language not in LANGUAGES:
        raise SuiteGateError(
            f"item {item_id!r} has a language outside {LANGUAGES}: {language!r}"
        )

    if "provenance" not in item:
        raise SuiteGateError(f"item {item_id!r} is missing 'provenance'")
    provenance = item["provenance"]
    if provenance not in _VALID_PROVENANCE:
        raise SuiteGateError(
            f"item {item_id!r} has an invalid provenance value: {provenance!r}"
        )

    if "contamination_risk" not in item:
        raise SuiteGateError(f"item {item_id!r} is missing 'contamination_risk'")
    expected_risk = provenance == "public"
    if item["contamination_risk"] != expected_risk:
        raise SuiteGateError(
            f"item {item_id!r} declares provenance={provenance!r} but "
            f"contamination_risk={item['contamination_risk']!r} (expected "
            f"{expected_risk!r})"
        )
