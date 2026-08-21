import subprocess
import sys
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

    # Name the expected call for this platform: an `or` across both branches
    # passes either way and would not catch the two being swapped.
    if sys.platform == "win32":
        fake_process.send_signal.assert_called_once()
        fake_process.terminate.assert_not_called()
    else:
        fake_process.terminate.assert_called_once()
        fake_process.send_signal.assert_not_called()
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


def test_stop_server_kills_process_that_ignores_the_grace_period() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None
    fake_process.wait.side_effect = [
        subprocess.TimeoutExpired(cmd="llama-server", timeout=server.SHUTDOWN_GRACE_S),
        0,
    ]

    server.stop_server(fake_process)

    fake_process.kill.assert_called_once()
    assert fake_process.wait.call_count == 2


def test_running_server_stops_the_process_on_normal_exit() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    # stop_server is deliberately NOT mocked: the criterion is that leaving the
    # block terminates the process, which a mocked stop_server cannot show.
    with (
        patch("wave_local_ai_v2.server.start_server", return_value=fake_process),
        server.running_server(Path("llama-server.exe"), []) as process,
    ):
        assert process is fake_process

    if sys.platform == "win32":
        fake_process.send_signal.assert_called_once()
    else:
        fake_process.terminate.assert_called_once()
    fake_process.wait.assert_called()
