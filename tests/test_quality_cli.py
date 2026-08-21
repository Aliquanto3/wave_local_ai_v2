from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2 import mistral_client, quality_cli
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.mistral_client import MistralRequestError
from wave_local_ai_v2.results import read_rows
from wave_local_ai_v2.settings import Settings, SettingsError

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


def test_cloud_calls_pin_temperature_and_seed(stubbed_run) -> None:
    _, started = stubbed_run

    quality_cli._run()

    for call in started["complete_prompt"].call_args_list:
        assert call.kwargs["temperature"] == 0
        assert isinstance(call.kwargs["random_seed"], int)


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
