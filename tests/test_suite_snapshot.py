from wave_local_ai_v2 import classification_suite
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.suite_snapshot import build_snapshot


def test_snapshot_carries_the_live_suites_identity() -> None:
    snapshot = build_snapshot()

    assert snapshot["suite_id"] == classification_suite.SUITE_ID
    assert snapshot["suite_version"] == classification_suite.SUITE_VERSION
    assert snapshot["prompt_set_hash"] == classification_suite.PROMPT_SET_HASH
    assert snapshot["max_output_tokens"] == classification_suite.MAX_OUTPUT_TOKENS
    assert snapshot["stop_sequences"] == classification_suite.STOP_SEQUENCES
    assert snapshot["context_length"] == classification_suite.CONTEXT_LENGTH


def test_snapshot_items_round_trip_the_live_suite_exactly() -> None:
    snapshot = build_snapshot()

    assert len(snapshot["items"]) == len(CLASSIFICATION_TASK_SUITE)
    for snapshot_item, live_item in zip(
        snapshot["items"], CLASSIFICATION_TASK_SUITE, strict=True
    ):
        assert snapshot_item == {
            "item_id": live_item["item_id"],
            "prompt": live_item["prompt"],
            "expected_label": live_item["expected_label"],
            "language": live_item["language"],
            "provenance": live_item["provenance"],
            "contamination_risk": live_item["contamination_risk"],
        }
