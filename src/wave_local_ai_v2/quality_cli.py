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

from wave_local_ai_v2 import (
    classification_suite,
    mistral_client,
    prompt_provenance,
    provenance,
    row_contract,
    server,
    suite_gate,
)
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.mistral_client import MistralRequestError
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.scoring import score_item, score_suite
from wave_local_ai_v2.settings import Settings, SettingsError, load_settings
from wave_local_ai_v2.suite_gate import SuiteGateError, SuiteGateResult

# Same model this harness's runtime CLI already validates end-to-end
# (`__init__.py`); reusing it removes model-selection as a variable this
# proof-of-concept slice doesn't need to resolve.
LOCAL_MODEL_ID = "Qwen3.6-35B-A3B"
MODEL_RELATIVE_PATH = Path(LOCAL_MODEL_ID) / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
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
        # requests.RequestException subclasses OSError, so every HTTP failure is
        # still caught here and the disk failures append_row can raise now are
        # too. The widening is deliberate and covers the whole run: any OS-level
        # failure (an absent llama-server binary, a denied read) is an operator
        # problem and belongs on stderr as one line, not as a traceback.
        OSError,
        MistralRequestError,
        LocalCompletionError,
        SuiteGateError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    settings = load_settings()
    # One id for the whole invocation: the local and cloud batches are two
    # halves of one comparison, and a reader must be able to tell which local
    # rows a given cloud row was scored against.
    run_id = new_run_id()
    provenance_fields = provenance.capture_provenance()
    # Every pre-condition is checked before the (expensive) local suite runs,
    # cheapest first: the two offline ones cost nothing, and the catalog call is
    # the only one that needs the network. The order still matters even though a
    # cloud failure no longer discards the local rows: it avoids paying for a
    # multi-minute local run that could never have been completed anyway.
    if not settings.mistral_api_key:
        raise SettingsError("MISTRAL_API_KEY is not set")
    model_path = _local_model_path(settings)
    # Also offline, also cheap: a refused suite (missing/inconsistent tags) must
    # abort before the network catalog call, let alone the multi-minute local run.
    gate_result = suite_gate.gate_suite(CLASSIFICATION_TASK_SUITE)
    deprecation_notice = mistral_client.check_model_available(settings.mistral_api_key)
    if deprecation_notice:
        # A retirement date is news, not a failure: the model still answers until
        # then. stderr keeps stdout to the accuracy lines the operator parses.
        print(deprecation_notice, file=sys.stderr)

    local_completions = _run_local_suite(settings, model_path)
    # Persisted before the cloud suite starts: a 429, a dropped connection or a
    # malformed body would otherwise throw away the multi-minute local run and
    # write zero rows. Both batches share one run_id, so a partial run is still
    # recognizable as one session.
    _score_and_write(
        settings,
        run_id=run_id,
        model_id=LOCAL_MODEL_ID,
        provider="local",
        completions=local_completions,
        sampling=LOCAL_SAMPLING,
        gate_result=gate_result,
        provenance_fields=provenance_fields,
        endpoint=prompt_provenance.LOCAL_COMPLETION_ENDPOINT,
    )

    cloud_endpoint, cloud_completions = _run_cloud_suite(settings)
    _score_and_write(
        settings,
        run_id=run_id,
        model_id=mistral_client.MODEL,
        provider="mistral",
        completions=cloud_completions,
        sampling=CLOUD_SAMPLING,
        gate_result=gate_result,
        provenance_fields=provenance_fields,
        endpoint=cloud_endpoint,
    )


def _local_model_path(settings: Settings) -> Path:
    """Resolve the local GGUF, or raise: a missing file must cost no network call."""
    model_path = settings.slm_models_dir / MODEL_RELATIVE_PATH
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")
    return model_path


def _run_local_suite(settings: Settings, model_path: Path) -> list[str]:
    flags = server.build_flags(model_path)
    completions: list[str] = []

    with server.running_server(settings.llama_server_path, flags):
        for item in CLASSIFICATION_TASK_SUITE:
            response = requests.post(
                f"http://{server.HOST}:{server.PORT}/completion",
                json={
                    "prompt": item["prompt"],
                    "n_predict": classification_suite.MAX_OUTPUT_TOKENS,
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


def _run_cloud_suite(settings: Settings) -> tuple[str, list[str]]:
    # The same cap the local half runs under (`n_predict` above): the suite
    # declares one generation cap for every model it compares, and every row
    # publishes it as what that row ran under. Sending it to only one provider
    # would make the cloud rows' `max_output_tokens` a claim about a limit that
    # was never applied.
    completions = [
        mistral_client.complete_prompt(
            item["prompt"],
            settings.mistral_api_key,
            temperature=CLOUD_SAMPLING["temperature"],
            random_seed=CLOUD_SAMPLING["random_seed"],
            max_tokens=classification_suite.MAX_OUTPUT_TOKENS,
        )
        for item in CLASSIFICATION_TASK_SUITE
    ]
    # Every call hits the same endpoint within one run; the first response
    # names it, sourced from the module that actually made the call rather
    # than read off mistral_client's own constants at this call site.
    endpoint = completions[0]["endpoint"]
    return endpoint, [completion["content"] for completion in completions]


def _score_and_write(
    settings: Settings,
    *,
    run_id: str,
    model_id: str,
    provider: str,
    completions: list[str],
    sampling: dict[str, Any],
    gate_result: SuiteGateResult,
    provenance_fields: dict[str, Any],
    endpoint: str,
) -> None:
    prompt_template_id = (
        prompt_provenance.TEMPLATE_ID_NONE
        if provider == "local"
        else prompt_provenance.TEMPLATE_ID_MISTRAL_CHAT_MESSAGE
    )
    prompt_template_hash = (
        None if provider == "local" else prompt_provenance.MISTRAL_CHAT_MESSAGE_HASH
    )
    scored_items = [
        score_item(item, completion)
        for item, completion in zip(CLASSIFICATION_TASK_SUITE, completions, strict=True)
    ]
    suite_accuracy = score_suite(scored_items)

    for item, scored in zip(CLASSIFICATION_TASK_SUITE, scored_items, strict=True):
        row = {
            "schema_version": row_contract.SCHEMA_VERSION,
            "run_id": run_id,
            "captured_at": captured_at(),
            **provenance_fields,
            "endpoint": endpoint,
            "prompt_template_id": prompt_template_id,
            "prompt_template_hash": prompt_template_hash,
            "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
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
            "max_output_tokens": classification_suite.MAX_OUTPUT_TOKENS,
            "stop_sequences": list(classification_suite.STOP_SEQUENCES),
            "context_length": classification_suite.CONTEXT_LENGTH,
            "suite_id": classification_suite.SUITE_ID,
            "suite_version": classification_suite.SUITE_VERSION,
            "prompt_set_hash": classification_suite.PROMPT_SET_HASH,
            "language": item["language"],
            "provenance": item["provenance"],
            "contamination_risk": item["contamination_risk"],
            "indicative": gate_result["indicative"],
            "indicative_reasons": list(gate_result["indicative_reasons"]),
        }
        append_row(settings.quality_results_path, "quality", row)

    print(f"model={model_id} provider={provider} accuracy={suite_accuracy:.2f}")
