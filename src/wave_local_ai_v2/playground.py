"""The demo playground: a client types to one local roster model and watches it answer.

The playground launches llama-server for a roster entry exactly as a benchmark
run launches it -- `server.build_flags` under the service machine's declared
run profile, then `server.start_server`, on the engine's loopback address and
port -- and proxies one typed prompt at a time to the engine's chat endpoint,
streamed back as it is generated.

It shares the console's one occupancy lock (`demo_console`): llama-server has
one port and one owner, so a console run and a loaded playground model
exclude each other, each refusal naming the holder.

Nothing is recorded. The only browser-supplied values that reach a process are
a roster id and a thinking policy, each checked against its enumerated set;
the typed text is only ever message content in a JSON body sent to the
loopback llama-server. This module logs nothing, imports no row writer and
opens no file for writing, and no timing figure is forwarded: any number on
the playground screen would read as a measurement.
"""

from __future__ import annotations

import json
import subprocess
import threading
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import (
    demo_console,
    engines,
    local_client,
    machines,
    preflight,
    profiles,
    roster,
    row_contract,
    server,
)
from wave_local_ai_v2.settings import ServiceSettings

THINKING_POLICIES = tuple(sorted(row_contract.THINKING_POLICIES))
START_FIELDS = frozenset({"roster_entry_id"})
CHAT_FIELDS = frozenset({"prompt", "thinking_policy"})
# The launch preference when the service machine declares both modes: the
# GPU profile is the one a client would see in a pitch.
MODE_PREFERENCE = (machines.COMPUTE_MODE_GPU, machines.COMPUTE_MODE_CPU_ONLY)
# (connect, read) seconds: a read timeout is the gap between two streamed
# chunks, not the whole answer.
CHAT_TIMEOUT_S = (5.0, 120.0)
SSE_DATA = "data:"
SSE_DONE = "[DONE]"


class PlaygroundRequestError(ValueError):
    """A playground request naming a field or value outside the declared sets."""


class PlaygroundUnavailable(RuntimeError):
    """The playground cannot run on this service: an install or machine is missing."""


class PlaygroundBusy(RuntimeError):
    """The lock is held by someone else, or no model is loaded for a chat."""

    def __init__(self, message: str, holder: demo_console.Holder | None) -> None:
        super().__init__(message)
        self.holder = holder


@dataclass(frozen=True)
class ChatRequest:
    """A validated exchange: the typed text and a declared thinking policy."""

    prompt: str
    thinking_policy: str


@dataclass(frozen=True)
class PreparedChat:
    """Everything one exchange sends, resolved before any byte is streamed."""

    url: str
    body: dict[str, Any]
    thinking_policy: str


def _closed_fields(payload: object, fields: frozenset[str]) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise PlaygroundRequestError("the request body must be a JSON object")
    unknown = sorted(set(payload) - fields)
    if unknown:
        raise PlaygroundRequestError(
            f"unknown field(s) {unknown}: a playground request carries only "
            f"{sorted(fields)}"
        )
    return payload


def validate_entry(payload: object, settings: ServiceSettings) -> str:
    """The roster id a start request names, checked against the roster's ids."""
    body = _closed_fields(payload, START_FIELDS)
    entry_id = body.get("roster_entry_id")
    entries = demo_console.roster_entry_ids(settings)
    if (
        not isinstance(entry_id, str)
        or not demo_console._IDENTIFIER.fullmatch(entry_id)
        or entry_id not in entries
    ):
        raise PlaygroundRequestError(
            f"roster_entry_id must be one of {sorted(entries)}"
        )
    return entry_id


def validate_chat(payload: object, settings: ServiceSettings) -> ChatRequest:
    """The typed text and thinking policy, within the cap and the declared pair."""
    body = _closed_fields(payload, CHAT_FIELDS)
    policy = body.get("thinking_policy")
    if not isinstance(policy, str) or policy not in THINKING_POLICIES:
        raise PlaygroundRequestError(
            f"thinking_policy must be one of {list(THINKING_POLICIES)}"
        )
    prompt = body.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        raise PlaygroundRequestError("prompt must be a non-empty string")
    cap = settings.playground_max_prompt_chars
    if len(prompt) > cap:
        raise PlaygroundRequestError(
            f"prompt is {len(prompt)} characters, over the "
            f"PLAYGROUND_MAX_PROMPT_CHARS cap of {cap}"
        )
    return ChatRequest(prompt=prompt, thinking_policy=policy)


def launch_profile(
    entry: roster.RosterEntry, machine_id: str
) -> profiles.ResolvedProfile:
    """The service machine's declared profile of `entry`, GPU first."""
    declared = {
        mode
        for machine, mode in profiles.tracked_registry().defaults
        if machine == machine_id
    }
    for mode in MODE_PREFERENCE:
        if mode in declared:
            return profiles.resolve_for_run(
                entry, machine_id, mode, operator_n_cpu_moe=None, operator_threads=None
            )
    raise PlaygroundUnavailable(
        f"machine {machine_id!r} declares no run profile: nothing to launch under"
    )


def check_minimums(
    settings: ServiceSettings,
    entry: roster.RosterEntry,
    profile: profiles.ResolvedProfile,
    models_dir: Path,
) -> None:
    """Refuse a model below the entry's declared minimums, recording nothing.

    The same observation and comparison the benchmark pre-flight makes
    (`preflight.observe`, `preflight.first_failure`), without its refusal
    record: the playground writes nothing. `preflight.PreflightError` (a
    declared minimum nothing observed) propagates as the roster error it is.
    """
    machine = machines.load_registry(settings.machine_registry_path).entries[
        profile.machine_id
    ]
    observation = preflight.observe(machine, profile.compute_mode, models_dir, entry)
    failure = preflight.first_failure(entry, profile.compute_mode, observation)
    if failure is not None:
        requirement, declared, observed = failure
        raise PlaygroundUnavailable(
            f"roster entry {entry.entry_id!r} under {profile.profile_id} requires "
            f"{requirement} >= {declared} GB; this machine reports {observed} GB. "
            "Nothing was started."
        )


def _install(settings: ServiceSettings) -> tuple[Path, Path]:
    """The llama-server binary and models directory, or `PlaygroundUnavailable`."""
    server_path, models_dir = settings.llama_server_path, settings.slm_models_dir
    if server_path is None or not server_path.is_file():
        raise PlaygroundUnavailable(
            "LLAMA_SERVER_PATH is not set to an existing llama-server on the service"
        )
    if models_dir is None or not models_dir.is_dir():
        raise PlaygroundUnavailable(
            "SLM_MODELS_DIR is not set to an existing directory on the service"
        )
    return server_path, models_dir


class PlaygroundSession:
    """The one playground model this service holds, if any.

    `_lifecycle` serialises start, switch and stop; the occupancy lock itself
    lives in `demo_console`, shared with the console run.
    """

    def __init__(self, settings: ServiceSettings) -> None:
        self._settings = settings
        self._lifecycle = threading.Lock()
        self._process: subprocess.Popen[bytes] | None = None
        self._entry: roster.RosterEntry | None = None
        self._holder: demo_console.PlaygroundHolder | None = None

    def loaded(self) -> dict[str, str] | None:
        """The loaded model's roster id and profile, or `None`."""
        holder = self._holder
        if holder is None:
            return None
        return {
            "roster_entry_id": holder.roster_entry_id,
            "profile_id": holder.profile_id,
        }

    def start(self, entry_id: str) -> dict[str, str]:
        """Load `entry_id`, replacing this session's own model on a switch.

        Every check runs before the current model is stopped, so a refused
        request leaves a loaded model in place. Raises `PlaygroundBusy` naming
        the holder when a console run holds the lock.
        """
        with self._lifecycle:
            entry = roster.load_roster(self._settings.roster_path).entries[entry_id]
            try:
                machine_id = demo_console.service_machine(self._settings)
            except demo_console.ConsoleRequestError as exc:
                raise PlaygroundUnavailable(str(exc)) from exc
            server_path, models_dir = _install(self._settings)
            model_path = models_dir / entry.file
            if not model_path.is_file():
                raise PlaygroundUnavailable(
                    f"model file for {entry_id!r} is not in SLM_MODELS_DIR"
                )
            profile = launch_profile(entry, machine_id)
            check_minimums(self._settings, entry, profile, models_dir)
            flags = server.build_flags(entry, profile, model_path)

            self._stop_locked()
            holder = demo_console.PlaygroundHolder(
                roster_entry_id=entry_id,
                profile_id=profile.profile_id,
                started_at=datetime.now(UTC).isoformat(),
            )
            occupied_by = demo_console.try_acquire(holder)
            if occupied_by is not None:
                raise PlaygroundBusy(
                    demo_console.busy_message(occupied_by), occupied_by
                )
            try:
                process = server.start_server(server_path, flags)
            except (server.ServerStartupError, OSError) as exc:
                demo_console.release_if(holder)
                raise PlaygroundUnavailable(
                    f"llama-server could not be started for {entry_id!r}: {exc}"
                ) from exc
            except BaseException:
                # Any other failure (a stop signal during the readiness wait,
                # an unexpected error) must not leave the console held until
                # the service restarts.
                demo_console.release_if(holder)
                raise
            self._process, self._entry, self._holder = process, entry, holder
            return {"roster_entry_id": entry_id, "profile_id": profile.profile_id}

    def stop(self) -> bool:
        """Stop the loaded model and free the lock; `False` when none was loaded."""
        with self._lifecycle:
            return self._stop_locked()

    def _stop_locked(self) -> bool:
        process, holder = self._process, self._holder
        self._process, self._entry, self._holder = None, None, None
        if process is None or holder is None:
            return False
        try:
            server.stop_server(process)
        finally:
            demo_console.release_if(holder)
        return True

    def prepare_chat(self, request: ChatRequest) -> PreparedChat:
        """The body one exchange sends, or a refusal before anything is sent."""
        entry = self._entry
        if entry is None:
            holder = demo_console.current_holder()
            message = (
                "no playground model is loaded"
                if holder is None
                else demo_console.busy_message(holder)
            )
            raise PlaygroundBusy(message, holder)
        engine = engines.tracked_reference_engine()
        try:
            thinking = local_client.thinking_kwargs(
                request.thinking_policy, entry, engine
            )
        except local_client.LocalRequestError as exc:
            raise PlaygroundRequestError(str(exc)) from exc
        return PreparedChat(
            url=f"{engines.base_url(engine)}{engine.endpoints['chat']}",
            body={
                # The typed text's one destination: message content.
                "messages": [{"role": "user", "content": request.prompt}],
                "stream": True,
                "max_tokens": self._settings.playground_max_tokens,
                **thinking,
            },
            thinking_policy=request.thinking_policy,
        )


def _chunk_events(data: str) -> tuple[list[dict[str, str]], str | None]:
    """The text events one SSE `data:` payload carries, and its finish reason."""
    chunk = json.loads(data)
    choices = chunk.get("choices") or [{}]
    delta = choices[0].get("delta") or {}
    events = [
        {key: delta[field]}
        for field, key in (("reasoning_content", "reasoning"), ("content", "delta"))
        if isinstance(delta.get(field), str) and delta[field]
    ]
    return events, choices[0].get("finish_reason")


def stream_chat(
    prepared: PreparedChat,
) -> Iterator[dict[str, Any]]:
    """The answer's text as it is generated, then one final event.

    Only text is forwarded: llama-server's `timings` and `usage` are dropped.
    A failure ends the stream with an error naming the status or the
    transport, never the request or response body.
    """
    final: dict[str, Any] = {
        "thinking_policy": prepared.thinking_policy,
        "finish_reason": None,
        "error": None,
    }
    try:
        with requests.post(
            prepared.url, json=prepared.body, stream=True, timeout=CHAT_TIMEOUT_S
        ) as response:
            if response.status_code != 200:
                final["error"] = f"llama-server answered {response.status_code}"
            else:
                for raw in response.iter_lines():
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line.startswith(SSE_DATA):
                        continue
                    data = line[len(SSE_DATA) :].strip()
                    if data == SSE_DONE:
                        break
                    events, finish_reason = _chunk_events(data)
                    yield from events
                    if finish_reason is not None:
                        final["finish_reason"] = finish_reason
    except (requests.RequestException, ValueError) as exc:
        final["error"] = f"the local model stopped answering ({type(exc).__name__})"
    yield {"final": final}


def options_payload(
    settings: ServiceSettings, session: PlaygroundSession
) -> dict[str, Any]:
    """The declared choices, the caps, the loaded model and who holds the lock."""
    holder = demo_console.current_holder()
    return {
        "roster_entries": list(demo_console.roster_entry_ids(settings)),
        "thinking_policies": list(THINKING_POLICIES),
        "max_prompt_chars": settings.playground_max_prompt_chars,
        "max_tokens": settings.playground_max_tokens,
        "loaded": session.loaded(),
        "holder": None if holder is None else demo_console.holder_payload(holder),
    }
