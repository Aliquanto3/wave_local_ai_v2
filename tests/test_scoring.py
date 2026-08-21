from wave_local_ai_v2.classification_suite import LABELS, ClassificationItem
from wave_local_ai_v2.scoring import normalize_label, score_item, score_suite


def test_normalize_label_matches_clean_completion() -> None:
    assert normalize_label("billing", LABELS) == "billing"


def test_normalize_label_strips_whitespace_and_case() -> None:
    assert normalize_label("  Technical \n", LABELS) == "technical"


def test_normalize_label_matches_first_label_token_in_longer_text() -> None:
    assert (
        normalize_label("The category is account, based on the message.", LABELS)
        == "account"
    )


def test_normalize_label_returns_none_for_unparseable_completion() -> None:
    assert normalize_label("I'm not sure how to classify this one.", LABELS) is None


def test_score_item_correct_when_predicted_matches_expected() -> None:
    item = ClassificationItem(item_id="x", prompt="p", expected_label="billing")

    scored = score_item(item, "billing")

    assert scored["correct"] is True
    assert scored["predicted_label"] == "billing"


def test_score_item_incorrect_when_predicted_differs() -> None:
    item = ClassificationItem(item_id="x", prompt="p", expected_label="billing")

    scored = score_item(item, "technical")

    assert scored["correct"] is False
    assert scored["predicted_label"] == "technical"


def test_score_item_incorrect_and_no_raise_when_unparseable() -> None:
    item = ClassificationItem(item_id="x", prompt="p", expected_label="billing")

    scored = score_item(item, "no idea honestly")

    assert scored["correct"] is False
    assert scored["predicted_label"] is None


def test_score_suite_returns_zero_for_empty_list() -> None:
    assert score_suite([]) == 0.0


def test_score_suite_returns_exact_fraction_correct() -> None:
    item = ClassificationItem(item_id="x", prompt="p", expected_label="billing")
    scored_items = [
        score_item(item, "billing"),
        score_item(item, "billing"),
        score_item(item, "technical"),
        score_item(item, "gibberish"),
    ]

    assert score_suite(scored_items) == 0.5
