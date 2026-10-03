"""Fixtures every test module may use."""

from __future__ import annotations

import signal
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from store_fixtures import build_bundle


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
