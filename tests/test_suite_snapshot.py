import json

from wave_local_ai_v2 import suite_registry, suite_snapshot
from wave_local_ai_v2.suite_snapshot import (
    SUITE_DEFINITIONS_DIR,
    all_snapshots,
    build_snapshot,
    snapshot_filename,
    snapshot_text,
)

CLASSIFICATION = suite_registry.resolve("classification-support-routing")
TRANSLATION = suite_registry.resolve("translation-business-short-form")


def classification_snapshot() -> dict:
    return build_snapshot(CLASSIFICATION)


def translation_snapshot() -> dict:
    return build_snapshot(TRANSLATION)


def test_snapshot_carries_the_registered_suites_identity() -> None:
    for definition in (CLASSIFICATION, TRANSLATION):
        snapshot = build_snapshot(definition)

        assert snapshot["suite_id"] == definition.suite_id
        assert snapshot["suite_version"] == definition.suite_version
        assert snapshot["prompt_set_hash"] == definition.prompt_set_hash
        assert snapshot["max_output_tokens"] == definition.max_output_tokens
        assert snapshot["stop_sequences"] == definition.stop_sequences
        assert snapshot["thinking_policy"] == definition.thinking_policy
        assert snapshot["context_length"] == definition.context_length


def test_snapshot_publishes_exactly_the_keys_it_always_published() -> None:
    # The scoring-rule name and task_suite are definition fields, never
    # snapshot fields: exporting them would rewrite every committed file.
    # `level` joined with the version bump that declared it, and
    # `divergence_tolerance` with the next one. A suite drawn from a public
    # benchmark also publishes its size target, its selection rule and its
    # source table; no development suite carries them.
    published = {
        "suite_id",
        "suite_version",
        "level",
        "divergence_tolerance",
        "prompt_set_hash",
        "max_output_tokens",
        "stop_sequences",
        "thinking_policy",
        "context_length",
        "items",
    }
    drawn = {"size_target", "size_target_reason", "selection_rule", "source_table"}
    for snapshot in all_snapshots():
        if snapshot["level"] == "publication":
            assert set(snapshot) == published | drawn
        else:
            assert set(snapshot) == published


def test_classification_snapshot_items_carry_exactly_the_published_fields() -> None:
    snapshot = classification_snapshot()

    assert len(snapshot["items"]) == len(CLASSIFICATION.items)
    for snapshot_item, live_item in zip(
        snapshot["items"], CLASSIFICATION.items, strict=True
    ):
        assert snapshot_item == dict(live_item)
        assert set(snapshot_item) == {
            "item_id",
            "prompt",
            "expected_label",
            "language",
            "provenance",
            "contamination_risk",
            "licence",
        }


def test_a_drawn_snapshots_items_carry_their_source_and_content_hash() -> None:
    snapshot = build_snapshot(
        suite_registry.resolve("classification-banking-intents-minds14")
    )

    for item in snapshot["items"]:
        assert set(item) == {
            "item_id",
            "prompt",
            "expected_label",
            "language",
            "provenance",
            "contamination_risk",
            "licence",
            "source",
            "source_revision",
            "content_hash",
        }


def test_translation_snapshot_items_carry_exactly_the_published_fields() -> None:
    snapshot = translation_snapshot()

    assert len(snapshot["items"]) == len(TRANSLATION.items)
    for snapshot_item, live_item in zip(
        snapshot["items"], TRANSLATION.items, strict=True
    ):
        assert snapshot_item == dict(live_item)
        assert set(snapshot_item) == {
            "item_id",
            "prompt",
            "source_text",
            "reference",
            "language",
            "target_language",
            "provenance",
            "contamination_risk",
            "licence",
        }


def test_translation_snapshot_publishes_no_expected_label() -> None:
    # A reference-scored suite has no closed label set; a snapshot claiming
    # one would invite a reader to score it by exact match.
    for item in translation_snapshot()["items"]:
        assert "expected_label" not in item
        assert item["reference"].strip() != ""
        assert item["target_language"] != item["language"]


def test_every_snapshot_round_trips_through_json() -> None:
    for snapshot in all_snapshots():
        assert json.loads(snapshot_text(snapshot)) == snapshot


def test_every_registered_suite_is_exported() -> None:
    ids = {snapshot["suite_id"] for snapshot in all_snapshots()}

    assert ids == {
        "classification-support-routing",
        "classification-banking-intents-minds14",
        "translation-business-short-form",
        "code-generation-python-javascript",
    }


def test_a_snapshot_is_addressed_by_suite_id_and_version() -> None:
    assert snapshot_filename("a-suite", "3") == "a-suite@3.json"


def test_every_shipped_suite_resolves_to_a_committed_definition_file() -> None:
    """The pointer a published row follows has to exist for the live suites,
    not only for the versions the reference bundle happens to cite."""
    for snapshot in all_snapshots():
        path = SUITE_DEFINITIONS_DIR / snapshot_filename(
            snapshot["suite_id"], snapshot["suite_version"]
        )
        assert path.exists(), f"{path} is missing: re-export the snapshots"


def test_every_committed_definition_equals_its_export_byte_for_byte() -> None:
    """Existence is not integrity: a suite's items cannot change under an
    unchanged version, so the committed file must be exactly what the export
    writes. Compared as text, not as parsed JSON, so a key-order or
    whitespace drift in the export fails too -- the migration of the two
    shipped suites onto data must not move a byte. `read_text` folds the
    platform newline, the only difference a checkout may introduce."""
    for snapshot in all_snapshots():
        path = SUITE_DEFINITIONS_DIR / snapshot_filename(
            snapshot["suite_id"], snapshot["suite_version"]
        )
        committed = path.read_text(encoding="utf-8")
        assert committed == snapshot_text(snapshot), (
            f"{path} differs from its export: bump the suite version "
            "and re-export the snapshots, never edit either side alone"
        )


def test_a_version_bump_never_overwrites_its_predecessor() -> None:
    """The property the rename bought.

    Both suites bumped in this increment, and both predecessors are still on
    disk carrying their own version and the same prompt-set hash -- which is
    what says the items did not change, only what the subject was sent.
    """
    for builder, previous in (
        (classification_snapshot, "2"),
        (classification_snapshot, "3"),
        (translation_snapshot, "1"),
        (translation_snapshot, "2"),
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


def test_every_hand_written_item_names_its_licence_at_the_development_level() -> None:
    """The level and the per-item licence the version bump added, with the
    prompt-set hash its predecessor published: no item text moved."""
    for snapshot, predecessor in (
        (classification_snapshot(), "3"),
        (translation_snapshot(), "2"),
    ):
        assert snapshot["level"] == "development"
        for item in snapshot["items"]:
            assert item["provenance"] == "hand_written"
            assert item["licence"] == "CC-BY-4.0"
            assert "source" not in item
        old_path = SUITE_DEFINITIONS_DIR / snapshot_filename(
            snapshot["suite_id"], predecessor
        )
        old = json.loads(old_path.read_text(encoding="utf-8"))
        assert "level" not in old
        assert old["prompt_set_hash"] == snapshot["prompt_set_hash"]
        assert [item["prompt"] for item in old["items"]] == [
            item["prompt"] for item in snapshot["items"]
        ]


def test_exporting_over_a_published_file_with_other_content_is_refused(
    tmp_path, monkeypatch, capsys
) -> None:
    monkeypatch.setattr(suite_snapshot, "SUITE_DEFINITIONS_DIR", tmp_path)
    published = tmp_path / snapshot_filename(
        CLASSIFICATION.suite_id, CLASSIFICATION.suite_version
    )
    published.write_text('{"published": true}', encoding="utf-8")

    assert suite_snapshot.main() == 1

    assert published.read_text(encoding="utf-8") == '{"published": true}'
    # Nothing else was written either: the refusal is checked before any write.
    assert sorted(path.name for path in tmp_path.iterdir()) == [published.name]
    assert published.name in capsys.readouterr().err


def test_re_exporting_identical_content_is_a_no_op(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(suite_snapshot, "SUITE_DEFINITIONS_DIR", tmp_path)

    assert suite_snapshot.main() == 0
    before = {path.name: path.read_bytes() for path in tmp_path.iterdir()}

    assert suite_snapshot.main() == 0
    assert {path.name: path.read_bytes() for path in tmp_path.iterdir()} == before
