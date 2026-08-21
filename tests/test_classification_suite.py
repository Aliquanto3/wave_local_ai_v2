from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE, LABELS


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
