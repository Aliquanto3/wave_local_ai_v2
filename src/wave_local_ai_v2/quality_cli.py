"""CLI entry point: score the classification task suite against one local SLM
and one cloud model, writing one quality row per (task, model).

Deliberately collects none of the runtime harness's fields (fiche, timings,
GPU stats, energy): a quality row must be readable on its own, without any
hardware or runtime context, and vice versa (`aidd_docs/memory/architecture.md`:
"the two are never merged into a single table").
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import mistral_client, server
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.mistral_client import MistralRequestError
from wave_local_ai_v2.results import append_row
from wave_local_ai_v2.scoring import score_item, score_suite
from wave_local_ai_v2.settings import Settings, SettingsError, load_settings

# Same model this harness's runtime CLI already validates end-to-end
# (`__init__.py`); reusing it removes model-selection as a variable this
# proof-of-concept slice doesn't need to resolve.
LOCAL_MODEL_ID = "Qwen3.6-35B-A3B"
MODEL_RELATIVE_PATH = Path(LOCAL_MODEL_ID) / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
FIXED_MAX_TOKENS = 32
REQUEST_TIMEOUT_S = 300


def main() -> None:
    try:
        _run()
    except (
        SettingsError,
        server.ServerStartupError,
        requests.RequestException,
        MistralRequestError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    settings = load_settings()

    local_completions = _run_local_suite(settings)
    cloud_completions = _run_cloud_suite(settings)

    _score_and_write(
        settings,
        model_id=LOCAL_MODEL_ID,
        provider="local",
        completions=local_completions,
    )
    _score_and_write(
        settings,
        model_id=mistral_client.MODEL,
        provider="mistral",
        completions=cloud_completions,
    )


def _run_local_suite(settings: Settings) -> list[str]:
    model_path = settings.slm_models_dir / MODEL_RELATIVE_PATH
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")

    flags = server.build_flags(model_path)
    completions: list[str] = []

    with server.running_server(settings.llama_server_path, flags):
        for item in CLASSIFICATION_TASK_SUITE:
            response = requests.post(
                f"http://{server.HOST}:{server.PORT}/completion",
                json={"prompt": item["prompt"], "n_predict": FIXED_MAX_TOKENS},
                timeout=REQUEST_TIMEOUT_S,
            )
            response.raise_for_status()
            response_json: dict[str, Any] = response.json()
            completions.append(response_json["content"])

    return completions


def _run_cloud_suite(settings: Settings) -> list[str]:
    if not settings.mistral_api_key:
        raise SettingsError("MISTRAL_API_KEY is not set")

    return [
        mistral_client.complete_prompt(item["prompt"], settings.mistral_api_key)
        for item in CLASSIFICATION_TASK_SUITE
    ]


def _score_and_write(
    settings: Settings, *, model_id: str, provider: str, completions: list[str]
) -> None:
    scored_items = [
        score_item(item, completion)
        for item, completion in zip(CLASSIFICATION_TASK_SUITE, completions, strict=True)
    ]
    suite_accuracy = score_suite(scored_items)

    for item, scored in zip(CLASSIFICATION_TASK_SUITE, scored_items, strict=True):
        row = {
            "model_id": model_id,
            "provider": provider,
            "task_suite": "classification",
            "item_id": scored["item_id"],
            "prompt": item["prompt"],
            "expected_label": scored["expected_label"],
            "predicted_label": scored["predicted_label"],
            "correct": scored["correct"],
            "suite_accuracy": suite_accuracy,
        }
        append_row(settings.quality_results_path, row)

    print(f"model={model_id} provider={provider} accuracy={suite_accuracy:.2f}")
