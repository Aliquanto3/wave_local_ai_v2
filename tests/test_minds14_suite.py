"""The MInDS-14 loader and draw, over a constructed table (no download).

The live fetch is the operator's (`scripts/minds14_suite.py verify`): CI
replays the draw over a table built here in MInDS-14's shape, so the mapping,
the table's hash, the draw and the replay are all checked without a network
(owner answer Q132 (a)).
"""

from __future__ import annotations

import json
import random
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import minds14_suite as loader

from wave_local_ai_v2 import subset_replay, suite_registry

INTENTS = [
    "abroad",
    "address",
    "app_error",
    "atm_limit",
    "balance",
    "business_loan",
    "card_issues",
    "cash_deposit",
    "direct_debit",
    "freeze",
    "high_value_payment",
    "joint_account",
    "latest_transactions",
    "pay_bill",
]


def _config_rows(config: str, per_intent: int = 10) -> list[dict]:
    paths, texts, intent_ids = [], [], []
    for index, intent in enumerate(INTENTS):
        for number in range(per_intent):
            paths.append(f"{config}~{intent.upper()}/response_{number}.wav")
            texts.append(f"{config} caller {number} about {intent.replace('_', ' ')}")
            intent_ids.append(index)
    return loader.source_rows(config, paths, texts, intent_ids, INTENTS)


def _rows() -> list[dict]:
    return [row for config in loader.CONFIGS for row in _config_rows(config)]


def _record(table: str, licence_paths: tuple[str, ...] = ()) -> dict:
    return loader.fetch_record(
        table,
        parquet={"en-US/train-00000-of-00001.parquet": "0" * 64},
        licence_paths=licence_paths,
        loader_version="25.0.1",
    )


def test_a_config_maps_to_the_suite_language_and_its_intent_names() -> None:
    row = _config_rows("fr-FR")[20]

    assert row == {
        "source": "PolyAI/minds14",
        "language": "fr",
        "path": "fr-FR~APP_ERROR/response_0.wav",
        "transcription": "fr-FR caller 0 about app error",
        "intent_class": "app_error",
    }


def test_a_class_index_outside_the_names_is_refused() -> None:
    with pytest.raises(loader.LoaderError, match="outside its names"):
        loader.source_rows("en-US", ["a.wav"], ["text"], [14], INTENTS)


def test_the_table_and_its_hash_do_not_depend_on_row_order() -> None:
    rows = _rows()
    shuffled = rows[:]
    random.Random(3).shuffle(shuffled)

    text = loader.table_text(rows)

    assert text == loader.table_text(shuffled)
    assert text.count("\n") == len(rows) == 3 * 14 * 10
    assert _record(text)["table_sha256"] == loader.sha256_hex(text.encode("utf-8"))
    assert _record(text)["row_count"] == len(rows)


def test_the_intent_names_come_from_the_parquet_features_metadata() -> None:
    metadata = {
        b"huggingface": json.dumps(
            {"info": {"features": {"intent_class": {"names": INTENTS}}}}
        ).encode("utf-8")
    }

    assert loader.intent_names(metadata) == INTENTS
    with pytest.raises(loader.LoaderError, match="no Hugging Face"):
        loader.intent_names(None)
    with pytest.raises(loader.LoaderError, match="names no intent_class"):
        loader.intent_names({b"huggingface": b'{"info": {"features": {}}}'})


def test_a_licence_file_anywhere_in_the_tree_is_found() -> None:
    tree = [
        {"type": "file", "path": "README.md"},
        {"type": "file", "path": ".gitattributes"},
        {"type": "directory", "path": "LICENSE"},
        {"type": "file", "path": "en-US/train-00000-of-00001.parquet"},
    ]

    assert loader.licence_files(tree) == []
    assert loader.licence_files([*tree, {"type": "file", "path": "x/Licence.txt"}]) == [
        "x/Licence.txt"
    ]


def test_a_parquet_is_checked_against_the_hash_the_tree_records() -> None:
    path = "de-DE/train-00000-of-00001.parquet"
    tree = [{"type": "file", "path": path, "lfs": {"oid": "a" * 64}}]

    assert loader.parquet_sha256(tree, path) == "a" * 64
    with pytest.raises(loader.LoaderError, match="records no LFS"):
        loader.parquet_sha256([{"type": "file", "path": path}], path)
    with pytest.raises(loader.LoaderError, match="is not in the tree"):
        loader.parquet_sha256(tree, "fr-FR/train-00000-of-00001.parquet")


def test_the_draw_certifies_at_publication_and_replays_to_its_ids(
    tmp_path: Path, capsys
) -> None:
    rows = _rows()
    table = tmp_path / "minds14.jsonl"
    table.write_bytes(loader.table_text(rows).encode("utf-8"))
    record = tmp_path / "record.json"
    record.write_text(json.dumps(_record(loader.table_text(rows))), encoding="utf-8")
    out = tmp_path / "definition.json"

    assert (
        loader.main(
            ["draw", "--table", str(table), "--record", str(record), "--out", str(out)]
        )
        == 0
    )
    definition = suite_registry.load_definition(out)

    assert definition.gate["level"] == "publication"
    assert definition.gate["language_counts"] == {"en": 100, "fr": 100, "de": 100}
    assert definition.extra["source_table"]["sha256"] == loader.sha256_hex(
        table.read_bytes()
    )
    assert definition.labels == frozenset(INTENTS)
    for item in definition.items:
        assert item["contamination_risk"] is True
        assert item["prompt"].startswith("Classify the following e-banking")
    capsys.readouterr()
    assert subset_replay.main(["--definition", str(out), "--source", str(table)]) == 0
    assert "reproduced: 300 items" in capsys.readouterr().out


def test_a_revision_shipping_a_licence_file_is_not_drawn(tmp_path: Path) -> None:
    rows = _rows()

    with pytest.raises(loader.LoaderError, match="reopens the spike"):
        loader.build_definition(
            rows, _record(loader.table_text(rows), licence_paths=("LICENSE",))
        )


def test_a_draw_from_an_unreadable_record_is_refused(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "absent.json"

    assert (
        loader.main(
            [
                "draw",
                "--table",
                str(missing),
                "--record",
                str(missing),
                "--out",
                str(tmp_path / "out.json"),
            ]
        )
        == 1
    )
    assert "refused:" in capsys.readouterr().err


def test_a_moved_table_is_named_against_the_recorded_hash() -> None:
    text = loader.table_text(_rows())
    recorded = loader.sha256_hex(text.encode("utf-8"))

    assert loader.verify_table(text, recorded) is None
    problem = loader.verify_table(text + "{}\n", recorded)
    assert problem is not None and recorded in problem


def test_the_committed_suite_records_the_loader_and_the_story_parameters() -> None:
    definition = suite_registry.resolve(loader.SUITE_ID)

    assert definition.suite_version == loader.SUITE_VERSION
    assert definition.extra["source_table"]["loader_script"] == loader.LOADER_SCRIPT
    assert definition.extra["selection_rule"]["loader"]["library"] == "pyarrow"
    revision = "40ce77cb32a384e4d50a568e1ec39ac804019d33"  # pragma: allowlist secret
    assert loader.REVISION == revision
    assert loader.CONFIGS == {"en-US": "en", "fr-FR": "fr", "de-DE": "de"}
