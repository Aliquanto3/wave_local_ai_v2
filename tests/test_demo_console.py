"""The demo console: declared sets, validation, the lock, the child, the final event."""

from __future__ import annotations

import subprocess
import sys
import textwrap
import time
from collections.abc import Iterator
from dataclasses import replace
from pathlib import Path

import pytest
from store_fixtures import ROSTER_ENTRY_ID

from wave_local_ai_v2 import demo_console, profiles, roster, suite_registry
from wave_local_ai_v2.settings import ServiceSettings

MACHINE = "laptop-mobile-gpu"
SUITE = "translation-business-short-form"
PROFILE_ID = profiles.profile_id_for(ROSTER_ENTRY_ID, MACHINE, "gpu")
HOLDER = demo_console.RunHolder(
    kind="quality",
    suite=SUITE,
    roster_entry_id=ROSTER_ENTRY_ID,
    profile_id=PROFILE_ID,
    started_at="2026-09-24T10:00:00+00:00",
)


@pytest.fixture(autouse=True)
def _free_console() -> Iterator[None]:
    demo_console.release()
    yield
    demo_console.release()


@pytest.fixture
def settings(bundle: dict[str, Path], tmp_path: Path) -> ServiceSettings:
    return ServiceSettings(
        api_key="a-key",  # pragma: allowlist secret
        host="127.0.0.1",
        port=8000,
        schema_floor="7",
        runtime_results_path=bundle["runtime"],
        quality_results_path=bundle["quality"],
        fiche_registry_dir=bundle["fiches"],
        roster_path=bundle["roster"],
        suite_definitions_dir=bundle["suites"],
        leader_sets_dir=bundle["leader_sets"],
        dashboard_bundle_dir=tmp_path / "dist",
        dashboard_origin="https://127.0.0.1:8000",
        tls_certfile=tmp_path / "cert.pem",
        tls_keyfile=tmp_path / "key.pem",
        machine_registry_path=bundle["machines"],
        demo_mode=True,
        machine_id=MACHINE,
    )


# --------------------------------------------------------------------------
# Declared sets
# --------------------------------------------------------------------------


def test_suite_ids_are_the_suite_registrys_own_ids() -> None:
    assert demo_console.suite_ids() == tuple(suite_registry.registered_ids())


def test_roster_entry_ids_are_the_loaded_rosters_keys(
    settings: ServiceSettings,
) -> None:
    expected = tuple(roster.load_roster(settings.roster_path).entries)

    assert demo_console.roster_entry_ids(settings) == expected == (ROSTER_ENTRY_ID,)


def test_the_options_payload_composes_every_set_and_the_holder(
    settings: ServiceSettings,
) -> None:
    payload = demo_console.options_payload(settings, HOLDER)

    assert payload["kinds"] == ["runtime", "quality"]
    assert payload["suites"] == suite_registry.registered_ids()
    assert payload["roster_entries"] == [ROSTER_ENTRY_ID]
    assert payload["machine_id"] == MACHINE
    assert payload["machine_absence"] is None
    assert payload["holder"] == {
        "kind": "quality",
        "suite": SUITE,
        "roster_entry_id": ROSTER_ENTRY_ID,
        "profile_id": PROFILE_ID,
        "started_at": "2026-09-24T10:00:00+00:00",
        "run_id": None,
    }
    assert demo_console.options_payload(settings, None)["holder"] is None


def test_the_options_list_this_machines_declared_profiles_only(
    settings: ServiceSettings,
) -> None:
    offered = demo_console.options_payload(settings, None)["profiles"]

    declared_here = [
        p
        for p in profiles.declared_profiles(
            profiles.tracked_registry(), ROSTER_ENTRY_ID
        )
        if f"@{MACHINE}/" in p
    ]
    assert [p["profile_id"] for p in offered[ROSTER_ENTRY_ID]] == declared_here
    assert {p["machine_id"] for p in offered[ROSTER_ENTRY_ID]} == {MACHINE}
    assert {p["compute_mode"] for p in offered[ROSTER_ENTRY_ID]} == {"gpu", "cpu_only"}


@pytest.mark.parametrize(
    ("machine_id", "reason"),
    [(None, "MACHINE_ID is not set"), ("a-stranger", "not a declared machine")],
)
def test_with_no_usable_service_machine_no_profile_is_offered_and_the_absence_is_named(
    settings: ServiceSettings, machine_id: str | None, reason: str
) -> None:
    payload = demo_console.options_payload(
        replace(settings, machine_id=machine_id), None
    )

    assert payload["machine_id"] is None
    assert reason in payload["machine_absence"]
    assert payload["profiles"] == {ROSTER_ENTRY_ID: []}


# --------------------------------------------------------------------------
# The occupancy lock
# --------------------------------------------------------------------------


def test_a_free_console_installs_the_holder() -> None:
    assert demo_console.try_acquire(HOLDER) is None
    assert demo_console.current_holder() == HOLDER


def test_a_held_console_answers_the_original_holder_never_the_caller() -> None:
    demo_console.try_acquire(HOLDER)
    demo_console.record_run_id("abc123")
    second = replace(HOLDER, kind="runtime", suite=None, started_at="later")

    refused_by = demo_console.try_acquire(second)

    assert refused_by == replace(HOLDER, run_id="abc123")
    assert demo_console.current_holder() == replace(HOLDER, run_id="abc123")


def test_release_frees_the_console_for_the_next_acquire() -> None:
    demo_console.try_acquire(HOLDER)
    demo_console.release()

    assert demo_console.current_holder() is None
    assert demo_console.try_acquire(HOLDER) is None


def test_recording_a_run_id_on_a_free_console_does_nothing() -> None:
    demo_console.record_run_id("abc123")

    assert demo_console.current_holder() is None


# --------------------------------------------------------------------------
# Request validation
# --------------------------------------------------------------------------

VALID_RUNTIME = {
    "kind": "runtime",
    "roster_entry_id": ROSTER_ENTRY_ID,
    "machine_id": MACHINE,
    "compute_mode": "gpu",
}
VALID_QUALITY = {**VALID_RUNTIME, "kind": "quality", "suite": SUITE}
RUNTIME_REQUEST = demo_console.ConsoleRequest(
    "runtime", None, ROSTER_ENTRY_ID, MACHINE, "gpu"
)
QUALITY_REQUEST = demo_console.ConsoleRequest(
    "quality", SUITE, ROSTER_ENTRY_ID, MACHINE, "cpu_only"
)


@pytest.fixture
def no_spawn(monkeypatch) -> list[object]:
    """Fail the test if anything reaches `subprocess.Popen`."""
    spawned: list[object] = []

    def refuse(*args: object, **kwargs: object) -> None:
        spawned.append(args)
        raise AssertionError("a refused request must start no process")

    monkeypatch.setattr(demo_console.subprocess, "Popen", refuse)
    return spawned


def test_a_valid_runtime_request_names_no_suite(settings: ServiceSettings) -> None:
    request = demo_console.validate_request(dict(VALID_RUNTIME), settings)

    assert request == RUNTIME_REQUEST
    assert request.profile_id == PROFILE_ID


def test_a_valid_quality_request_carries_its_suite(settings: ServiceSettings) -> None:
    payload = {**VALID_QUALITY, "compute_mode": "cpu_only"}

    request = demo_console.validate_request(payload, settings)

    assert request == QUALITY_REQUEST


@pytest.mark.parametrize(
    "payload",
    [
        ["runtime"],
        {**VALID_RUNTIME, "extra": "x"},
        {**VALID_RUNTIME, "kind": "judge-probe"},
        {**VALID_RUNTIME, "suite": "classification"},
        {**VALID_QUALITY, "suite": "bogus"},
        {**VALID_QUALITY, "suite": None},
        {**VALID_RUNTIME, "roster_entry_id": "not-in-the-roster"},
        {**VALID_RUNTIME, "roster_entry_id": "../models.json"},
        {**VALID_RUNTIME, "roster_entry_id": "a;rm -rf /"},
        {**VALID_RUNTIME, "roster_entry_id": "--help"},
        {**VALID_RUNTIME, "roster_entry_id": "$(whoami)"},
        {**VALID_RUNTIME, "roster_entry_id": 3},
        {"kind": "runtime"},
        {**VALID_RUNTIME, "compute_mode": "turbo"},
        {**VALID_RUNTIME, "compute_mode": None},
        {**VALID_RUNTIME, "machine_id": "../machines.json"},
        {**VALID_RUNTIME, "profile_id": PROFILE_ID},
        {k: v for k, v in VALID_RUNTIME.items() if k != "machine_id"},
    ],
)
def test_a_request_outside_the_declared_sets_is_refused_before_any_spawn(
    settings: ServiceSettings, no_spawn: list[object], payload: object
) -> None:
    with pytest.raises(demo_console.ConsoleRequestError):
        demo_console.validate_request(payload, settings)

    assert no_spawn == []


def test_a_profile_of_another_declared_machine_is_refused_naming_both(
    settings: ServiceSettings, no_spawn: list[object]
) -> None:
    payload = {**VALID_RUNTIME, "machine_id": "tower-desktop-gpu"}

    with pytest.raises(demo_console.ConsoleRequestError) as exc_info:
        demo_console.validate_request(payload, settings)

    assert "'tower-desktop-gpu'" in str(exc_info.value)
    assert f"({MACHINE!r})" in str(exc_info.value)
    assert no_spawn == []


def test_every_request_is_refused_while_the_service_names_no_machine(
    settings: ServiceSettings, no_spawn: list[object]
) -> None:
    with pytest.raises(demo_console.ConsoleRequestError, match="MACHINE_ID"):
        demo_console.validate_request(
            dict(VALID_RUNTIME), replace(settings, machine_id=None)
        )

    assert no_spawn == []


def test_a_mode_this_machine_declares_no_profile_for_is_refused(
    settings: ServiceSettings, no_spawn: list[object]
) -> None:
    pro_pc = replace(settings, machine_id="pro-pc-no-gpu")
    payload = {**VALID_RUNTIME, "machine_id": "pro-pc-no-gpu"}

    with pytest.raises(demo_console.ConsoleRequestError, match="no run profile"):
        demo_console.validate_request(payload, pro_pc)

    assert no_spawn == []


def test_the_runtime_command_is_constants_plus_the_validated_id() -> None:
    argv, env = demo_console.command_for(RUNTIME_REQUEST)

    assert argv == [sys.executable, "-u", "-m", "wave_local_ai_v2"]
    assert env == {
        "ROSTER_ENTRY_ID": ROSTER_ENTRY_ID,
        "MACHINE_ID": MACHINE,
        "COMPUTE_MODE": "gpu",
    }


def test_the_quality_command_passes_the_validated_suite_as_its_own_argument() -> None:
    argv, env = demo_console.command_for(QUALITY_REQUEST)

    assert argv == [
        sys.executable,
        "-u",
        "-m",
        "wave_local_ai_v2.quality_cli",
        "--suite",
        SUITE,
    ]
    assert env == {
        "ROSTER_ENTRY_ID": ROSTER_ENTRY_ID,
        "MACHINE_ID": MACHINE,
        "COMPUTE_MODE": "cpu_only",
    }


def test_a_dotenv_holding_the_key_cannot_restore_it_in_a_real_child(
    monkeypatch, tmp_path: Path
) -> None:
    # The CLIs call `load_dotenv()`, which fills only absent variables: the
    # blanked key must survive a `.env` that sets it.
    secret = "key-from-dotenv"  # pragma: allowlist secret
    dotenv = tmp_path / ".env"
    dotenv.write_text(f"SERVICE_API_KEY={secret}\n", encoding="utf-8")
    monkeypatch.setenv("SERVICE_API_KEY", "the-service-key")  # pragma: allowlist secret
    code = (
        "import os; from dotenv import load_dotenv; "
        f"load_dotenv({str(dotenv)!r}); "
        "print(repr(os.environ.get('SERVICE_API_KEY')))"
    )
    monkeypatch.setattr(
        demo_console,
        "command_for",
        lambda _request: ([sys.executable, "-u", "-c", code], {}),
    )

    process = demo_console.launch(RUNTIME_REQUEST)
    output, _ = process.communicate(timeout=30)

    assert process.returncode == 0
    assert output.decode().strip() == "''"


def test_the_child_is_launched_without_a_shell_and_without_the_service_key(
    monkeypatch,
) -> None:
    monkeypatch.setenv("SERVICE_API_KEY", "the-service-key")  # pragma: allowlist secret
    calls: list[tuple[object, dict[str, object]]] = []
    monkeypatch.setattr(
        demo_console.subprocess,
        "Popen",
        lambda argv, **kwargs: calls.append((argv, kwargs)),
    )

    monkeypatch.setenv("MACHINE_ID", "tower-desktop-gpu")
    monkeypatch.setenv("COMPUTE_MODE", "cpu_only")

    demo_console.launch(RUNTIME_REQUEST)

    [(argv, kwargs)] = calls
    assert isinstance(argv, list)
    assert "shell" not in kwargs
    env = kwargs["env"]
    assert isinstance(env, dict)
    # Blanked, so the CLI's own `load_dotenv()` cannot restore it either.
    assert env["SERVICE_API_KEY"] == ""
    assert not any("the-service-key" in value for value in env.values())
    assert env["ROSTER_ENTRY_ID"] == ROSTER_ENTRY_ID
    # The profile's machine and mode, never the service's inherited ones.
    assert env["MACHINE_ID"] == MACHINE
    assert env["COMPUTE_MODE"] == "gpu"
    assert env["PYTHONUNBUFFERED"] == "1"
    assert kwargs["stderr"] is subprocess.STDOUT
    if sys.platform == "win32":
        assert kwargs["creationflags"] == subprocess.CREATE_NEW_PROCESS_GROUP


# --------------------------------------------------------------------------
# A real child: streaming, exit paths, teardown
# --------------------------------------------------------------------------

RUN_ID = "0123456789abcdef0123456789abcdef"
REQUEST = RUNTIME_REQUEST


def stub(monkeypatch, code: str) -> None:
    """Make the launcher start `python -c code` in place of the real CLI."""
    monkeypatch.setattr(
        demo_console,
        "command_for",
        lambda _request: ([sys.executable, "-u", "-c", textwrap.dedent(code)], {}),
    )


def run_stub(monkeypatch, code: str) -> demo_console.ConsoleRun:
    stub(monkeypatch, code)
    demo_console.try_acquire(HOLDER)
    return demo_console.start_run(REQUEST)


def test_lines_arrive_as_the_child_writes_them_not_at_exit(monkeypatch) -> None:
    run = run_stub(
        monkeypatch,
        f"""
        import time
        print("{RUN_ID}")
        print("first")
        time.sleep(1.5)
        print("second")
        """,
    )

    arrivals: list[tuple[str, float]] = []
    for line in run.follow():
        arrivals.append((line, time.monotonic()))

    assert [line for line, _ in arrivals] == [RUN_ID, "first", "second"]
    # A buffered stream would deliver all three together at exit.
    assert arrivals[2][1] - arrivals[1][1] > 1.0
    assert run.exit_code == 0
    assert run.run_id == RUN_ID


def test_the_announced_run_id_is_recorded_on_the_holder(monkeypatch) -> None:
    run = run_stub(
        monkeypatch,
        f"""
        import time
        print("{RUN_ID}")
        time.sleep(1.0)
        """,
    )

    follow = run.follow()
    assert next(follow) == RUN_ID
    holder = demo_console.current_holder()
    assert holder is not None and holder.run_id == RUN_ID
    list(follow)


def test_a_first_line_that_is_not_a_run_id_announces_none(monkeypatch) -> None:
    run = run_stub(monkeypatch, 'print("error: SLM_MODELS_DIR is not set")')

    assert list(run.follow()) == ["error: SLM_MODELS_DIR is not set"]
    assert run.run_id is None


def test_a_crashing_child_releases_the_console_with_its_exit_status(
    monkeypatch,
) -> None:
    run = run_stub(
        monkeypatch,
        f"""
        import sys
        print("{RUN_ID}")
        print("error: disk full", file=sys.stderr)
        sys.exit(3)
        """,
    )

    lines = list(run.follow())
    run.join(timeout=5)

    assert lines == [RUN_ID, "error: disk full"]
    assert run.exit_code == 3
    assert demo_console.current_holder() is None


def test_the_console_is_released_exactly_once_per_run(monkeypatch) -> None:
    releases: list[bool] = []
    monkeypatch.setattr(demo_console, "release", lambda: releases.append(True))
    run = run_stub(monkeypatch, "raise SystemExit(0)")

    list(run.follow())
    run.join(timeout=5)

    assert releases == [True]


def test_stop_child_lets_a_graceful_child_clean_up_inside_the_grace_window(
    monkeypatch,
) -> None:
    run = run_stub(
        monkeypatch,
        """
        import time
        from wave_local_ai_v2 import server
        server.install_graceful_stop()
        try:
            print("ready")
            while True:
                time.sleep(0.1)
        finally:
            print("cleanup-ran")
        """,
    )
    follow = run.follow()
    assert next(follow) == "ready"

    started = time.monotonic()
    demo_console.stop_child(run.process)
    elapsed = time.monotonic() - started

    assert "cleanup-ran" in list(follow)
    assert elapsed < demo_console.GRACE_S / 2


def test_stop_child_kills_a_child_that_ignores_the_signal_at_the_grace_window(
    monkeypatch,
) -> None:
    monkeypatch.setattr(demo_console, "GRACE_S", 1.0)
    run = run_stub(
        monkeypatch,
        """
        import signal, sys, time
        stop = signal.SIGBREAK if sys.platform == "win32" else signal.SIGTERM
        signal.signal(stop, signal.SIG_IGN)
        print("ready")
        time.sleep(60)
        """,
    )
    follow = run.follow()
    assert next(follow) == "ready"

    started = time.monotonic()
    demo_console.stop_child(run.process)
    elapsed = time.monotonic() - started
    list(follow)

    assert 1.0 <= elapsed < 10.0
    assert run.exit_code != 0


def test_stop_child_on_an_exited_child_is_a_no_op(monkeypatch) -> None:
    run = run_stub(monkeypatch, "pass")
    list(run.follow())

    demo_console.stop_child(run.process)

    assert run.exit_code == 0


def test_a_stopped_cli_still_tears_down_its_llama_server(monkeypatch) -> None:
    # The real `running_server` teardown, with the real signal handler a CLI's
    # `main()` installs; only llama-server itself is stood in for by a sleeping
    # grandchild in its own process group, the way `start_server` spawns it.
    run = run_stub(
        monkeypatch,
        """
        import subprocess, sys, time
        from pathlib import Path
        from wave_local_ai_v2 import server

        def fake_start_server(_path, _flags, *, stderr_sink=None, engine=None):
            kwargs = {}
            if sys.platform == "win32":
                kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
            return subprocess.Popen(
                [sys.executable, "-c", "import time; time.sleep(60)"], **kwargs
            )

        server.start_server = fake_start_server
        server.install_graceful_stop()
        try:
            with server.running_server(Path("llama-server"), []) as llama:
                print("serving")
                while True:
                    time.sleep(0.1)
        except server.StopRequested:
            print(f"llama-server exit code {llama.poll()}")
            sys.exit(1)
        """,
    )
    follow = run.follow()
    assert next(follow) == "serving"

    demo_console.stop_child(run.process)
    rest = list(follow)

    [teardown] = [line for line in rest if line.startswith("llama-server exit code")]
    assert teardown != "llama-server exit code None"
    assert run.exit_code == 1


# --------------------------------------------------------------------------
# The final event
# --------------------------------------------------------------------------


def finished_run(
    monkeypatch, code: str, kind: str = "runtime"
) -> demo_console.ConsoleRun:
    stub(monkeypatch, code)
    demo_console.try_acquire(HOLDER)
    run = demo_console.start_run(
        QUALITY_REQUEST if kind == "quality" else RUNTIME_REQUEST
    )
    list(run.follow())
    return run


def test_exit_zero_carries_the_view_read_back_for_the_announced_run_id(
    monkeypatch,
) -> None:
    run = finished_run(monkeypatch, f'print("{RUN_ID}")', kind="quality")
    asked: list[tuple[str, str]] = []

    def read_back(kind: str, run_id: str) -> tuple[dict[str, object] | None, str]:
        asked.append((kind, run_id))
        return {"entries": ["the row"]}, ""

    event = demo_console.final_event(run, read_back)

    assert asked == [("quality", RUN_ID)]
    assert event == {
        "ok": True,
        "kind": "quality",
        "profile_id": QUALITY_REQUEST.profile_id,
        "run_id": RUN_ID,
        "exit_code": 0,
        "error_line": None,
        "view": {"entries": ["the row"]},
        "missing": None,
    }


def test_exit_zero_with_no_row_carries_the_routes_own_missing_detail(
    monkeypatch,
) -> None:
    run = finished_run(monkeypatch, f'print("{RUN_ID}")')

    event = demo_console.final_event(run, lambda _k, _r: (None, "no row, 404"))

    assert event["ok"] is False
    assert event["view"] is None
    assert event["missing"] == "no row, 404"


def test_exit_zero_with_no_announced_run_id_reads_nothing_back(monkeypatch) -> None:
    run = finished_run(monkeypatch, 'print("no id here")')

    def read_back(_kind: str, _run_id: str) -> tuple[None, str]:
        raise AssertionError("nothing to read back without a run_id")

    event = demo_console.final_event(run, read_back)

    assert event["ok"] is False
    assert event["missing"] == demo_console.NO_RUN_ID


def test_a_nonzero_exit_carries_the_clis_own_error_line_verbatim(
    monkeypatch,
) -> None:
    run = finished_run(
        monkeypatch,
        f"""
        import sys
        print("{RUN_ID}")
        print("error: first failure", file=sys.stderr)
        print("error: disk full", file=sys.stderr)
        sys.exit(3)
        """,
    )

    event = demo_console.final_event(run, lambda _k, _r: ({"row": 1}, ""))

    assert event["ok"] is False
    assert event["exit_code"] == 3
    assert event["error_line"] == "error: disk full"
    assert event["view"] is None


def test_a_nonzero_exit_with_no_error_line_states_the_exit_code_alone(
    monkeypatch,
) -> None:
    run = finished_run(monkeypatch, "raise SystemExit(2)")

    event = demo_console.final_event(run, lambda _k, _r: ({"row": 1}, ""))

    assert event["exit_code"] == 2
    assert event["error_line"] is None
