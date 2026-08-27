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


def test_suite_has_twenty_items() -> None:
    assert len(CLASSIFICATION_TASK_SUITE) == 20


def test_every_language_has_at_least_a_quarter_share() -> None:
    total = len(CLASSIFICATION_TASK_SUITE)
    for language in ("en", "fr", "de"):
        count = sum(
            1 for item in CLASSIFICATION_TASK_SUITE if item["language"] == language
        )
        assert count / total >= 0.25


def test_added_items_are_hand_written() -> None:
    for item in CLASSIFICATION_TASK_SUITE:
        if item["language"] in {"fr", "de"}:
            assert item["provenance"] == "hand_written"


def test_no_two_items_share_the_same_prompt() -> None:
    prompts = {item["prompt"] for item in CLASSIFICATION_TASK_SUITE}
    assert len(prompts) == len(CLASSIFICATION_TASK_SUITE)


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


_ORIGINAL_EN_ITEMS = {
    "billing-01": (
        "I was charged twice for my subscription this month, can you refund one?",
        "billing",
    ),
    "billing-02": (
        (
            "My invoice shows a currency I don't recognize -- can you confirm "
            "what I owe in EUR?"
        ),
        "billing",
    ),
    "technical-01": (
        "The app crashes every time I try to export a report to PDF.",
        "technical",
    ),
    "technical-02": (
        "I'm getting a 500 error when uploading a file larger than 10MB.",
        "technical",
    ),
    "account-01": (
        "I can't log in anymore since I changed my email address last week.",
        "account",
    ),
    "account-02": (
        "Please delete my account and all associated data permanently.",
        "account",
    ),
    "other-01": (
        "Do you have any plans to support a language other than English?",
        "other",
    ),
    "other-02": (
        "Just wanted to say the new dashboard redesign looks great, thanks!",
        "other",
    ),
    "billing-03": (
        "The discount code from your newsletter didn't apply at checkout.",
        "billing",
    ),
    "technical-03": (
        "Search results stopped updating after the last update went out.",
        "technical",
    ),
}


def test_original_ten_english_items_are_unchanged() -> None:
    en_items = {
        item["item_id"]: item
        for item in CLASSIFICATION_TASK_SUITE
        if item["language"] == "en"
    }

    assert en_items.keys() == _ORIGINAL_EN_ITEMS.keys()
    for item_id, (message, expected_label) in _ORIGINAL_EN_ITEMS.items():
        item = en_items[item_id]
        assert item["prompt"].endswith(message)
        assert item["expected_label"] == expected_label


def test_prompt_set_hash_changes_when_a_prompt_is_edited() -> None:
    edited = copy.deepcopy(CLASSIFICATION_TASK_SUITE)
    edited[0]["prompt"] += " edited"

    assert prompt_set_hash(edited) != prompt_set_hash(CLASSIFICATION_TASK_SUITE)
