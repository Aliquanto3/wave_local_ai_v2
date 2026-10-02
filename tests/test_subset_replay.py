import json
import random
from pathlib import Path

import pytest
from subset_fixtures import SOURCE, drawn_definition

from wave_local_ai_v2 import subset_replay


def _files(tmp_path: Path, definition: dict, rows: list[dict]) -> list[str]:
    definition_path = tmp_path / "fixture-drawn.json"
    definition_path.write_text(json.dumps(definition), encoding="utf-8")
    source_path = tmp_path / "source.jsonl"
    source_path.write_text(
        "\n".join(json.dumps(row) for row in rows) + "\n\n", encoding="utf-8"
    )
    return ["--definition", str(definition_path), "--source", str(source_path)]


def test_replaying_over_the_same_source_reproduces_it(tmp_path, capsys) -> None:
    definition, rows = drawn_definition()
    random.Random(5).shuffle(rows)

    assert subset_replay.main(_files(tmp_path, definition, rows)) == 0

    out = capsys.readouterr().out
    assert "sampler 1, seed 7 (attempts 1, seeds tried [7])" in out
    assert "recorded loader json stdlib, recorded generator CPython" in out
    assert "reproduced: 102 items, same ids, same order" in out


def test_an_edited_source_item_is_named_and_fails_the_replay(tmp_path, capsys) -> None:
    definition, rows = drawn_definition()
    target = definition["items"][3]["item_id"]
    row = next(row for row in rows if f"{SOURCE}:{row['id']}" == target)
    row["text"] = "silently rewritten upstream"

    assert subset_replay.main(_files(tmp_path, definition, rows)) == 1

    err = capsys.readouterr().err
    assert f"item {target!r} no longer matches its content_hash" in err
    assert "ids differ" not in err


def test_a_removed_source_item_is_named_and_the_order_difference_shown(
    tmp_path, capsys
) -> None:
    definition, rows = drawn_definition()
    target = definition["items"][0]["item_id"]
    rows = [row for row in rows if f"{SOURCE}:{row['id']}" != target]

    assert subset_replay.main(_files(tmp_path, definition, rows)) == 1

    err = capsys.readouterr().err
    assert f"item {target!r} is not in the source" in err
    assert "ids differ from position 0" in err


def test_a_changed_seed_fails_the_replay(tmp_path, capsys) -> None:
    definition, rows = drawn_definition()
    definition["selection_rule"].update(seed=8, seeds_tried=[8])

    assert subset_replay.main(_files(tmp_path, definition, rows)) == 1

    assert "ids differ from position" in capsys.readouterr().err


def test_a_rule_whose_size_was_edited_fails_the_replay(tmp_path, capsys) -> None:
    definition, rows = drawn_definition()
    definition["items"].append(dict(definition["items"][0], item_id=f"{SOURCE}:x"))
    definition["selection_rule"]["size"] = 103

    # 103 is drawn as 35/34/34: a different subset, not the recorded one.
    assert subset_replay.main(_files(tmp_path, definition, rows)) == 1
    assert "not reproduced" in capsys.readouterr().err


def test_a_suite_without_a_rule_is_refused(capsys, tmp_path) -> None:
    source = tmp_path / "source.jsonl"
    source.write_text("", encoding="utf-8")

    assert (
        subset_replay.main(
            ["--suite", "classification-support-routing", "--source", str(source)]
        )
        == 1
    )
    assert "records no selection rule" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("text", "message"),
    [("{not json\n", "line 1 is not JSON"), ("[1]\n", "line 1 is not a JSON object")],
)
def test_an_unreadable_source_is_refused_naming_the_line(
    tmp_path, capsys, text, message
) -> None:
    definition, rows = drawn_definition()
    args = _files(tmp_path, definition, rows)
    Path(args[-1]).write_text(text, encoding="utf-8")

    assert subset_replay.main(args) == 1
    assert message in capsys.readouterr().err


def test_a_source_the_rule_cannot_draw_from_is_refused(tmp_path, capsys) -> None:
    definition, rows = drawn_definition()
    rows = [row for row in rows if row["language"] != "de"]

    assert subset_replay.main(_files(tmp_path, definition, rows)) == 1
    assert "replay refused: stratum language 'de'" in capsys.readouterr().err


def test_a_missing_definition_is_refused(tmp_path, capsys) -> None:
    args = ["--definition", str(tmp_path / "absent.json"), "--source", "x.jsonl"]

    assert subset_replay.main(args) == 1
    assert "replay refused" in capsys.readouterr().err
