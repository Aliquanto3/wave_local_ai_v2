import copy

from wave_local_ai_v2.classification_suite import (
    CLASSIFICATION_TASK_SUITE,
    CONTEXT_LENGTH,
    LABELS,
    MAX_OUTPUT_TOKENS,
    STOP_SEQUENCES,
    SUITE_ID,
    SUITE_VERSION,
    prompt_set_hash,
)


def test_suite_has_at_least_eight_items() -> None:
    assert len(CLASSIFICATION_TASK_SUITE) >= 8


def test_every_expected_label_is_in_label_set() -> None:
    for item in CLASSIFICATION_TASK_SUITE:
        assert item["expected_label"] in LABELS


def test_every_item_has_a_unique_id_and_nonempty_prompt() -> None:
    ids = [item["item_id"] for item in CLASSIFICATION_TASK_SUITE]
    assert len(ids) == len(set(ids))
    for item in CLASSIFICATION_TASK_SUITE:
        assert item["prompt"].strip()


def test_every_prompt_embeds_the_full_label_set() -> None:
    for item in CLASSIFICATION_TASK_SUITE:
        for label in LABELS:
            assert label in item["prompt"]


def test_every_item_carries_consistent_language_provenance_and_risk_tags() -> None:
    for item in CLASSIFICATION_TASK_SUITE:
        assert item["language"] in {"en", "fr", "de"}
        assert item["provenance"] in {"hand_written", "licensed", "public"}
        assert item["contamination_risk"] == (item["provenance"] == "public")


def test_suite_declares_id_version_and_caps() -> None:
    assert SUITE_ID
    assert SUITE_VERSION
    assert MAX_OUTPUT_TOKENS > 0
    assert isinstance(STOP_SEQUENCES, list)
    assert CONTEXT_LENGTH > 0


def test_prompt_set_hash_is_stable_across_calls() -> None:
    assert prompt_set_hash(CLASSIFICATION_TASK_SUITE) == prompt_set_hash(
        CLASSIFICATION_TASK_SUITE
    )


def test_prompt_set_hash_changes_when_a_prompt_is_edited() -> None:
    edited = copy.deepcopy(CLASSIFICATION_TASK_SUITE)
    edited[0]["prompt"] += " edited"

    assert prompt_set_hash(edited) != prompt_set_hash(CLASSIFICATION_TASK_SUITE)
