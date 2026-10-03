import dataclasses
import json
import signal
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

from wave_local_ai_v2 import engines, profiles, roster, server

REAL_ROSTER_PATH = Path("aidd_docs/roster/models.json")
REAL_ROSTER_ENTRY_ID = "qwen3.6-35b-a3b-ud-iq4xs"
SHIPPED_DENSE_ENTRY_ID = "qwen3-0.6b-q8"
LAPTOP = "laptop-mobile-gpu"
TOWER = "tower-desktop-gpu"


def _shipped_entry(entry_id: str = REAL_ROSTER_ENTRY_ID) -> roster.RosterEntry:
    loaded = roster.load_roster(REAL_ROSTER_PATH)
    return roster.resolve_entry(loaded, entry_id)


def _shipped_profile(
    entry: roster.RosterEntry,
    mode: str = "gpu",
    *,
    n_cpu_moe: int | None = None,
    threads: int | None = None,
) -> profiles.ResolvedProfile:
    """The shipped laptop profile of `entry`, with any operator override."""
    return profiles.resolve_for_run(
        entry, LAPTOP, mode, operator_n_cpu_moe=n_cpu_moe, operator_threads=threads
    )


def _explicit_profile(
    entry: roster.RosterEntry,
    *,
    n_cpu_moe: int | None,
    mode: str = "gpu",
    n_gpu_layers: int | None = None,
) -> profiles.ResolvedProfile:
    if n_gpu_layers is None:
        n_gpu_layers = 0 if mode == "cpu_only" else entry.server_flags["n_gpu_layers"]
    return profiles.ResolvedProfile(
        profile_id=profiles.profile_id_for(entry.entry_id, "test-machine", mode),
        entry_id=entry.entry_id,
        machine_id="test-machine",
        compute_mode=mode,
        n_gpu_layers=n_gpu_layers,
        n_cpu_moe=n_cpu_moe,
        threads=8,
    )


def test_build_flags_matches_baseline() -> None:
    entry = _shipped_entry()

    flags = server.build_flags(
        entry, _shipped_profile(entry), model_path=Path("model.gguf")
    )

    # The shipped roster entry under its shipped laptop `gpu` run profile must
    # reproduce the exact flag list the old hardcoded-constant version built.
    # The host values come from the profile registry, not from literals here,
    # so a profile edit fails this test rather than silently changing what the
    # CLIs launch. `37` and `8` moved from the roster's `validated_host` into
    # the profile: the same command, reached through the profile.
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


def test_the_laptop_and_tower_gpu_profiles_launch_different_host_values(
    tmp_path: Path,
) -> None:
    """One model on two machines is two named profiles, never one reused."""

    def fact(value: int) -> dict[str, object]:
        return {"value": value, "source": "declared", "read_from": "test"}

    path = tmp_path / "profiles.json"
    path.write_text(
        json.dumps(
            {
                "registry_version": 1,
                "defaults": {
                    LAPTOP: {"gpu": {"threads": fact(8)}},
                    TOWER: {"gpu": {"threads": fact(12)}},
                },
                "entries": {
                    REAL_ROSTER_ENTRY_ID: {
                        LAPTOP: {"gpu": {"n_cpu_moe": fact(37)}},
                        TOWER: {"gpu": {"n_cpu_moe": fact(20)}},
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    registry = profiles.load_registry(path)
    entry = _shipped_entry()
    laptop = profiles.resolve(registry, entry, LAPTOP, "gpu")
    tower = profiles.resolve(registry, entry, TOWER, "gpu")

    laptop_flags = server.build_flags(entry, laptop, Path("model.gguf"))
    tower_flags = server.build_flags(entry, tower, Path("model.gguf"))

    def value(flags: list[str], flag: str) -> str:
        return flags[flags.index(flag) + 1]

    assert laptop.profile_id != tower.profile_id
    assert (value(laptop_flags, "-t"), value(laptop_flags, "--n-cpu-moe")) == (
        "8",
        "37",
    )
    assert (value(tower_flags, "-t"), value(tower_flags, "--n-cpu-moe")) == (
        "12",
        "20",
    )


def test_build_flags_refuses_a_profile_resolved_for_another_entry() -> None:
    entry = _shipped_entry()
    other = _shipped_profile(_shipped_entry(SHIPPED_DENSE_ENTRY_ID))
    with pytest.raises(roster.RosterError, match="resolved for roster entry"):
        server.build_flags(entry, other, Path("model.gguf"))


def test_build_flags_refuses_a_cpu_only_profile_that_keeps_gpu_layers() -> None:
    entry = _shipped_entry()
    profile = _explicit_profile(entry, n_cpu_moe=None, mode="cpu_only", n_gpu_layers=99)
    with pytest.raises(roster.RosterError, match="n_gpu_layers=99"):
        server.build_flags(entry, profile, Path("model.gguf"))


def test_build_flags_refuses_a_dense_entry_given_a_host_n_cpu_moe() -> None:
    dense_entry = _make_entry(
        entry_id="fake-dense-model",
        kind="dense",
        expert_count=0,
    )

    with (
        pytest.raises(roster.RosterError, match="fake-dense-model"),
        patch("wave_local_ai_v2.server.subprocess.Popen") as mock_popen,
    ):
        server.build_flags(
            dense_entry,
            _explicit_profile(dense_entry, n_cpu_moe=1),
            model_path=Path("model.gguf"),
        )

    mock_popen.assert_not_called()


def test_build_flags_refuses_an_over_ceiling_host_n_cpu_moe() -> None:
    moe_entry = _make_entry(
        entry_id="fake-moe-model",
        kind="moe",
        expert_count=40,
    )

    with (
        pytest.raises(roster.RosterError, match="40"),
        patch("wave_local_ai_v2.server.subprocess.Popen") as mock_popen,
    ):
        server.build_flags(
            moe_entry,
            _explicit_profile(moe_entry, n_cpu_moe=41),
            model_path=Path("model.gguf"),
        )

    mock_popen.assert_not_called()


def test_build_flags_for_a_dense_entry_omits_the_moe_offload() -> None:
    """A dense entry under its laptop `gpu` profile: no `--n-cpu-moe`.

    Not a `kind == "dense"` branch in the flag builder -- the profile declares
    no `n_cpu_moe` for the entry and no operator override is set, so the
    resolution produces no flag. Every other flag keeps its position.
    """
    entry = _shipped_entry(SHIPPED_DENSE_ENTRY_ID)

    flags = server.build_flags(
        entry, _shipped_profile(entry), model_path=Path("model.gguf")
    )

    assert "--n-cpu-moe" not in flags
    assert flags == [
        "-m",
        "model.gguf",
        "-ngl",
        str(entry.server_flags["n_gpu_layers"]),
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
        "auto",
        "--temp",
        "0.6",
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


def test_cpu_only_puts_every_layer_on_the_cpu_and_emits_no_moe_offload() -> None:
    """`cpu_only` on the MoE flagship: `-ngl 0 --device none`, no `--n-cpu-moe`.

    The flagship's `n_cpu_moe` 37 is its laptop `gpu` profile's value only;
    the `cpu_only` profile overrides the roster's `-ngl` with 0 and declares
    no offload. Every other flag keeps its place.
    """
    entry = _shipped_entry()
    gpu = server.build_flags(
        entry, _shipped_profile(entry), model_path=Path("model.gguf")
    )

    flags = server.build_flags(
        entry, _shipped_profile(entry, "cpu_only"), model_path=Path("model.gguf")
    )

    assert flags[:6] == ["-m", "model.gguf", "-ngl", "0", "--device", "none"]
    assert "--n-cpu-moe" not in flags
    # The gpu list minus its `-m`/`-ngl` head and its `--n-cpu-moe 37` pair.
    assert flags[6:] == gpu[6:]


def test_cpu_only_refuses_a_supplied_n_cpu_moe_naming_the_mode() -> None:
    entry = _shipped_entry()
    with pytest.raises(roster.RosterError, match="cpu_only"):
        server.build_flags(
            entry,
            _shipped_profile(entry, "cpu_only", n_cpu_moe=37),
            model_path=Path("model.gguf"),
        )


def test_build_flags_refuses_a_shipped_dense_entry_given_an_explicit_zero() -> None:
    """`SERVER_N_CPU_MOE=0` is an instruction, not the absence of one.

    The unset state is `None`. An operator who writes `0` has asked for MoE
    offload of no experts, which a dense entry cannot honour.
    """
    entry = _shipped_entry(SHIPPED_DENSE_ENTRY_ID)

    with (
        pytest.raises(roster.RosterError, match=SHIPPED_DENSE_ENTRY_ID),
        patch("wave_local_ai_v2.server.subprocess.Popen") as mock_popen,
    ):
        server.build_flags(
            entry, _shipped_profile(entry, n_cpu_moe=0), model_path=Path("model.gguf")
        )

    mock_popen.assert_not_called()


def _make_entry(*, entry_id: str, kind: str, expert_count: int) -> roster.RosterEntry:
    return roster.RosterEntry(
        entry_id=entry_id,
        repo="fake/repo",
        revision="main",
        file="fake.gguf",
        display_id="Fake Model",
        quant="UD-IQ4_XS",
        sha256="0" * 64,
        architecture=roster.Architecture(
            kind=kind, expert_count=expert_count, active_params_b=3.1
        ),
        server_flags={
            "n_gpu_layers": 99,
            "context_size": 32768,
            "flash_attention": "on",
            "jinja": True,
            "parallel_slots": 1,
            "load_mode": "none",
            "sampler": {
                "temperature": 1.0,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0,
                "presence_penalty": 1.5,
            },
        },
    )


def test_sampler_settings_matches_the_shipped_entry() -> None:
    entry = _shipped_entry()

    assert server.sampler_settings(entry) == {
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


def test_a_stop_during_the_readiness_wait_stops_the_half_started_server() -> None:
    # A large model loads for tens of seconds; a stop landing then happens
    # before `running_server`'s own teardown covers the process.
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    with (
        patch("wave_local_ai_v2.server._port_is_open", return_value=False),
        patch("wave_local_ai_v2.server.subprocess.Popen", return_value=fake_process),
        patch(
            "wave_local_ai_v2.server.requests.get",
            return_value=MagicMock(status_code=503),
        ),
        patch(
            "wave_local_ai_v2.server.time.sleep",
            side_effect=server.StopRequested("run stopped by signal 21"),
        ),
        patch("wave_local_ai_v2.server.stop_server") as mock_stop,
        pytest.raises(server.StopRequested),
    ):
        server.start_server(Path("llama-server.exe"), [])

    mock_stop.assert_called_once_with(fake_process)


def test_the_graceful_stop_signal_raises_stop_requested() -> None:
    # The conftest fixture restores the previous handler after this test.
    stop_signal = signal.SIGBREAK if sys.platform == "win32" else signal.SIGTERM

    server.install_graceful_stop()
    handler = signal.getsignal(stop_signal)

    assert callable(handler)
    with pytest.raises(server.StopRequested, match="stopped by signal"):
        handler(stop_signal, None)


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
        pytest.raises(server.ServerStartupError, match="port 8080 on 127.0.0.1"),
    ):
        server.start_server(Path("llama-server.exe"), [])

    # Nothing was spawned: a doomed second process would otherwise pass the
    # readiness poll against the stale server and be measured in its place.
    mock_popen.assert_not_called()


def _engine(**changes: object) -> engines.EngineEntry:
    return dataclasses.replace(engines.tracked_reference_engine(), **changes)  # type: ignore[arg-type]


def test_host_port_and_health_path_are_read_from_the_engine_entry() -> None:
    engine = _engine(host="127.0.0.2", default_port=9191)
    fake_process = MagicMock()
    fake_process.poll.return_value = None

    entry = _shipped_entry()
    flags = server.build_flags(
        entry, _shipped_profile(entry), Path("<gguf>"), engine=engine
    )
    with (
        patch("wave_local_ai_v2.server._port_is_open", return_value=False) as probe,
        patch("wave_local_ai_v2.server.subprocess.Popen", return_value=fake_process),
        patch(
            "wave_local_ai_v2.server.requests.get",
            return_value=MagicMock(status_code=200),
        ) as get,
    ):
        server.start_server(Path("llama-server.exe"), flags, engine=engine)

    assert flags[-4:] == ["--host", "127.0.0.2", "--port", "9191"]
    probe.assert_called_once_with("127.0.0.2", 9191)
    assert get.call_args.args[0] == "http://127.0.0.2:9191/health"


def test_an_attached_engine_is_never_spawned() -> None:
    engine = _engine(lifecycle=engines.LIFECYCLE_ATTACHED)

    with (
        patch("wave_local_ai_v2.server.subprocess.Popen") as mock_popen,
        pytest.raises(server.ServerStartupError, match="'attached'"),
    ):
        server.start_server(Path("llama-server.exe"), [], engine=engine)

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

    def fake_start(server_path, flags, *, stderr_sink, engine):
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
