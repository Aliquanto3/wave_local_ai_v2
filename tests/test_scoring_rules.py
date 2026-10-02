from wave_local_ai_v2 import chrf, scoring_rules, suite_registry

CLASSIFICATION = suite_registry.resolve("classification-support-routing")
TRANSLATION = suite_registry.resolve("translation-business-short-form")


def _completion(
    content: str, generated_tokens: int = 2, *, truncated: bool = False
) -> dict:
    return {
        "content": content,
        "truncated": truncated,
        "generated_tokens": generated_tokens,
        "truncation_reason": None,
    }


def test_the_rule_table_names_exactly_the_two_shipped_rules() -> None:
    assert set(scoring_rules.SCORING_RULES) == {
        "exact_label_match",
        "chrf_against_reference",
    }


def test_exact_label_match_judges_truncation_against_the_cap_it_is_given() -> None:
    items = CLASSIFICATION.items[:1]
    # A truncated generation of 5 tokens: the cap's fault when the cap is 5,
    # the context's when the cap is 32.
    completions = [_completion("billing", generated_tokens=5, truncated=True)]

    under_cap, _ = scoring_rules.exact_label_match(
        items, completions, max_output_tokens=32
    )
    at_cap, batch = scoring_rules.exact_label_match(
        items, completions, max_output_tokens=5
    )

    assert under_cap[0]["failure_reason"] == "truncated_context"
    assert at_cap[0]["failure_reason"] == "truncated_max_tokens"
    assert batch["failure_counts"]["truncated_max_tokens"] == 1


def test_exact_label_match_publishes_the_exact_match_shape_only() -> None:
    items = CLASSIFICATION.items
    per_item, batch = scoring_rules.exact_label_match(
        items,
        [_completion(item["expected_label"]) for item in items],
        max_output_tokens=CLASSIFICATION.max_output_tokens,
    )

    assert all(row["correct"] is True for row in per_item)
    assert batch["suite_accuracy"] == 1.0
    assert set(batch["language_breakdown"]) == {"en", "fr", "de"}
    assert "suite_score" not in batch


def test_chrf_against_reference_publishes_the_graded_shape_only() -> None:
    items = TRANSLATION.items
    per_item, batch = scoring_rules.chrf_against_reference(
        items,
        [_completion(item["reference"]) for item in items],
        max_output_tokens=TRANSLATION.max_output_tokens,
    )

    assert all(row["item_score"] == 1.0 for row in per_item)
    assert all(row["correct"] is None for row in per_item)
    assert per_item[0]["metric_id"] == chrf.METRIC_ID
    assert per_item[0]["reference_output"] == items[0]["reference"]
    assert batch["suite_score"] == 1.0
    assert batch["suite_accuracy"] is None
    assert batch["language_breakdown"] is None
