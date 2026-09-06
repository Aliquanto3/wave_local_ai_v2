from wave_local_ai_v2 import translation_suite
from wave_local_ai_v2.classification_suite import (
    CLASSIFICATION_TASK_SUITE,
    prompt_set_hash,
)
from wave_local_ai_v2.suite_gate import MIN_SUITE_ITEMS, gate_suite
from wave_local_ai_v2.translation_suite import (
    DIRECTIONS,
    TRANSLATION_TASK_SUITE,
)


def test_suite_holds_twenty_one_items() -> None:
    assert len(TRANSLATION_TASK_SUITE) == 21
    assert len(TRANSLATION_TASK_SUITE) >= MIN_SUITE_ITEMS


def test_gate_accepts_the_suite_with_no_indicative_reason() -> None:
    result = gate_suite(TRANSLATION_TASK_SUITE)

    assert result["indicative"] is False
    assert result["indicative_reasons"] == []
    assert result["item_count"] == 21


def test_every_source_language_holds_at_least_a_quarter_share() -> None:
    result = gate_suite(TRANSLATION_TASK_SUITE)

    for language in ("en", "fr", "de"):
        assert result["language_counts"][language] == 7
        assert result["language_shares"][language] >= 0.25


def test_every_direction_is_one_of_the_three_declared_ones() -> None:
    for item in TRANSLATION_TASK_SUITE:
        direction = (item["language"], item["target_language"])
        assert direction in DIRECTIONS
        assert item["language"] != item["target_language"]


def test_each_declared_direction_carries_seven_items() -> None:
    for source, target in DIRECTIONS:
        matching = [
            item
            for item in TRANSLATION_TASK_SUITE
            if (item["language"], item["target_language"]) == (source, target)
        ]
        assert len(matching) == 7


def test_every_item_id_is_unique() -> None:
    ids = [item["item_id"] for item in TRANSLATION_TASK_SUITE]
    assert len(set(ids)) == len(ids)


def test_every_item_is_hand_written_and_uncontaminated() -> None:
    for item in TRANSLATION_TASK_SUITE:
        assert item["provenance"] == "hand_written"
        assert item["contamination_risk"] is False


def test_every_source_text_and_reference_is_non_empty() -> None:
    for item in TRANSLATION_TASK_SUITE:
        assert item["source_text"].strip() != ""
        assert item["reference"].strip() != ""


def test_no_two_items_share_a_source_text_or_a_reference() -> None:
    # No item is another item's source translated: the suite would otherwise
    # be asking a model to translate text a translator already smoothed.
    sources = {item["source_text"] for item in TRANSLATION_TASK_SUITE}
    references = {item["reference"] for item in TRANSLATION_TASK_SUITE}
    assert len(sources) == len(TRANSLATION_TASK_SUITE)
    assert len(references) == len(TRANSLATION_TASK_SUITE)
    assert sources & references == set()


def test_every_prompt_embeds_its_source_text_and_names_both_languages() -> None:
    names = {"en": "English", "fr": "French", "de": "German"}
    for item in TRANSLATION_TASK_SUITE:
        assert item["prompt"].endswith(item["source_text"])
        assert names[item["language"]] in item["prompt"]
        assert names[item["target_language"]] in item["prompt"]


def test_prompt_set_hash_is_computed_over_the_live_items() -> None:
    assert translation_suite.PROMPT_SET_HASH == prompt_set_hash(TRANSLATION_TASK_SUITE)


def test_prompt_set_hash_differs_from_the_classification_suites() -> None:
    assert translation_suite.PROMPT_SET_HASH != prompt_set_hash(
        CLASSIFICATION_TASK_SUITE
    )


def test_editing_a_prompt_moves_the_hash() -> None:
    edited = [dict(item) for item in TRANSLATION_TASK_SUITE]
    edited[0]["prompt"] = edited[0]["prompt"] + " Please."

    assert prompt_set_hash(edited) != translation_suite.PROMPT_SET_HASH


def test_suite_declares_its_identity_and_its_generation_caps() -> None:
    assert translation_suite.SUITE_ID == "translation-business-short-form"
    assert translation_suite.SUITE_VERSION == "2"
    # 128, not the classification suite's 32: a sentence truncates there.
    assert translation_suite.MAX_OUTPUT_TOKENS == 128
    assert translation_suite.STOP_SEQUENCES == []
    # The cap above only holds under this policy: probed live, a
    # thinking-by-default model spends all 128 tokens reasoning and answers
    # nothing, which would make the cap the reason it failed.
    assert translation_suite.THINKING_POLICY == "disabled"
    assert translation_suite.CONTEXT_LENGTH == 32768
