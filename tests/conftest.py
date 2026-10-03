"""Fixtures every test module may use."""

from __future__ import annotations

import signal
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from store_fixtures import build_bundle

from wave_local_ai_v2 import code_sandbox


class FakeSandbox:
    """A sandbox runner that never starts a container.

    Every test scores code-generation items through this one unless it asks
    for the real runner, so no test ever needs Docker and none can run
    generated code on the host. `outcomes` maps a solution to its status;
    anything else fails its tests. `runs` records each call.
    """

    def __init__(self) -> None:
        self.outcomes: dict[str, str] = {}
        self.runs: list[tuple[str, str, str]] = []
        self.checked: list[tuple[str, ...]] = []

    def check_available(self, languages: tuple[str, ...]) -> None:
        self.checked.append(languages)

    def describe(self, language: str) -> dict[str, object]:
        return {
            "runtime": code_sandbox.RUNTIME,
            "image": code_sandbox.DEFAULT_IMAGES[language],
            "image_id": "sha256:" + "0" * 64,
            "network": "none",
            "host_mount": False,
            "wall_clock_cap_s": code_sandbox.WALL_CLOCK_CAP_S,
            "memory_cap_mib": code_sandbox.MEMORY_CAP_MIB,
            "pids_cap": code_sandbox.PIDS_CAP,
        }

    def run(
        self, language: str, solution: str, tests: str
    ) -> code_sandbox.SandboxOutcome:
        self.runs.append((language, solution, tests))
        return code_sandbox.SandboxOutcome(
            self.outcomes.get(solution, code_sandbox.STATUS_TESTS_FAILED)
        )


@pytest.fixture(autouse=True)
def fake_sandbox(monkeypatch: pytest.MonkeyPatch) -> FakeSandbox:
    """Substitute the fake runner for `code_sandbox.active_runner()`."""
    fake = FakeSandbox()
    monkeypatch.setattr(code_sandbox, "active_runner", lambda: fake)
    return fake


@pytest.fixture
def bundle(tmp_path: Path) -> dict[str, Path]:
    """A self-contained store + fiche registry + roster + suite dir on disk."""
    return build_bundle(tmp_path)


@pytest.fixture(autouse=True)
def _restore_graceful_stop_handler() -> Iterator[None]:
    """Undo a CLI `main()`'s `server.install_graceful_stop()` after each test.

    Without this, one test calling a real `main()` would leave the pytest
    process itself turning SIGTERM/SIGBREAK into `StopRequested`.
    """
    stop_signal = signal.SIGBREAK if sys.platform == "win32" else signal.SIGTERM
    previous = signal.getsignal(stop_signal)
    yield
    signal.signal(stop_signal, previous)


MARKING_VARIANT_ID = "test_marking"


def mark_prompt(prompt: str) -> str:
    """What the test-only marking variant makes of an authored prompt."""
    return f"[marked] {prompt}"


@pytest.fixture
def marking_variant(monkeypatch: pytest.MonkeyPatch) -> str:
    """Register a test-only variant that visibly transforms the prompt.

    A real non-identity variant arrives with its own story; this one exists
    so a test can see where the variant's output went -- into the engine's
    templating and every request body -- rather than infer it from identity.
    Returns the variant id for the caller to declare on its writer.
    """
    from wave_local_ai_v2 import prompt_variants

    monkeypatch.setitem(
        prompt_variants._TRANSFORMATIONS,
        "test_mark",
        lambda definition, prompt: mark_prompt(prompt),
    )
    definition = {"transformation": "test_mark"}
    registry = prompt_variants.load_registry(
        [
            *prompt_variants.REGISTERED_VARIANTS,
            {
                "variant_id": MARKING_VARIANT_ID,
                "version": "1",
                "definition": definition,
                "definition_hash": prompt_variants.definition_hash(definition),
            },
        ]
    )
    monkeypatch.setattr(prompt_variants, "REGISTRY", registry)
    return MARKING_VARIANT_ID
