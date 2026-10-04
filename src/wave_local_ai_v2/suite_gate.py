"""The suite gate: refuses an internally inconsistent suite, and certifies a
consistent one at the level it declares.

Two levels (Methodology 4). A `development` suite is gated as it always was:
an under-sized or language-imbalanced one is marked indicative rather than
passed or failed outright. A `publication` suite is certified there or
refused: at least `MIN_PUBLICATION_SUITE_ITEMS` items and at least its
declared size target, the same per-language share, a declared size target
with the reason it was chosen, and a licence, a source and that source's
revision on every item. A shortfall raises naming every one of them -- a
suite that claims the publication level never passes quietly at the
development one.

Licence, source and revision are author declarations (Methodology 5): the
gate checks they are present and well formed, never that they are true.

Duck-typed against any object exposing `item_id`, `language`, `provenance`,
`contamination_risk` (and, where declared, `licence`, `source`,
`source_revision`) -- not `isinstance` against `classification_suite`'s
`ClassificationItem` shape, per the story's "validates fields, not a suite
shape" and the epic's boundary that the suite-shape/registry work belongs to
a sibling epic.

Every suite also declares the per-item divergence tolerance its cloud
subjects' re-runs are decided under (Methodology 8): a value, its unit and the
reason for that value. `gate_divergence_tolerance` refuses a suite that
declares none or a malformed one; the registry runs it on every load beside
`gate_suite`, so no suite without a tolerance can be resolved.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import TypedDict

MIN_SUITE_ITEMS = 20
MIN_LANGUAGE_SHARE = 0.25
MIN_PER_LANGUAGE_CELL_ITEMS = 10
LANGUAGES = ("en", "fr", "de")

LEVEL_DEVELOPMENT = "development"
LEVEL_PUBLICATION = "publication"
SUITE_LEVELS = frozenset({LEVEL_DEVELOPMENT, LEVEL_PUBLICATION})

# The publication floor, whatever target the suite declares.
MIN_PUBLICATION_SUITE_ITEMS = 100
# The two targets a publication suite may declare: 300 where its public
# source supplies them, the 100-item floor where it does not.
PUBLICATION_SIZE_TARGETS = (MIN_PUBLICATION_SUITE_ITEMS, 300)

# The licence every hand-written item of this repository is published under.
HAND_WRITTEN_LICENCE = "CC-BY-4.0"

# The per-item declarations a publication suite owes on every item, and that
# any suite's item may carry.
ITEM_SOURCE_DECLARATIONS = ("licence", "source", "source_revision")

_VALID_PROVENANCE = {"hand_written", "licensed", "public"}

# The divergence tolerance's one unit: the share of a batch's items whose
# compared per-item value (`verdict.quality_verdict`'s `compared_field`)
# differs from the reference. One unit serves an exact-match and a graded
# suite alike, since both are compared on one per-item value.
TOLERANCE_UNIT_FRACTION_OF_ITEMS = "fraction_of_items"
TOLERANCE_UNITS = frozenset({TOLERANCE_UNIT_FRACTION_OF_ITEMS})
DIVERGENCE_TOLERANCE_KEY = "divergence_tolerance"


class SuiteGateError(ValueError):
    """Raised when an item's declaration is missing, out of range, or
    internally inconsistent, or when a suite falls short of the level it
    declares."""


class DivergenceTolerance(TypedDict):
    value: float
    unit: str
    reason: str


class SuiteGateResult(TypedDict):
    # The level the suite was certified at: always the level it declared,
    # since a suite that falls short of it is refused rather than downgraded.
    level: str
    item_count: int
    language_counts: dict[str, int]
    language_shares: dict[str, float]
    indicative: bool
    indicative_reasons: list[str]
    per_language_indicative: dict[str, bool]


def gate_suite(
    items: Iterable[Mapping[str, object]],
    *,
    level: str = LEVEL_DEVELOPMENT,
    size_target: object = None,
    size_target_reason: object = None,
) -> SuiteGateResult:
    """Validate every item's declaration, then certify the suite at `level`.

    Raises `SuiteGateError` on the first item whose language is missing or
    outside `LANGUAGES`, whose provenance/contamination_risk declaration is
    missing or self-inconsistent, or whose declared licence, source or source
    revision is not a non-empty string -- this step checks the declaration's
    presence and internal consistency only, never its truth. Raises too on an
    unknown level, on a size target declared by a development suite, and on a
    publication suite that falls short, naming every shortfall.
    """
    if level not in SUITE_LEVELS:
        raise SuiteGateError(
            f"suite declares level {level!r}, not one of "
            f"{', '.join(sorted(SUITE_LEVELS))}"
        )
    if level == LEVEL_DEVELOPMENT and (
        size_target is not None or size_target_reason is not None
    ):
        raise SuiteGateError(
            "suite declares level 'development' with a size target: a size "
            "target is a publication-level declaration"
        )

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

    count_reasons: list[str] = []
    if item_count < MIN_SUITE_ITEMS:
        count_reasons.append(
            f"item_count {item_count} is below the minimum of {MIN_SUITE_ITEMS}"
        )
    share_reasons: list[str] = []
    for lang in LANGUAGES:
        share = language_shares[lang]
        if share < MIN_LANGUAGE_SHARE:
            share_reasons.append(
                f"language {lang!r} share {share:.0%} is below the minimum of "
                f"{MIN_LANGUAGE_SHARE:.0%}"
            )
    indicative_reasons = count_reasons + share_reasons

    if level == LEVEL_PUBLICATION:
        shortfalls = _publication_shortfalls(
            items, item_count, size_target, size_target_reason
        )
        shortfalls += share_reasons
        if shortfalls:
            raise SuiteGateError(
                "suite declares level 'publication' and falls short of it: "
                + "; ".join(shortfalls)
            )

    per_language_indicative = {
        lang: language_counts[lang] < MIN_PER_LANGUAGE_CELL_ITEMS for lang in LANGUAGES
    }

    return SuiteGateResult(
        level=level,
        item_count=item_count,
        language_counts=language_counts,
        language_shares=language_shares,
        indicative=bool(indicative_reasons),
        indicative_reasons=indicative_reasons,
        per_language_indicative=per_language_indicative,
    )


def gate_divergence_tolerance(declaration: object) -> DivergenceTolerance:
    """Refuse a missing or malformed divergence tolerance; return it checked.

    The declaration is `{"value", "unit", "reason"}`: a number in `[0, 1]`
    under `TOLERANCE_UNITS`, and a non-empty reason recording what the value
    was set against, so a reader can dispute the value itself. Its truth is
    not checked here, only its presence and shape.
    """
    if declaration is None:
        raise SuiteGateError(
            f"suite declares no {DIVERGENCE_TOLERANCE_KEY}: every suite states "
            "the per-item divergence a cloud subject's re-run is decided under"
        )
    if not isinstance(declaration, Mapping):
        raise SuiteGateError(
            f"suite declares a malformed {DIVERGENCE_TOLERANCE_KEY}: "
            f"{declaration!r} is not an object with value, unit and reason"
        )
    value = declaration.get("value")
    if (
        not isinstance(value, int | float)
        or isinstance(value, bool)
        or not 0 <= value <= 1
    ):
        raise SuiteGateError(
            f"{DIVERGENCE_TOLERANCE_KEY} value {value!r} is not a number in [0, 1]"
        )
    unit = declaration.get("unit")
    if unit not in TOLERANCE_UNITS:
        raise SuiteGateError(
            f"{DIVERGENCE_TOLERANCE_KEY} unit {unit!r} is not one of "
            f"{', '.join(sorted(TOLERANCE_UNITS))}"
        )
    reason = declaration.get("reason")
    if not (isinstance(reason, str) and reason.strip()):
        raise SuiteGateError(
            f"{DIVERGENCE_TOLERANCE_KEY} reason is missing: a suite records why "
            "its tolerance has the value it has"
        )
    return DivergenceTolerance(value=float(value), unit=unit, reason=reason)


def _publication_shortfalls(
    items: list[Mapping[str, object]],
    item_count: int,
    size_target: object,
    size_target_reason: object,
) -> list[str]:
    """Every way a suite falls short of the publication level, except the
    language shares, which the development check already names."""
    shortfalls: list[str] = []
    if item_count < MIN_PUBLICATION_SUITE_ITEMS:
        shortfalls.append(
            f"item_count {item_count} is below the publication floor of "
            f"{MIN_PUBLICATION_SUITE_ITEMS}"
        )
    targets = ", ".join(str(target) for target in PUBLICATION_SIZE_TARGETS)
    if (
        not isinstance(size_target, int)
        or isinstance(size_target, bool)
        or size_target not in PUBLICATION_SIZE_TARGETS
    ):
        shortfalls.append(
            f"size_target {size_target!r} is not a declared target (one of {targets})"
        )
    elif item_count < size_target:
        shortfalls.append(
            f"item_count {item_count} is below the declared size_target of "
            f"{size_target}"
        )
    if not (isinstance(size_target_reason, str) and size_target_reason.strip()):
        shortfalls.append(
            "size_target_reason is missing: a publication suite records why it "
            "was built to its target"
        )
    for item in items:
        missing = [key for key in ITEM_SOURCE_DECLARATIONS if key not in item]
        if missing:
            shortfalls.append(
                f"item {item.get('item_id', '<unknown>')!r} declares no "
                f"{', '.join(missing)}"
            )
    return shortfalls


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

    # Optional at the development level, owed at the publication one: where
    # declared, each is a non-empty string, never a placeholder.
    for key in ITEM_SOURCE_DECLARATIONS:
        if key in item:
            value = item[key]
            if not (isinstance(value, str) and value.strip()):
                raise SuiteGateError(
                    f"item {item_id!r} declares a malformed {key}: {value!r}"
                )
