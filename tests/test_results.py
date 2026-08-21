from pathlib import Path

from wave_local_ai_v2.results import append_row, read_rows


def test_append_and_read_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "runtime.jsonl"
    row = {"model": "Qwen3.6-35B-A3B", "gen_tok_per_s": 26.1}

    append_row(path, row)
    rows = read_rows(path)

    assert rows == [row]


def test_append_row_creates_missing_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "runtime.jsonl"

    append_row(path, {"a": 1})

    assert path.exists()
    assert read_rows(path) == [{"a": 1}]


def test_read_rows_returns_empty_list_when_file_missing(tmp_path: Path) -> None:
    assert read_rows(tmp_path / "absent.jsonl") == []
