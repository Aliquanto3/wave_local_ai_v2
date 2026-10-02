import pytest

from wave_local_ai_v2 import suite_registry
from wave_local_ai_v2.suite_gate import (
    LEVEL_DEVELOPMENT,
    LEVEL_PUBLICATION,
    SuiteGateError,
    gate_suite,
)


def _item(item_id: str, language: str, *, provenance: str = "hand_written") -> dict:
    return {
        "item_id": item_id,
        "language": language,
        "provenance": provenance,
        "contamination_risk": provenance == "public",
    }


def _compliant_suite() -> list[dict]:
    # 40 items, 14 en / 13 fr / 13 de: every language >=25% share and >=10 items.
    items = []
    for i in range(14):
        items.append(_item(f"en-{i}", "en"))
    for i in range(13):
        items.append(_item(f"fr-{i}", "fr"))
    for i in range(13):
        items.append(_item(f"de-{i}", "de"))
    return items


def test_below_item_count_is_indicative_with_a_named_reason() -> None:
    suite = [_item(f"en-{i}", "en") for i in range(19)]

    result = gate_suite(suite)

    assert result["indicative"] is True
    assert any("19" in reason for reason in result["indicative_reasons"])


def test_below_language_share_is_indicative_with_a_named_reason() -> None:
    # 20 items, DE at 4 (20%) < 25% minimum.
    suite = (
        [_item(f"en-{i}", "en") for i in range(8)]
        + [_item(f"fr-{i}", "fr") for i in range(8)]
        + [_item(f"de-{i}", "de") for i in range(4)]
    )

    result = gate_suite(suite)

    assert result["indicative"] is True
    assert any("de" in reason for reason in result["indicative_reasons"])


def test_missing_provenance_raises() -> None:
    suite = [{"item_id": "x", "language": "en", "contamination_risk": False}]

    with pytest.raises(SuiteGateError, match="x"):
        gate_suite(suite)


def test_missing_language_raises() -> None:
    suite = [
        {"item_id": "x", "provenance": "hand_written", "contamination_risk": False}
    ]

    with pytest.raises(SuiteGateError, match="x"):
        gate_suite(suite)


def test_untagged_items_are_refused_rather_than_diluting_the_shares() -> None:
    # 40 items, 14 en / 13 fr / 13 de would pass every threshold; adding 10
    # items tagged with a language outside the closed set must refuse the suite,
    # not push it to a 50-item count whose three shares silently sum to 0.8.
    suite = _compliant_suite() + [_item(f"es-{i}", "es") for i in range(10)]

    with pytest.raises(SuiteGateError, match="es-0"):
        gate_suite(suite)


def test_self_inconsistent_declaration_raises() -> None:
    suite = [
        {
            "item_id": "x",
            "language": "en",
            "provenance": "public",
            "contamination_risk": False,
        }
    ]

    with pytest.raises(SuiteGateError, match="x"):
        gate_suite(suite)


def test_thin_per_language_cell_is_flagged_independent_of_overall_verdict() -> None:
    # 20 items total, en=5 (thin cell, <10) but still >=25% share (25%).
    suite = (
        [_item(f"en-{i}", "en") for i in range(5)]
        + [_item(f"fr-{i}", "fr") for i in range(8)]
        + [_item(f"de-{i}", "de") for i in range(7)]
    )

    result = gate_suite(suite)

    assert result["per_language_indicative"]["en"] is True


def test_fully_compliant_suite_is_not_indicative() -> None:
    result = gate_suite(_compliant_suite())

    assert result["indicative"] is False
    assert not any(result["per_language_indicative"].values())


def test_real_classification_suite_is_not_indicative_at_the_suite_level() -> None:
    result = gate_suite(suite_registry.resolve("classification-support-routing").items)

    assert result["indicative"] is False
    assert result["per_language_indicative"] == {
        "en": False,
        "fr": True,
        "de": True,
    }


def test_real_translation_suite_certifies_at_development_unchanged() -> None:
    result = gate_suite(suite_registry.resolve("translation-business-short-form").items)

    assert result["level"] == LEVEL_DEVELOPMENT
    assert result["indicative"] is False
    assert result["indicative_reasons"] == []
    assert result["per_language_indicative"] == {"en": True, "fr": True, "de": True}


@pytest.mark.parametrize(
    "suite_id", ["classification-support-routing", "translation-business-short-form"]
)
def test_both_hand_written_suites_certify_at_development(suite_id) -> None:
    definition = suite_registry.resolve(suite_id)

    assert definition.level == LEVEL_DEVELOPMENT
    assert definition.gate["level"] == LEVEL_DEVELOPMENT
    assert definition.gate == gate_suite(definition.items)


# --- the publication level ---------------------------------------------------


def _declared(item: dict, index: int) -> dict:
    return {
        **item,
        "licence": "CC-BY-SA-4.0",
        "source": "example-benchmark",
        "source_revision": f"rev-{index}",
    }


def _publication_suite(en: int, fr: int, de: int) -> list[dict]:
    items = (
        [_item(f"en-{i}", "en", provenance="public") for i in range(en)]
        + [_item(f"fr-{i}", "fr", provenance="public") for i in range(fr)]
        + [_item(f"de-{i}", "de", provenance="public") for i in range(de)]
    )
    return [_declared(item, index) for index, item in enumerate(items)]


_FLOOR = {"size_target": 100, "size_target_reason": "the source holds fewer than 300"}


def test_a_compliant_publication_suite_certifies_at_publication() -> None:
    result = gate_suite(
        _publication_suite(34, 33, 33), level=LEVEL_PUBLICATION, **_FLOOR
    )

    assert result["level"] == LEVEL_PUBLICATION
    assert result["indicative"] is False
    assert result["item_count"] == 100


def test_ninety_nine_items_at_publication_fails_naming_the_count() -> None:
    with pytest.raises(SuiteGateError, match="item_count 99 is below the publication"):
        gate_suite(_publication_suite(33, 33, 33), level=LEVEL_PUBLICATION, **_FLOOR)


def test_a_language_below_its_share_at_publication_fails_naming_the_language() -> None:
    # 100 items, de at 24%.
    with pytest.raises(SuiteGateError) as exc:
        gate_suite(_publication_suite(38, 38, 24), level=LEVEL_PUBLICATION, **_FLOOR)

    message = str(exc.value)
    assert "language 'de' share 24%" in message
    assert "item_count" not in message


def test_an_item_without_a_licence_or_a_source_fails_naming_the_item() -> None:
    suite = _publication_suite(34, 33, 33)
    del suite[0]["licence"]
    del suite[1]["source"]
    del suite[2]["source_revision"]

    with pytest.raises(SuiteGateError) as exc:
        gate_suite(suite, level=LEVEL_PUBLICATION, **_FLOOR)

    message = str(exc.value)
    assert "item 'en-0' declares no licence" in message
    assert "item 'en-1' declares no source" in message
    assert "item 'en-2' declares no source_revision" in message


def test_a_declared_300_target_holding_250_fails_naming_the_target() -> None:
    with pytest.raises(SuiteGateError, match="below the declared size_target of 300"):
        gate_suite(
            _publication_suite(84, 83, 83),
            level=LEVEL_PUBLICATION,
            size_target=300,
            size_target_reason="the source supplies 300 items per language mix",
        )


@pytest.mark.parametrize("size_target", [None, 200, True, "100"])
def test_a_publication_suite_without_a_valid_target_fails(size_target) -> None:
    with pytest.raises(SuiteGateError, match="is not a declared target"):
        gate_suite(
            _publication_suite(34, 33, 33),
            level=LEVEL_PUBLICATION,
            size_target=size_target,
            size_target_reason="why",
        )


def test_a_publication_suite_without_a_target_reason_fails() -> None:
    with pytest.raises(SuiteGateError, match="size_target_reason is missing"):
        gate_suite(
            _publication_suite(34, 33, 33), level=LEVEL_PUBLICATION, size_target=100
        )


def test_a_short_publication_suite_never_passes_at_development_instead() -> None:
    """The same items certify at development when they declare it, and are
    refused when they declare publication: the gate never downgrades."""
    suite = _publication_suite(30, 30, 30)

    assert gate_suite(suite)["level"] == LEVEL_DEVELOPMENT
    with pytest.raises(SuiteGateError, match="publication"):
        gate_suite(suite, level=LEVEL_PUBLICATION, **_FLOOR)


def test_an_unknown_level_is_refused() -> None:
    with pytest.raises(SuiteGateError, match="'draft'"):
        gate_suite(_compliant_suite(), level="draft")


def test_a_development_suite_declaring_a_size_target_is_refused() -> None:
    with pytest.raises(SuiteGateError, match="publication-level declaration"):
        gate_suite(_compliant_suite(), size_target=100)


@pytest.mark.parametrize("key", ["licence", "source", "source_revision"])
@pytest.mark.parametrize("value", ["", "  ", None, 4])
def test_a_malformed_item_declaration_is_refused_at_any_level(key, value) -> None:
    suite = _compliant_suite()
    suite[0][key] = value

    with pytest.raises(SuiteGateError, match=f"en-0.*malformed {key}"):
        gate_suite(suite)
