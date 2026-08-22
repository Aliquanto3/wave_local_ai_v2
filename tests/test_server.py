import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from wave_local_ai_v2 import server


def test_build_flags_matches_baseline() -> None:
    flags = server.build_flags(Path("model.gguf"))

    # The sampler constants moved from strings to numbers so `SAMPLER_SETTINGS`
    # can be reused as the row's `sampling` block; the produced flag list must
    # not move by one byte.
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


def test_sampler_settings_matches_the_flag_constants() -> None:
    assert server.SAMPLER_SETTINGS == {
        "temperature": 1.0,
        "top_p": 0.95,
        "top_k": 20,
        "min_p": 0,
        "presence_penalty": 1.5,
    }


def test_start_server_returns_once_health_reports_ready() -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    not_ready = MagicMock(status_code=503)
    ready = MagicMock(status_code=200)

    with (
        patch("wave_local_ai_v2.server._port_is_open", return_value=False),
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
        patch("wave_local_ai_v2.server._port_is_open", return_value=False),
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


def test_running_server_dumps_the_stderr_tail_for_a_server_failure(capsys) -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    with (
        patch("wave_local_ai_v2.server.start_server", return_value=fake_process),
        patch("wave_local_ai_v2.server.stop_server"),
        pytest.raises(ValueError),
        server.running_server(Path("llama-server.exe"), []),
    ):
        raise ValueError("boom")

    assert "llama-server stderr tail:" in capsys.readouterr().err


def test_running_server_stays_silent_for_a_quiet_exception(capsys) -> None:
    # A generation the caller judged unusable came back over a healthy
    # connection: the child's log explains nothing and would bury the caller's
    # own one-line diagnosis. The exception still propagates untouched.
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    with (
        patch("wave_local_ai_v2.server.start_server", return_value=fake_process),
        patch("wave_local_ai_v2.server.stop_server") as mock_stop,
        pytest.raises(ValueError),
        server.running_server(
            Path("llama-server.exe"), [], quiet_exceptions=(ValueError,)
        ),
    ):
        raise ValueError("boom")

    assert capsys.readouterr().err == ""
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


def test_start_server_refuses_to_run_against_an_occupied_port() -> None:
    with (
        patch("wave_local_ai_v2.server._port_is_open", return_value=True),
        patch("wave_local_ai_v2.server.subprocess.Popen") as mock_popen,
        pytest.raises(server.ServerStartupError, match=str(server.PORT)),
    ):
        server.start_server(Path("llama-server.exe"), [])

    # Nothing was spawned: a doomed second process would otherwise pass the
    # readiness poll against the stale server and be measured in its place.
    mock_popen.assert_not_called()


def test_port_is_open_reports_false_when_nothing_listens() -> None:
    with patch(
        "wave_local_ai_v2.server.socket.create_connection",
        side_effect=OSError("refused"),
    ):
        assert server._port_is_open("127.0.0.1", 8080) is False


def test_running_server_prints_the_stderr_tail_before_reraising(capsys) -> None:
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    def fake_start(server_path, flags, *, stderr_sink):
        stderr_sink.write(b"ggml_cuda: out of memory")
        return fake_process

    with (
        patch("wave_local_ai_v2.server.start_server", side_effect=fake_start),
        patch("wave_local_ai_v2.server.stop_server") as mock_stop,
        pytest.raises(ValueError, match="mid-run failure"),
        server.running_server(Path("llama-server.exe"), []),
    ):
        raise ValueError("mid-run failure")

    captured = capsys.readouterr()
    assert "llama-server stderr tail:" in captured.err
    assert "ggml_cuda: out of memory" in captured.err
    mock_stop.assert_called_once_with(fake_process)


def test_start_server_leaves_a_supplied_stderr_sink_open() -> None:
    # The whole point of the sink: the caller keeps reading it after the
    # readiness wait returns, so a mid-run crash still has diagnostics.
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    with tempfile.TemporaryFile() as sink:
        with (
            patch("wave_local_ai_v2.server._port_is_open", return_value=False),
            patch(
                "wave_local_ai_v2.server.subprocess.Popen", return_value=fake_process
            ),
            patch(
                "wave_local_ai_v2.server.requests.get",
                return_value=MagicMock(status_code=200),
            ),
        ):
            server.start_server(Path("llama-server.exe"), [], stderr_sink=sink)

        sink.write(b"still writable")
        assert sink.closed is False
