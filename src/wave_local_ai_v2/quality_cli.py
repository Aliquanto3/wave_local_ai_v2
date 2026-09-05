"""CLI entry point: score the classification task suite against one local SLM
and two cloud models, writing one quality row per (task, model).

Deliberately collects none of the runtime harness's fields (fiche, timings,
GPU stats, energy): a quality row must be readable on its own, without any
hardware or runtime context, and vice versa (`aidd_docs/memory/architecture.md`:
"the two are never merged into a single table").

The two cloud providers share one dispatch shape (`_run_cloud_batch`, fed a
provider-specific per-item completion function, call-path builder and price
table) rather than two copy-pasted `_run_..._suite`/`_..._call_path`/
`_..._batch_fields` triplets -- the cloud subject is selectable by provider,
not hard-wired to Mistral.

The provider *set* is itself configuration (`settings.QUALITY_PROVIDERS`).
Both cloud providers are optional: a provider absent from that set, missing
its API key, or failing its pre-flight/batch call (`_try_run_cloud_provider`,
keyed by `_CLOUD_PROVIDERS`) is skipped with one stderr line rather than
aborting the run -- the local batch is the only one whose own failure still
does. This was a live-run finding: this project's Mistral workspace sits on
the Free tier, whose rate floor 429s a request burst like this suite's
20-item loop; a provider that fails there should not discard local rows that
already succeeded.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypedDict

import requests

from wave_local_ai_v2 import (
    build_probe,
    classification_suite,
    cost,
    emissions,
    fiche_registry,
    google_client,
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
from wave_local_ai_v2.classification_suite import (
    CLASSIFICATION_TASK_SUITE,
    ClassificationItem,
)
from wave_local_ai_v2.energy import (
    ENERGY_METHOD_UNAVAILABLE,
    EnergyResult,
    measure_energy,
)
from wave_local_ai_v2.hardware import build_fiche, capture_fiche
from wave_local_ai_v2.mistral_client import MistralCompletion, MistralRequestError
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.scoring import (
    FAILURE_REASON_TRUNCATED_CONTEXT,
    FAILURE_REASON_TRUNCATED_MAX_TOKENS,
    score_item,
    score_suite,
    score_suite_by_language,
)
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

# Distinct keys from both existing sampling blocks (parity with the
# "random_seed" not in sampling / "presence_penalty" not in sampling test
# pattern): a google row's sampling block is never confusable with a local or
# mistral one just by inspecting its keys. temperature 0 alone is not
# reproducible on this provider -- the seed is what makes it so.
GOOGLE_SAMPLING: dict[str, Any] = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 1,
    "seed": QUALITY_SEED,
}


class LocalCompletionError(RuntimeError):
    """Raised when a local llama-server /completion response has no usable content."""


class _Completion(TypedDict):
    """One provider's per-item generation, unified across local and cloud shapes."""

    content: str
    truncated: bool
    generated_tokens: int
    # None on every existing (local, mistral) call site, which keeps today's
    # generated_tokens >= max_output_tokens comparison in score_item.
    # Google's own call site sets this directly off finishReason / the
    # context pre-flight, since that comparison misclassifies its responses.
    truncation_reason: str | None


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
        # MistralRequestError and google_client.GoogleRequestError are
        # deliberately absent here: both cloud providers are optional and
        # `_try_run_cloud_provider` catches its own provider's error type
        # internally, printing a skip line rather than letting it reach main.
        # Only a local-suite failure still aborts the whole run.
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
    # Loaded once per run, not once per row: raises before any HTTP call is made.
    loaded_roster = roster.load_roster(settings.roster_path)
    roster_entry = roster.resolve_entry(loaded_roster, settings.roster_entry_id)
    model_path = _local_model_path(settings, roster_entry)
    # Offline, cheap: a refused suite (missing/inconsistent tags) must abort
    # before the multi-minute local run, let alone any network call.
    gate_result = suite_gate.gate_suite(CLASSIFICATION_TASK_SUITE)

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

    for provider in ("mistral", "google"):
        _try_run_cloud_provider(
            provider,
            settings,
            run_id=run_id,
            gate_result=gate_result,
            provenance_fields=provenance_fields,
            roster_entry=roster_entry,
            roster_version=loaded_roster.roster_version,
            fiche_hash=fiche_hash_value,
        )


def _mistral_batch(
    settings: Settings, api_key: str
) -> tuple[
    str, dict[str, Any], list[_Completion], dict[str, Any], dict[str, Any], None
]:
    deprecation_notice = mistral_client.check_model_available(api_key)
    if deprecation_notice:
        # A retirement date is news, not a failure: the model still answers
        # until then. stderr keeps stdout to the accuracy lines the operator
        # parses.
        print(deprecation_notice, file=sys.stderr)
    completions, call_path_fields, batch_fields, _ = _run_cloud_batch(
        settings,
        api_key,
        mistral_client.MODEL,
        cost.PRICE_TABLES["mistral"],
        _mistral_complete_item,
        _mistral_call_path,
    )
    return (
        mistral_client.MODEL,
        CLOUD_SAMPLING,
        completions,
        call_path_fields,
        batch_fields,
        None,
    )


def _google_batch(
    settings: Settings, api_key: str
) -> tuple[
    str,
    dict[str, Any],
    list[_Completion],
    dict[str, Any],
    dict[str, Any],
    list[dict[str, Any]],
]:
    model_info = google_client.check_model_available(api_key)
    completions, call_path_fields, batch_fields, extra_row_fields = _run_cloud_batch(
        settings,
        api_key,
        google_client.MODEL,
        cost.PRICE_TABLES["google"],
        _make_google_complete_item(model_info),
        _google_call_path,
        extra_row_fields_fn=lambda response: _google_extra_fields(response, model_info),
    )
    return (
        google_client.MODEL,
        GOOGLE_SAMPLING,
        completions,
        call_path_fields,
        batch_fields,
        extra_row_fields,
    )


# The one dispatch table both cloud providers run through: an api-key getter,
# the env var name to name in a skip line, the request-error type that means
# "this provider failed, skip it" (never abort the run), and the batch runner
# itself (pre-flight + suite loop, in one function so a mid-batch failure --
# Google's GoogleBlockedError included -- is caught by the same except clause
# as a pre-flight failure and never partially writes a row).
_CLOUD_PROVIDERS: dict[str, dict[str, Any]] = {
    "mistral": {
        "api_key": lambda settings: settings.mistral_api_key,
        "env_var": "MISTRAL_API_KEY",
        "error_type": MistralRequestError,
        "run_batch": _mistral_batch,
    },
    "google": {
        "api_key": lambda settings: settings.google_api_key,
        "env_var": "GOOGLE_API_KEY",
        "error_type": google_client.GoogleRequestError,
        "run_batch": _google_batch,
    },
}


def _try_run_cloud_provider(
    provider: str,
    settings: Settings,
    *,
    run_id: str,
    gate_result: SuiteGateResult,
    provenance_fields: dict[str, Any],
    roster_entry: roster.RosterEntry,
    roster_version: int,
    fiche_hash: str,
) -> None:
    """Run one cloud provider's batch, or skip it with one stderr line.

    A configured provider whose key is missing or whose pre-flight/batch call
    fails is skipped, never aborts the run: this is what makes the quality
    CLI's cloud provider set configuration rather than two hard-wired,
    all-or-nothing calls. Nothing about a skipped provider lands in the rows.
    """
    spec = _CLOUD_PROVIDERS[provider]
    if provider not in settings.quality_providers:
        print(f"{provider} skipped: not enabled in QUALITY_PROVIDERS", file=sys.stderr)
        return

    api_key = spec["api_key"](settings)
    if not api_key:
        print(f"{provider} skipped: {spec['env_var']} is not set", file=sys.stderr)
        return

    try:
        (
            model_id,
            sampling,
            completions,
            call_path_fields,
            batch_fields,
            extra_row_fields,
        ) = spec["run_batch"](settings, api_key)
    except spec["error_type"] as exc:
        print(f"{provider} skipped: {exc}", file=sys.stderr)
        return

    _score_and_write(
        settings,
        run_id=run_id,
        model_id=model_id,
        provider=provider,
        completions=completions,
        sampling=sampling,
        gate_result=gate_result,
        provenance_fields=provenance_fields,
        roster_entry=roster_entry,
        roster_version=roster_version,
        call_path_fields=call_path_fields,
        fiche_hash=fiche_hash,
        batch_fields=batch_fields,
        extra_row_fields=extra_row_fields,
    )


def _local_call_path() -> dict[str, Any]:
    """The four call-path fields of the raw local `/completion` path."""
    return {
        "endpoint": prompt_provenance.LOCAL_COMPLETION_ENDPOINT,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_NONE,
        "prompt_template_hash": None,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
    }


def _mistral_call_path(responses: list[MistralCompletion]) -> dict[str, Any]:
    """The four call-path fields of the Mistral chat path, endpoint as called.

    Built from the batch's own responses rather than a module constant: the
    endpoint and the template that endpoint applies are one fact, sourced
    from the module that actually made the call.
    """
    return {
        "endpoint": responses[0]["endpoint"],
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_MISTRAL_CHAT_MESSAGE,
        "prompt_template_hash": prompt_provenance.MISTRAL_CHAT_MESSAGE_HASH,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
    }


def _google_call_path(
    _responses: list[google_client.GoogleCompletion | None],
) -> dict[str, Any]:
    """The four call-path fields of the Google generateContent path.

    The endpoint is a fixed module constant here, unlike Mistral's: every
    Google call in a batch hits the same URL, including the items whose
    response is None (a context-fits refusal never reaches generateContent,
    but the row still names the endpoint the batch as a whole targets).
    """
    return {
        "endpoint": google_client.GENERATE_URL,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_GOOGLE_CHAT_MESSAGE,
        "prompt_template_hash": prompt_provenance.GOOGLE_CHAT_MESSAGE_HASH,
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
                    truncation_reason=None,
                )
            )

    return completions


def _mistral_complete_item(
    item: ClassificationItem, api_key: str
) -> tuple[_Completion, MistralCompletion]:
    # The same cap the local half runs under (`n_predict` above): the suite
    # declares one generation cap for every model it compares, and every row
    # publishes it as what that row ran under. Sending it to only one provider
    # would make the cloud rows' `max_output_tokens` a claim about a limit that
    # was never applied.
    response = mistral_client.complete_prompt(
        item["prompt"],
        api_key,
        temperature=CLOUD_SAMPLING["temperature"],
        random_seed=CLOUD_SAMPLING["random_seed"],
        max_tokens=classification_suite.MAX_OUTPUT_TOKENS,
    )
    completion = _Completion(
        content=response["content"],
        # Both of Mistral's cut-short reasons, not just the cap one: which of
        # the two it was is `generated_tokens` versus the suite's cap,
        # decided in `score_item`'s default comparison (no override here).
        truncated=response["finish_reason"] in mistral_client.TRUNCATING_FINISH_REASONS,
        generated_tokens=response["generated_tokens"],
        truncation_reason=None,
    )
    return completion, response


def _make_google_complete_item(
    model_info: google_client.GoogleModelInfo,
) -> Callable[
    [ClassificationItem, str], tuple[_Completion, google_client.GoogleCompletion | None]
]:
    """Build this batch's per-item completion function, closed over `model_info`.

    A closure, not a plain function, because Google's per-item call needs the
    pre-flight's `input_token_limit` -- known only after `check_model_available`
    runs, once per batch, not once per item.
    """

    def complete_item(
        item: ClassificationItem, api_key: str
    ) -> tuple[_Completion, google_client.GoogleCompletion | None]:
        try:
            google_client.check_context_fits(
                item["prompt"], api_key, model_info["input_token_limit"]
            )
        except google_client.ContextWindowExceededError:
            # Refused pre-flight, never sent to generateContent: this is the
            # only place `truncated_context` can honestly originate from on
            # this provider (free-tier context overflow never surfaces as a
            # finishReason -- the input-token quota's 429 always fires first).
            # Non-blank placeholder content: score_item checks blankness
            # before truncation, so an empty string here would score `empty`
            # instead of the truncation_reason override below. Never
            # published on the row -- score_item only reads it to decide the
            # failure taxonomy.
            return (
                _Completion(
                    content="[context window exceeded, no generateContent call made]",
                    truncated=True,
                    generated_tokens=0,
                    truncation_reason=FAILURE_REASON_TRUNCATED_CONTEXT,
                ),
                None,
            )

        response = google_client.complete_prompt(
            item["prompt"],
            api_key,
            temperature=GOOGLE_SAMPLING["temperature"],
            top_p=GOOGLE_SAMPLING["top_p"],
            top_k=GOOGLE_SAMPLING["top_k"],
            seed=GOOGLE_SAMPLING["seed"],
            max_tokens=classification_suite.MAX_OUTPUT_TOKENS,
        )
        # Read off finishReason directly, never generated_tokens versus the
        # cap: Google can report fewer generated tokens than the cap it
        # actually enforced, which would misclassify a cap-truncated item as
        # context-truncated under score_item's default comparison.
        truncated = response["finish_reason"] == "MAX_TOKENS"
        completion = _Completion(
            content=response["content"],
            truncated=truncated,
            generated_tokens=response["generated_tokens"],
            truncation_reason=(
                FAILURE_REASON_TRUNCATED_MAX_TOKENS if truncated else None
            ),
        )
        return completion, response

    return complete_item


def _google_extra_fields(
    response: google_client.GoogleCompletion | None,
    model_info: google_client.GoogleModelInfo,
) -> dict[str, Any]:
    """The two non-required keys a google row carries beyond every other row's.

    `model_version` falls back to the pre-flight's catalog `version` when the
    response omitted `modelVersion` -- including when there was no response
    at all (a context-fits refusal): the row still names the build the batch
    ran against.
    """
    model_version = response["model_version"] if response is not None else None
    return {
        "model_version": model_version or model_info["version"],
        "api_version": "v1",
    }


def _run_cloud_batch(
    settings: Settings,
    api_key: str,
    model: str,
    price_table: dict[str, cost.Price],
    complete_item: Callable[[ClassificationItem, str], tuple[_Completion, Any]],
    call_path_fields_fn: Callable[[list[Any]], dict[str, Any]],
    extra_row_fields_fn: Callable[[Any], dict[str, Any]] = lambda _response: {},
) -> tuple[list[_Completion], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Run one cloud provider's suite loop, then derive its call-path and cost fields.

    The one dispatch shape both cloud providers run through: `complete_item`
    supplies the provider-specific per-item call, everything after the loop
    (call-path identity, cost/energy) is generic over the raw responses it
    collected. A `None` response (Google's context-fits refusal) costs
    nothing -- known-zero, not unknown -- rather than making the whole
    batch's token total undefined.
    """
    completions: list[_Completion] = []
    responses: list[Any] = []
    for item in CLASSIFICATION_TASK_SUITE:
        completion, response = complete_item(item, api_key)
        completions.append(completion)
        responses.append(response)

    prompt_tokens = [
        response["prompt_tokens"] if response is not None else 0
        for response in responses
    ]
    completion_tokens_total = sum(
        response["generated_tokens"] if response is not None else 0
        for response in responses
    )
    batch_fields = _cloud_batch_fields(
        settings, model, price_table, prompt_tokens, completion_tokens_total
    )
    call_path_fields = call_path_fields_fn(responses)
    extra_row_fields = [extra_row_fields_fn(response) for response in responses]
    return completions, call_path_fields, batch_fields, extra_row_fields


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
        # Derived, not hardcoded null: total_tokens is unknown while
        # tokens_in_total is, so the rate is undefined today -- but it starts
        # publishing on its own the day the local path captures prompt tokens.
        "cost_per_million_tokens": cost.cost_per_million_tokens(cost_total, None),
        "normalization_unit": cost.NORMALIZATION_UNIT,
        "kwh_price_eur": settings.kwh_price_eur,
        "kwh_price_currency": "EUR",
        "kwh_price_recorded_at": settings.kwh_price_recorded_at,
        "list_price_input_per_million": None,
        "list_price_output_per_million": None,
        "list_price_per_million_tokens": None,
        "list_price_currency": None,
        "list_price_retrieved_at": None,
    }


def _cloud_batch_fields(
    settings: Settings,
    model: str,
    price_table: dict[str, cost.Price],
    prompt_tokens: list[int | None],
    completion_tokens_total: int,
) -> dict[str, Any]:
    """The per-batch energy/emissions/cost fields shared by every cloud row.

    Generic over `model`/`price_table` so one function serves both Mistral
    and Google rather than being copy-pasted per provider (plan.md's
    Decisions). No on-machine energy exists to attribute to a network call:
    the three CodeCarbon channels stay null/"unavailable", and
    energy_kwh/emissions_kg instead come from the Scope-3 Wh-per-token
    formula, keyed to this batch's total tokens.

    A `None` entry in `prompt_tokens` (an absent count on a real response)
    makes the batch's input token count unknown, not zero: every figure keyed
    to a token total -- the Scope-3 energy and emissions estimate, the cost,
    the normalized rate -- degrades to `None` rather than silently pricing
    the prompts at nothing. The price snapshot itself still lands on the row:
    it is what the provider charges, not something this batch derived.
    """
    prompt_tokens_total = cost.total_or_none(prompt_tokens)
    total_tokens = (
        prompt_tokens_total + completion_tokens_total
        if prompt_tokens_total is not None
        else None
    )
    price = price_table[model]
    if total_tokens is None or prompt_tokens_total is None:
        energy_kwh: float | None = None
        emissions_kg: float | None = None
        cost_total: float | None = None
    else:
        energy_kwh, emissions_kg = emissions.scope3_cloud_emissions(
            total_tokens,
            settings.scope3_wh_per_token,
            settings.emission_factor_kg_per_kwh,
        )
        cost_total = cost.cloud_cost(
            prompt_tokens_total, completion_tokens_total, price
        )
    # Three price figures, not one: the two rates the table actually charges,
    # so a reader can recompute cost_total from tokens_in_total and
    # tokens_out_total a year later, plus the blended rate this batch's own
    # token mix worked out to. The blend alone is derived FROM cost_total, so
    # publishing only it would be circular.
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
        # The currency the price table quotes, published even when cost_total
        # is null: it names the unit the list-price fields beside it are in.
        "cost_currency": price["currency"],
        "cost_per_million_tokens": cost.cost_per_million_tokens(
            cost_total, total_tokens
        ),
        "normalization_unit": cost.NORMALIZATION_UNIT,
        "kwh_price_eur": None,
        "kwh_price_currency": None,
        "kwh_price_recorded_at": None,
        "list_price_input_per_million": price["input_per_million"],
        "list_price_output_per_million": price["output_per_million"],
        "list_price_per_million_tokens": cost.cost_per_million_tokens(
            cost_total, total_tokens
        ),
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
    extra_row_fields: list[dict[str, Any]] | None = None,
) -> None:
    scored_items = [
        score_item(
            item,
            completion["content"],
            truncated=completion["truncated"],
            generated_tokens=completion["generated_tokens"],
            max_output_tokens=classification_suite.MAX_OUTPUT_TOKENS,
            truncation_reason=completion["truncation_reason"],
        )
        for item, completion in zip(CLASSIFICATION_TASK_SUITE, completions, strict=True)
    ]
    suite_score = score_suite(scored_items)
    suite_accuracy = suite_score["accuracy"]
    failure_counts = suite_score["failure_counts"]
    language_breakdown = score_suite_by_language(
        CLASSIFICATION_TASK_SUITE, scored_items
    )

    rows: list[dict[str, Any]] = []
    for index, (item, scored) in enumerate(
        zip(CLASSIFICATION_TASK_SUITE, scored_items, strict=True)
    ):
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
            "language_breakdown": language_breakdown,
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
        # Extra, non-required keys (google rows' model_version/api_version):
        # applied after every contract field, never overriding one.
        if extra_row_fields is not None:
            row.update(extra_row_fields[index])
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
