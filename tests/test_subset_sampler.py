import copy
import hashlib
import json
import random
from collections import Counter

import pytest
from subset_fixtures import (
    BENCHMARK,
    CLASSIFICATION_SPEC,
    LOADER,
    SOURCE,
    TRANSLATION_SPEC,
    classification_source,
    drawn_definition,
    publication_gate_accepts,
)

from wave_local_ai_v2 import subset_sampler, suite_gate
from wave_local_ai_v2.subset_sampler import SubsetSamplerError


def _ids(items) -> list[str]:
    return [item["item_id"] for item in items]


def _row(rows, item_id: str) -> dict:
    return next(row for row in rows if f"{SOURCE}:{row['id']}" == item_id)


# --- the draw -------------------------------------------------------------------


def test_the_same_seed_and_source_return_the_same_ids_in_the_same_order() -> None:
    rows = classification_source()

    first = subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)
    second = subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)

    assert first == second
    assert len(first) == 102


def test_a_shuffled_source_returns_the_same_ids_in_the_same_order() -> None:
    rows = classification_source()
    shuffled = copy.deepcopy(rows)
    random.Random(1234).shuffle(shuffled)
    assert shuffled != rows

    assert subset_sampler.draw(shuffled, CLASSIFICATION_SPEC, 7) == (
        subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)
    )


def test_a_changed_seed_changes_the_ids() -> None:
    rows = classification_source()

    assert _ids(subset_sampler.draw(rows, CLASSIFICATION_SPEC, 8)) != _ids(
        subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)
    )


def test_a_classification_draw_is_stratified_by_language_and_label() -> None:
    rows = classification_source()
    items = subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)

    languages = Counter(item["language"] for item in items)
    cells = Counter(
        (item["language"], _row(rows, item["item_id"])["intent"]) for item in items
    )

    assert languages == {"en": 34, "fr": 34, "de": 34}
    # 34 over four labels in sorted order: account, billing, other, technical.
    for language in suite_gate.LANGUAGES:
        assert [
            cells[(language, label)]
            for label in ("account", "billing", "other", "technical")
        ] == [9, 9, 8, 8]


def test_a_translation_draw_is_stratified_by_language_only() -> None:
    items = subset_sampler.draw(classification_source(), TRANSLATION_SPEC, 7)

    assert Counter(item["language"] for item in items) == {
        "en": 34,
        "fr": 34,
        "de": 34,
    }


def test_each_drawn_item_carries_its_terms_and_its_content_hash() -> None:
    rows = classification_source()
    item = subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)[0]

    assert item["item_id"].startswith(f"{SOURCE}:")
    assert (item["provenance"], item["contamination_risk"]) == ("public", True)
    assert (item["licence"], item["source"], item["source_revision"]) == (
        "CC-BY-4.0",
        SOURCE,
        "rev-1",
    )
    assert item["content_hash"] == subset_sampler.content_hash(
        _row(rows, item["item_id"]), ("text", "intent"), BENCHMARK
    )


def test_the_draw_certifies_at_publication_on_the_first_seed() -> None:
    items, rule = subset_sampler.draw_with_retries(
        classification_source(),
        CLASSIFICATION_SPEC,
        first_seed=7,
        accept=publication_gate_accepts,
        loader=LOADER,
    )

    assert (rule["attempts"], rule["seeds_tried"], rule["seed"]) == (1, [7], 7)
    result = suite_gate.gate_suite(
        items, level="publication", size_target=100, size_target_reason="small"
    )
    assert result["level"] == "publication"


# Pinned, not recomputed: these fail the CI matrix (ubuntu and windows) when a
# Python release or a platform draws other items from the same seed and
# source, rather than letting a redraw silently pick a different subset.
_GOLDEN_FIRST_IDS = [
    "fixture-intents:en-account-05",
    "fixture-intents:en-account-02",
    "fixture-intents:en-account-06",
    "fixture-intents:en-account-10",
    "fixture-intents:en-account-00",
    "fixture-intents:en-account-01",
]
_GOLDEN_IDS_SHA256 = "f1d753f08078c63f1eeccd9a25897a05f3a6e562770de54442cc27e47feced6b"  # pragma: allowlist secret
_GOLDEN_DEFINITION_SHA256 = "5d36642f779cfd82a9f9a3771da2114fb41e76d108e151d1cd7e9b7b1e0322bb"  # pragma: allowlist secret


def test_seed_7_draws_the_pinned_items_in_the_pinned_order() -> None:
    definition, _ = drawn_definition(seed=7)
    ids = _ids(definition["items"])

    assert ids[:6] == _GOLDEN_FIRST_IDS
    assert hashlib.sha256("\n".join(ids).encode("utf-8")).hexdigest() == (
        _GOLDEN_IDS_SHA256
    )
    assert definition["selection_rule"]["generator"] == {
        "library": "CPython random.Random",
        "version": "3.12",
    }
    assert (
        hashlib.sha256(
            json.dumps(definition, sort_keys=True).encode("utf-8")
        ).hexdigest()
        == _GOLDEN_DEFINITION_SHA256
    )


def test_the_rule_records_every_field_the_replay_needs() -> None:
    definition, _ = drawn_definition()

    assert definition["selection_rule"] == {
        "sampler_version": "1",
        "seed": 7,
        "attempts": 1,
        "seeds_tried": [7],
        "loader": {"library": "json", "version": "stdlib"},
        "generator": subset_sampler.drawing_generator(),
        "stable_source_key": "id",
        "canonical_ordering": "source-then-stable-key-ascending",
        "stratify_by": ["language", "intent"],
        "content_fields": ["text", "intent"],
        "size": 102,
        "benchmarks": [
            {"source": SOURCE, "licence": "CC-BY-4.0", "source_revision": "rev-1"}
        ],
    }
    assert (
        subset_sampler.check_selection_rule(
            definition["selection_rule"], "classification"
        )
        == []
    )


def test_a_retried_draw_records_every_seed_tried() -> None:
    refusals = iter([False, False, True])

    _, rule = subset_sampler.draw_with_retries(
        classification_source(),
        CLASSIFICATION_SPEC,
        first_seed=7,
        accept=lambda items: next(refusals),
        loader=LOADER,
    )

    assert (rule["attempts"], rule["seeds_tried"], rule["seed"]) == (3, [7, 8, 9], 9)
    assert subset_sampler.check_selection_rule(rule, "classification") == []


def test_a_draw_no_seed_satisfies_names_every_seed_tried() -> None:
    with pytest.raises(SubsetSamplerError, match="seeds tried: 7, 8, 9"):
        subset_sampler.draw_with_retries(
            classification_source(),
            CLASSIFICATION_SPEC,
            first_seed=7,
            accept=lambda items: False,
            loader=LOADER,
            max_attempts=3,
        )


def test_a_stratum_the_source_cannot_fill_is_refused_naming_it() -> None:
    rows = [
        row
        for row in classification_source(per_label=15)
        if not (
            row["language"] == "de"
            and row["intent"] == "other"
            and row["id"] > "de-other-03"
        )
    ]

    with pytest.raises(SubsetSamplerError, match="language 'de', label 'other'"):
        subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)


def test_a_language_the_source_lacks_is_refused_naming_it() -> None:
    rows = [row for row in classification_source() if row["language"] != "fr"]

    with pytest.raises(SubsetSamplerError, match="stratum language 'fr' holds 0"):
        subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)
    with pytest.raises(SubsetSamplerError, match="stratum language 'fr' holds 0"):
        subset_sampler.draw(rows, TRANSLATION_SPEC, 7)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"source": "elsewhere"}, "does not draw from"),
        ({"id": ""}, "no stable source key"),
        ({"id": True}, "no stable source key"),
        ({"language": "es"}, "language outside"),
    ],
)
def test_a_source_row_the_rule_cannot_place_is_refused(change, message) -> None:
    rows = classification_source()
    rows[0] = {**rows[0], **change}

    with pytest.raises(SubsetSamplerError, match=message):
        subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)


def test_a_duplicate_source_key_is_refused() -> None:
    rows = classification_source()
    rows.append(dict(rows[0]))

    with pytest.raises(SubsetSamplerError, match="twice"):
        subset_sampler.draw(rows, CLASSIFICATION_SPEC, 7)


def test_an_integer_stable_key_orders_by_its_string_form() -> None:
    rows = [{**row, "id": index} for index, row in enumerate(classification_source())]

    items = subset_sampler.draw(rows, TRANSLATION_SPEC, 7)

    assert all(item["item_id"].startswith(f"{SOURCE}:") for item in items)


# --- the content hash -------------------------------------------------------------


def test_the_content_hash_ignores_whitespace_and_composition_only() -> None:
    row = {"text": "Café  ouvert\n"}
    same = {"text": "Café ouvert"}
    edited = {"text": "Café fermé"}

    assert subset_sampler.content_hash(row, ("text",), BENCHMARK) == (
        subset_sampler.content_hash(same, ("text",), BENCHMARK)
    )
    assert subset_sampler.content_hash(row, ("text",), BENCHMARK) != (
        subset_sampler.content_hash(edited, ("text",), BENCHMARK)
    )


def test_the_content_hash_covers_the_licence_and_the_revision() -> None:
    row = {"text": "hello"}
    relicensed = subset_sampler.Benchmark(SOURCE, "CC-BY-SA-4.0", "rev-1")
    revised = subset_sampler.Benchmark(SOURCE, "CC-BY-4.0", "rev-2")

    hashes = {
        subset_sampler.content_hash(row, ("text",), benchmark)
        for benchmark in (BENCHMARK, relicensed, revised)
    }
    assert len(hashes) == 3


def test_a_row_missing_a_content_field_is_refused() -> None:
    with pytest.raises(SubsetSamplerError, match="no text field 'text'"):
        subset_sampler.content_hash({"intent": "billing"}, ("text",), BENCHMARK)


# --- the replay -------------------------------------------------------------------


def test_replaying_the_rule_over_the_same_source_reproduces_it() -> None:
    definition, rows = drawn_definition()
    random.Random(99).shuffle(rows)

    report = subset_sampler.replay(
        definition["items"], definition["selection_rule"], rows
    )

    assert report.reproduced
    assert report.recorded_ids == report.redrawn_ids
    assert report.first_difference is None


def test_an_edited_source_item_is_named_by_its_id_on_replay() -> None:
    definition, rows = drawn_definition()
    target = definition["items"][5]["item_id"]
    row = _row(rows, target)
    row["text"] = row["text"] + " (edited upstream)"

    report = subset_sampler.replay(
        definition["items"], definition["selection_rule"], rows
    )

    assert report.edited == (target,)
    assert report.recorded_ids == report.redrawn_ids
    assert not report.reproduced


def test_a_retagged_source_item_is_named_by_its_id_on_replay() -> None:
    definition, rows = drawn_definition()
    target = definition["items"][0]["item_id"]
    row = _row(rows, target)
    row["intent"] = "other" if row["intent"] != "other" else "billing"

    report = subset_sampler.replay(
        definition["items"], definition["selection_rule"], rows
    )

    assert target in report.edited


def test_a_source_item_removed_upstream_is_named_as_absent() -> None:
    definition, rows = drawn_definition()
    target = definition["items"][0]["item_id"]
    rows.remove(_row(rows, target))

    report = subset_sampler.replay(
        definition["items"], definition["selection_rule"], rows
    )

    assert report.absent == (target,)
    assert report.first_difference is not None


def test_a_changed_rule_seed_replays_to_other_ids() -> None:
    definition, rows = drawn_definition()
    rule = {**definition["selection_rule"], "seed": 8, "seeds_tried": [8]}

    report = subset_sampler.replay(definition["items"], rule, rows)

    assert report.first_difference is not None
    assert not report.reproduced


def test_a_shorter_redraw_differs_at_its_end() -> None:
    report = subset_sampler.ReplayReport(
        recorded_ids=("a", "b"), redrawn_ids=("a",), edited=(), absent=()
    )

    assert report.first_difference == 1


# --- the rule check ---------------------------------------------------------------


def _rule(**changes) -> dict:
    definition, _ = drawn_definition()
    return {**definition["selection_rule"], **changes}


@pytest.mark.parametrize(
    ("rule", "message"),
    [
        ("seed 7", "is not an object"),
        ({}, "is missing attempts, benchmarks"),
        (_rule(extra=1), "unknown extra"),
        (_rule(sampler_version="2"), "sampler_version '2'"),
        (_rule(canonical_ordering="as-loaded"), "canonical_ordering 'as-loaded'"),
        (_rule(seed="7"), "must be integers"),
        (_rule(attempts=0, seeds_tried=[]), "attempts 0 is below 1"),
        (_rule(seeds_tried=[True]), "integers only"),
        (_rule(seed=9, attempts=3, seeds_tried=[9]), "1 seeds for 3 attempts"),
        (_rule(seed=9, attempts=2, seeds_tried=[9, 9]), "one seed twice"),
        (_rule(seed=9, attempts=2, seeds_tried=[9, 8]), "is not the recorded seed"),
        (_rule(loader={"library": "json"}), "loader"),
        (_rule(generator={"library": "x", "version": ""}), "generator"),
        (_rule(stable_source_key=" "), "stable_source_key"),
        (_rule(content_fields=[]), "content_fields"),
        (_rule(stratify_by=["language"]), "for a classification suite"),
        (_rule(stratify_by=["intent", "language"]), "for a classification suite"),
        (_rule(content_fields=["text"]), "not among content_fields"),
        (_rule(size=0), "size 0"),
        (_rule(benchmarks=[]), "benchmarks must"),
        (_rule(benchmarks=[{"source": SOURCE}]), "benchmarks must"),
        (
            _rule(
                benchmarks=[
                    {"source": SOURCE, "licence": "x", "source_revision": "y"},
                    {"source": SOURCE, "licence": "x", "source_revision": "z"},
                ]
            ),
            "one source twice",
        ),
    ],
)
def test_a_rule_that_cannot_be_replayed_is_refused(rule, message) -> None:
    problems = subset_sampler.check_selection_rule(rule, "classification")

    assert any(message in problem for problem in problems), problems


def test_a_non_classification_rule_stratifies_by_language_only() -> None:
    assert (
        subset_sampler.check_selection_rule(
            _rule(stratify_by=["language"]), "translation"
        )
        == []
    )
    assert subset_sampler.check_selection_rule(_rule(), "translation") == [
        "stratify_by ['language', 'intent'] is not ['language']"
    ]


# --- the drawn items against their rule -------------------------------------------


def test_drawn_items_matching_their_rule_pass() -> None:
    definition, _ = drawn_definition()

    assert (
        subset_sampler.check_drawn_items(
            definition["items"], definition["selection_rule"]
        )
        == []
    )


def test_drawn_items_disagreeing_with_their_rule_are_named() -> None:
    definition, _ = drawn_definition()
    items = definition["items"][:4]
    items[0] = {key: value for key, value in items[0].items() if key != "content_hash"}
    items[1] = {**items[1], "content_hash": "not-a-hash"}
    items[2] = {**items[2], "source": "elsewhere"}
    items[3] = {**items[3], "licence": "MIT"}

    problems = subset_sampler.check_drawn_items(items, definition["selection_rule"])

    assert problems[0] == "the suite holds 4 items, its selection rule draws 102"
    assert any("carries no content_hash" in problem for problem in problems)
    assert any("not a SHA-256 hex digest" in problem for problem in problems)
    assert any("not drawn from a benchmark" in problem for problem in problems)
    assert any("other than its benchmark" in problem for problem in problems)
