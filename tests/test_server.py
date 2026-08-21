from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from wave_local_ai_v2 import server


def test_build_flags_matches_baseline() -> None:
    flags = server.build_flags(Path("model.gguf"))

    assert flags == [
        "-m",
        "model.gguf",
        "-ngl",
        "99",
        "--n-cpu-moe",
        "37",
        "-c",
        "32768",
        "-fa",
        "on",
        "-t",
        "8",
        "--jinja",
        "-np",
        "1",
        "--load-mode",
        "none",
        "--temp",
        "1.0",
        "--top-p",
        "0.95",
        "--top-k",
        "20",
        "--min-p",
        "0",
        "--presence-penalty",
        "1.5",
        "--host",
        "127.0.0.1",
        "--port",
        "8080",
    ]


def test_start_server_returns_once_health_reports_ready() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    not_ready = MagicMock(status_code=503)
    ready = MagicMock(status_code=200)

    with (
        patch("wave_local_ai_v2.server.subprocess.Popen", return_value=fake_process),
        patch(
            "wave_local_ai_v2.server.requests.get",
            side_effect=[requests.exceptions.ConnectionError(), not_ready, ready],
        ),
        patch("wave_local_ai_v2.server.time.sleep"),
    ):
        result = server.start_server(Path("llama-server.exe"), [])

    assert result is fake_process


def test_start_server_raises_immediately_when_process_dies() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = 1
    fake_process.returncode = 1

    with (
        patch("wave_local_ai_v2.server.subprocess.Popen", return_value=fake_process),
        patch("wave_local_ai_v2.server.time.sleep") as mock_sleep,
        pytest.raises(server.ServerStartupError),
    ):
        server.start_server(Path("llama-server.exe"), [])

    mock_sleep.assert_not_called()


def test_stop_server_terminates_running_process() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    server.stop_server(fake_process)

    assert fake_process.send_signal.called or fake_process.terminate.called
    fake_process.wait.assert_called()


def test_stop_server_skips_already_exited_process() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = 0

    server.stop_server(fake_process)

    fake_process.wait.assert_not_called()


def test_running_server_stops_on_exception() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    with (
        patch("wave_local_ai_v2.server.start_server", return_value=fake_process),
        patch("wave_local_ai_v2.server.stop_server") as mock_stop,
        pytest.raises(ValueError),
        server.running_server(Path("llama-server.exe"), []),
    ):
        raise ValueError("boom")

    mock_stop.assert_called_once_with(fake_process)
