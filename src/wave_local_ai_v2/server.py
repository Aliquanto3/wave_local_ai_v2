"""llama-server process lifecycle: flag builder, launch, readiness wait, shutdown.

Reproduces the validated baseline command from `context_input/baseline_qwen36.md`
verbatim. Every flag value is a named constant so a future increment can override
one (e.g. --n-cpu-moe) without touching the builder's shape.
"""

from __future__ import annotations

import signal
import socket
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import IO

import requests

HOST = "127.0.0.1"
PORT = 8080
N_GPU_LAYERS = 99
N_CPU_MOE = 37
CONTEXT_SIZE = 32768
FLASH_ATTENTION = "on"
THREADS = 8
PARALLEL_SLOTS = 1
TEMPERATURE = "1.0"
TOP_P = "0.95"
TOP_K = "20"
MIN_P = "0"
PRESENCE_PENALTY = "1.5"

PORT_PROBE_TIMEOUT_S = 0.5
READY_POLL_INTERVAL_S = 1.0
READY_TIMEOUT_S = 120.0
SHUTDOWN_GRACE_S = 5.0


class ServerStartupError(RuntimeError):
    """Raised when llama-server fails to become ready."""


def build_flags(model_path: Path) -> list[str]:
    """Build the exact flag list validated in the baseline for this model/machine."""
    return [
        "-m",
        str(model_path),
        "-ngl",
        str(N_GPU_LAYERS),
        "--n-cpu-moe",
        str(N_CPU_MOE),
        "-c",
        str(CONTEXT_SIZE),
        "-fa",
        FLASH_ATTENTION,
        "-t",
        str(THREADS),
        "--jinja",
        "-np",
        str(PARALLEL_SLOTS),
        "--load-mode",
        "none",
        "--temp",
        TEMPERATURE,
        "--top-p",
        TOP_P,
        "--top-k",
        TOP_K,
        "--min-p",
        MIN_P,
        "--presence-penalty",
        PRESENCE_PENALTY,
        "--host",
        HOST,
        "--port",
        str(PORT),
    ]


def _port_is_open(host: str, port: int, timeout: float = PORT_PROBE_TIMEOUT_S) -> bool:
    """Return True when something already accepts connections on `host:port`."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_server(
    server_path: Path, flags: list[str], *, stderr_sink: IO[bytes] | None = None
) -> subprocess.Popen[bytes]:
    """Launch llama-server and poll until it reports ready. Raises on timeout or crash.

    `stderr_sink`, when given, receives the child's stderr and is neither opened
    nor closed here: `running_server` owns one for the whole context so a
    mid-run crash still has readable diagnostics. With None a temporary file is
    opened and closed around the readiness wait, as before.
    """
    # A stale llama-server still holding the port would answer the first /health
    # poll with 200, so the doomed process we just spawned would pass readiness
    # and every metric of the run would be attributed to the wrong process.
    if _port_is_open(HOST, PORT):
        raise ServerStartupError(
            f"port {PORT} on {HOST} is already accepting connections; "
            f"a previous llama-server is likely still running. "
            f"Stop it before starting a measured run."
        )

    if stderr_sink is not None:
        return _spawn_and_wait_ready(server_path, flags, stderr_sink)
    with tempfile.TemporaryFile() as stderr_file:
        return _spawn_and_wait_ready(server_path, flags, stderr_file)


def _spawn_and_wait_ready(
    server_path: Path, flags: list[str], stderr_file: IO[bytes]
) -> subprocess.Popen[bytes]:
    popen_kwargs: dict[str, object] = {
        "stderr": stderr_file,
        "stdout": subprocess.DEVNULL,
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(  # type: ignore[call-overload]
        [str(server_path), *flags], **popen_kwargs
    )

    deadline = time.monotonic() + READY_TIMEOUT_S
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise ServerStartupError(
                f"llama-server exited early with code {process.returncode}: "
                f"{_read_stderr_tail(stderr_file)}"
            )
        try:
            response = requests.get(f"http://{HOST}:{PORT}/health", timeout=2)
            if response.status_code == 200:
                return process
        except requests.exceptions.RequestException:
            pass
        time.sleep(READY_POLL_INTERVAL_S)

    stop_server(process)
    raise ServerStartupError(
        f"llama-server did not become ready within {READY_TIMEOUT_S}s: "
        f"{_read_stderr_tail(stderr_file)}"
    )


def stop_server(process: subprocess.Popen[bytes]) -> None:
    """Terminate the server gracefully, killing it if it doesn't exit in time."""
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
    else:
        process.terminate()
    try:
        process.wait(timeout=SHUTDOWN_GRACE_S)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


@contextmanager
def running_server(
    server_path: Path, flags: list[str]
) -> Iterator[subprocess.Popen[bytes]]:
    """Context manager: start the server, guarantee shutdown on exit or exception.

    The stderr file lives for the whole context, not just the readiness wait, so
    a failure inside the body (a request that dies mid-run) can still be
    explained by what the child printed rather than surfacing as a bare
    ConnectionError.
    """
    with tempfile.TemporaryFile() as stderr_file:
        process = start_server(server_path, flags, stderr_sink=stderr_file)
        try:
            yield process
        except BaseException:
            # Diagnostics only: the body's exception is re-raised untouched.
            print("llama-server stderr tail:", file=sys.stderr)
            print(_read_stderr_tail(stderr_file), file=sys.stderr)
            raise
        finally:
            stop_server(process)


def _read_stderr_tail(stderr_file: IO[bytes], max_bytes: int = 2000) -> str:
    try:
        stderr_file.seek(0)
        data = stderr_file.read()
        return data[-max_bytes:].decode(errors="replace")
    except Exception:  # noqa: BLE001 - best-effort diagnostics only
        return "<stderr unavailable>"
