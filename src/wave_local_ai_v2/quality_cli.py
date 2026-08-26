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
from typing import Any, TypedDict

import requests

from wave_local_ai_v2 import (
    build_probe,
    classification_suite,
    cost,
    emissions,
    fiche_registry,
    mistral_client,
    prompt_provenance,
    provenance,
    results,
    roster,
    row_contract,
    server,
    suite_gate,
    verdict,
)
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.energy import (
    ENERGY_METHOD_UNAVAILABLE,
    EnergyResult,
    measure_energy,
)
from wave_local_ai_v2.hardware import build_fiche, capture_fiche
from wave_local_ai_v2.mistral_client import MistralCompletion, MistralRequestError
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.scoring import score_item, score_suite
from wave_local_ai_v2.settings import Settings, SettingsError, load_settings
from wave_local_ai_v2.suite_gate import SuiteGateError, SuiteGateResult

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


class _Completion(TypedDict):
    """One provider's per-item generation, unified across local and cloud shapes."""

    content: str
    truncated: bool
    generated_tokens: int


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
        roster.RosterError,
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
    # cheapest first: the three offline ones cost nothing, and the catalog call is
    # the only one that needs the network. The order still matters even though a
    # cloud failure no longer discards the local rows: it avoids paying for a
    # multi-minute local run that could never have been completed anyway.
    if not settings.mistral_api_key:
        raise SettingsError("MISTRAL_API_KEY is not set")
    # Loaded once per run, not once per row: raises before any HTTP call is made.
    loaded_roster = roster.load_roster(settings.roster_path)
    roster_entry = roster.resolve_entry(loaded_roster, settings.roster_entry_id)
    model_path = _local_model_path(settings, roster_entry)
    # Also offline, also cheap: a refused suite (missing/inconsistent tags) must
    # abort before the network catalog call, let alone the multi-minute local run.
    gate_result = suite_gate.gate_suite(CLASSIFICATION_TASK_SUITE)
    deprecation_notice = mistral_client.check_model_available(settings.mistral_api_key)
    if deprecation_notice:
        # A retirement date is news, not a failure: the model still answers until
        # then. stderr keeps stdout to the accuracy lines the operator parses.
        print(deprecation_notice, file=sys.stderr)

    # Refuses (roster.RosterError) before any process spawns when
    # settings.host_n_cpu_moe cannot be applied to roster_entry -- the check
    # lives inside build_flags itself (server.py's one call site).
    flags = server.build_flags(
        roster_entry, settings.host_n_cpu_moe, settings.host_threads, model_path
    )
    # Probing the binary itself doesn't need the server running, so this is
    # done before launch rather than costing readiness-wait time. An
    # unreadable build is an explicit None, never a fallback string.
    llama_cpp_build = build_probe.probe_build(settings.llama_server_path)
    # One fiche per invocation, built from the one local launch this run
    # performs, cited by both the local-provider and the mistral-provider
    # rows it also writes (plan.md's Decisions table): the run-specific
    # fiche follows the same run_id/roster_entry reuse pattern already
    # established below.
    run_fiche = build_fiche(
        capture_fiche(),
        llama_cpp_build=llama_cpp_build,
        roster_entry_id=roster_entry.entry_id,
        model_sha256=roster_entry.sha256,
        quant=roster_entry.quant,
        flags=flags,
    )
    fiche_hash_value = fiche_registry.write_fiche(
        run_fiche, settings.fiche_registry_dir
    )

    # The tracker spans the whole suite loop (server launch, every item, the
    # server's own teardown when the `with` block exits), not per item -- the
    # same span `__init__.py`'s runtime harness measures over, and the same
    # repeated-batch-value pattern `suite_accuracy` already uses.
    local_completions, local_energy = measure_energy(
        lambda: _run_local_suite(settings, flags),
        country_iso_code=settings.emission_country_iso_code,
    )
    # Persisted before the cloud suite starts: a 429, a dropped connection or a
    # malformed body would otherwise throw away the multi-minute local run and
    # write zero rows. Both batches share one run_id, so a partial run is still
    # recognizable as one session.
    _score_and_write(
        settings,
        run_id=run_id,
        # The entry the local half actually launched names itself: a row can
        # never report one model while its `roster_entry_id` cites another.
        model_id=roster_entry.display_id,
        provider="local",
        completions=local_completions,
        sampling=LOCAL_SAMPLING,
        gate_result=gate_result,
        provenance_fields=provenance_fields,
        roster_entry=roster_entry,
        roster_version=loaded_roster.roster_version,
        call_path_fields=_local_call_path(),
        fiche_hash=fiche_hash_value,
        batch_fields=_local_batch_fields(settings, local_energy, local_completions),
    )

    cloud_endpoint, cloud_completions, cloud_responses = _run_cloud_suite(settings)
    _score_and_write(
        settings,
        run_id=run_id,
        model_id=mistral_client.MODEL,
        provider="mistral",
        completions=cloud_completions,
        sampling=CLOUD_SAMPLING,
        gate_result=gate_result,
        provenance_fields=provenance_fields,
        roster_entry=roster_entry,
        roster_version=loaded_roster.roster_version,
        call_path_fields=_mistral_call_path(cloud_endpoint),
        fiche_hash=fiche_hash_value,
        batch_fields=_cloud_batch_fields(settings, cloud_responses),
    )


def _local_call_path() -> dict[str, Any]:
    """The four call-path fields of the raw local `/completion` path."""
    return {
        "endpoint": prompt_provenance.LOCAL_COMPLETION_ENDPOINT,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_NONE,
        "prompt_template_hash": None,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
    }


def _mistral_call_path(endpoint: str) -> dict[str, Any]:
    """The four call-path fields of the Mistral chat path, endpoint as called.

    Built here, beside the call that produced `endpoint`, rather than derived
    from the `provider` string inside `_score_and_write`: the endpoint and the
    template that endpoint applies are one fact, and a future third provider
    must state its own rather than inherit Mistral's by falling off an `else`.
    """
    return {
        "endpoint": endpoint,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_MISTRAL_CHAT_MESSAGE,
        "prompt_template_hash": prompt_provenance.MISTRAL_CHAT_MESSAGE_HASH,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
    }


def _local_model_path(settings: Settings, roster_entry: roster.RosterEntry) -> Path:
    """Resolve the local GGUF, or raise: a missing file must cost no network call."""
    model_path = settings.slm_models_dir / roster_entry.file
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")
    return model_path


def _run_local_suite(settings: Settings, flags: list[str]) -> list[_Completion]:
    completions: list[_Completion] = []

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
            completions.append(
                _Completion(
                    content=content,
                    truncated=bool(response_json.get("stopped_limit", False)),
                    generated_tokens=response_json.get("tokens_predicted", 0),
                )
            )

    return completions


def _run_cloud_suite(
    settings: Settings,
) -> tuple[str, list[_Completion], list[MistralCompletion]]:
    # The same cap the local half runs under (`n_predict` above): the suite
    # declares one generation cap for every model it compares, and every row
    # publishes it as what that row ran under. Sending it to only one provider
    # would make the cloud rows' `max_output_tokens` a claim about a limit that
    # was never applied.
    responses = [
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
    endpoint = responses[0]["endpoint"]
    completions = [
        _Completion(
            content=response["content"],
            # Both of Mistral's cut-short reasons, not just the cap one: which
            # of the two it was is `generated_tokens` versus the suite's cap,
            # decided in `score_item`.
            truncated=response["finish_reason"]
            in mistral_client.TRUNCATING_FINISH_REASONS,
            generated_tokens=response["generated_tokens"],
        )
        for response in responses
    ]
    return endpoint, completions, responses


def _local_batch_fields(
    settings: Settings, energy: EnergyResult, completions: list[_Completion]
) -> dict[str, Any]:
    """The per-batch energy/emissions/cost fields shared by every local row.

    tokens_in_total stays null: the local `/completion` path this suite calls
    (`_run_local_suite`) never captures a prompt-token count, so publishing
    one here would fabricate it (same honesty rule `__init__.py`'s runtime
    tokens_in_total follows).
    """
    emissions_kg = emissions.local_emissions(
        energy["energy_kwh"], settings.emission_factor_kg_per_kwh
    )
    cost_total = cost.local_cost(energy["energy_kwh"], settings.kwh_price_eur)
    tokens_out_total = sum(completion["generated_tokens"] for completion in completions)
    return {
        **energy,
        "emissions_kg": emissions_kg,
        "emission_factor_kg_per_kwh": settings.emission_factor_kg_per_kwh,
        "emission_region": settings.emission_region,
        "emissions_scope": emissions.EMISSIONS_SCOPE_2,
        "emissions_scope_formula_id": None,
        "scope_comparability": None,
        "tokens_in_total": None,
        "tokens_out_total": tokens_out_total,
        "cost_total": cost_total,
        "cost_currency": "EUR",
        "cost_per_million_tokens": None,
        "normalization_unit": cost.NORMALIZATION_UNIT,
        "kwh_price_eur": settings.kwh_price_eur,
        "kwh_price_currency": "EUR",
        "kwh_price_recorded_at": settings.kwh_price_recorded_at,
        "list_price_per_million_tokens": None,
        "list_price_currency": None,
        "list_price_retrieved_at": None,
    }


def _cloud_batch_fields(
    settings: Settings, responses: list[MistralCompletion]
) -> dict[str, Any]:
    """The per-batch energy/emissions/cost fields shared by every mistral row.

    No on-machine energy exists to attribute to a network call: the three
    CodeCarbon channels stay null/"unavailable", and energy_kwh/emissions_kg
    instead come from the Scope-3 Wh-per-token formula, keyed to this batch's
    total tokens (plan.md's Decisions).
    """
    prompt_tokens_total = sum(response["prompt_tokens"] or 0 for response in responses)
    completion_tokens_total = sum(
        response["generated_tokens"] for response in responses
    )
    total_tokens = prompt_tokens_total + completion_tokens_total
    energy_kwh, emissions_kg = emissions.scope3_cloud_emissions(
        total_tokens, settings.scope3_wh_per_token, settings.emission_factor_kg_per_kwh
    )
    price = cost.MISTRAL_PRICE_TABLE[mistral_client.MODEL]
    cost_total = cost.cloud_cost(prompt_tokens_total, completion_tokens_total, price)
    # The list price for this batch's actual token mix, not a single input or
    # output rate in isolation: what the price table says this exact split of
    # prompt/completion tokens costs, cited as the derivation input cost_total
    # was computed from.
    list_price_per_million_tokens = cost_total / total_tokens * 1_000_000
    return {
        "cpu_energy_kwh": None,
        "cpu_energy_method": ENERGY_METHOD_UNAVAILABLE,
        "gpu_energy_kwh": None,
        "gpu_energy_method": ENERGY_METHOD_UNAVAILABLE,
        "ram_energy_kwh": None,
        "ram_energy_method": ENERGY_METHOD_UNAVAILABLE,
        "energy_kwh": energy_kwh,
        "emissions_kg": emissions_kg,
        "emission_factor_kg_per_kwh": settings.emission_factor_kg_per_kwh,
        "emission_region": settings.emission_region,
        "emissions_scope": emissions.EMISSIONS_SCOPE_3,
        "emissions_scope_formula_id": emissions.SCOPE3_FORMULA_ID,
        "scope_comparability": emissions.SCOPE_COMPARABILITY_NOTE,
        "tokens_in_total": prompt_tokens_total,
        "tokens_out_total": completion_tokens_total,
        "cost_total": cost_total,
        "cost_currency": price["currency"],
        "cost_per_million_tokens": cost.cost_per_million_tokens(
            cost_total, total_tokens
        ),
        "normalization_unit": cost.NORMALIZATION_UNIT,
        "kwh_price_eur": None,
        "kwh_price_currency": None,
        "kwh_price_recorded_at": None,
        "list_price_per_million_tokens": list_price_per_million_tokens,
        "list_price_currency": price["currency"],
        "list_price_retrieved_at": price["retrieved_at"],
    }


def _score_and_write(
    settings: Settings,
    *,
    run_id: str,
    model_id: str,
    provider: str,
    completions: list[_Completion],
    sampling: dict[str, Any],
    gate_result: SuiteGateResult,
    provenance_fields: dict[str, Any],
    roster_entry: roster.RosterEntry,
    roster_version: int,
    call_path_fields: dict[str, Any],
    fiche_hash: str,
    batch_fields: dict[str, Any],
) -> None:
    scored_items = [
        score_item(
            item,
            completion["content"],
            truncated=completion["truncated"],
            generated_tokens=completion["generated_tokens"],
            max_output_tokens=classification_suite.MAX_OUTPUT_TOKENS,
        )
        for item, completion in zip(CLASSIFICATION_TASK_SUITE, completions, strict=True)
    ]
    suite_score = score_suite(scored_items)
    suite_accuracy = suite_score["accuracy"]
    failure_counts = suite_score["failure_counts"]

    rows: list[dict[str, Any]] = []
    for item, scored in zip(CLASSIFICATION_TASK_SUITE, scored_items, strict=True):
        row = {
            "schema_version": row_contract.SCHEMA_VERSION,
            "run_id": run_id,
            "captured_at": captured_at(),
            **provenance_fields,
            "roster_entry_id": roster_entry.entry_id,
            "roster_version": roster_version,
            **call_path_fields,
            "model_id": model_id,
            "provider": provider,
            "fiche_hash": fiche_hash,
            **batch_fields,
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
            "failure_reason": scored["failure_reason"],
            "failure_counts": dict(failure_counts),
        }
        rows.append(row)

    # The verdict is per suite-run, not per item: every row of this
    # (model, provider) batch shares it, the same pattern suite_accuracy
    # already uses.
    reference_rows = [
        row
        for row in results.read_rows(settings.quality_reference_path)
        if row.get("model_id") == model_id
    ]
    batch_verdict = verdict.quality_verdict(rows, reference_rows)
    for row in rows:
        row["verdict"] = batch_verdict
        append_row(settings.quality_results_path, "quality", row)

    print(f"model={model_id} provider={provider} accuracy={suite_accuracy:.2f}")
