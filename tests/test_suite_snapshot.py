import json

from wave_local_ai_v2 import classification_suite, translation_suite
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.suite_snapshot import (
    SNAPSHOT_BUILDERS,
    SUITE_DEFINITIONS_DIR,
    classification_snapshot,
    snapshot_filename,
    translation_snapshot,
)
from wave_local_ai_v2.translation_suite import TRANSLATION_TASK_SUITE


def test_snapshot_carries_the_live_suites_identity() -> None:
    snapshot = classification_snapshot()

    assert snapshot["suite_id"] == classification_suite.SUITE_ID
    assert snapshot["suite_version"] == classification_suite.SUITE_VERSION
    assert snapshot["prompt_set_hash"] == classification_suite.PROMPT_SET_HASH
    assert snapshot["max_output_tokens"] == classification_suite.MAX_OUTPUT_TOKENS
    assert snapshot["stop_sequences"] == classification_suite.STOP_SEQUENCES
    assert snapshot["thinking_policy"] == classification_suite.THINKING_POLICY
    assert snapshot["context_length"] == classification_suite.CONTEXT_LENGTH


def test_snapshot_items_round_trip_the_live_suite_exactly() -> None:
    snapshot = classification_snapshot()

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


def test_translation_snapshot_carries_the_live_suites_identity() -> None:
    snapshot = translation_snapshot()

    assert snapshot["suite_id"] == translation_suite.SUITE_ID
    assert snapshot["suite_version"] == translation_suite.SUITE_VERSION
    assert snapshot["prompt_set_hash"] == translation_suite.PROMPT_SET_HASH
    assert snapshot["max_output_tokens"] == translation_suite.MAX_OUTPUT_TOKENS
    assert snapshot["stop_sequences"] == translation_suite.STOP_SEQUENCES
    assert snapshot["thinking_policy"] == translation_suite.THINKING_POLICY
    assert snapshot["context_length"] == translation_suite.CONTEXT_LENGTH


def test_translation_snapshot_items_round_trip_the_live_suite_exactly() -> None:
    snapshot = translation_snapshot()

    assert len(snapshot["items"]) == len(TRANSLATION_TASK_SUITE)
    for snapshot_item, live_item in zip(
        snapshot["items"], TRANSLATION_TASK_SUITE, strict=True
    ):
        assert snapshot_item == {
            "item_id": live_item["item_id"],
            "prompt": live_item["prompt"],
            "source_text": live_item["source_text"],
            "reference": live_item["reference"],
            "language": live_item["language"],
            "target_language": live_item["target_language"],
            "provenance": live_item["provenance"],
            "contamination_risk": live_item["contamination_risk"],
        }


def test_translation_snapshot_publishes_no_expected_label() -> None:
    # A reference-scored suite has no closed label set; a snapshot claiming
    # one would invite a reader to score it by exact match.
    for item in translation_snapshot()["items"]:
        assert "expected_label" not in item
        assert item["reference"].strip() != ""
        assert item["target_language"] != item["language"]


def test_both_snapshots_round_trip_through_json() -> None:
    for builder in SNAPSHOT_BUILDERS:
        snapshot = builder()
        assert json.loads(json.dumps(snapshot, sort_keys=True)) == snapshot


def test_the_two_snapshots_are_distinct_suites() -> None:
    ids = {builder()["suite_id"] for builder in SNAPSHOT_BUILDERS}

    assert ids == {
        classification_suite.SUITE_ID,
        translation_suite.SUITE_ID,
    }


def test_a_snapshot_is_addressed_by_suite_id_and_version() -> None:
    assert snapshot_filename("a-suite", "3") == "a-suite@3.json"


def test_every_shipped_suite_resolves_to_a_committed_definition_file() -> None:
    """The pointer a published row follows has to exist for the live suites,
    not only for the versions the reference bundle happens to cite."""
    for builder in SNAPSHOT_BUILDERS:
        snapshot = builder()
        path = SUITE_DEFINITIONS_DIR / snapshot_filename(
            snapshot["suite_id"], snapshot["suite_version"]
        )
        assert path.exists(), f"{path} is missing: re-export the snapshots"


def test_a_version_bump_never_overwrites_its_predecessor() -> None:
    """The property the rename bought.

    Both suites bumped in this increment, and both predecessors are still on
    disk carrying their own version and the same prompt-set hash -- which is
    what says the items did not change, only what the subject was sent.
    """
    for builder, previous in (
        (classification_snapshot, "2"),
        (translation_snapshot, "1"),
    ):
        snapshot = builder()
        assert snapshot["suite_version"] != previous
        old_path = SUITE_DEFINITIONS_DIR / snapshot_filename(
            snapshot["suite_id"], previous
        )
        assert old_path.exists(), f"{old_path} was overwritten by the bump"
        old = json.loads(old_path.read_text(encoding="utf-8"))
        assert old["suite_version"] == previous
        assert old["prompt_set_hash"] == snapshot["prompt_set_hash"]
