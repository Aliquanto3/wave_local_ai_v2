import dataclasses
from datetime import datetime, timedelta
from unittest.mock import DEFAULT, MagicMock, patch

import pytest

from wave_local_ai_v2 import classification_suite, mistral_client, quality_cli
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.mistral_client import MistralRequestError, ModelUnavailableError
from wave_local_ai_v2.results import read_rows
from wave_local_ai_v2.row_contract import SCHEMA_VERSION
from wave_local_ai_v2.settings import Settings, SettingsError
from wave_local_ai_v2.suite_gate import SuiteGateError

RUNTIME_ONLY_FIELDS = {
    "cpu",
    "ram_gb",
    "gpu_name",
    "ttft_ms",
    "prompt_tok_per_s",
    "gen_tok_per_s",
    "energy_method",
}


@pytest.fixture
def stubbed_run(tmp_path, monkeypatch):
    """Stub every I/O boundary quality_cli.main() touches: process, both HTTP clients."""
    quality_results_path = tmp_path / "quality.jsonl"
    model_dir = tmp_path / "models"
    (model_dir / quality_cli.LOCAL_MODEL_ID).mkdir(parents=True)
    (model_dir / quality_cli.MODEL_RELATIVE_PATH).write_text("")
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    fake_settings = Settings(
        slm_models_dir=model_dir,
        llama_server_path=server_path,
        results_path=tmp_path / "runtime.jsonl",
        quality_results_path=quality_results_path,
        mistral_api_key="fake-key",  # pragma: allowlist secret
    )
    fake_process = MagicMock(pid=1234)

    patches = {
        "load_settings": patch(
            "wave_local_ai_v2.quality_cli.load_settings", return_value=fake_settings
        ),
        "running_server": patch("wave_local_ai_v2.quality_cli.server.running_server"),
        "post": patch(
            "wave_local_ai_v2.quality_cli.requests.post",
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"content": "billing"},
                raise_for_status=lambda: None,
            ),
        ),
        "complete_prompt": patch(
            "wave_local_ai_v2.quality_cli.mistral_client.complete_prompt",
            return_value="billing",
        ),
        # Without this every test in this file would issue a live GET to the
        # Mistral model catalog before the suite runs.
        "check_model": patch(
            "wave_local_ai_v2.quality_cli.mistral_client.check_model_available",
            return_value=None,
        ),
        "capture_provenance": patch(
            "wave_local_ai_v2.quality_cli.provenance.capture_provenance",
            return_value={
                "release_version": "v0.1.0",
                "commit_sha": "deadbeef",
                "tree_dirty": False,
            },
        ),
    }
    started = {name: p.start() for name, p in patches.items()}
    started["running_server"].return_value.__enter__.return_value = fake_process
    started["running_server"].return_value.__exit__.return_value = False

    yield quality_results_path, started

    for p in patches.values():
        p.stop()


def test_run_writes_one_row_per_item_per_model(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    rows = read_rows(quality_results_path)
    assert len(rows) == 2 * len(CLASSIFICATION_TASK_SUITE)
    for row in rows:
        assert row["schema_version"] == SCHEMA_VERSION


def test_every_row_carries_the_suite_caps_tags_and_gate_verdict(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    # Keyed by (provider, item_id), not item_id alone: the two providers write
    # one row each per item, so an item_id-only key silently drops the local
    # half and leaves ten of the twenty rows unasserted.
    rows_by_key = {
        (row["provider"], row["item_id"]): row
        for row in read_rows(quality_results_path)
    }
    items_by_id = {item["item_id"]: item for item in CLASSIFICATION_TASK_SUITE}
    assert len(rows_by_key) == 2 * len(CLASSIFICATION_TASK_SUITE)

    for (provider, item_id), row in rows_by_key.items():
        item = items_by_id[item_id]
        assert provider in {"local", "mistral"}
        assert row["max_output_tokens"] == classification_suite.MAX_OUTPUT_TOKENS
        assert row["stop_sequences"] == classification_suite.STOP_SEQUENCES
        assert row["context_length"] == classification_suite.CONTEXT_LENGTH
        assert row["suite_id"] == classification_suite.SUITE_ID
        assert row["suite_version"] == classification_suite.SUITE_VERSION
        assert row["prompt_set_hash"] == classification_suite.PROMPT_SET_HASH
        assert row["language"] == item["language"]
        assert row["provenance"] == item["provenance"]
        assert row["contamination_risk"] == item["contamination_risk"]
        # The real suite is under-sized and EN-only: every row this fixture
        # writes must land marked indicative, never a silent pass.
        assert row["indicative"] is True
        assert row["indicative_reasons"]

    # Methodology 3's "two models compared on one item record identical values"
    # stated as its own assertion: the caps are what makes the two halves
    # comparable, so a future per-provider cap must fail here.
    capped_fields = ("max_output_tokens", "stop_sequences", "context_length")
    for item_id in items_by_id:
        local_row = rows_by_key[("local", item_id)]
        cloud_row = rows_by_key[("mistral", item_id)]
        for field in capped_fields:
            assert local_row[field] == cloud_row[field]


def test_gate_refusal_aborts_before_any_row_is_written(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    with (
        patch(
            "wave_local_ai_v2.quality_cli.suite_gate.gate_suite",
            side_effect=SuiteGateError("boom"),
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        quality_cli.main()

    assert exit_info.value.code == 1
    assert read_rows(quality_results_path) == []


def test_local_server_started_exactly_once_for_the_whole_suite(stubbed_run) -> None:
    _, started = stubbed_run

    quality_cli._run()

    assert started["running_server"].call_count == 1
    assert started["post"].call_count == len(CLASSIFICATION_TASK_SUITE)


def test_rows_carry_no_runtime_fields(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    for row in read_rows(quality_results_path):
        assert RUNTIME_ONLY_FIELDS.isdisjoint(row.keys())


def test_rows_carry_the_shared_prompt_for_both_models(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    rows = read_rows(quality_results_path)
    prompts_by_item = {
        item["item_id"]: item["prompt"] for item in CLASSIFICATION_TASK_SUITE
    }
    for row in rows:
        assert row["prompt"] == prompts_by_item[row["item_id"]]


def test_cloud_call_made_once_per_item_with_the_shared_prompt(stubbed_run) -> None:
    _, started = stubbed_run

    quality_cli._run()

    assert started["complete_prompt"].call_count == len(CLASSIFICATION_TASK_SUITE)
    called_prompts = [
        call.args[0] for call in started["complete_prompt"].call_args_list
    ]
    expected_prompts = [item["prompt"] for item in CLASSIFICATION_TASK_SUITE]
    assert called_prompts == expected_prompts


def test_run_raises_before_any_local_or_cloud_call_when_mistral_key_missing(
    tmp_path,
) -> None:
    model_dir = tmp_path / "models"
    (model_dir / quality_cli.LOCAL_MODEL_ID).mkdir(parents=True)
    (model_dir / quality_cli.MODEL_RELATIVE_PATH).write_text("")
    server_path = tmp_path / "llama-server.exe"
    server_path.write_text("")

    fake_settings = Settings(
        slm_models_dir=model_dir,
        llama_server_path=server_path,
        results_path=tmp_path / "runtime.jsonl",
        quality_results_path=tmp_path / "quality.jsonl",
        mistral_api_key="",
    )
    fake_process = MagicMock(pid=1234)

    with (
        patch("wave_local_ai_v2.quality_cli.load_settings", return_value=fake_settings),
        patch("wave_local_ai_v2.quality_cli.server.running_server") as running_server,
        patch(
            "wave_local_ai_v2.quality_cli.requests.post",
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"content": "billing"},
                raise_for_status=lambda: None,
            ),
        ),
        patch(
            "wave_local_ai_v2.quality_cli.mistral_client.complete_prompt"
        ) as complete,
        pytest.raises(SettingsError),
    ):
        running_server.return_value.__enter__.return_value = fake_process
        running_server.return_value.__exit__.return_value = False
        quality_cli._run()

    running_server.assert_not_called()
    complete.assert_not_called()


def test_run_raises_local_completion_error_on_malformed_response(stubbed_run) -> None:
    _, started = stubbed_run
    started["post"].return_value = MagicMock(
        status_code=200,
        json=lambda: {"no_content_here": True},
        raise_for_status=lambda: None,
    )

    with pytest.raises(quality_cli.LocalCompletionError):
        quality_cli._run()


def test_run_propagates_mistral_request_error(stubbed_run) -> None:
    _, started = stubbed_run
    started["complete_prompt"].side_effect = MistralRequestError("boom")

    with pytest.raises(MistralRequestError):
        quality_cli._run()


def test_run_raises_local_completion_error_when_response_is_not_an_object(
    stubbed_run,
) -> None:
    _, started = stubbed_run
    started["post"].return_value = MagicMock(
        status_code=200,
        json=lambda: ["billing"],
        raise_for_status=lambda: None,
    )

    with pytest.raises(quality_cli.LocalCompletionError):
        quality_cli._run()


def test_main_exits_one_on_local_completion_error(stubbed_run, capsys) -> None:
    _, started = stubbed_run
    started["post"].return_value = MagicMock(
        status_code=200,
        json=lambda: {"no_content_here": True},
        raise_for_status=lambda: None,
    )

    with pytest.raises(SystemExit) as exit_info:
        quality_cli.main()

    assert exit_info.value.code == 1
    assert "unexpected /completion response shape" in capsys.readouterr().err


def test_run_raises_local_completion_error_when_content_is_not_text(
    stubbed_run,
) -> None:
    _, started = stubbed_run
    started["post"].return_value = MagicMock(
        status_code=200,
        json=lambda: {"content": None},
        raise_for_status=lambda: None,
    )

    with pytest.raises(quality_cli.LocalCompletionError):
        quality_cli._run()


def test_every_local_completion_request_pins_the_sampler(stubbed_run) -> None:
    _, started = stubbed_run

    quality_cli._run()

    assert started["post"].call_count == len(CLASSIFICATION_TASK_SUITE)
    for call in started["post"].call_args_list:
        body = call.kwargs["json"]
        # Literal expectations, not a comparison against LOCAL_SAMPLING: comparing
        # the request to the constant that built it would still pass if a key were
        # deleted from both.
        assert body["temperature"] == 0
        assert body["top_k"] == 0
        assert body["top_p"] == 1.0
        assert body["presence_penalty"] == 0
        assert isinstance(body["seed"], int)
        assert body["seed"] >= 0, "-1 asks llama-server for a fresh random seed"


def test_cloud_calls_pin_temperature_seed_and_the_suites_cap(stubbed_run) -> None:
    _, started = stubbed_run

    quality_cli._run()

    for call in started["complete_prompt"].call_args_list:
        assert call.kwargs["temperature"] == 0
        assert isinstance(call.kwargs["random_seed"], int)
        # The cloud half must be sent the cap its rows publish, and the same one
        # the local half's `n_predict` applies.
        assert call.kwargs["max_tokens"] == classification_suite.MAX_OUTPUT_TOKENS


def test_every_row_records_the_sampling_that_produced_it(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    rows = read_rows(quality_results_path)
    providers = {row["provider"] for row in rows}
    assert providers == {"local", "mistral"}

    for row in rows:
        sampling = row["sampling"]
        assert sampling["temperature"] == 0
        if row["provider"] == "local":
            assert sampling["seed"] >= 0
            assert sampling["presence_penalty"] == 0
            # A cloud block swapped in here would carry random_seed instead.
            assert "random_seed" not in sampling
        else:
            assert isinstance(sampling["random_seed"], int)
            # A local block swapped in here would carry the llama-server penalties.
            assert "presence_penalty" not in sampling


def test_cloud_rows_record_the_dated_model_id(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    cloud_ids = {
        row["model_id"]
        for row in read_rows(quality_results_path)
        if row["provider"] == "mistral"
    }
    assert cloud_ids == {mistral_client.MODEL}
    assert not mistral_client.MODEL.endswith("-latest")


def test_run_pays_no_local_lifecycle_when_the_model_id_is_gone(stubbed_run) -> None:
    _, started = stubbed_run
    started["check_model"].side_effect = ModelUnavailableError("gone")

    with pytest.raises(ModelUnavailableError):
        quality_cli._run()

    assert started["running_server"].call_count == 0
    assert started["post"].call_count == 0


def test_run_rejects_an_unset_key_before_touching_the_catalog(stubbed_run) -> None:
    _, started = stubbed_run
    started["load_settings"].return_value = dataclasses.replace(
        started["load_settings"].return_value, mistral_api_key=""
    )

    with pytest.raises(SettingsError, match="MISTRAL_API_KEY is not set"):
        quality_cli._run()

    # Offline first: an unset key must not cost a network round trip.
    assert started["check_model"].call_count == 0


def test_run_checks_the_model_once_before_starting_the_local_server(
    stubbed_run,
) -> None:
    _, started = stubbed_run
    order: list[str] = []
    started["check_model"].side_effect = lambda *a, **k: order.append("check")
    # DEFAULT keeps running_server's configured context manager as the return.
    started["running_server"].side_effect = lambda *a, **k: (
        order.append("server") or DEFAULT
    )

    quality_cli._run()

    assert order == ["check", "server"]


def test_run_surfaces_a_deprecation_notice_and_still_writes_every_row(
    stubbed_run, capsys
) -> None:
    quality_results_path, started = stubbed_run
    notice = "warning: model 'x' is deprecated as of 2026-08-31T12:00:00Z"
    started["check_model"].return_value = notice

    quality_cli._run()

    captured = capsys.readouterr()
    assert notice in captured.err
    # Positively, not just "the notice is absent": stdout is what the operator
    # parses, so any line added to it beyond the two accuracy lines must fail here.
    accuracy_lines = captured.out.splitlines()
    assert len(accuracy_lines) == 2
    assert all(line.startswith("model=") for line in accuracy_lines)
    assert len(read_rows(quality_results_path)) == 2 * len(CLASSIFICATION_TASK_SUITE)


def test_main_exits_1_when_the_model_id_is_gone(stubbed_run, capsys) -> None:
    _, started = stubbed_run
    started["check_model"].side_effect = ModelUnavailableError(
        "Mistral model 'mistral-small-9999' is not on the live catalog"
    )

    with pytest.raises(SystemExit) as exit_info:
        quality_cli.main()

    assert exit_info.value.code == 1
    assert "mistral-small-9999" in capsys.readouterr().err


def test_all_rows_of_one_run_share_one_run_id(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    rows = read_rows(quality_results_path)
    assert len(rows) == 2 * len(CLASSIFICATION_TASK_SUITE)
    assert len({row["run_id"] for row in rows}) == 1
    for row in rows:
        parsed = datetime.fromisoformat(row["captured_at"])
        assert parsed.utcoffset() == timedelta(0)
    assert RUNTIME_ONLY_FIELDS.isdisjoint(rows[0].keys())


def test_all_rows_of_one_run_share_the_identical_provenance_triple(
    stubbed_run,
) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()

    rows = read_rows(quality_results_path)
    assert len(rows) == 2 * len(CLASSIFICATION_TASK_SUITE)
    triples = {
        (row["release_version"], row["commit_sha"], row["tree_dirty"]) for row in rows
    }
    assert triples == {("v0.1.0", "deadbeef", False)}


def test_two_runs_carry_two_distinct_run_ids(stubbed_run) -> None:
    quality_results_path, _ = stubbed_run

    quality_cli._run()
    quality_cli._run()

    assert len({row["run_id"] for row in read_rows(quality_results_path)}) == 2


def test_main_exits_one_when_the_results_path_cannot_be_written(
    stubbed_run, capsys
) -> None:
    # An unwritable or absent results drive surfaces from append_row as OSError.
    # Since the local batch is persisted first, it raises on the first local row,
    # before the cloud suite runs; the operator gets a line, not a traceback.
    with (
        patch(
            "wave_local_ai_v2.quality_cli.append_row",
            side_effect=OSError("[Errno 30] Read-only file system"),
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        quality_cli.main()

    assert exit_info.value.code == 1
    assert "error: [Errno 30] Read-only file system" in capsys.readouterr().err


def test_a_cloud_failure_leaves_the_local_rows_on_disk(stubbed_run) -> None:
    quality_results_path, started = stubbed_run
    started["complete_prompt"].side_effect = MistralRequestError("429 rate limited")

    with pytest.raises(MistralRequestError):
        quality_cli._run()

    rows = read_rows(quality_results_path)
    assert len(rows) == len(CLASSIFICATION_TASK_SUITE)
    assert {row["provider"] for row in rows} == {"local"}
    assert len({row["run_id"] for row in rows}) == 1


def test_local_rows_are_written_before_the_first_cloud_call(stubbed_run) -> None:
    quality_results_path, started = stubbed_run
    rows_at_first_cloud_call: list[int] = []

    def record_then_answer(*args: object, **kwargs: object) -> str:
        rows_at_first_cloud_call.append(len(read_rows(quality_results_path)))
        return "billing"

    started["complete_prompt"].side_effect = record_then_answer

    quality_cli._run()

    assert rows_at_first_cloud_call[0] == len(CLASSIFICATION_TASK_SUITE)
