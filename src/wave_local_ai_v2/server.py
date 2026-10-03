"""llama-server process lifecycle: flag builder, launch, readiness wait, shutdown.

Reproduces the validated baseline command from `context_input/baseline_qwen36.md`
verbatim under the MoE flagship's laptop `gpu` run profile, sourcing every
model-intrinsic flag from a roster entry (`roster.py`) and the host-fitted
values (`-ngl` override, `--n-cpu-moe`, `-t`) from the resolved run profile
(`profiles.py`), instead of from module constants. A profile that resolves no
`--n-cpu-moe` is how a dense entry launches without the flag at all.

Where the server listens, which path answers its health check and whether
this harness may spawn it at all come from the engine registry entry
(`engines.py`), never from module constants. Every function takes the entry
and defaults to the tracked reference engine (llama.cpp).
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

from wave_local_ai_v2 import engines, profiles, roster

PORT_PROBE_TIMEOUT_S = 0.5
READY_POLL_INTERVAL_S = 1.0
READY_TIMEOUT_S = 120.0
SHUTDOWN_GRACE_S = 5.0


# What `cpu_only` adds after `-ngl 0`. Observed on the laptop's CUDA build
# (b10537, `qwen3-0.6b-q8`, a 4001-token prompt): `-ngl 0` alone still drove
# the GPU to 74% utilisation during prompt processing (the host-tensor
# operation offload), while `-ngl 0 --device none` kept it at 0% throughout
# (aidd_docs/tasks/2026_10/2026_10_02_gpu-cpu-never-share-a-fiche/evidence/).
# So `-ngl 0` alone is not CPU-only, and this pair is what the mode emits.
CPU_ONLY_N_GPU_LAYERS = 0
CPU_ONLY_DEVICE_FLAGS: tuple[str, ...] = ("--device", "none")


class ServerStartupError(RuntimeError):
    """Raised when llama-server fails to become ready."""


def build_flags(
    entry: roster.RosterEntry,
    profile: profiles.ResolvedProfile,
    model_path: Path,
    *,
    engine: engines.EngineEntry | None = None,
) -> list[str]:
    """Build the full launch flag list for `entry` under its resolved run profile.

    The one flag builder. `profile` is required: the host-fitted values come
    from the (entry x machine x mode) profile `profiles.resolve` returned
    (entry default, then profile, then operator override), never from a
    default that would silently reuse another machine's values.

    `-ngl` is the profile's (the roster's model-intrinsic default unless the
    profile overrides it; `cpu_only` profiles declare 0), followed under
    `cpu_only` by `CPU_ONLY_DEVICE_FLAGS`. `--n-cpu-moe` is emitted only when
    the profile resolves a value, and `-t` is the profile's thread count. The
    remaining model-intrinsic flags (`-c`, `-fa`, `--jinja`, `-np`,
    `--load-mode`, the sampler flags) come from `entry.server_flags`;
    `--host`/`--port` come from the engine entry (`engine`, default the
    tracked reference engine), and stay outside the fiche's hashed
    projection: the engine configuration hash drops them
    (`engines.normalise_config`).

    This is the one call site for `roster.validate_host_fit`: it runs on the
    resolved value before any flag is built, so a mismatched flag set refuses
    before `running_server` ever spawns a process.
    """
    if profile.entry_id != entry.entry_id:
        raise roster.RosterError(
            f"run profile {profile.profile_id!r} was resolved for roster entry "
            f"{profile.entry_id!r}, not {entry.entry_id!r}"
        )
    roster.validate_host_fit(entry, profile)
    engine = engine or engines.tracked_reference_engine()
    cpu_only = profile.cpu_only
    if cpu_only and profile.n_gpu_layers != CPU_ONLY_N_GPU_LAYERS:
        raise roster.RosterError(
            f"run profile {profile.profile_id!r} is cpu_only but resolves "
            f"n_gpu_layers={profile.n_gpu_layers}"
        )

    flags = entry.server_flags
    sampler = flags["sampler"]
    result = [
        "-m",
        str(model_path),
        "-ngl",
        str(profile.n_gpu_layers),
    ]
    if cpu_only:
        result += CPU_ONLY_DEVICE_FLAGS
    if profile.n_cpu_moe is not None:
        result += ["--n-cpu-moe", str(profile.n_cpu_moe)]
    result += [
        "-c",
        str(flags["context_size"]),
        "-fa",
        str(flags["flash_attention"]),
        "-t",
        str(profile.threads),
    ]
    if flags["jinja"]:
        result.append("--jinja")
    result += [
        "-np",
        str(flags["parallel_slots"]),
        "--load-mode",
        str(flags["load_mode"]),
        "--temp",
        str(sampler["temperature"]),
        "--top-p",
        str(sampler["top_p"]),
        "--top-k",
        str(sampler["top_k"]),
        "--min-p",
        str(sampler["min_p"]),
        "--presence-penalty",
        str(sampler["presence_penalty"]),
        "--host",
        engine.host,
        "--port",
        str(engine.default_port),
    ]
    return result


def sampler_settings(entry: roster.RosterEntry) -> dict[str, float | int]:
    """The five sampler values `entry` launches with, as a runtime-row-shaped dict.

    One source for what `build_flags` puts on the command line and what a
    runtime row reports under `sampling` (`__init__.py`): the five values a
    `/completion` request does not need to re-send because the server
    already applies them from these flags. Only `seed` is sent per request
    (see `RUNTIME_SAMPLING` in `__init__.py`).
    """
    sampler = entry.server_flags["sampler"]
    return {
        "temperature": sampler["temperature"],
        "top_p": sampler["top_p"],
        "top_k": sampler["top_k"],
        "min_p": sampler["min_p"],
        "presence_penalty": sampler["presence_penalty"],
    }


def _port_is_open(host: str, port: int, timeout: float = PORT_PROBE_TIMEOUT_S) -> bool:
    """Return True when something already accepts connections on `host:port`."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def start_server(
    server_path: Path,
    flags: list[str],
    *,
    stderr_sink: IO[bytes] | None = None,
    engine: engines.EngineEntry | None = None,
) -> subprocess.Popen[bytes]:
    """Launch llama-server and poll until it reports ready. Raises on timeout or crash.

    Only a `spawned` engine is launched here: an `attached` engine is a daemon
    this harness does not own, and spawning a second copy of it would be the
    wrong process to measure.

    `stderr_sink`, when given, receives the child's stderr and is neither opened
    nor closed here: `running_server` owns one for the whole context so a
    mid-run crash still has readable diagnostics. With None a temporary file is
    opened and closed around the readiness wait, as before.
    """
    engine = engine or engines.tracked_reference_engine()
    if engine.lifecycle != engines.LIFECYCLE_SPAWNED:
        raise ServerStartupError(
            f"engine {engine.engine_id!r} is declared {engine.lifecycle!r}, not "
            f"{engines.LIFECYCLE_SPAWNED!r}: this harness does not launch it"
        )
    # A stale llama-server still holding the port would answer the first /health
    # poll with 200, so the doomed process we just spawned would pass readiness
    # and every metric of the run would be attributed to the wrong process.
    if _port_is_open(engine.host, engine.default_port):
        raise ServerStartupError(
            f"port {engine.default_port} on {engine.host} is already accepting "
            f"connections; a previous llama-server is likely still running. "
            f"Stop it before starting a measured run."
        )

    health_url = f"{engines.base_url(engine)}{engine.endpoints['health']}"
    if stderr_sink is not None:
        return _spawn_and_wait_ready(server_path, flags, stderr_sink, health_url)
    with tempfile.TemporaryFile() as stderr_file:
        return _spawn_and_wait_ready(server_path, flags, stderr_file, health_url)


def _spawn_and_wait_ready(
    server_path: Path, flags: list[str], stderr_file: IO[bytes], health_url: str
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
            response = requests.get(health_url, timeout=2)
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
    server_path: Path,
    flags: list[str],
    *,
    quiet_exceptions: tuple[type[BaseException], ...] = (),
    engine: engines.EngineEntry | None = None,
) -> Iterator[subprocess.Popen[bytes]]:
    """Context manager: start the server, guarantee shutdown on exit or exception.

    The stderr file lives for the whole context, not just the readiness wait, so
    a failure inside the body (a request that dies mid-run) can still be
    explained by what the child printed rather than surfacing as a bare
    ConnectionError.

    `quiet_exceptions` names the failures that are *not* the server's: a
    generation the caller judged unusable came back over a healthy connection
    from a healthy process, so dumping the child's stderr would bury the
    caller's own one-line diagnosis under 2000 bytes of unrelated log. Those
    still propagate untouched, they just do not trigger the dump.
    """
    with tempfile.TemporaryFile() as stderr_file:
        process = start_server(
            server_path, flags, stderr_sink=stderr_file, engine=engine
        )
        try:
            yield process
        except Exception as exc:
            # Exception, not BaseException: a Ctrl+C is the operator ending the
            # run, not the server failing, and does not warrant a stderr dump.
            # Diagnostics only: the body's exception is re-raised untouched.
            if not isinstance(exc, quiet_exceptions):
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
