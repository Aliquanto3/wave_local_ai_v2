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

# A quality score is only meaningful if a second run reproduces it
# (`aidd_docs/memory/architecture.md`: "quality scores are reproducible (model +
# prompt + seed)"). The local server is launched with the runtime benchmark's
# validated flag set, which samples at `--temp 1.0` with no seed -- correct for
# that benchmark, fatal here. `server.build_flags` must not change, because the
# runtime harness is required to reproduce its validated command exactly, so the
# sampler is pinned per request instead: llama-server lets a `/completion` body
# override the server's command-line defaults.
QUALITY_SEED = 20260821

LOCAL_SAMPLING: dict[str, Any] = {
    "seed": QUALITY_SEED,  # server default: -1, a fresh random seed per request
    "temperature": 0,  # server launched with --temp 1.0
    "top_k": 0,  # disabled; server launched with --top-k 20
    "top_p": 1.0,  # disabled; server launched with --top-p 0.95
    # The server is launched with --presence-penalty 1.5. Penalties are applied
    # to the logits *before* the sampler selects, so temperature 0 alone would
    # still be greedy over penalised logits: deterministic, but scoring a
    # distribution skewed by a penalty tuned for long-form generation.
    "presence_penalty": 0,
}

# Mistral names the seed field `random_seed`. It exposes no penalty controls on
# this endpoint, so pinning temperature and the seed is the whole surface.
CLOUD_SAMPLING: dict[str, Any] = {
    "temperature": 0,
    "random_seed": QUALITY_SEED,
}


class LocalCompletionError(RuntimeError):
    """Raised when a local llama-server /completion response has no usable content."""


def main() -> None:
    try:
        _run()
    except (
        SettingsError,
        server.ServerStartupError,
        requests.RequestException,
        MistralRequestError,
        LocalCompletionError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    settings = load_settings()
    if not settings.mistral_api_key:
        # Check before the (expensive) local suite runs, not only before the cloud
        # loop, so a missing key fails immediately instead of after a full
        # llama-server lifecycle.
        raise SettingsError("MISTRAL_API_KEY is not set")

    local_completions = _run_local_suite(settings)
    cloud_completions = _run_cloud_suite(settings)

    _score_and_write(
        settings,
        model_id=LOCAL_MODEL_ID,
        provider="local",
        completions=local_completions,
        sampling=LOCAL_SAMPLING,
    )
    _score_and_write(
        settings,
        model_id=mistral_client.MODEL,
        provider="mistral",
        completions=cloud_completions,
        sampling=CLOUD_SAMPLING,
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
                json={
                    "prompt": item["prompt"],
                    "n_predict": FIXED_MAX_TOKENS,
                    **LOCAL_SAMPLING,
                },
                timeout=REQUEST_TIMEOUT_S,
            )
            response.raise_for_status()
            response_json: dict[str, Any] = response.json()
            try:
                content = response_json["content"]
            except (KeyError, TypeError) as exc:
                raise LocalCompletionError(
                    f"unexpected /completion response shape: {response_json!r}"
                ) from exc
            if not isinstance(content, str):
                # A present-but-non-text content (null, object) would only fail
                # further down in normalize_label, as an uncaught AttributeError.
                raise LocalCompletionError(
                    f"unexpected /completion content type: {content!r}"
                )
            completions.append(content)

    return completions


def _run_cloud_suite(settings: Settings) -> list[str]:
    return [
        mistral_client.complete_prompt(
            item["prompt"],
            settings.mistral_api_key,
            temperature=CLOUD_SAMPLING["temperature"],
            random_seed=CLOUD_SAMPLING["random_seed"],
        )
        for item in CLASSIFICATION_TASK_SUITE
    ]


def _score_and_write(
    settings: Settings,
    *,
    model_id: str,
    provider: str,
    completions: list[str],
    sampling: dict[str, Any],
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
            # Nested so a row is self-describing: a greedy row and a future
            # sampled row can share `quality.jsonl` and stay distinguishable
            # without consulting git history, and adding a sampler key can never
            # collide with a scoring field. Each row records the parameters sent
            # to its own provider, never a merged union of both.
            "sampling": dict(sampling),
        }
        append_row(settings.quality_results_path, row)

    print(f"model={model_id} provider={provider} accuracy={suite_accuracy:.2f}")
