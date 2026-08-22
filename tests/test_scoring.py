from wave_local_ai_v2.classification_suite import LABELS, ClassificationItem
from wave_local_ai_v2.scoring import normalize_label, score_item, score_suite

MAX_OUTPUT_TOKENS = 32


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


def _score(
    raw_completion: str,
    *,
    truncated: bool = False,
    generated_tokens: int = 5,
    max_output_tokens: int = MAX_OUTPUT_TOKENS,
    expected_label: str = "billing",
):
    item = ClassificationItem(item_id="x", prompt="p", expected_label=expected_label)
    return score_item(
        item,
        raw_completion,
        truncated=truncated,
        generated_tokens=generated_tokens,
        max_output_tokens=max_output_tokens,
    )


def test_score_item_correct_when_predicted_matches_expected() -> None:
    scored = _score("billing")

    assert scored["correct"] is True
    assert scored["predicted_label"] == "billing"
    assert scored["failure_reason"] is None


def test_score_item_incorrect_when_predicted_differs() -> None:
    scored = _score("technical")

    assert scored["correct"] is False
    assert scored["predicted_label"] == "technical"
    assert scored["failure_reason"] is None


def test_score_item_empty_completion_fails_as_empty() -> None:
    scored = _score("")

    assert scored["correct"] is False
    assert scored["predicted_label"] is None
    assert scored["failure_reason"] == "empty"


def test_score_item_whitespace_only_completion_fails_as_empty() -> None:
    scored = _score("   \n\t  ")

    assert scored["correct"] is False
    assert scored["predicted_label"] is None
    assert scored["failure_reason"] == "empty"


def test_score_item_unparseable_completion_fails_and_does_not_raise() -> None:
    scored = _score("no idea honestly")

    assert scored["correct"] is False
    assert scored["predicted_label"] is None
    assert scored["failure_reason"] == "unparseable"


def test_score_item_truncated_at_the_suites_cap() -> None:
    scored = _score(
        "billi",
        truncated=True,
        generated_tokens=MAX_OUTPUT_TOKENS,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    assert scored["correct"] is False
    assert scored["predicted_label"] is None
    assert scored["failure_reason"] == "truncated_max_tokens"


def test_score_item_truncated_below_the_suites_cap_is_context_truncation() -> None:
    scored = _score(
        "billi",
        truncated=True,
        generated_tokens=MAX_OUTPUT_TOKENS - 1,
        max_output_tokens=MAX_OUTPUT_TOKENS,
    )

    assert scored["correct"] is False
    assert scored["predicted_label"] is None
    assert scored["failure_reason"] == "truncated_context"


def test_score_suite_returns_zero_accuracy_for_empty_list() -> None:
    suite_score = score_suite([])

    assert suite_score["accuracy"] == 0.0
    assert suite_score["failure_counts"] == {
        "empty": 0,
        "unparseable": 0,
        "truncated_max_tokens": 0,
        "truncated_context": 0,
    }


def test_score_suite_returns_exact_fraction_correct() -> None:
    scored_items = [
        _score("billing"),
        _score("billing"),
        _score("technical"),
        _score("gibberish"),
    ]

    suite_score = score_suite(scored_items)

    assert suite_score["accuracy"] == 0.5


def test_score_suite_divides_by_the_full_count_including_failed_items() -> None:
    scored_items = [_score("billing"), _score("")]

    suite_score = score_suite(scored_items)

    # 1 correct out of 2 items -- the failed item stays in the denominator.
    assert suite_score["accuracy"] == 0.5


def test_score_suite_failure_counts_sum_to_the_failed_item_count() -> None:
    scored_items = [
        _score("billing"),
        _score(""),
        _score("gibberish"),
        _score(
            "x",
            truncated=True,
            generated_tokens=MAX_OUTPUT_TOKENS,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
        _score(
            "x",
            truncated=True,
            generated_tokens=1,
            max_output_tokens=MAX_OUTPUT_TOKENS,
        ),
    ]

    suite_score = score_suite(scored_items)

    assert suite_score["failure_counts"] == {
        "empty": 1,
        "unparseable": 1,
        "truncated_max_tokens": 1,
        "truncated_context": 1,
    }
    assert sum(suite_score["failure_counts"].values()) == 4
