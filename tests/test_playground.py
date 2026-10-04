"""The demo playground: gates, the shared lock, the model lifecycle, the proxy.

No test starts a real llama-server or opens a socket to one: `start_server`,
`stop_server` and the chat HTTP call are stubbed at the module boundary.
"""

from __future__ import annotations

import json
import logging
from dataclasses import replace
from pathlib import Path
from typing import Any, Self

import pytest
import requests
from starlette.testclient import TestClient

import wave_local_ai_v2.settings as settings_module
from wave_local_ai_v2 import (
    demo_console,
    google_client,
    mistral_client,
    playground,
    preflight,
    roster,
    server,
    service,
)
from wave_local_ai_v2.settings import PlaygroundCloudSubject, ServiceSettings

API_KEY = "a-playground-key"  # pragma: allowlist secret
KEYED = {"X-API-Key": API_KEY}
LOOPBACK = ("127.0.0.1", 12345)
TRACKED_ROSTER = Path("aidd_docs/roster/models.json")
TRACKED_MACHINES = Path("aidd_docs/roster/machines.json")
MACHINE = "laptop-mobile-gpu"
ENTRY = "qwen3-0.6b-q8"
OTHER_ENTRY = "qwen3-1.7b-q8"
OPTIONS = "/api/playground/options"
SESSION = "/api/playground/session"
CHAT = "/api/playground/chat"
CONSOLE_RUNS = "/api/console/runs"
PROMPT = "zebra-violet-4419 tell me about tides"
RUN_HOLDER = demo_console.RunHolder(
    kind="runtime",
    suite=None,
    roster_entry_id=ENTRY,
    profile_id=f"{ENTRY}@{MACHINE}/gpu",
    started_at="2026-10-02T22:00:00+00:00",
)


class FakeProcess:
    """Stands in for the llama-server `Popen` `server.start_server` returns."""

    def __init__(self, flags: list[str]) -> None:
        self.flags = flags


@pytest.fixture
def install(tmp_path: Path) -> tuple[Path, Path]:
    """A llama-server binary and a models dir holding every tracked roster file."""
    server_path = tmp_path / "llama" / "llama-server.exe"
    server_path.parent.mkdir()
    server_path.write_bytes(b"")
    models = tmp_path / "models"
    for entry_id in (ENTRY, OTHER_ENTRY):
        model = models / roster.load_roster(TRACKED_ROSTER).entries[entry_id].file
        model.parent.mkdir(parents=True, exist_ok=True)
        model.write_bytes(b"gguf")
    return server_path, models


@pytest.fixture
def settings(bundle: dict[str, Path], install: tuple[Path, Path]) -> ServiceSettings:
    server_path, models = install
    return ServiceSettings(
        api_key=API_KEY,
        host="127.0.0.1",
        port=8000,
        schema_floor="7",
        runtime_results_path=bundle["runtime"],
        quality_results_path=bundle["quality"],
        fiche_registry_dir=bundle["fiches"],
        roster_path=TRACKED_ROSTER,
        suite_definitions_dir=bundle["suites"],
        leader_sets_dir=bundle["leader_sets"],
        dashboard_bundle_dir=bundle["fiches"],
        dashboard_origin="https://127.0.0.1:8000",
        tls_certfile=bundle["fiches"],
        tls_keyfile=bundle["fiches"],
        machine_registry_path=TRACKED_MACHINES,
        demo_mode=True,
        machine_id=MACHINE,
        llama_server_path=server_path,
        slm_models_dir=models,
        playground_max_prompt_chars=200,
        playground_max_tokens=64,
    )


@pytest.fixture(autouse=True)
def ample_machine(monkeypatch) -> list[str]:  # type: ignore[no-untyped-def]
    """A machine above every declared minimum, read without touching the host."""
    observed: list[str] = []

    def observe(machine: Any, mode: str, models_dir: Path, entry: Any) -> Any:
        observed.append(entry.entry_id)
        return preflight.Observation(ram_gb=64.0, vram_gb=None, disk_free_gb=None)

    monkeypatch.setattr(preflight, "observe", observe)
    return observed


@pytest.fixture
def servers(monkeypatch) -> dict[str, list[Any]]:  # type: ignore[no-untyped-def]
    """Record every llama-server start and stop instead of spawning one."""
    calls: dict[str, list[Any]] = {"started": [], "stopped": []}

    def start(server_path: Path, flags: list[str]) -> FakeProcess:
        process = FakeProcess(flags)
        calls["started"].append(process)
        return process

    monkeypatch.setattr(server, "start_server", start)
    monkeypatch.setattr(server, "stop_server", calls["stopped"].append)
    return calls


def client_for(settings: ServiceSettings) -> TestClient:
    return TestClient(service.create_app(settings), client=LOOPBACK)


@pytest.fixture
def client(settings: ServiceSettings, servers: dict[str, list[Any]]):  # type: ignore[no-untyped-def]
    demo_console.release()
    with client_for(settings) as test_client:
        yield test_client
    demo_console.release()


# --------------------------------------------------------------------------
# Gates
# --------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", OPTIONS), ("post", SESSION), ("delete", SESSION), ("post", CHAT)],
)
def test_every_playground_route_refuses_a_keyless_loopback_client(
    client: TestClient, servers: dict[str, list[Any]], method: str, path: str
) -> None:
    response = client.request(method, path, json={"roster_entry_id": ENTRY})

    assert response.status_code == 401
    assert servers["started"] == []


def test_the_playground_is_refused_with_demo_mode_off(
    settings: ServiceSettings, servers: dict[str, list[Any]]
) -> None:
    with client_for(replace(settings, demo_mode=False)) as off:
        response = off.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert response.status_code == 403
    assert "SERVICE_DEMO_MODE" in response.json()["detail"]
    assert servers["started"] == []


@pytest.mark.parametrize(
    "body",
    [
        {"roster_entry_id": "not-a-roster-model"},
        {"roster_entry_id": "--model"},
        {"roster_entry_id": 3},
        {"roster_entry_id": ENTRY, "flags": "-ngl 99"},
        ["not", "an", "object"],
    ],
)
def test_a_start_outside_the_roster_ids_is_refused_with_no_process(
    client: TestClient, servers: dict[str, list[Any]], body: object
) -> None:
    response = client.post(SESSION, json=body, headers=KEYED)

    assert response.status_code == 422
    assert servers["started"] == []
    assert demo_console.current_holder() is None


def test_the_options_name_the_declared_sets_and_the_caps(client: TestClient) -> None:
    body = client.get(OPTIONS, headers=KEYED).json()

    assert body["roster_entries"] == [
        "qwen3.6-35b-a3b-ud-iq4xs",
        ENTRY,
        OTHER_ENTRY,
        "qwen3-4b-q4km",
        "granite-4.0-h-350m-q8",
        "lfm2.5-1.2b-instruct-q8",
        "granite-3.1-1b-a400m-instruct-q8",
        "granite-3.1-3b-a800m-instruct-q4km",
    ]
    assert body["thinking_policies"] == ["allowed", "disabled"]
    assert body["max_prompt_chars"] == 200
    assert body["max_tokens"] == 64
    assert body["loaded"] is None
    assert body["holder"] is None


# --------------------------------------------------------------------------
# Lifecycle and the shared lock
# --------------------------------------------------------------------------


def test_a_start_launches_the_benchmark_flags_and_holds_the_lock(
    client: TestClient, servers: dict[str, list[Any]], settings: ServiceSettings
) -> None:
    response = client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert response.status_code == 200
    assert response.json() == {
        "roster_entry_id": ENTRY,
        "profile_id": f"{ENTRY}@{MACHINE}/gpu",
    }
    [process] = servers["started"]
    entry = roster.load_roster(TRACKED_ROSTER).entries[ENTRY]
    profile = playground.launch_profile(entry, MACHINE)
    assert settings.slm_models_dir is not None
    # The very flags a benchmark run builds, loopback host and fixed port included.
    assert process.flags == server.build_flags(
        entry, profile, settings.slm_models_dir / entry.file
    )
    assert process.flags[process.flags.index("--host") + 1] == "127.0.0.1"
    holder = demo_console.current_holder()
    assert isinstance(holder, demo_console.PlaygroundHolder)
    assert client.get(OPTIONS, headers=KEYED).json()["holder"]["session"] == (
        "playground"
    )


def test_a_run_is_refused_naming_the_playground_while_it_holds_the_model(
    client: TestClient, monkeypatch
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)
    spawned: list[object] = []
    monkeypatch.setattr(
        demo_console.subprocess, "Popen", lambda *a, **k: spawned.append(a)
    )

    response = client.post(
        CONSOLE_RUNS,
        json={
            "kind": "runtime",
            "roster_entry_id": ENTRY,
            "machine_id": MACHINE,
            "compute_mode": "gpu",
        },
        headers=KEYED,
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "the playground holds a local model"
    assert detail["holder"]["session"] == "playground"
    assert detail["holder"]["roster_entry_id"] == ENTRY
    assert spawned == []


def test_the_playground_is_refused_naming_the_run_while_a_run_holds_the_lock(
    client: TestClient, servers: dict[str, list[Any]]
) -> None:
    demo_console.try_acquire(RUN_HOLDER)

    response = client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "a run is in progress"
    assert detail["holder"]["session"] == "run"
    assert servers["started"] == []
    assert demo_console.current_holder() == RUN_HOLDER


def test_a_stop_releases_the_model_and_the_lock(
    client: TestClient, servers: dict[str, list[Any]]
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    response = client.delete(SESSION, headers=KEYED)

    assert response.json() == {"stopped": True}
    assert servers["stopped"] == servers["started"]
    assert demo_console.current_holder() is None
    assert client.delete(SESSION, headers=KEYED).json() == {"stopped": False}


def test_a_switch_stops_the_first_model_before_starting_the_second(
    client: TestClient, servers: dict[str, list[Any]]
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    response = client.post(
        SESSION, json={"roster_entry_id": OTHER_ENTRY}, headers=KEYED
    )

    assert response.status_code == 200
    first, _second = servers["started"]
    assert servers["stopped"] == [first]
    holder = demo_console.current_holder()
    assert isinstance(holder, demo_console.PlaygroundHolder)
    assert holder.roster_entry_id == OTHER_ENTRY


def test_a_refused_switch_leaves_the_loaded_model_in_place(
    client: TestClient, servers: dict[str, list[Any]], settings: ServiceSettings
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    # The 4B file is not in the test models dir: refused before any stop.
    response = client.post(
        SESSION, json={"roster_entry_id": "qwen3-4b-q4km"}, headers=KEYED
    )

    assert response.status_code == 503
    assert servers["stopped"] == []
    assert client.get(OPTIONS, headers=KEYED).json()["loaded"]["roster_entry_id"] == (
        ENTRY
    )


def test_service_shutdown_releases_the_model(
    settings: ServiceSettings, servers: dict[str, list[Any]]
) -> None:
    demo_console.release()
    with client_for(settings) as test_client:
        test_client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert servers["stopped"] == servers["started"] != []
    assert demo_console.current_holder() is None


def test_the_shutdown_backstop_stops_the_playground_model(
    settings: ServiceSettings, servers: dict[str, list[Any]]
) -> None:
    demo_console.release()
    app = service.create_app(settings)
    app.state.playground.start(ENTRY)

    service._stop_console_runs(app)

    assert servers["stopped"] == servers["started"] != []
    assert demo_console.current_holder() is None


@pytest.mark.parametrize(
    ("change", "named"),
    [
        ({"llama_server_path": None}, "LLAMA_SERVER_PATH"),
        ({"slm_models_dir": None}, "SLM_MODELS_DIR"),
        ({"machine_id": None}, "MACHINE_ID"),
    ],
)
def test_a_missing_install_or_machine_is_a_503_naming_it(
    settings: ServiceSettings,
    servers: dict[str, list[Any]],
    change: dict[str, Any],
    named: str,
) -> None:
    demo_console.release()
    with client_for(replace(settings, **change)) as test_client:
        response = test_client.post(
            SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED
        )

    assert response.status_code == 503
    assert named in response.json()["detail"]
    assert servers["started"] == []
    assert demo_console.current_holder() is None


def test_a_failed_start_frees_the_lock(client: TestClient, monkeypatch) -> None:
    def refuse(server_path: Path, flags: list[str]) -> None:
        raise server.ServerStartupError("port 8080 is already accepting connections")

    monkeypatch.setattr(server, "start_server", refuse)

    response = client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert response.status_code == 503
    assert "port 8080" in response.json()["detail"]
    assert demo_console.current_holder() is None


def test_a_machine_with_no_gpu_profile_launches_cpu_only(monkeypatch) -> None:
    entry = roster.load_roster(TRACKED_ROSTER).entries[ENTRY]
    modes: list[str] = []
    monkeypatch.setattr(
        playground.profiles,
        "resolve_for_run",
        lambda entry, machine, mode, **_: modes.append(mode),
    )

    playground.launch_profile(entry, "pro-pc-no-gpu")

    assert modes == ["cpu_only"]
    with pytest.raises(playground.PlaygroundUnavailable, match="no run profile"):
        playground.launch_profile(entry, "undeclared-machine")


def test_an_undeclared_profile_value_is_a_503_naming_it(
    settings: ServiceSettings, servers: dict[str, list[Any]]
) -> None:
    demo_console.release()
    with client_for(replace(settings, machine_id="pro-pc-no-gpu")) as test_client:
        response = test_client.post(
            SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED
        )

    assert response.status_code == 503
    assert "threads" in response.json()["detail"]
    assert servers["started"] == []


def test_a_late_release_cannot_free_another_sessions_lock() -> None:
    demo_console.release()
    stale = demo_console.PlaygroundHolder(ENTRY, "p", "t")
    demo_console.try_acquire(RUN_HOLDER)

    demo_console.release_if(stale)

    assert demo_console.current_holder() == RUN_HOLDER
    demo_console.release()


# --------------------------------------------------------------------------
# The streamed chat proxy
# --------------------------------------------------------------------------

SSE_ANSWER = [
    b'data: {"choices":[{"delta":{"role":"assistant"}}]}',
    b"",
    b'data: {"choices":[{"delta":{"reasoning_content":"hmm"}}]}',
    b'data: {"choices":[{"delta":{"content":"Tides "}}]}',
    b": keep-alive comment",
    (
        b'data: {"choices":[{"delta":{"content":"rise."},"finish_reason":"stop"}],'
        b'"timings":{"predicted_per_second":312.5},"usage":{"completion_tokens":2}}'
    ),
    b"data: [DONE]",
]


class FakeResponse:
    def __init__(self, status_code: int, lines: list[bytes]) -> None:
        self.status_code = status_code
        self._lines = lines

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        return None

    def iter_lines(self) -> list[bytes]:
        return self._lines


@pytest.fixture
def llama(monkeypatch) -> list[dict[str, Any]]:  # type: ignore[no-untyped-def]
    """A stub llama-server chat endpoint: records each call, streams `SSE_ANSWER`."""
    calls: list[dict[str, Any]] = []

    def post(url: str, **kwargs: Any) -> FakeResponse:
        calls.append({"url": url, **kwargs})
        return FakeResponse(200, SSE_ANSWER)

    monkeypatch.setattr(playground.requests, "post", post)
    return calls


def chat_events(client: TestClient, body: dict[str, Any]) -> list[dict[str, Any]]:
    response = client.post(CHAT, json=body, headers=KEYED)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "application/x-ndjson"
    return [json.loads(line) for line in response.text.splitlines()]


def test_an_exchange_streams_text_then_the_policy_in_force(
    client: TestClient, llama: list[dict[str, Any]]
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    events = chat_events(client, {"prompt": PROMPT, "thinking_policy": "disabled"})

    assert events == [
        {"reasoning": "hmm"},
        {"delta": "Tides "},
        {"delta": "rise."},
        {
            "final": {
                "thinking_policy": "disabled",
                "finish_reason": "stop",
                "error": None,
            }
        },
    ]


def test_the_typed_text_is_only_message_content_under_the_entrys_spelling(
    client: TestClient, llama: list[dict[str, Any]]
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    chat_events(client, {"prompt": PROMPT, "thinking_policy": "disabled"})
    chat_events(client, {"prompt": PROMPT, "thinking_policy": "allowed"})

    disabled, allowed = llama
    assert disabled["url"] == "http://127.0.0.1:8080/v1/chat/completions"
    assert disabled["json"] == {
        "messages": [{"role": "user", "content": PROMPT}],
        "stream": True,
        "max_tokens": 64,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    assert "chat_template_kwargs" not in allowed["json"]
    for call in llama:
        rest = {key: value for key, value in call.items() if key != "json"}
        others = {k: v for k, v in call["json"].items() if k != "messages"}
        assert PROMPT not in repr(rest) + repr(others)


@pytest.mark.parametrize(
    ("body", "fragment"),
    [
        ({"prompt": "x" * 201, "thinking_policy": "allowed"}, "PLAYGROUND_MAX"),
        ({"prompt": PROMPT, "thinking_policy": "maybe"}, "thinking_policy"),
        ({"prompt": "   ", "thinking_policy": "allowed"}, "prompt"),
        ({"prompt": PROMPT}, "thinking_policy"),
        ({"prompt": PROMPT, "thinking_policy": "allowed", "model": "x"}, "unknown"),
    ],
)
def test_a_chat_outside_its_caps_or_sets_is_refused_before_anything_is_sent(
    client: TestClient,
    llama: list[dict[str, Any]],
    body: dict[str, Any],
    fragment: str,
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    response = client.post(CHAT, json=body, headers=KEYED)

    assert response.status_code == 422
    assert fragment in response.json()["detail"]
    assert llama == []


def test_a_chat_with_no_model_loaded_is_refused(
    client: TestClient, llama: list[dict[str, Any]]
) -> None:
    response = client.post(
        CHAT, json={"prompt": PROMPT, "thinking_policy": "allowed"}, headers=KEYED
    )

    assert response.status_code == 409
    assert response.json()["detail"]["holder"] is None
    assert llama == []


def test_an_entry_with_no_spelling_is_refused_under_disabled(
    settings: ServiceSettings, servers: dict[str, list[Any]]
) -> None:
    demo_console.release()
    session = playground.PlaygroundSession(settings)
    session.start(ENTRY)
    assert session._entry is not None
    session._entry = replace(session._entry, thinking_control=None)

    with pytest.raises(playground.PlaygroundRequestError, match="thinking_control"):
        session.prepare_chat(playground.ChatRequest(PROMPT, "disabled"))
    session.stop()


@pytest.mark.parametrize(
    ("post", "error"),
    [
        (lambda url, **kw: FakeResponse(500, []), "llama-server answered 500"),
        (
            lambda url, **kw: (_ for _ in ()).throw(requests.ConnectionError()),
            "stopped answering (ConnectionError)",
        ),
        (
            lambda url, **kw: FakeResponse(200, [b"data: {not json"]),
            "stopped answering (JSONDecodeError)",
        ),
    ],
)
def test_a_failed_exchange_ends_with_an_error_and_no_body(
    monkeypatch, post: Any, error: str
) -> None:
    monkeypatch.setattr(playground.requests, "post", post)
    prepared = playground.PreparedChat("http://127.0.0.1:8080/x", {}, "allowed")

    events = list(playground.stream_chat(prepared))

    [final] = events
    assert final["final"]["finish_reason"] is None
    assert final["final"]["error"].endswith(error)


# --------------------------------------------------------------------------
# Nothing is recorded
# --------------------------------------------------------------------------


def snapshot(root: Path) -> dict[str, bytes]:
    return {
        str(path.relative_to(root)): path.read_bytes()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def test_an_exchange_leaves_every_store_registry_and_log_untouched(
    client: TestClient,
    llama: list[dict[str, Any]],
    settings: ServiceSettings,
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    from store_fixtures import make_row, write_store

    write_store(settings.runtime_results_path, [make_row("runtime")])
    write_store(settings.quality_results_path, [make_row("quality")])
    workspace = settings.runtime_results_path.parent
    committed = Path("aidd_docs/results")
    before = snapshot(workspace), snapshot(committed)
    caplog.set_level(logging.DEBUG)

    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)
    events = chat_events(client, {"prompt": PROMPT, "thinking_policy": "disabled"})
    client.delete(SESSION, headers=KEYED)

    assert events[-1]["final"]["error"] is None
    assert (snapshot(workspace), snapshot(committed)) == before
    # The fiche registry and both stores live under `workspace`.
    assert settings.fiche_registry_dir.parent == workspace
    captured = capfd.readouterr()
    for text in (caplog.text, captured.out, captured.err):
        assert PROMPT not in text
    for content in (*before[0].values(), *before[1].values()):
        assert PROMPT.encode() not in content


# --------------------------------------------------------------------------
# Review follow-ups
# --------------------------------------------------------------------------


def test_any_failure_while_starting_frees_the_lock_and_propagates(
    settings: ServiceSettings, monkeypatch
) -> None:
    demo_console.release()

    def interrupted(server_path: Path, flags: list[str]) -> None:
        raise server.StopRequested()

    monkeypatch.setattr(server, "start_server", interrupted)
    session = playground.PlaygroundSession(settings)

    with pytest.raises(server.StopRequested):
        session.start(ENTRY)

    assert demo_console.current_holder() is None
    assert session.loaded() is None


def test_a_machine_below_a_declared_minimum_is_refused_and_nothing_recorded(
    client: TestClient,
    servers: dict[str, list[Any]],
    settings: ServiceSettings,
    monkeypatch,
) -> None:
    workspace = settings.runtime_results_path.parent
    before = sorted(str(path) for path in workspace.rglob("*"))
    monkeypatch.setattr(
        preflight,
        "observe",
        lambda *args: preflight.Observation(
            ram_gb=0.5, vram_gb=None, disk_free_gb=None
        ),
    )

    response = client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert response.status_code == 503
    assert "ram_gb >= 1.08 GB" in response.json()["detail"]
    assert "0.5 GB" in response.json()["detail"]
    assert servers["started"] == []
    assert demo_console.current_holder() is None
    assert sorted(str(path) for path in workspace.rglob("*")) == before


def test_the_start_checks_the_declared_minimums_of_the_entry_it_launches(
    client: TestClient, ample_machine: list[str]
) -> None:
    client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)

    assert ample_machine == [ENTRY]


def test_a_chat_refused_while_a_run_holds_the_lock_names_the_run(
    client: TestClient, llama: list[dict[str, Any]]
) -> None:
    demo_console.try_acquire(RUN_HOLDER)

    response = client.post(
        CHAT, json={"prompt": PROMPT, "thinking_policy": "allowed"}, headers=KEYED
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "a run is in progress"
    assert detail["holder"]["session"] == "run"
    assert llama == []


# --------------------------------------------------------------------------
# The cloud subject: opt-in, through the existing provider client
# --------------------------------------------------------------------------

CLOUD_KEY = "provider-key-7f3c9e"  # pragma: allowlist secret
CLOUD_ANSWER = "Tides follow the moon."


def cloud_settings(
    settings: ServiceSettings, provider: str = "mistral", pacing_s: float = 0.0
) -> ServiceSettings:
    model = {"mistral": mistral_client.MODEL, "google": google_client.MODEL}
    return replace(
        settings,
        playground_cloud=PlaygroundCloudSubject(
            provider=provider,
            model=model[provider],
            api_key=CLOUD_KEY,
            pacing_s=pacing_s,
            max_retries=4,
        ),
    )


@pytest.fixture
def cloud_calls(monkeypatch) -> dict[str, list[dict[str, Any]]]:  # type: ignore[no-untyped-def]
    """Stub both providers' clients at their own boundary; record every call."""
    calls: dict[str, list[dict[str, Any]]] = {"mistral": [], "google": []}

    def fake(provider: str) -> Any:
        def complete_prompt(prompt: str, api_key: str, **kwargs: Any) -> Any:
            calls[provider].append({"prompt": prompt, "api_key": api_key, **kwargs})
            return {"content": CLOUD_ANSWER, "finish_reason": "stop"}

        return complete_prompt

    monkeypatch.setattr(mistral_client, "complete_prompt", fake("mistral"))
    monkeypatch.setattr(google_client, "complete_prompt", fake("google"))
    return calls


@pytest.fixture
def sleeps(monkeypatch) -> list[float]:  # type: ignore[no-untyped-def]
    """Record every pacing and backoff sleep instead of waiting."""
    slept: list[float] = []
    monkeypatch.setattr(playground.time, "sleep", slept.append)
    return slept


@pytest.fixture
def cloud_client(settings: ServiceSettings, servers: dict[str, list[Any]], sleeps):  # type: ignore[no-untyped-def]
    demo_console.release()
    with client_for(cloud_settings(settings)) as test_client:
        yield test_client
    demo_console.release()


CLOUD_START = {"cloud_subject": "mistral"}
DISABLED_CHAT = {"prompt": PROMPT, "thinking_policy": "disabled"}


def test_unconfigured_the_cloud_subject_is_absent_refused_and_never_called(
    client: TestClient,
    cloud_calls: dict[str, list[dict[str, Any]]],
    monkeypatch,
) -> None:
    # The benchmark keys are present; they alone enable nothing.
    monkeypatch.setenv("MISTRAL_API_KEY", CLOUD_KEY)
    monkeypatch.setenv("GOOGLE_API_KEY", CLOUD_KEY)
    monkeypatch.delenv("PLAYGROUND_CLOUD_SUBJECT", raising=False)
    assert settings_module._playground_cloud_subject() is None

    options = client.get(OPTIONS, headers=KEYED).json()
    started = client.post(SESSION, json=CLOUD_START, headers=KEYED)
    chat = client.post(CHAT, json=DISABLED_CHAT, headers=KEYED)

    assert options["cloud_subject"] is None
    assert started.status_code == 422
    assert "PLAYGROUND_CLOUD_SUBJECT is unset" in started.json()["detail"]
    assert chat.status_code == 409
    assert cloud_calls == {"mistral": [], "google": []}
    assert demo_console.current_holder() is None


@pytest.mark.parametrize(
    "body",
    [
        {"cloud_subject": "google"},
        {"cloud_subject": "mistral", "roster_entry_id": ENTRY},
        {},
    ],
)
def test_a_start_naming_another_or_two_subjects_is_refused(
    cloud_client: TestClient, body: dict[str, str]
) -> None:
    assert cloud_client.post(SESSION, json=body, headers=KEYED).status_code == 422
    assert demo_console.current_holder() is None


def test_configured_the_options_name_the_subject_and_never_the_key(
    cloud_client: TestClient,
) -> None:
    response = cloud_client.get(OPTIONS, headers=KEYED)

    assert response.json()["cloud_subject"] == {
        "provider": "mistral",
        "label": "Mistral",
        "model": mistral_client.MODEL,
    }
    assert CLOUD_KEY not in response.text


def test_a_cloud_exchange_goes_through_the_provider_client_and_holds_the_lock(
    cloud_client: TestClient, cloud_calls: dict[str, list[dict[str, Any]]]
) -> None:
    started = cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)
    options = cloud_client.get(OPTIONS, headers=KEYED).json()
    events = chat_events(cloud_client, DISABLED_CHAT)

    assert started.json() == {"provider": "mistral", "model": mistral_client.MODEL}
    assert options["loaded"] == started.json()
    assert options["holder"]["session"] == "playground"
    assert options["holder"]["provider"] == "mistral"
    assert events == [
        {"delta": CLOUD_ANSWER},
        {
            "final": {
                "thinking_policy": playground.CLOUD_THINKING_POLICY,
                "finish_reason": "stop",
                "error": None,
            }
        },
    ]
    (call,) = cloud_calls["mistral"]
    assert call["prompt"] == PROMPT
    assert call["api_key"] == CLOUD_KEY
    assert call["max_tokens"] == 64
    assert cloud_calls["google"] == []


def test_the_cloud_samplers_are_the_quality_clis_own() -> None:
    from wave_local_ai_v2 import quality_cli

    assert playground.MISTRAL_SAMPLING == quality_cli.CLOUD_SAMPLING
    assert playground.GOOGLE_SAMPLING == quality_cli.GOOGLE_SAMPLING
    assert playground.RETRY_BASE_DELAY_S == quality_cli._RETRY_BASE_DELAY_S


def test_a_google_subject_goes_through_the_google_client(
    settings: ServiceSettings,
    servers: dict[str, list[Any]],
    cloud_calls: dict[str, list[dict[str, Any]]],
    sleeps: list[float],
) -> None:
    demo_console.release()
    with client_for(cloud_settings(settings, "google")) as test_client:
        test_client.post(SESSION, json={"cloud_subject": "google"}, headers=KEYED)
        events = chat_events(test_client, DISABLED_CHAT)
    demo_console.release()

    assert events[0] == {"delta": CLOUD_ANSWER}
    (call,) = cloud_calls["google"]
    assert call["seed"] == playground.GOOGLE_SAMPLING["seed"]
    assert cloud_calls["mistral"] == []


def test_a_local_exchange_never_reaches_a_cloud_client(
    cloud_client: TestClient,
    cloud_calls: dict[str, list[dict[str, Any]]],
    llama: list[dict[str, Any]],
) -> None:
    cloud_client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)
    events = chat_events(cloud_client, DISABLED_CHAT)

    assert events[-1]["final"]["error"] is None
    assert cloud_calls == {"mistral": [], "google": []}
    (call,) = llama
    assert call["url"].startswith("http://127.0.0.1:")


def test_selecting_the_cloud_subject_stops_the_local_model(
    cloud_client: TestClient, servers: dict[str, list[Any]]
) -> None:
    cloud_client.post(SESSION, json={"roster_entry_id": ENTRY}, headers=KEYED)
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    assert servers["stopped"] == servers["started"]
    assert isinstance(demo_console.current_holder(), demo_console.CloudPlaygroundHolder)
    stopped = cloud_client.delete(SESSION, headers=KEYED).json()
    assert stopped == {"stopped": True}
    assert demo_console.current_holder() is None


def test_the_cloud_subject_is_refused_while_a_run_holds_the_lock(
    cloud_client: TestClient, cloud_calls: dict[str, list[dict[str, Any]]]
) -> None:
    demo_console.try_acquire(RUN_HOLDER)

    response = cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    assert response.status_code == 409
    assert response.json()["detail"]["holder"]["session"] == "run"
    assert cloud_calls == {"mistral": [], "google": []}


def test_a_send_is_refused_if_a_run_took_the_lock_after_the_selection(
    cloud_client: TestClient, cloud_calls: dict[str, list[dict[str, Any]]]
) -> None:
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)
    # The console pump's unconditional release, then a run taking the lock.
    demo_console.release()
    demo_console.try_acquire(RUN_HOLDER)

    response = cloud_client.post(CHAT, json=DISABLED_CHAT, headers=KEYED)

    assert response.status_code == 409
    assert response.json()["detail"]["message"] == "a run is in progress"
    assert cloud_calls == {"mistral": [], "google": []}


def test_a_send_is_refused_if_the_lock_was_freed_under_the_selection(
    cloud_client: TestClient, cloud_calls: dict[str, list[dict[str, Any]]]
) -> None:
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)
    demo_console.release()

    response = cloud_client.post(CHAT, json=DISABLED_CHAT, headers=KEYED)

    assert response.status_code == 409
    assert "no longer holds" in response.json()["detail"]["message"]
    assert cloud_calls == {"mistral": [], "google": []}


def test_a_run_is_refused_naming_the_cloud_subject_while_it_is_selected(
    cloud_client: TestClient, monkeypatch
) -> None:
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)
    spawned: list[object] = []
    monkeypatch.setattr(
        demo_console.subprocess, "Popen", lambda *a, **k: spawned.append(a)
    )

    response = cloud_client.post(
        CONSOLE_RUNS,
        json={
            "kind": "runtime",
            "roster_entry_id": ENTRY,
            "machine_id": MACHINE,
            "compute_mode": "gpu",
        },
        headers=KEYED,
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert detail["message"] == "the playground holds its mistral cloud subject"
    assert detail["holder"]["provider"] == "mistral"
    assert spawned == []


def _raising(exc: Exception, calls: list[int]) -> Any:
    def complete_prompt(*args: Any, **kwargs: Any) -> Any:
        calls.append(1)
        raise exc

    return complete_prompt


def test_a_rate_limit_is_retried_then_shown_as_a_refusal_naming_the_provider(
    cloud_client: TestClient, monkeypatch, sleeps: list[float]
) -> None:
    calls: list[int] = []
    limited = mistral_client.RetryableRequestError(
        f"Mistral request failed with status 429: echo {CLOUD_KEY}",
        status_code=429,
        retry_after_s=2.0,
    )
    monkeypatch.setattr(mistral_client, "complete_prompt", _raising(limited, calls))
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    response = cloud_client.post(CHAT, json=DISABLED_CHAT, headers=KEYED)
    events = [json.loads(line) for line in response.text.splitlines()]

    # The first attempt and the four retries of a one-item budget, each
    # waiting the provider's own hint.
    assert len(calls) == 5
    assert sleeps == [2.0] * 4
    assert events == [
        {
            "final": {
                "thinking_policy": playground.CLOUD_THINKING_POLICY,
                "finish_reason": None,
                "error": "refused by Mistral: it answered 429 (rate limit or "
                "provider failure) through 4 retries",
            }
        }
    ]
    assert CLOUD_KEY not in response.text


@pytest.mark.parametrize(
    ("exc", "error"),
    [
        (
            mistral_client.MistralRequestError(f"status 400: {CLOUD_KEY}"),
            "refused by Mistral: MistralRequestError",
        ),
        (
            requests.ConnectionError(f"https://api.mistral.ai {CLOUD_KEY}"),
            "Mistral could not be reached (ConnectionError)",
        ),
    ],
)
def test_a_provider_failure_names_the_provider_and_never_the_clients_message(
    cloud_client: TestClient, monkeypatch, exc: Exception, error: str
) -> None:
    monkeypatch.setattr(mistral_client, "complete_prompt", _raising(exc, []))
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    response = cloud_client.post(CHAT, json=DISABLED_CHAT, headers=KEYED)

    assert json.loads(response.text.splitlines()[-1])["final"]["error"] == error
    assert CLOUD_KEY not in response.text


def test_an_empty_cloud_answer_is_a_refusal_not_an_empty_answer(
    cloud_client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        mistral_client,
        "complete_prompt",
        lambda *a, **k: {"content": "", "finish_reason": "stop"},
    )
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    events = chat_events(cloud_client, DISABLED_CHAT)

    assert events == [
        {
            "final": {
                "thinking_policy": playground.CLOUD_THINKING_POLICY,
                "finish_reason": "stop",
                "error": "refused by Mistral: it returned no text",
            }
        }
    ]


def test_consecutive_cloud_sends_are_paced_at_the_providers_interval(
    settings: ServiceSettings,
    servers: dict[str, list[Any]],
    cloud_calls: dict[str, list[dict[str, Any]]],
    sleeps: list[float],
) -> None:
    demo_console.release()
    with client_for(cloud_settings(settings, pacing_s=30.0)) as test_client:
        test_client.post(SESSION, json=CLOUD_START, headers=KEYED)
        chat_events(test_client, DISABLED_CHAT)
        chat_events(test_client, DISABLED_CHAT)
    demo_console.release()

    assert len(cloud_calls["mistral"]) == 2
    (slept,) = sleeps
    assert 29.0 < slept <= 30.0


def test_no_response_body_or_log_line_carries_the_provider_key(
    cloud_client: TestClient,
    cloud_calls: dict[str, list[dict[str, Any]]],
    caplog: pytest.LogCaptureFixture,
    capfd: pytest.CaptureFixture[str],
) -> None:
    caplog.set_level(logging.DEBUG)
    bodies = [
        cloud_client.get(OPTIONS, headers=KEYED).text,
        cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED).text,
        cloud_client.get(OPTIONS, headers=KEYED).text,
        cloud_client.post(CHAT, json=DISABLED_CHAT, headers=KEYED).text,
        cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED).text,
        cloud_client.delete(SESSION, headers=KEYED).text,
    ]

    assert len(cloud_calls["mistral"]) == 1
    captured = capfd.readouterr()
    for text in (*bodies, caplog.text, captured.out, captured.err):
        assert CLOUD_KEY not in text
        assert PROMPT not in text


def test_a_retry_wait_over_the_playground_cap_is_refused_without_waiting(
    cloud_client: TestClient, monkeypatch, sleeps: list[float]
) -> None:
    calls: list[int] = []
    limited = mistral_client.RetryableRequestError(
        "Mistral request failed with status 429",
        status_code=429,
        retry_after_s=playground.PLAYGROUND_MAX_RETRY_WAIT_S + 50,
    )
    monkeypatch.setattr(mistral_client, "complete_prompt", _raising(limited, calls))
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    events = chat_events(cloud_client, DISABLED_CHAT)

    assert calls == [1]
    assert sleeps == []
    error = events[-1]["final"]["error"]
    assert error.startswith(
        "refused by Mistral: it answered 429 and asked to wait 60.0 s"
    )
    assert f"{playground.PLAYGROUND_MAX_RETRY_WAIT_S} s cap" in error


def test_an_unexpected_failure_still_ends_with_a_final_event_naming_the_provider(
    cloud_client: TestClient, monkeypatch
) -> None:
    monkeypatch.setattr(
        mistral_client,
        "complete_prompt",
        _raising(KeyError(f"choices {CLOUD_KEY}"), []),
    )
    cloud_client.post(SESSION, json=CLOUD_START, headers=KEYED)

    response = cloud_client.post(CHAT, json=DISABLED_CHAT, headers=KEYED)

    assert [json.loads(line) for line in response.text.splitlines()] == [
        {
            "final": {
                "thinking_policy": playground.CLOUD_THINKING_POLICY,
                "finish_reason": None,
                "error": "refused by Mistral: KeyError",
            }
        }
    ]
    assert CLOUD_KEY not in response.text
