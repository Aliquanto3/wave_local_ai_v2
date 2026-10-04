"""The demo playground: a client types to one local roster model and watches it answer.

The playground launches llama-server for a roster entry exactly as a benchmark
run launches it -- `server.build_flags` under the service machine's declared
run profile, then `server.start_server`, on the engine's loopback address and
port -- and proxies one typed prompt at a time to the engine's chat endpoint,
streamed back as it is generated.

It shares the console's one occupancy lock (`demo_console`): llama-server has
one port and one owner, so a console run and a loaded playground model
exclude each other, each refusal naming the holder.

When the operator sets `PLAYGROUND_CLOUD_SUBJECT`, the same screen offers one
cloud subject: the release's one path on which typed text leaves the machine.
Selecting it takes the same lock; each send goes through the provider's
existing client (`mistral_client`/`google_client`) under the benchmark's
pacing and retry rules. Unset, it is absent from the options and refused, and
no local exchange ever reaches a cloud client.

Nothing is recorded. The only browser-supplied values that reach a process are
a roster id and a thinking policy, each checked against its enumerated set;
the typed text is only ever message content in a JSON body sent to the
loopback llama-server, or to the configured provider. This module logs nothing, imports no row writer and
opens no file for writing, and no timing figure is forwarded: any number on
the playground screen would read as a measurement.
"""

from __future__ import annotations

import json
import subprocess
import threading
import time
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import (
    demo_console,
    engines,
    google_client,
    local_client,
    machines,
    mistral_client,
    preflight,
    profiles,
    retry,
    roster,
    row_contract,
    server,
)
from wave_local_ai_v2.settings import PlaygroundCloudSubject, ServiceSettings

THINKING_POLICIES = tuple(sorted(row_contract.THINKING_POLICIES))
START_FIELDS = frozenset({"roster_entry_id", "cloud_subject"})
CHAT_FIELDS = frozenset({"prompt", "thinking_policy"})
# The launch preference when the service machine declares both modes: the
# GPU profile is the one a client would see in a pitch.
MODE_PREFERENCE = (machines.COMPUTE_MODE_GPU, machines.COMPUTE_MODE_CPU_ONLY)
# (connect, read) seconds: a read timeout is the gap between two streamed
# chunks, not the whole answer.
CHAT_TIMEOUT_S = (5.0, 120.0)
SSE_DATA = "data:"
SSE_DONE = "[DONE]"

# How the screen names each provider a cloud subject can be configured for.
PROVIDER_LABELS = {"mistral": "Mistral", "google": "Google"}
# Neither cloud client sends a thinking control, so a cloud exchange reports
# that none was sent rather than echoing the browser's choice back.
CLOUD_THINKING_POLICY = "not_sent"
# The quality CLI's cloud samplers (`quality_cli.CLOUD_SAMPLING`,
# `GOOGLE_SAMPLING`), restated because this module imports no row writer and
# `quality_cli` does; a test holds them equal.
MISTRAL_SAMPLING = {"temperature": 0, "random_seed": 20260821}
GOOGLE_SAMPLING = {"temperature": 0, "top_p": 1, "top_k": 1, "seed": 20260821}
# The quality CLI's backoff base for a retryable failure with no provider hint.
RETRY_BASE_DELAY_S = 1.0
# The longest one retry wait may last in the playground. A batch can afford a
# provider's minute-long `Retry-After`; a client watching the screen cannot,
# so a longer request is a refusal naming the provider instead of a hang.
PLAYGROUND_MAX_RETRY_WAIT_S = 10.0


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
class PreparedCloudChat:
    """One exchange with the cloud subject, resolved before anything is sent."""

    subject: PlaygroundCloudSubject
    prompt: str
    max_tokens: int
    pacer: retry.Pacer
    # Serialises the session's cloud sends so the pacer spaces every one.
    send_lock: threading.Lock


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


def validate_start(
    payload: object, settings: ServiceSettings
) -> str | PlaygroundCloudSubject:
    """A start request's subject: a roster id, or the configured cloud subject."""
    body = _closed_fields(payload, START_FIELDS)
    if len(body) != 1:
        raise PlaygroundRequestError(
            f"a start request names exactly one of {sorted(START_FIELDS)}"
        )
    if "cloud_subject" not in body:
        return validate_entry(body, settings)
    cloud = settings.playground_cloud
    if cloud is None:
        raise PlaygroundRequestError(
            "no cloud subject is configured on this service "
            "(PLAYGROUND_CLOUD_SUBJECT is unset)"
        )
    if body["cloud_subject"] != cloud.provider:
        raise PlaygroundRequestError(f"cloud_subject must be {cloud.provider!r}")
    return cloud


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
        self._cloud: PlaygroundCloudSubject | None = None
        self._holder: (
            demo_console.PlaygroundHolder | demo_console.CloudPlaygroundHolder | None
        ) = None
        # One pacer for the service's lifetime, not per selection: stopping and
        # reselecting the cloud subject must not reset its spacing.
        cloud = settings.playground_cloud
        self._pacer = (
            retry.Pacer(cloud.pacing_s, sleep=time.sleep) if cloud is not None else None
        )
        self._send_lock = threading.Lock()

    def loaded(self) -> dict[str, str] | None:
        """The loaded model's roster id and profile, the cloud subject, or `None`."""
        holder = self._holder
        if holder is None:
            return None
        if isinstance(holder, demo_console.CloudPlaygroundHolder):
            return {"provider": holder.provider, "model": holder.model}
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

    def start_cloud(self, subject: PlaygroundCloudSubject) -> dict[str, str]:
        """Select the configured cloud subject, stopping this session's local model.

        It takes the shared lock like a local model: refused, naming the
        holder, while a console run holds it. Nothing is sent here.
        """
        with self._lifecycle:
            self._stop_locked()
            holder = demo_console.CloudPlaygroundHolder(
                provider=subject.provider,
                model=subject.model,
                started_at=datetime.now(UTC).isoformat(),
            )
            occupied_by = demo_console.try_acquire(holder)
            if occupied_by is not None:
                raise PlaygroundBusy(
                    demo_console.busy_message(occupied_by), occupied_by
                )
            self._cloud, self._holder = subject, holder
            return {"provider": subject.provider, "model": subject.model}

    def stop(self) -> bool:
        """Stop the loaded model and free the lock; `False` when none was loaded."""
        with self._lifecycle:
            return self._stop_locked()

    def _stop_locked(self) -> bool:
        process, holder = self._process, self._holder
        self._process, self._entry, self._cloud, self._holder = None, None, None, None
        if holder is None:
            return False
        try:
            if process is not None:
                server.stop_server(process)
        finally:
            demo_console.release_if(holder)
        return True

    def prepare_chat(self, request: ChatRequest) -> PreparedChat | PreparedCloudChat:
        """The body one exchange sends, or a refusal before anything is sent."""
        cloud, holder, pacer = self._cloud, self._holder, self._pacer
        if cloud is not None and holder is not None and pacer is not None:
            occupied_by = demo_console.current_holder()
            if occupied_by is not holder:
                # Asserted per send, not assumed from the selection: no
                # playground text leaves the machine while a run holds the lock.
                raise PlaygroundBusy(
                    "the cloud subject no longer holds the console"
                    if occupied_by is None
                    else demo_console.busy_message(occupied_by),
                    occupied_by,
                )
            return PreparedCloudChat(
                subject=cloud,
                prompt=request.prompt,
                max_tokens=self._settings.playground_max_tokens,
                pacer=pacer,
                send_lock=self._send_lock,
            )
        entry = self._entry
        if entry is None:
            current = demo_console.current_holder()
            message = (
                "no playground model is loaded"
                if current is None
                else demo_console.busy_message(current)
            )
            raise PlaygroundBusy(message, current)
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


def _complete_mistral(
    prompt: str, api_key: str, max_tokens: int
) -> tuple[str, str | None]:
    completion = mistral_client.complete_prompt(
        prompt,
        api_key,
        temperature=MISTRAL_SAMPLING["temperature"],
        random_seed=MISTRAL_SAMPLING["random_seed"],
        max_tokens=max_tokens,
    )
    return completion["content"], completion["finish_reason"]


def _complete_google(
    prompt: str, api_key: str, max_tokens: int
) -> tuple[str, str | None]:
    completion = google_client.complete_prompt(
        prompt,
        api_key,
        temperature=GOOGLE_SAMPLING["temperature"],
        top_p=GOOGLE_SAMPLING["top_p"],
        top_k=GOOGLE_SAMPLING["top_k"],
        seed=GOOGLE_SAMPLING["seed"],
        max_tokens=max_tokens,
    )
    return completion["content"], completion["finish_reason"]


# provider -> (the client call, the client's retryable error)
_CLOUD_CALLS: dict[
    str, tuple[Callable[[str, str, int], tuple[str, str | None]], type[Exception]]
] = {
    "mistral": (_complete_mistral, mistral_client.RetryableRequestError),
    "google": (_complete_google, google_client.RetryableRequestError),
}


def _retry_hint_s(exc: Exception) -> float | None:
    hint = getattr(exc, "retry_after_s", None)
    return hint if isinstance(hint, int | float) else None


def _within_wait_cap(exc: Exception) -> bool:
    hint = _retry_hint_s(exc)
    return hint is None or hint <= PLAYGROUND_MAX_RETRY_WAIT_S


def _stream_cloud(prepared: PreparedCloudChat) -> Iterator[dict[str, Any]]:
    """The cloud subject's whole answer as one text event, then one final event.

    The call goes through the provider's own client, paced and retried by the
    quality CLI's rules. A failure is a refusal naming the provider, never an
    empty answer, and never quotes the client's message: it embeds the
    provider's response body.
    """
    subject = prepared.subject
    label = PROVIDER_LABELS[subject.provider]
    call, retryable = _CLOUD_CALLS[subject.provider]
    final: dict[str, Any] = {
        "thinking_policy": CLOUD_THINKING_POLICY,
        "finish_reason": None,
        "error": None,
    }
    try:
        with prepared.send_lock:
            prepared.pacer.wait()
            (content, finish_reason), _ = retry.call_with_retry(
                lambda: call(prepared.prompt, subject.api_key, prepared.max_tokens),
                is_retryable=lambda exc: (
                    isinstance(exc, retryable) and _within_wait_cap(exc)
                ),
                retry_hint_s=_retry_hint_s,
                budget=retry.RetryBudget(subject.max_retries),
                base_delay_s=RETRY_BASE_DELAY_S,
                max_delay_s=PLAYGROUND_MAX_RETRY_WAIT_S,
                sleep=time.sleep,
            )
    except retry.RetryBudgetExhausted as exc:
        status = getattr(exc.__cause__, "status_code", "an error")
        retries = subject.max_retries
        final["error"] = (
            f"refused by {label}: it answered {status} (rate limit or provider "
            f"failure) through {retries} retr{'y' if retries == 1 else 'ies'}"
        )
    except retryable as exc:
        # Only reached when the provider asked for a wait over the cap.
        final["error"] = (
            f"refused by {label}: it answered {getattr(exc, 'status_code', '')} "
            f"and asked to wait {_retry_hint_s(exc)} s, over the playground's "
            f"{PLAYGROUND_MAX_RETRY_WAIT_S} s cap"
        )
    except requests.RequestException as exc:
        final["error"] = f"{label} could not be reached ({type(exc).__name__})"
    except Exception as exc:  # noqa: BLE001 - every send ends with a final event
        # Every other failure, the client's own errors included, still ends
        # the stream with a final event, naming only the provider and class.
        final["error"] = f"refused by {label}: {type(exc).__name__}"
    else:
        final["finish_reason"] = finish_reason
        if content:
            yield {"delta": content}
        else:
            final["error"] = f"refused by {label}: it returned no text"
    yield {"final": final}


def stream_chat(
    prepared: PreparedChat | PreparedCloudChat,
) -> Iterator[dict[str, Any]]:
    """The answer's text as it is generated, then one final event.

    Only text is forwarded: llama-server's `timings` and `usage` are dropped.
    A failure ends the stream with an error naming the status or the
    transport, never the request or response body.
    """
    if isinstance(prepared, PreparedCloudChat):
        yield from _stream_cloud(prepared)
        return
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
    cloud = settings.playground_cloud
    return {
        "roster_entries": list(demo_console.roster_entry_ids(settings)),
        # Absent unless the operator configured one; never the key.
        "cloud_subject": None
        if cloud is None
        else {
            "provider": cloud.provider,
            "label": PROVIDER_LABELS[cloud.provider],
            "model": cloud.model,
        },
        "thinking_policies": list(THINKING_POLICIES),
        "max_prompt_chars": settings.playground_max_prompt_chars,
        "max_tokens": settings.playground_max_tokens,
        "loaded": session.loaded(),
        "holder": None if holder is None else demo_console.holder_payload(holder),
    }
