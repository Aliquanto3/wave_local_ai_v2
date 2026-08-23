from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wave_local_ai_v2.results import append_row, captured_at, new_run_id, read_rows
from wave_local_ai_v2.row_contract import RowContractError

COMPLETE_QUALITY_ROW = {
    "schema_version": "1",
    "run_id": "run-1",
    "captured_at": "2026-08-22T00:00:00+00:00",
    "release_version": "v0.1.0",
    "commit_sha": "deadbeef",
    "tree_dirty": False,
    "roster_entry_id": "qwen3.6-35b-a3b-ud-iq4xs",
    "roster_version": 1,
    "endpoint": "/completion",
    "prompt_template_id": "none",
    "prompt_template_hash": None,
    "prompt_capture": "captured",
    "model_id": "Qwen3.6-35B-A3B",
    "provider": "local",
    "task_suite": "classification",
    "item_id": "billing-01",
    "prompt": "hello",
    "expected_label": "billing",
    "predicted_label": "billing",
    "correct": True,
    "suite_accuracy": 1.0,
    "sampling": {"seed": 1},
    "max_output_tokens": 32,
    "stop_sequences": [],
    "context_length": 32768,
    "suite_id": "classification-support-routing",
    "suite_version": "1",
    "prompt_set_hash": "deadbeef",
    "language": "en",
    "provenance": "hand_written",
    "contamination_risk": False,
    "indicative": True,
    "indicative_reasons": ["item_count 10 is below the minimum of 20"],
    "failure_reason": None,
    "failure_counts": {
        "empty": 0,
        "unparseable": 0,
        "truncated_max_tokens": 0,
        "truncated_context": 0,
    },
}


def test_append_and_read_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"

    append_row(path, "quality", COMPLETE_QUALITY_ROW)
    rows = read_rows(path)

    assert rows == [COMPLETE_QUALITY_ROW]


def test_append_row_creates_missing_parent_dirs(tmp_path: Path) -> None:
    path = tmp_path / "nested" / "dir" / "quality.jsonl"

    append_row(path, "quality", COMPLETE_QUALITY_ROW)

    assert path.exists()
    assert read_rows(path) == [COMPLETE_QUALITY_ROW]


def test_read_rows_returns_empty_list_when_file_missing(tmp_path: Path) -> None:
    assert read_rows(tmp_path / "absent.jsonl") == []


def test_new_run_id_differs_between_calls() -> None:
    assert new_run_id() != new_run_id()


def test_captured_at_round_trips_as_a_utc_datetime() -> None:
    parsed = datetime.fromisoformat(captured_at())

    assert parsed.tzinfo is not None
    assert parsed.utcoffset() == timedelta(0)


def test_append_row_with_incomplete_row_raises_and_writes_nothing(
    tmp_path: Path,
) -> None:
    path = tmp_path / "quality.jsonl"
    incomplete = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != "model_id"}

    with pytest.raises(RowContractError, match="model_id"):
        append_row(path, "quality", incomplete)

    assert not path.exists()


def test_append_row_with_incomplete_row_leaves_an_existing_file_unchanged(
    tmp_path: Path,
) -> None:
    path = tmp_path / "quality.jsonl"
    append_row(path, "quality", COMPLETE_QUALITY_ROW)
    incomplete = {k: v for k, v in COMPLETE_QUALITY_ROW.items() if k != "model_id"}

    with pytest.raises(RowContractError):
        append_row(path, "quality", incomplete)

    assert read_rows(path) == [COMPLETE_QUALITY_ROW]


def test_read_rows_filters_by_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"
    row_v1 = {**COMPLETE_QUALITY_ROW, "schema_version": "1"}
    row_v2 = {**COMPLETE_QUALITY_ROW, "schema_version": "2"}

    append_row(path, "quality", row_v1)
    append_row(path, "quality", row_v2)

    assert read_rows(path, schema_version="1") == [row_v1]
