from datetime import datetime, timedelta
from pathlib import Path

import pytest

from wave_local_ai_v2.results import (
    append_row,
    captured_at,
    new_run_id,
    read_rows,
    resume_skip_reason,
    rows_for_run,
)
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
    "fiche_hash": "a" * 64,
    "cpu_energy_kwh": 0.0003,
    "cpu_energy_method": "estimated_tdp",
    "gpu_energy_kwh": None,
    "gpu_energy_method": "unavailable",
    "ram_energy_kwh": 0.00012,
    "ram_energy_method": "estimated_constant",
    "energy_kwh": 0.00042,
    "emissions_kg": 0.0000235,
    "emission_factor_kg_per_kwh": 0.056039,
    "emission_region": "FR",
    "emissions_scope": "scope_2",
    "emissions_scope_formula_id": None,
    "scope_comparability": None,
    "tokens_in_total": None,
    "tokens_out_total": 640,
    "cost_total": 0.0000815,
    "cost_currency": "EUR",
    "cost_per_million_tokens": None,
    "normalization_unit": "cost_per_million_total_tokens",
    "kwh_price_eur": 0.194,
    "kwh_price_currency": "EUR",
    "kwh_price_recorded_at": "2026-02-01",
    "list_price_input_per_million": None,
    "list_price_output_per_million": None,
    "list_price_per_million_tokens": None,
    "list_price_currency": None,
    "list_price_retrieved_at": None,
    "verdict": {"verdict": "not_comparable", "reference_run_id": None},
    "task_suite": "classification",
    "item_id": "billing-01",
    "prompt": "hello",
    "expected_label": "billing",
    "predicted_label": "billing",
    "correct": True,
    "suite_accuracy": 1.0,
    "language_breakdown": {
        "en": {"accuracy": 1.0, "n": 1, "indicative": True},
        "fr": {"accuracy": 0.0, "n": 0, "indicative": True},
        "de": {"accuracy": 0.0, "n": 0, "indicative": True},
    },
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
    "retries": 0,
    "resumed": False,
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


def test_rows_for_run_returns_empty_list_when_the_store_is_absent(
    tmp_path: Path,
) -> None:
    assert rows_for_run(tmp_path / "absent.jsonl", "run-1") == []


def test_rows_for_run_returns_empty_list_for_an_unknown_run_id(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"
    append_row(path, "quality", COMPLETE_QUALITY_ROW)

    assert rows_for_run(path, "run-unknown") == []


def test_rows_for_run_filters_to_the_matching_run_id_only(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"
    row_a = {**COMPLETE_QUALITY_ROW, "run_id": "run-a"}
    row_b = {**COMPLETE_QUALITY_ROW, "run_id": "run-b"}
    append_row(path, "quality", row_a)
    append_row(path, "quality", row_b)

    assert rows_for_run(path, "run-a") == [row_a]


def _write_items(
    path: Path,
    run_id: str,
    provider: str,
    item_ids: list[str],
    task_suite: str = "classification",
) -> None:
    for item_id in item_ids:
        append_row(
            path,
            "quality",
            {
                **COMPLETE_QUALITY_ROW,
                "run_id": run_id,
                "provider": provider,
                "item_id": item_id,
                "task_suite": task_suite,
            },
        )


def test_resume_skip_reason_runs_a_batch_that_wrote_nothing(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"
    _write_items(path, "run-1", "local", ["a", "b", "c"])

    # Another provider's completed batch says nothing about this one.
    assert (
        resume_skip_reason(path, "run-1", "mistral", 3, task_suite="classification")
        is None
    )
    # Nor does another run's.
    assert (
        resume_skip_reason(path, "run-2", "local", 3, task_suite="classification")
        is None
    )
    # Nor does an absent store.
    assert (
        resume_skip_reason(
            tmp_path / "absent.jsonl", "run-1", "local", 3, task_suite="classification"
        )
        is None
    )


def test_resume_skip_reason_skips_a_complete_batch_by_name(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"
    _write_items(path, "run-1", "local", ["a", "b", "c"])

    assert (
        resume_skip_reason(path, "run-1", "local", 3, task_suite="classification")
        == "run run-1 already complete"
    )


def test_resume_skip_reason_refuses_a_partially_written_batch(tmp_path: Path) -> None:
    path = tmp_path / "quality.jsonl"
    _write_items(path, "run-1", "local", ["a", "b"])

    assert resume_skip_reason(
        path, "run-1", "local", 5, task_suite="classification"
    ) == ("run run-1 is partially written (2/5 items); re-running would duplicate them")


def test_resume_skip_reason_decides_against_the_callers_own_item_count(
    tmp_path: Path,
) -> None:
    # The same two rows are a complete batch for a two-item caller and a
    # partial one for a five-item caller: the count is the caller's, not a
    # suite length read from a module.
    path = tmp_path / "probe.jsonl"
    _write_items(path, "run-1", "google", ["a", "b"])

    assert resume_skip_reason(
        path, "run-1", "google", 2, task_suite="classification"
    ) == ("run run-1 already complete")
    assert "partially written (2/5" in str(
        resume_skip_reason(path, "run-1", "google", 5, task_suite="classification")
    )


def test_resume_never_skips_a_batch_on_the_strength_of_another_suites_rows(
    tmp_path: Path,
) -> None:
    # One store now holds two suites. A run_id complete under classification
    # says nothing about the same run_id under translation: without the
    # task_suite filter, `--resume <id> --suite translation` would skip a
    # batch that was never run and publish nothing for it.
    path = tmp_path / "quality.jsonl"
    _write_items(path, "run-1", "local", ["a", "b", "c"], task_suite="classification")

    assert (
        resume_skip_reason(path, "run-1", "local", 3, task_suite="translation") is None
    )
    assert (
        resume_skip_reason(path, "run-1", "local", 3, task_suite="classification")
        == "run run-1 already complete"
    )
