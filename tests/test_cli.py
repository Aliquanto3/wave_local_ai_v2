from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from wave_local_ai_v2 import FIXED_MAX_TOKENS, FIXED_PROMPT, _run, main
from wave_local_ai_v2.results import read_rows
from wave_local_ai_v2.row_contract import SCHEMA_VERSION
from wave_local_ai_v2.settings import Settings

SAMPLE_TIMINGS_RESPONSE = {
    "content": "a mixture-of-experts model routes tokens...",
    "timings": {
        "prompt_ms": 457.1,
        "prompt_per_second": 280.0,
        "predicted_per_second": 26.0,
    },
}

# The mirror of `RUNTIME_ONLY_FIELDS` in tests/test_quality_cli.py. Both
# directions need a guard for `aidd_docs/memory/architecture.md`'s "the two are
# never merged into a single table" to hold: that file stops a runtime field
# reaching a quality row, this one stops a quality field reaching a runtime row.
QUALITY_ONLY_FIELDS = {
    "sampling",
    "suite_accuracy",
    "expected_label",
    "predicted_label",
    "correct",
    "task_suite",
    "item_id",
    "provider",
    "max_output_tokens",
    "stop_sequences",
    "context_length",
    "suite_id",
    "suite_version",
    "prompt_set_hash",
    "language",
    "provenance",
    "contamination_risk",
    "indicative",
    "indicative_reasons",
}


@pytest.fixture
def stubbed_run(tmp_path, monkeypatch):
    """Stub every I/O boundary main() touches: process, HTTP, GPU, RSS, energy.

    measure_energy is patched here on purpose: unpatched it builds a real
    CodeCarbon EmissionsTracker, which imports codecarbon, probes the hardware
    and starts a sampling thread, costing seconds per test and making the
    result machine-dependent.
    """
    results_path = tmp_path / "runtime.jsonl"
    model_dir = tmp_path / "models"
    (model_dir / "Qwen3.6-35B-A3B").mkdir(parents=True)
    (model_dir / "Qwen3.6-35B-A3B" / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf").write_text("")
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    fake_settings = Settings(
        slm_models_dir=model_dir,
        llama_server_path=server_path,
        results_path=results_path,
    )
    fake_process = MagicMock(pid=1234)

    patches = {
        "load_settings": patch(
            "wave_local_ai_v2.load_settings", return_value=fake_settings
        ),
        "capture_fiche": patch(
            "wave_local_ai_v2.capture_fiche",
            return_value={
                "cpu": "x",
                "ram_gb": 32.0,
                "gpu_name": "y",
                "gpu_driver_version": "1.2.3",
                "os": "z",
                "cuda_ceiling": "12.4",
            },
        ),
        "running_server": patch("wave_local_ai_v2.server.running_server"),
        "post": patch(
            "wave_local_ai_v2.requests.post",
            return_value=MagicMock(
                status_code=200,
                json=lambda: SAMPLE_TIMINGS_RESPONSE,
                raise_for_status=lambda: None,
            ),
        ),
        "gpu_stats": patch(
            "wave_local_ai_v2.read_gpu_stats",
            return_value={"vram_used_mib": 3161.0, "gpu_draw_w": 45.0},
        ),
        "rss": patch("wave_local_ai_v2.read_process_rss", return_value=500_000_000),
        "energy": patch(
            "wave_local_ai_v2.measure_energy",
            side_effect=lambda fn: (
                fn(),
                {"energy_kwh": 0.00042, "energy_method": "estimated_tdp"},
            ),
        ),
    }
    started = {name: p.start() for name, p in patches.items()}
    started["running_server"].return_value.__enter__.return_value = fake_process
    started["running_server"].return_value.__exit__.return_value = False

    yield results_path, started

    for p in patches.values():
        p.stop()


def test_run_appends_one_row_with_fiche_and_metrics(stubbed_run) -> None:
    results_path, _ = stubbed_run

    _run()

    rows = read_rows(results_path)
    assert len(rows) == 1
    row = rows[0]
    for field in ("cpu", "ram_gb", "gpu_name", "os"):
        assert field in row
    assert row["gen_tok_per_s"] == 26.0
    assert row["prompt_tok_per_s"] == 280.0
    assert row["energy_method"] == "estimated_tdp"
    assert row["energy_kwh"] == 0.00042
    assert row["flags"]
    assert row["schema_version"] == SCHEMA_VERSION
    assert QUALITY_ONLY_FIELDS.isdisjoint(row.keys())


def test_run_appends_zero_rows_when_request_fails(tmp_path, monkeypatch) -> None:
    results_path = tmp_path / "runtime.jsonl"
    model_dir = tmp_path / "models"
    (model_dir / "Qwen3.6-35B-A3B").mkdir(parents=True)
    (model_dir / "Qwen3.6-35B-A3B" / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf").write_text("")
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    fake_settings = Settings(
        slm_models_dir=model_dir,
        llama_server_path=server_path,
        results_path=results_path,
    )
    fake_process = MagicMock(pid=1234)

    with (
        patch("wave_local_ai_v2.load_settings", return_value=fake_settings),
        patch("wave_local_ai_v2.capture_fiche", return_value={}),
        patch("wave_local_ai_v2.server.running_server") as running_server,
        patch(
            "wave_local_ai_v2.requests.post",
            side_effect=requests.ConnectionError("mid-run failure"),
        ),
        # Without this the real EmissionsTracker is built before the request
        # fails, costing seconds for a test about appending zero rows.
        patch(
            "wave_local_ai_v2.measure_energy",
            side_effect=lambda fn: (fn(), {"energy_kwh": None, "energy_method": "x"}),
        ),
        pytest.raises(requests.ConnectionError),
    ):
        running_server.return_value.__enter__.return_value = fake_process
        running_server.return_value.__exit__.return_value = False
        _run()

    assert read_rows(results_path) == []


def test_run_appends_zero_rows_when_server_never_becomes_ready(tmp_path) -> None:
    from wave_local_ai_v2.server import ServerStartupError

    results_path = tmp_path / "runtime.jsonl"
    model_dir = tmp_path / "models"
    (model_dir / "Qwen3.6-35B-A3B").mkdir(parents=True)
    (model_dir / "Qwen3.6-35B-A3B" / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf").write_text("")
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    fake_settings = Settings(
        slm_models_dir=model_dir,
        llama_server_path=server_path,
        results_path=results_path,
    )

    with (
        patch("wave_local_ai_v2.load_settings", return_value=fake_settings),
        patch("wave_local_ai_v2.capture_fiche", return_value={}),
        patch(
            "wave_local_ai_v2.server.running_server",
            side_effect=ServerStartupError("timed out"),
        ),
        pytest.raises(ServerStartupError),
    ):
        _run()

    assert read_rows(results_path) == []


def test_run_sends_the_fixed_prompt_and_max_tokens_exactly_once(stubbed_run) -> None:
    _, started = stubbed_run

    _run()

    assert started["post"].call_count == 1
    body = started["post"].call_args.kwargs["json"]
    assert body["prompt"] == FIXED_PROMPT
    assert body["n_predict"] == FIXED_MAX_TOKENS


def test_run_stamps_the_row_with_run_provenance(stubbed_run) -> None:
    results_path, _ = stubbed_run

    _run()

    row = read_rows(results_path)[0]
    assert row["run_id"]
    parsed = datetime.fromisoformat(row["captured_at"])
    assert parsed.utcoffset() == timedelta(0)


def test_two_runs_carry_two_distinct_run_ids(stubbed_run) -> None:
    results_path, _ = stubbed_run

    _run()
    _run()

    run_ids = {row["run_id"] for row in read_rows(results_path)}
    assert len(run_ids) == 2


def test_main_exits_one_when_the_results_path_cannot_be_written(
    stubbed_run, capsys
) -> None:
    # An unwritable or absent results drive surfaces from append_row as OSError,
    # after the measurement already succeeded; the operator gets a line, not a
    # traceback.
    with (
        patch(
            "wave_local_ai_v2.append_row",
            side_effect=OSError("[Errno 30] Read-only file system"),
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    assert exit_info.value.code == 1
    assert "error: [Errno 30] Read-only file system" in capsys.readouterr().err


def test_run_still_appends_its_row_when_the_rss_read_fails(stubbed_run) -> None:
    results_path, started = stubbed_run
    # The server exited between the completion response and the RSS read: the
    # measurement already succeeded, so the row must survive with a null column.
    started["rss"].return_value = None

    _run()

    rows = read_rows(results_path)
    assert len(rows) == 1
    assert rows[0]["process_rss_bytes"] is None
    assert rows[0]["gen_tok_per_s"] == 26.0
