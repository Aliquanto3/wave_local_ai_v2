from dataclasses import replace
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
import requests

from wave_local_ai_v2 import FIXED_MAX_TOKENS, FIXED_PROMPT, _run, main
from wave_local_ai_v2.aggregation import AGGREGATION_LABELS
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
    "stop_type": "limit",
    "tokens_predicted": 128,
}

# The mirror of `RUNTIME_ONLY_FIELDS` in tests/test_quality_cli.py. Both
# directions need a guard for `aidd_docs/memory/architecture.md`'s "the two are
# never merged into a single table" to hold: that file stops a runtime field
# reaching a quality row, this one stops a quality field reaching a runtime row.
# `sampling` is not here: both row kinds carry it now, one seeded per request.
QUALITY_ONLY_FIELDS = {
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
    "failure_reason",
    "failure_counts",
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
        "capture_provenance": patch(
            "wave_local_ai_v2.provenance.capture_provenance",
            return_value={
                "release_version": "v0.1.0",
                "commit_sha": "deadbeef",
                "tree_dirty": False,
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
        "machine_state": patch(
            "wave_local_ai_v2.read_machine_state",
            return_value={
                "gpu_temp_c": 68.0,
                "gpu_throttle_reasons": [],
                "cpu_temp_c": None,
                "cpu_temp_source": "unavailable",
            },
        ),
        "rss": patch("wave_local_ai_v2.read_process_rss", return_value=500_000_000),
        "energy": patch(
            "wave_local_ai_v2.measure_energy",
            side_effect=lambda fn: (
                fn(),
                {"energy_kwh": 0.00042, "energy_method": "estimated_tdp"},
            ),
        ),
        # Real would sleep runtime_cooldown_s (10.0 by default) between every
        # repetition -- N-1 times plus once after the warm-up.
        "sleep": patch("wave_local_ai_v2.time.sleep"),
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
    assert row["release_version"] == "v0.1.0"
    assert row["commit_sha"] == "deadbeef"
    assert row["tree_dirty"] is False
    assert row["endpoint"] == "/completion"
    assert row["prompt_template_id"] == "none"
    assert row["prompt_template_hash"] is None
    assert row["prompt_capture"] == "captured"
    assert row["seed_pinned"] is True
    assert row["sampling"]["seed"]
    assert row["warmup_count"] == 1
    assert len(row["warmup_repetitions"]) == 1
    assert row["restart_between_repetitions"] is False
    assert row["cooldown_s"] == 10.0
    assert row["repetitions_n"] == 5
    assert row["slot_reset_method"] == "cache_prompt_false"
    assert len(row["repetitions"]) == 5
    assert [r["index"] for r in row["repetitions"]] == [1, 2, 3, 4, 5]
    assert row["aggregation"] == dict(AGGREGATION_LABELS)
    assert row["gen_tok_per_s_mean"] == 26.0
    assert row["gen_tok_per_s_sd"] == 0.0
    assert row["vram_used_mib"] == 3161.0
    assert row["wall_clock_s"] >= 0.0
    assert all("machine_state" in r for r in row["repetitions"])
    assert all("machine_state" in w for w in row["warmup_repetitions"])
    assert row["thermal_posture"] == "fixed_cooldown"
    assert row["ttft_source"] == "server_reported"
    assert row["unreliable"] is False
    assert row["gen_tok_per_s_spread"] == 0.0
    assert "ttft_ms_spread" in row
    assert "prompt_tok_per_s_spread" in row


def _timings_response(ttft_ms: float, prompt_tps: float, gen_tps: float) -> dict:
    return {
        "content": "hello",
        "timings": {
            "prompt_ms": ttft_ms,
            "prompt_per_second": prompt_tps,
            "predicted_per_second": gen_tps,
        },
        "stop_type": "limit",
        "tokens_predicted": 128,
    }


def _bytes_or_empty(path) -> bytes:
    return path.read_bytes() if path.exists() else b""


def _mock_completion(ttft_ms: float, prompt_tps: float, gen_tps: float) -> MagicMock:
    body = _timings_response(ttft_ms, prompt_tps, gen_tps)
    return MagicMock(status_code=200, json=lambda: body, raise_for_status=lambda: None)


def test_run_aggregates_five_differing_repetitions_into_medians_and_peaks(
    stubbed_run,
) -> None:
    results_path, started = stubbed_run
    # One warm-up response, then five differing counted responses.
    started["post"].side_effect = [
        _mock_completion(90.0, 260.0, 22.0),
        *[
            _mock_completion(ttft, prompt_tps, gen_tps)
            for ttft, prompt_tps, gen_tps in [
                (100.0, 270.0, 24.0),
                (110.0, 280.0, 25.0),
                (120.0, 290.0, 26.0),
                (130.0, 300.0, 27.0),
                (140.0, 310.0, 28.0),
            ]
        ],
    ]
    started["gpu_stats"].side_effect = [
        {"vram_used_mib": 3000.0 + i, "gpu_draw_w": 40.0 + i} for i in range(6)
    ]
    started["rss"].side_effect = [500_000_000 + i for i in range(6)]

    _run()

    row = read_rows(results_path)[0]
    assert row["ttft_ms"] == 120.0
    assert row["ttft_ms_mean"] == 120.0
    assert row["prompt_tok_per_s"] == 290.0
    assert row["gen_tok_per_s"] == 26.0
    # Peaks over the counted repetitions (indices 1..5, i.e. 3001..3005), not
    # the warm-up (index 0, i.e. 3000) and not simply the last sample.
    assert row["vram_used_mib"] == 3005.0
    assert row["process_rss_bytes"] == 500_000_005


def test_run_respects_a_raised_spread_threshold_override(stubbed_run) -> None:
    results_path, started = stubbed_run
    # gen_tok_per_s spread ~17.2% -- flags at the default 10% threshold.
    started["post"].side_effect = [
        _mock_completion(90.0, 260.0, 22.0),
        *[
            _mock_completion(ttft, prompt_tps, gen_tps)
            for ttft, prompt_tps, gen_tps in [
                (100.0, 270.0, 20.0),
                (110.0, 280.0, 24.0),
                (120.0, 290.0, 26.0),
                (130.0, 300.0, 28.0),
                (140.0, 310.0, 32.0),
            ]
        ],
    ]
    base_settings = started["load_settings"].return_value
    started["load_settings"].return_value = replace(
        base_settings, runtime_spread_threshold=0.20
    )

    _run()

    row = read_rows(results_path)[0]
    assert row["gen_tok_per_s_spread"] > 0.10
    assert row["unreliable"] is False


def test_run_takes_the_mean_of_the_two_middle_values_when_n_is_even(
    tmp_path,
) -> None:
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
        runtime_repetitions=4,
    )
    fake_process = MagicMock(pid=1234)

    with (
        patch("wave_local_ai_v2.load_settings", return_value=fake_settings),
        patch(
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
        patch(
            "wave_local_ai_v2.provenance.capture_provenance",
            return_value={
                "release_version": "v0.1.0",
                "commit_sha": "deadbeef",
                "tree_dirty": False,
            },
        ),
        patch("wave_local_ai_v2.server.running_server") as running_server,
        patch(
            "wave_local_ai_v2.requests.post",
            side_effect=[
                _mock_completion(90.0, 260.0, 22.0),
                *[
                    _mock_completion(ttft, prompt_tps, gen_tps)
                    for ttft, prompt_tps, gen_tps in [
                        (100.0, 270.0, 24.0),
                        (110.0, 280.0, 25.0),
                        (120.0, 290.0, 26.0),
                        (130.0, 300.0, 27.0),
                    ]
                ],
            ],
        ),
        patch(
            "wave_local_ai_v2.read_gpu_stats",
            return_value={"vram_used_mib": 3161.0, "gpu_draw_w": 45.0},
        ),
        patch(
            "wave_local_ai_v2.read_machine_state",
            return_value={
                "gpu_temp_c": 68.0,
                "gpu_throttle_reasons": [],
                "cpu_temp_c": None,
                "cpu_temp_source": "unavailable",
            },
        ),
        patch("wave_local_ai_v2.read_process_rss", return_value=500_000_000),
        patch(
            "wave_local_ai_v2.measure_energy",
            side_effect=lambda fn: (
                fn(),
                {"energy_kwh": 0.00042, "energy_method": "estimated_tdp"},
            ),
        ),
        patch("wave_local_ai_v2.time.sleep"),
    ):
        running_server.return_value.__enter__.return_value = fake_process
        running_server.return_value.__exit__.return_value = False
        _run()

    row = read_rows(results_path)[0]
    assert row["repetitions_n"] == 4
    # gen_tok_per_s over [24, 25, 26, 27]: the mean of the two middle values.
    assert row["gen_tok_per_s"] == 25.5
    assert len(row["repetitions"]) == 4


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


def test_run_sends_one_warmup_and_five_counted_requests_by_default(
    stubbed_run,
) -> None:
    _, started = stubbed_run

    _run()

    # One warm-up (RUNTIME_WARMUP_COUNT default 1) plus five counted
    # (RUNTIME_REPETITIONS default 5).
    assert started["post"].call_count == 6
    for call in started["post"].call_args_list:
        body = call.kwargs["json"]
        assert body["prompt"] == FIXED_PROMPT
        assert body["n_predict"] == FIXED_MAX_TOKENS
        assert body["cache_prompt"] is False
        assert body["seed"]


def test_run_applies_the_cooldown_between_repetitions(stubbed_run) -> None:
    _, started = stubbed_run

    _run()

    # 1 after the warm-up + (5 - 1) between the five counted repetitions.
    assert started["sleep"].call_count == 5
    started["sleep"].assert_called_with(10.0)


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


def test_main_exits_one_on_a_failing_repetition_and_writes_nothing(
    stubbed_run, capsys
) -> None:
    results_path, started = stubbed_run
    before = _bytes_or_empty(results_path)
    # Warm-up, then repetitions 1-2 succeed, repetition 3 returns blank.
    started["post"].side_effect = [
        _mock_completion(90.0, 260.0, 22.0),
        _mock_completion(100.0, 270.0, 24.0),
        _mock_completion(110.0, 280.0, 25.0),
        MagicMock(
            status_code=200,
            json=lambda: {"content": "", "stop_type": "limit", "tokens_predicted": 0},
            raise_for_status=lambda: None,
        ),
    ]

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    err = capsys.readouterr().err
    assert err.strip().count("\n") == 0
    assert "repetition 3 failed: empty" in err
    assert _bytes_or_empty(results_path) == before


def test_main_exits_one_on_an_unparseable_repetition(stubbed_run, capsys) -> None:
    results_path, started = stubbed_run
    before = _bytes_or_empty(results_path)
    started["post"].side_effect = [
        _mock_completion(90.0, 260.0, 22.0),
        MagicMock(
            status_code=200,
            json=lambda: {"content": "hello"},
            raise_for_status=lambda: None,
        ),
    ]

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    assert "repetition 1 failed: unparseable" in capsys.readouterr().err
    assert _bytes_or_empty(results_path) == before


def test_main_exits_one_when_the_context_is_exceeded(stubbed_run, capsys) -> None:
    results_path, started = stubbed_run
    before = _bytes_or_empty(results_path)
    started["post"].side_effect = [
        MagicMock(
            status_code=400,
            json=lambda: {
                "error": {
                    "type": "exceed_context_size_error",
                    "n_prompt_tokens": 6001,
                    "n_ctx": 4096,
                }
            },
            raise_for_status=lambda: None,
        ),
    ]

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    assert "repetition 0 failed: truncated_context" in capsys.readouterr().err
    assert _bytes_or_empty(results_path) == before


def test_main_exits_one_and_names_the_http_error_on_a_non_context_400(
    stubbed_run, capsys
) -> None:
    # A 400 that is not the context refusal has no `content` either, so passing
    # it through would have it classified as an `empty` generation and the
    # server's own message discarded. It must surface as the HTTP error it is.
    results_path, started = stubbed_run
    before = _bytes_or_empty(results_path)
    started["post"].side_effect = [
        MagicMock(
            status_code=400,
            json=lambda: {"error": {"type": "invalid_request_error", "n_ctx": 4096}},
            raise_for_status=MagicMock(
                side_effect=requests.HTTPError("400 Client Error: Bad Request")
            ),
        ),
    ]

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    err = capsys.readouterr().err
    assert "400 Client Error" in err
    assert "failed: empty" not in err
    assert _bytes_or_empty(results_path) == before


def test_main_exits_one_when_a_400_body_is_not_even_json(stubbed_run, capsys) -> None:
    # A proxy or a crashed handler can answer 400 with HTML. Nothing can be
    # classified from it, so it must raise rather than be read as an empty
    # generation.
    results_path, started = stubbed_run
    before = _bytes_or_empty(results_path)
    started["post"].side_effect = [
        MagicMock(
            status_code=400,
            json=MagicMock(side_effect=ValueError("no JSON object could be decoded")),
            raise_for_status=MagicMock(
                side_effect=requests.HTTPError("400 Client Error: Bad Request")
            ),
        ),
    ]

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    assert "400 Client Error" in capsys.readouterr().err
    assert _bytes_or_empty(results_path) == before


def test_main_exits_one_on_a_failing_warmup_with_no_retry(stubbed_run, capsys) -> None:
    results_path, started = stubbed_run
    before = _bytes_or_empty(results_path)
    started["post"].return_value = MagicMock(
        status_code=200,
        json=lambda: {"content": "", "stop_type": "limit", "tokens_predicted": 0},
        raise_for_status=lambda: None,
    )

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 1
    assert "repetition 0 failed: empty" in capsys.readouterr().err
    assert started["post"].call_count == 1
    assert _bytes_or_empty(results_path) == before
