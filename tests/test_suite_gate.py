import pytest

from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.suite_gate import SuiteGateError, gate_suite


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


def test_real_classification_suite_is_indicative_for_count_and_language_share() -> None:
    result = gate_suite(CLASSIFICATION_TASK_SUITE)

    assert result["indicative"] is True
    reasons = " ".join(result["indicative_reasons"])
    assert "10" in reasons  # item count shortfall names the 10-item count
    assert "fr" in reasons
    assert "de" in reasons
