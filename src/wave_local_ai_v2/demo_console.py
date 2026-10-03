"""The demo run console: declared choices, one run at a time, streamed output.

Everything a browser may pick is drawn from a set this module reads from the
CLIs' own sources of truth -- the suite registry `--suite` resolves against,
the roster file, the machine registry and the run profile registry --
imported, never copied, so the console cannot offer a choice the CLI itself
would not recognise.

A run executes on the machine the service runs on, named by the service's own
`MACHINE_ID`: only that machine's declared profiles are offered, and a request
naming another machine is refused, since its row would claim hardware it never
ran on. Whether a declared profile can actually run here (a value nobody has
declared yet, `gpu` on a GPU-less machine, a campaign it falls outside of) is
the CLI's own check, streamed as-is: the console adds no second one.

A run is the unchanged CLI, launched as a child process from constants plus
validated identifiers, never a shell and never a free-form string. The console
writes nothing itself: the row a run produces is the one the CLI appends.
"""

from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import threading
import uuid
from collections.abc import Callable, Iterator
from dataclasses import asdict, dataclass, replace
from typing import Any

from wave_local_ai_v2 import machines, profiles, roster, suite_registry
from wave_local_ai_v2.settings import ServiceSettings

KIND_RUNTIME = "runtime"
KIND_QUALITY = "quality"
KINDS = (KIND_RUNTIME, KIND_QUALITY)


class ConsoleRequestError(ValueError):
    """A console request naming a field or value outside the declared sets."""


def suite_ids() -> tuple[str, ...]:
    """The quality CLI's own `--suite` choices, read from the suite registry."""
    return tuple(suite_registry.registered_ids())


def roster_entry_ids(settings: ServiceSettings) -> tuple[str, ...]:
    """The roster entries the CLIs resolve `ROSTER_ENTRY_ID` against."""
    return tuple(roster.load_roster(settings.roster_path).entries)


def service_machine(settings: ServiceSettings) -> str:
    """The declared machine this service runs on, or `ConsoleRequestError`.

    Raises `machines.MachineRegistryError` when the registry is unreadable.
    """
    registry = machines.load_registry(settings.machine_registry_path)
    declared = ", ".join(sorted(registry.entries))
    if settings.machine_id is None:
        raise ConsoleRequestError(
            "MACHINE_ID is not set on the service: a console run executes on "
            f"this machine and must name it (declared: {declared})"
        )
    if settings.machine_id not in registry.entries:
        raise ConsoleRequestError(
            f"MACHINE_ID={settings.machine_id!r} on the service is not a "
            f"declared machine (declared: {declared})"
        )
    return settings.machine_id


def machine_profiles(entry_id: str, machine_id: str) -> list[dict[str, str]]:
    """The declared profiles of `entry_id` on `machine_id`, sorted by id."""
    registry = profiles.tracked_registry()
    return [
        {
            "profile_id": profiles.profile_id_for(entry_id, machine, mode),
            "machine_id": machine,
            "compute_mode": mode,
        }
        for machine, mode in sorted(registry.defaults)
        if machine == machine_id
    ]


@dataclass(frozen=True)
class RunHolder:
    """Who holds the console: the choices of the one run in flight."""

    kind: str
    suite: str | None
    roster_entry_id: str
    profile_id: str
    started_at: str
    # Unknown until the child announces it on its first stdout line.
    run_id: str | None = None


# The holder, not the guard's own `locked()` state, is the source of truth: a
# second request must be able to read *who* holds the console without racing
# the first, so the guard only ever protects reads and writes of `_holder`.
_guard = threading.Lock()
_holder: RunHolder | None = None


def current_holder() -> RunHolder | None:
    """The run in flight, or `None` when the console is free."""
    with _guard:
        return _holder


def try_acquire(holder: RunHolder) -> RunHolder | None:
    """Install `holder` and return `None`, or return the current holder unchanged.

    No queueing: a refused caller is told who holds the console and tries again
    later.
    """
    global _holder
    with _guard:
        if _holder is not None:
            return _holder
        _holder = holder
        return None


def record_run_id(run_id: str) -> None:
    """Attach the announced `run_id` to the current holder, if one is held."""
    global _holder
    with _guard:
        if _holder is not None:
            _holder = replace(_holder, run_id=run_id)


def release() -> None:
    """Free the console."""
    global _holder
    with _guard:
        _holder = None


def options_payload(
    settings: ServiceSettings, holder: RunHolder | None
) -> dict[str, Any]:
    """Every declared set the console offers, plus who holds it right now.

    With no usable service machine, every entry offers no profile and
    `machine_absence` names why, rather than the field being `null`.
    """
    entries = roster_entry_ids(settings)
    machine_id: str | None
    try:
        machine_id = service_machine(settings)
        absence = None
    except ConsoleRequestError as exc:
        machine_id, absence = None, str(exc)
    return {
        "kinds": list(KINDS),
        "suites": list(suite_ids()),
        "roster_entries": list(entries),
        "machine_id": machine_id,
        "machine_absence": absence,
        "profiles": {
            entry: [] if machine_id is None else machine_profiles(entry, machine_id)
            for entry in entries
        },
        "holder": None if holder is None else asdict(holder),
    }


# --------------------------------------------------------------------------
# Request validation
# --------------------------------------------------------------------------

REQUEST_FIELDS = frozenset(
    {"kind", "suite", "roster_entry_id", "machine_id", "compute_mode"}
)
# An allow-list, not an enumeration of shell metacharacters: letters, digits,
# dot, underscore, hyphen, and never a leading `-` or `.` (a flag, a relative
# path). Every value must also be a member of its declared set; this is the
# defence that still holds if a declared set ever carried a bad value.
_IDENTIFIER = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*")


@dataclass(frozen=True)
class ConsoleRequest:
    """A validated console request: every value drawn from its declared set."""

    kind: str
    suite: str | None
    roster_entry_id: str
    machine_id: str
    compute_mode: str

    @property
    def profile_id(self) -> str:
        return profiles.profile_id_for(
            self.roster_entry_id, self.machine_id, self.compute_mode
        )


def _identifier(payload: dict[str, Any], field: str) -> str:
    value = payload.get(field)
    if not isinstance(value, str) or not _IDENTIFIER.fullmatch(value):
        raise ConsoleRequestError(
            f"{field} must be an identifier from its declared set, got {value!r}"
        )
    return value


def validate_request(payload: object, settings: ServiceSettings) -> ConsoleRequest:
    """Check every field against its declared set, before anything runs.

    Raises `ConsoleRequestError` on an unknown or missing field, a value
    outside its set, a `suite` on a runtime request, or a profile of another
    machine; `roster.RosterError` (profile errors included) or
    `machines.MachineRegistryError` when a registry cannot be read.
    """
    if not isinstance(payload, dict):
        raise ConsoleRequestError("the request body must be a JSON object")
    unknown = set(payload) - REQUEST_FIELDS
    if unknown:
        raise ConsoleRequestError(f"unknown field(s): {', '.join(sorted(unknown))}")

    kind = _identifier(payload, "kind")
    if kind not in KINDS:
        raise ConsoleRequestError(f"kind must be one of {', '.join(KINDS)}")

    suite: str | None = None
    if kind == KIND_QUALITY:
        suite = _identifier(payload, "suite")
        if suite not in suite_ids():
            raise ConsoleRequestError(f"suite must be one of {', '.join(suite_ids())}")
    elif payload.get("suite") is not None:
        raise ConsoleRequestError("a runtime run takes no suite")

    # Both CLIs resolve their model from `ROSTER_ENTRY_ID` -- the quality
    # CLI's local batch included -- so both kinds name one.
    roster_entry_id = _identifier(payload, "roster_entry_id")
    if roster_entry_id not in roster_entry_ids(settings):
        raise ConsoleRequestError(
            f"roster_entry_id {roster_entry_id!r} is not in the roster"
        )

    machine_id = _identifier(payload, "machine_id")
    compute_mode = _identifier(payload, "compute_mode")
    here = service_machine(settings)
    if machine_id != here:
        raise ConsoleRequestError(
            f"machine_id {machine_id!r} is not this machine ({here!r}): a "
            "console run executes here and is never recorded under another "
            "machine's profile"
        )
    offered = {p["compute_mode"]: p for p in machine_profiles(roster_entry_id, here)}
    if compute_mode not in offered:
        declared = ", ".join(p["profile_id"] for p in offered.values()) or "none"
        raise ConsoleRequestError(
            f"no run profile is declared for ({roster_entry_id!r}, {here!r}, "
            f"{compute_mode!r}); declared here: {declared}"
        )
    return ConsoleRequest(
        kind=kind,
        suite=suite,
        roster_entry_id=roster_entry_id,
        machine_id=machine_id,
        compute_mode=compute_mode,
    )


# --------------------------------------------------------------------------
# Launch, stop, read
# --------------------------------------------------------------------------

# How long a stopped child gets to unwind before it is killed. The CLI's
# graceful-stop signal only takes effect once its current blocking call
# returns, and the longest one it makes on purpose is the inter-repetition
# cooldown (`Settings.runtime_cooldown_s`, default 10s); after that its own
# `running_server` teardown may wait `server.SHUTDOWN_GRACE_S` (5s) on
# llama-server. 10 + 5 + 10s margin: a window sized to `SHUTDOWN_GRACE_S`
# alone would routinely race the cooldown and escalate to a kill that
# orphans llama-server, the very thing the graceful path exists to prevent.
GRACE_S = 25.0

# The announced `run_id`: `results.new_run_id`'s `uuid4().hex`.
RUN_ID_PATTERN = re.compile(r"[0-9a-f]{32}")

_RUNTIME_MODULE = "wave_local_ai_v2"
_QUALITY_MODULE = "wave_local_ai_v2.quality_cli"


def command_for(request: ConsoleRequest) -> tuple[list[str], dict[str, str]]:
    """The argv and the env additions for `request`: constants plus its ids.

    The runtime CLI takes no arguments; the quality CLI takes `--suite` and
    runs its default prompt variant. Both read the roster entry and the run
    profile's machine and mode from the environment, set here from the
    validated request only.
    """
    env = {
        "ROSTER_ENTRY_ID": request.roster_entry_id,
        "MACHINE_ID": request.machine_id,
        "COMPUTE_MODE": request.compute_mode,
    }
    if request.kind == KIND_RUNTIME:
        return [sys.executable, "-u", "-m", _RUNTIME_MODULE], env
    assert request.suite is not None
    argv = [sys.executable, "-u", "-m", _QUALITY_MODULE]
    return [*argv, "--suite", request.suite], env


def child_env(additions: dict[str, str]) -> dict[str, str]:
    """The service's environment, unbuffered, without the service's API key.

    The key is blanked, not merely removed: every CLI calls `load_dotenv()`,
    which fills only variables absent from the environment, so a removed key
    would come back from a `.env` holding it.
    """
    return {
        **os.environ,
        "PYTHONUNBUFFERED": "1",
        "PYTHONIOENCODING": "utf-8",
        **additions,
        "SERVICE_API_KEY": "",
    }


def launch(request: ConsoleRequest) -> subprocess.Popen[bytes]:
    """Start the CLI for `request`: no shell, merged output, own process group.

    Its own group so the graceful-stop signal reaches the child alone:
    `CTRL_BREAK_EVENT` is delivered to a whole group, and a child sharing the
    service's would take the service down with it.
    """
    argv, additions = command_for(request)
    popen_kwargs: dict[str, object] = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "env": child_env(additions),
    }
    if sys.platform == "win32":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    process: subprocess.Popen[bytes] = subprocess.Popen(argv, **popen_kwargs)  # type: ignore[call-overload]
    return process


def stop_child(process: subprocess.Popen[bytes]) -> None:
    """Ask the child to stop, killing it if it has not exited within `GRACE_S`.

    The same shape as `server.stop_server`, against the console child and its
    own grace window.
    """
    if process.poll() is not None:
        return
    if sys.platform == "win32":
        process.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
    else:
        process.send_signal(signal.SIGTERM)
    try:
        process.wait(timeout=GRACE_S)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def iter_lines(process: subprocess.Popen[bytes]) -> Iterator[str]:
    """The child's merged stdout/stderr, one line at a time as it is written."""
    assert process.stdout is not None
    for raw in process.stdout:
        yield raw.decode("utf-8", errors="replace").rstrip("\r\n")


class ConsoleRun:
    """One launched child, its output so far, and its exit code once known.

    A pump thread drains the child's output whether or not a browser is
    reading it: a reader that disconnects must not leave the child blocked on
    a full pipe with the console held forever. The pump releases the console
    exactly once, when the child exits, on every exit path.
    """

    def __init__(
        self, request: ConsoleRequest, process: subprocess.Popen[bytes]
    ) -> None:
        self.launch_id = uuid.uuid4().hex
        self.request = request
        self.process = process
        self.run_id: str | None = None
        self.lines: list[str] = []
        self.exit_code: int | None = None
        self._changed = threading.Condition()
        self._pump_thread = threading.Thread(target=self._pump, daemon=True)

    def start(self) -> ConsoleRun:
        self._pump_thread.start()
        return self

    def join(self, timeout: float | None = None) -> None:
        self._pump_thread.join(timeout)

    def _pump(self) -> None:
        try:
            for line in iter_lines(self.process):
                # The CLI's first line is its run_id; an early refusal (a
                # settings or profile error before the id is minted)
                # announces none.
                if not self.lines and RUN_ID_PATTERN.fullmatch(line):
                    self.run_id = line
                    record_run_id(line)
                with self._changed:
                    self.lines.append(line)
                    self._changed.notify_all()
        finally:
            exit_code = self.process.wait()
            with self._changed:
                self.exit_code = exit_code
                self._changed.notify_all()
            release()

    def follow(self) -> Iterator[str]:
        """Every line from the first, then each new one as it arrives, until exit."""
        sent = 0
        while True:
            with self._changed:
                while len(self.lines) == sent and self.exit_code is None:
                    self._changed.wait()
                pending = self.lines[sent:]
                finished = self.exit_code is not None
            yield from pending
            sent += len(pending)
            if finished and sent == len(self.lines):
                return


ERROR_PREFIX = "error:"
# The final event when a run exits 0 without having announced a run_id.
NO_RUN_ID = "the run exited 0 without announcing a run_id"
# Reads back one run's view: `(view, "")`, or `(None, the route's 404 detail)`.
ReadBack = Callable[[str, str], tuple[dict[str, Any] | None, str]]


def final_event(run: ConsoleRun, read_back: ReadBack) -> dict[str, Any]:
    """What the child did, stated plainly: its row as read back, or its error.

    Never a row this module built: on exit 0 the row is whatever `read_back`
    -- the service's own per-kind read route -- finds for the announced
    `run_id`. On a nonzero exit, the CLI's own last `error:` line (both CLIs
    print one per failure), or none when it printed none, never a guess.
    """
    event: dict[str, Any] = {
        "ok": False,
        "kind": run.request.kind,
        "profile_id": run.request.profile_id,
        "run_id": run.run_id,
        "exit_code": run.exit_code,
        "error_line": None,
        "view": None,
        "missing": None,
    }
    if run.exit_code != 0:
        errors = [line for line in run.lines if line.startswith(ERROR_PREFIX)]
        event["error_line"] = errors[-1] if errors else None
        return event
    if run.run_id is None:
        event["missing"] = NO_RUN_ID
        return event
    view, missing = read_back(run.request.kind, run.run_id)
    if view is None:
        event["missing"] = missing
        return event
    event["ok"] = True
    event["view"] = view
    return event


def start_run(request: ConsoleRequest) -> ConsoleRun:
    """Launch `request`'s CLI and start draining its output."""
    return ConsoleRun(request, launch(request)).start()
