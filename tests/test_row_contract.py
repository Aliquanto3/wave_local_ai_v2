import pytest

from wave_local_ai_v2.row_contract import SCHEMA_VERSION, RowContractError, validate_row

COMPLETE_RUNTIME_ROW = {
    "schema_version": SCHEMA_VERSION,
    "run_id": "run-1",
    "captured_at": "2026-08-22T00:00:00+00:00",
    "cpu": "x",
    "ram_gb": 32.0,
    "gpu_name": "y",
    "gpu_driver_version": "1.2.3",
    "os": "z",
    "cuda_ceiling": "12.4",
    "llama_cpp_build": "b10537",
    "model_file": "model.gguf",
    "quant": "UD-IQ4_XS",
    "flags": ["-m", "model.gguf"],
    "prompt": "hello",
    "max_tokens": 128,
    "wall_clock_s": 1.2,
    "ttft_ms": 100.0,
    "prompt_tok_per_s": 280.0,
    "gen_tok_per_s": 26.0,
    "vram_used_mib": 3161.0,
    "gpu_draw_w": 45.0,
    "process_rss_bytes": 500_000_000,
    "energy_kwh": 0.00042,
    "energy_method": "estimated_tdp",
}

COMPLETE_QUALITY_ROW = {
    "schema_version": SCHEMA_VERSION,
    "run_id": "run-1",
    "captured_at": "2026-08-22T00:00:00+00:00",
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
}


def test_complete_runtime_row_passes() -> None:
    validate_row("runtime", COMPLETE_RUNTIME_ROW)


def test_complete_quality_row_passes() -> None:
    validate_row("quality", COMPLETE_QUALITY_ROW)


def test_missing_field_raises_and_names_it() -> None:
    incomplete = {k: v for k, v in COMPLETE_RUNTIME_ROW.items() if k != "gpu_name"}

    with pytest.raises(RowContractError, match="gpu_name"):
        validate_row("runtime", incomplete)


def test_explicit_none_value_is_accepted() -> None:
    row = {**COMPLETE_RUNTIME_ROW, "gpu_name": None}

    validate_row("runtime", row)
