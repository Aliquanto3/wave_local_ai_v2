import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from wave_local_ai_v2 import build_probe

# The real banner captured live on this machine (plan.md's Resources table),
# stderr only -- stdout is empty at exit code 0.
REAL_BANNER_STDERR = (
    "version: 0.1.2-dev (build 10537, commit bf0040e15)\n"
    "built with Clang 20.1.8 for Windows x86_64\n"
)


def test_probe_build_parses_the_real_captured_banner() -> None:
    with patch(
        "wave_local_ai_v2.build_probe.subprocess.run",
        return_value=MagicMock(stdout="", stderr=REAL_BANNER_STDERR),
    ) as mock_run:
        result = build_probe.probe_build(Path("llama-server.exe"))

    assert result == "b10537"
    mock_run.assert_called_once_with(
        ["llama-server.exe", "--version"],
        capture_output=True,
        text=True,
        timeout=build_probe.VERSION_PROBE_TIMEOUT_S,
        check=False,
    )


def test_probe_build_returns_none_on_an_unparseable_banner() -> None:
    with patch(
        "wave_local_ai_v2.build_probe.subprocess.run",
        return_value=MagicMock(stdout="", stderr="not a version banner at all"),
    ):
        result = build_probe.probe_build(Path("llama-server.exe"))

    assert result is None


def test_probe_build_returns_none_on_an_os_error() -> None:
    with patch(
        "wave_local_ai_v2.build_probe.subprocess.run",
        side_effect=OSError("binary not found"),
    ):
        result = build_probe.probe_build(Path("missing-server.exe"))

    assert result is None


def test_probe_build_returns_none_on_a_timeout() -> None:
    with patch(
        "wave_local_ai_v2.build_probe.subprocess.run",
        side_effect=subprocess.TimeoutExpired(
            cmd="llama-server.exe --version", timeout=5.0
        ),
    ):
        result = build_probe.probe_build(Path("llama-server.exe"))

    assert result is None


def test_probe_build_never_starts_a_real_subprocess() -> None:
    # A patched-out subprocess.run means no real process is ever spawned by
    # this test module, matching the phase's teardown note.
    with patch("wave_local_ai_v2.build_probe.subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(stdout="", stderr=REAL_BANNER_STDERR)
        build_probe.probe_build(Path("llama-server.exe"))
        assert mock_run.called
