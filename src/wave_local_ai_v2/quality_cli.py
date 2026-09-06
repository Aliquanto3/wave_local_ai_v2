"""CLI entry point: score one selectable task suite against one local SLM and
two cloud models, writing one quality row per (task, model).

`--suite` picks the suite; the provider set stays configuration
(`settings.QUALITY_PROVIDERS`). The two suites publish two different score
shapes on purpose: classification is scored by exact label match and
publishes `suite_accuracy`, translation is scored against a written
reference by chrF and publishes a graded block. One row never carries both
(`row_contract._validate_graded_structure`), because a reader picking up
"the score column" would otherwise be reading an accuracy half the time and
a character-n-gram F-score the other half.

`_SUITES` is a two-entry dispatch table, not a registry: the full suite
registry belongs to the `no-use-case-is-silently-absent` story, and this is
the minimum that stops the CLI being hard-wired to one suite -- the same
discipline `_CLOUD_PROVIDERS` follows for providers.

Deliberately collects none of the runtime harness's fields (fiche, timings,
GPU stats, energy): a quality row must be readable on its own, without any
hardware or runtime context, and vice versa (`aidd_docs/memory/architecture.md`:
"the two are never merged into a single table").

The two cloud providers share one dispatch shape (`_run_cloud_batch`, fed a
provider-specific per-item completion function, call-path builder and price
table) rather than two copy-pasted `_run_..._suite`/`_..._call_path`/batch-fields
triplets -- the cloud subject is selectable by provider, not hard-wired to
Mistral. The batch-fields builders themselves live in `quality_rows.py`, shared
with the judge probe's own two batches.

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

import argparse
import sys
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypedDict

import requests

from wave_local_ai_v2 import (
    build_probe,
    chrf,
    classification_suite,
    cost,
    fiche_registry,
    google_client,
    mistral_client,
    prompt_provenance,
    provenance,
    quality_rows,
    results,
    retry,
    roster,
    row_contract,
    server,
    suite_gate,
    translation_suite,
    verdict,
)
from wave_local_ai_v2.classification_suite import CLASSIFICATION_TASK_SUITE
from wave_local_ai_v2.energy import measure_energy
from wave_local_ai_v2.hardware import build_fiche, capture_fiche
from wave_local_ai_v2.mistral_client import MistralCompletion, MistralRequestError
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.scoring import (
    FAILURE_REASON_TRUNCATED_CONTEXT,
    FAILURE_REASON_TRUNCATED_MAX_TOKENS,
    score_graded_suite,
    score_graded_suite_by_language,
    score_item,
    score_suite,
    score_suite_by_language,
    score_translation_item,
)
from wave_local_ai_v2.settings import Settings, SettingsError, load_settings
from wave_local_ai_v2.suite_gate import SuiteGateError, SuiteGateResult
from wave_local_ai_v2.translation_suite import TRANSLATION_TASK_SUITE

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

# The exponential-backoff base for a retryable cloud failure with no
# provider-supplied retry hint (retry.call_with_retry's base_delay_s). Not a
# settings field: the pacing interval already governs steady-state request
# spacing, this only shapes how quickly a single item's retries widen.
_RETRY_BASE_DELAY_S = 1.0


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
    # Retries `retry.call_with_retry` took to produce this item's completion.
    # 0 for local, which never retries (no `RetryableRequestError` type exists
    # for the local /completion path).
    retries: int


# A suite item, as everything downstream of the suite module needs it: a
# mapping exposing `item_id`, `prompt` and the gate's tags. Duck-typed rather
# than one suite's TypedDict, the same choice `suite_gate.gate_suite` and
# `classification_suite.prompt_set_hash` already document -- the two suites
# carry different item shapes and neither is the CLI's business.
SuiteItem = Mapping[str, Any]

# One batch's scoring, as a suite supplies it: the items and their
# completions in, one dict of row fields per item plus one dict shared by the
# whole batch out. Everything suite-specific about a score lives behind this
# one callable, which is why the row builder below reads the same for an
# exact-match row and a graded one.
ScoreBatch = Callable[
    [Sequence[SuiteItem], list[_Completion]],
    tuple[list[dict[str, Any]], dict[str, Any]],
]


@dataclass(frozen=True)
class SuiteSpec:
    """One selectable suite: its identity, its caps, its items, its scorer."""

    task_suite: str
    items: Sequence[SuiteItem]
    suite_id: str
    suite_version: str
    prompt_set_hash: str
    max_output_tokens: int
    stop_sequences: list[str]
    context_length: int
    score_batch: ScoreBatch


def _score_classification_batch(
    items: Sequence[Any], completions: list[_Completion]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Exact-label-match scoring: today's fields, and no graded block."""
    scored_items = [
        score_item(
            item,
            completion["content"],
            truncated=completion["truncated"],
            generated_tokens=completion["generated_tokens"],
            max_output_tokens=classification_suite.MAX_OUTPUT_TOKENS,
            truncation_reason=completion["truncation_reason"],
        )
        for item, completion in zip(items, completions, strict=True)
    ]
    suite_score = score_suite(scored_items)
    per_item = [
        {
            "expected_label": scored["expected_label"],
            "predicted_label": scored["predicted_label"],
            "correct": scored["correct"],
            "failure_reason": scored["failure_reason"],
        }
        for scored in scored_items
    ]
    batch = {
        "suite_accuracy": suite_score["accuracy"],
        "language_breakdown": score_suite_by_language(items, scored_items),
        "failure_counts": dict(suite_score["failure_counts"]),
    }
    return per_item, batch


def _score_translation_batch(
    items: Sequence[Any], completions: list[_Completion]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """chrF scoring against each item's written reference.

    Every row carries `reference_output` beside its `subject_output` and the
    metric parameters the score ran under, so a reader who disputes a number
    can recompute it with sacreBLEU rather than take it on trust. The
    exact-match fields are explicitly nulled: `correct` is a boolean, a chrF
    is not, and `suite_accuracy` names an exact-match rate this suite never
    computed.
    """
    graded_items = [
        score_translation_item(
            item,
            completion["content"],
            truncated=completion["truncated"],
            generated_tokens=completion["generated_tokens"],
            max_output_tokens=translation_suite.MAX_OUTPUT_TOKENS,
            truncation_reason=completion["truncation_reason"],
        )
        for item, completion in zip(items, completions, strict=True)
    ]
    suite_score = score_graded_suite(graded_items)
    per_item = [
        {
            "expected_label": None,
            "predicted_label": None,
            "correct": None,
            "failure_reason": graded["failure_reason"],
            "item_score": graded["item_score"],
            "subject_output": completion["content"],
            "reference_output": item["reference"],
            "metric_id": chrf.METRIC_ID,
            "metric_version": chrf.METRIC_VERSION,
            # Copied, never shared: `chrf.METRIC_PARAMS` is one frozen object
            # and each row owns its own plain dict of it.
            "metric_params": dict(chrf.METRIC_PARAMS),
        }
        for item, completion, graded in zip(
            items, completions, graded_items, strict=True
        )
    ]
    batch = {
        "suite_accuracy": None,
        "language_breakdown": None,
        "suite_score": suite_score["suite_score"],
        "score_breakdown": score_graded_suite_by_language(items, graded_items),
        "failure_counts": dict(suite_score["failure_counts"]),
    }
    return per_item, batch


# Exactly two entries, built from the two suite modules. The boundary is
# deliberate: a suite registry -- discovery, per-suite config, a manifest --
# belongs to `no-use-case-is-silently-absent.md`. This is a literal dict, and
# adding a third suite here is meant to feel like the moment to build that.
_SUITES: dict[str, SuiteSpec] = {
    "classification": SuiteSpec(
        task_suite="classification",
        items=CLASSIFICATION_TASK_SUITE,
        suite_id=classification_suite.SUITE_ID,
        suite_version=classification_suite.SUITE_VERSION,
        prompt_set_hash=classification_suite.PROMPT_SET_HASH,
        max_output_tokens=classification_suite.MAX_OUTPUT_TOKENS,
        stop_sequences=classification_suite.STOP_SEQUENCES,
        context_length=classification_suite.CONTEXT_LENGTH,
        score_batch=_score_classification_batch,
    ),
    "translation": SuiteSpec(
        task_suite="translation",
        items=TRANSLATION_TASK_SUITE,
        suite_id=translation_suite.SUITE_ID,
        suite_version=translation_suite.SUITE_VERSION,
        prompt_set_hash=translation_suite.PROMPT_SET_HASH,
        max_output_tokens=translation_suite.MAX_OUTPUT_TOKENS,
        stop_sequences=translation_suite.STOP_SEQUENCES,
        context_length=translation_suite.CONTEXT_LENGTH,
        score_batch=_score_translation_batch,
    ),
}

DEFAULT_SUITE = "classification"


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="wave-local-ai-v2-quality")
    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        default=None,
        help=(
            "Resume a prior invocation's run_id: a provider whose rows for "
            "that run_id and this suite are already complete is skipped, "
            "never re-paid for; an incomplete one is re-run from item 1. "
            "Every row this invocation writes is marked resumed=true, "
            "including a provider resume re-ran from scratch."
        ),
    )
    parser.add_argument(
        "--suite",
        choices=list(_SUITES),
        default=DEFAULT_SUITE,
        help=(
            "Which task suite to score. 'classification' routes support "
            "messages to one of four labels and publishes an exact-match "
            "accuracy; 'translation' translates short business sentences in "
            "three directions and publishes a chrF score against a written "
            "reference. Default: %(default)s."
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    try:
        _run(resume_run_id=args.resume, suite=args.suite)
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


def _run(resume_run_id: str | None = None, suite: str = DEFAULT_SUITE) -> None:
    spec = _SUITES[suite]
    settings = load_settings()
    # One id for the whole invocation: the local and cloud batches are two
    # halves of one comparison, and a reader must be able to tell which local
    # rows a given cloud row was scored against. `--resume` reuses a prior
    # invocation's id instead of minting a fresh one, so a provider's rows
    # from that earlier invocation are recognizable as the same run.
    run_id = resume_run_id or new_run_id()
    is_resume = resume_run_id is not None
    provenance_fields = provenance.capture_provenance()
    # Loaded once per run, not once per row: raises before any HTTP call is made.
    loaded_roster = roster.load_roster(settings.roster_path)
    roster_entry = roster.resolve_entry(loaded_roster, settings.roster_entry_id)
    model_path = _local_model_path(settings, roster_entry)
    # Offline, cheap: a refused suite (missing/inconsistent tags) must abort
    # before the multi-minute local run, let alone any network call.
    gate_result = suite_gate.gate_suite(spec.items)

    # Refuses (roster.RosterError) before any process spawns when the
    # resolved n_cpu_moe cannot be applied to roster_entry -- the check lives
    # inside build_flags itself (server.py's one call site), and it runs on
    # the resolved value: settings.host_n_cpu_moe when set, the entry's own
    # validated_host value when unset.
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

    # `--resume` on a run_id whose local rows are already all on disk skips the
    # local batch entirely, before the server is even launched: the fiche
    # above is still built (cheap, no process spawn) because the cloud
    # batches below cite the same fiche_hash regardless of whether local ran
    # this invocation.
    local_skip_reason = (
        results.resume_skip_reason(
            settings.quality_results_path,
            run_id,
            "local",
            len(spec.items),
            task_suite=spec.task_suite,
        )
        if is_resume
        else None
    )
    if local_skip_reason is not None:
        print(f"local skipped: {local_skip_reason}", file=sys.stderr)
    else:
        # The tracker spans the whole suite loop (server launch, every item,
        # the server's own teardown when the `with` block exits), not per
        # item -- the same span `__init__.py`'s runtime harness measures
        # over, and the same repeated-batch-value pattern `suite_accuracy`
        # already uses.
        local_completions, local_energy = measure_energy(
            lambda: _run_local_suite(settings, flags, spec),
            country_iso_code=settings.emission_country_iso_code,
        )
        # Persisted before the cloud suite starts: a 429, a dropped connection
        # or a malformed body would otherwise throw away the multi-minute
        # local run and write zero rows. Both batches share one run_id, so a
        # partial run is still recognizable as one session.
        _score_and_write(
            settings,
            spec=spec,
            run_id=run_id,
            # The entry the local half actually launched names itself: a row
            # can never report one model while its `roster_entry_id` cites
            # another.
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
            batch_fields=quality_rows.local_batch_fields(
                settings, local_energy, local_completions
            ),
            resumed=is_resume,
        )

    for provider in ("mistral", "google"):
        _try_run_cloud_provider(
            provider,
            settings,
            spec=spec,
            run_id=run_id,
            is_resume=is_resume,
            gate_result=gate_result,
            provenance_fields=provenance_fields,
            roster_entry=roster_entry,
            roster_version=loaded_roster.roster_version,
            fiche_hash=fiche_hash_value,
        )


def _mistral_batch(
    settings: Settings, api_key: str, spec: SuiteSpec
) -> tuple[
    str, dict[str, Any], list[_Completion], dict[str, Any], dict[str, Any], None
]:
    deprecation_notice = mistral_client.check_model_available(api_key)
    if deprecation_notice:
        # A retirement date is news, not a failure: the model still answers
        # until then. stderr keeps stdout to the score lines the operator
        # parses.
        print(deprecation_notice, file=sys.stderr)
    completions, call_path_fields, batch_fields, _ = _run_cloud_batch(
        settings,
        api_key,
        spec,
        mistral_client.MODEL,
        cost.PRICE_TABLES["mistral"],
        _make_mistral_complete_item(settings, spec.max_output_tokens),
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
    settings: Settings, api_key: str, spec: SuiteSpec
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
        spec,
        google_client.MODEL,
        cost.PRICE_TABLES["google"],
        _make_google_complete_item(model_info, settings, spec.max_output_tokens),
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
    spec: SuiteSpec,
    run_id: str,
    is_resume: bool,
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
    provider_spec = _CLOUD_PROVIDERS[provider]
    if provider not in settings.quality_providers:
        print(f"{provider} skipped: not enabled in QUALITY_PROVIDERS", file=sys.stderr)
        return

    api_key = provider_spec["api_key"](settings)
    if not api_key:
        print(
            f"{provider} skipped: {provider_spec['env_var']} is not set",
            file=sys.stderr,
        )
        return

    skip_reason = (
        results.resume_skip_reason(
            settings.quality_results_path,
            run_id,
            provider,
            len(spec.items),
            task_suite=spec.task_suite,
        )
        if is_resume
        else None
    )
    if skip_reason is not None:
        print(f"{provider} skipped: {skip_reason}", file=sys.stderr)
        return

    try:
        (
            model_id,
            sampling,
            completions,
            call_path_fields,
            batch_fields,
            extra_row_fields,
        ) = provider_spec["run_batch"](settings, api_key, spec)
    except (
        provider_spec["error_type"],
        requests.RequestException,
        # A retry-budget exhaustion is this provider still failing, the same
        # way a 429 that outlives its own retries always was -- caught
        # alongside the provider's own error type and requests.RequestException
        # rather than reaching main's OSError clause and aborting the run.
        retry.RetryBudgetExhausted,
    ) as exc:
        print(f"{provider} skipped: {exc}", file=sys.stderr)
        return

    _score_and_write(
        settings,
        spec=spec,
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
        resumed=is_resume,
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


def _run_local_suite(
    settings: Settings, flags: list[str], spec: SuiteSpec
) -> list[_Completion]:
    completions: list[_Completion] = []

    with server.running_server(settings.llama_server_path, flags):
        for item in spec.items:
            response = requests.post(
                f"http://{server.HOST}:{server.PORT}/completion",
                json={
                    "prompt": item["prompt"],
                    "n_predict": spec.max_output_tokens,
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
                    retries=0,
                )
            )

    return completions


def _make_mistral_complete_item(
    settings: Settings, max_output_tokens: int
) -> Callable[[SuiteItem, str], tuple[_Completion, MistralCompletion]]:
    """Build this batch's per-item completion function, closed over one Pacer/RetryBudget pair.

    A closure, not a plain function: a `Pacer` and a `RetryBudget` are built
    once per batch and shared across every item, the same reason Google's
    counterpart is a closure over `model_info`. The budget is run-scoped, not
    per-item -- a batch's retries are spent as a shared pool.
    """
    pacer = retry.Pacer(settings.mistral_request_pacing_s, sleep=time.sleep)
    budget = retry.RetryBudget(settings.cloud_retry_max_attempts)

    def _is_retryable(exc: Exception) -> bool:
        return isinstance(exc, mistral_client.RetryableRequestError)

    def _retry_hint_s(exc: Exception) -> float | None:
        return (
            exc.retry_after_s
            if isinstance(exc, mistral_client.RetryableRequestError)
            else None
        )

    def complete_item(
        item: SuiteItem, api_key: str
    ) -> tuple[_Completion, MistralCompletion]:
        pacer.wait()
        # The same cap the local half runs under (`n_predict` above): the
        # suite declares one generation cap for every model it compares, and
        # every row publishes it as what that row ran under. Sending it to
        # only one provider would make the cloud rows' `max_output_tokens` a
        # claim about a limit that was never applied.
        response, retries_taken = retry.call_with_retry(
            lambda: mistral_client.complete_prompt(
                item["prompt"],
                api_key,
                temperature=CLOUD_SAMPLING["temperature"],
                random_seed=CLOUD_SAMPLING["random_seed"],
                max_tokens=max_output_tokens,
            ),
            is_retryable=_is_retryable,
            retry_hint_s=_retry_hint_s,
            budget=budget,
            base_delay_s=_RETRY_BASE_DELAY_S,
            sleep=time.sleep,
        )
        completion = _Completion(
            content=response["content"],
            # Both of Mistral's cut-short reasons, not just the cap one: which
            # of the two it was is `generated_tokens` versus the suite's cap,
            # decided in `score_item`'s default comparison (no override here).
            truncated=response["finish_reason"]
            in mistral_client.TRUNCATING_FINISH_REASONS,
            generated_tokens=response["generated_tokens"],
            truncation_reason=None,
            retries=retries_taken,
        )
        return completion, response

    return complete_item


def _make_google_complete_item(
    model_info: google_client.GoogleModelInfo,
    settings: Settings,
    max_output_tokens: int,
) -> Callable[
    [SuiteItem, str], tuple[_Completion, google_client.GoogleCompletion | None]
]:
    """Build this batch's per-item completion function, closed over `model_info`.

    A closure, not a plain function, because Google's per-item call needs the
    pre-flight's `input_token_limit` -- known only after `check_model_available`
    runs, once per batch, not once per item. Also closes over one `Pacer` and
    one `RetryBudget`, shared across the whole batch: an item's own two
    requests (context-fits, generateContent) take turns waiting on the same
    pacer, and every item's retries draw from the same run-scoped budget.
    """
    pacer = retry.Pacer(settings.google_request_pacing_s, sleep=time.sleep)
    budget = retry.RetryBudget(settings.cloud_retry_max_attempts)

    def _is_retryable(exc: Exception) -> bool:
        return isinstance(exc, google_client.RetryableRequestError)

    def _retry_hint_s(exc: Exception) -> float | None:
        return (
            exc.retry_after_s
            if isinstance(exc, google_client.RetryableRequestError)
            else None
        )

    def complete_item(
        item: SuiteItem, api_key: str
    ) -> tuple[_Completion, google_client.GoogleCompletion | None]:
        pacer.wait()
        context_retries = 0
        try:
            _, context_retries = retry.call_with_retry(
                lambda: google_client.check_context_fits(
                    item["prompt"], api_key, model_info["input_token_limit"]
                ),
                is_retryable=_is_retryable,
                retry_hint_s=_retry_hint_s,
                budget=budget,
                base_delay_s=_RETRY_BASE_DELAY_S,
                sleep=time.sleep,
            )
        except google_client.ContextWindowExceededError:
            # Refused pre-flight, never sent to generateContent: this is the
            # only place `truncated_context` can honestly originate from on
            # this provider (free-tier context overflow never surfaces as a
            # finishReason -- the input-token quota's 429 always fires first).
            # Non-blank placeholder content: both scorers check blankness
            # before truncation, so an empty string here would score `empty`
            # instead of the truncation_reason override below. On a graded
            # suite it is also what the row's `subject_output` would carry,
            # which is the honest record of what came back from the batch.
            return (
                _Completion(
                    content="[context window exceeded, no generateContent call made]",
                    truncated=True,
                    generated_tokens=0,
                    truncation_reason=FAILURE_REASON_TRUNCATED_CONTEXT,
                    retries=context_retries,
                ),
                None,
            )

        pacer.wait()
        response, generate_retries = retry.call_with_retry(
            lambda: google_client.complete_prompt(
                item["prompt"],
                api_key,
                temperature=GOOGLE_SAMPLING["temperature"],
                top_p=GOOGLE_SAMPLING["top_p"],
                top_k=GOOGLE_SAMPLING["top_k"],
                seed=GOOGLE_SAMPLING["seed"],
                max_tokens=max_output_tokens,
            ),
            is_retryable=_is_retryable,
            retry_hint_s=_retry_hint_s,
            budget=budget,
            base_delay_s=_RETRY_BASE_DELAY_S,
            sleep=time.sleep,
        )
        # Read off finishReason directly, never generated_tokens versus the
        # cap: Google can report fewer generated tokens than the cap it
        # actually enforced, which would misclassify a cap-truncated item as
        # context-truncated under score_item's default comparison. The set
        # comes from the provider module, the same way the mistral path above
        # reads mistral_client.TRUNCATING_FINISH_REASONS.
        truncated = response["finish_reason"] in google_client.TRUNCATING_FINISH_REASONS
        completion = _Completion(
            content=response["content"],
            truncated=truncated,
            generated_tokens=response["generated_tokens"],
            truncation_reason=(
                FAILURE_REASON_TRUNCATED_MAX_TOKENS if truncated else None
            ),
            retries=context_retries + generate_retries,
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
    spec: SuiteSpec,
    model: str,
    price_table: dict[str, cost.Price],
    complete_item: Callable[[SuiteItem, str], tuple[_Completion, Any]],
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
    for item in spec.items:
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
    batch_fields = quality_rows.cloud_batch_fields(
        settings, model, price_table, prompt_tokens, completion_tokens_total
    )
    call_path_fields = call_path_fields_fn(responses)
    extra_row_fields = [extra_row_fields_fn(response) for response in responses]
    return completions, call_path_fields, batch_fields, extra_row_fields


def _score_and_write(
    settings: Settings,
    *,
    spec: SuiteSpec,
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
    resumed: bool,
    extra_row_fields: list[dict[str, Any]] | None = None,
) -> None:
    per_item_fields, batch_score_fields = spec.score_batch(spec.items, completions)

    rows: list[dict[str, Any]] = []
    for index, (item, item_score_fields) in enumerate(
        zip(spec.items, per_item_fields, strict=True)
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
            "task_suite": spec.task_suite,
            "item_id": item["item_id"],
            "prompt": item["prompt"],
            # Everything the suite's own scorer decided: the exact-match
            # fields on one suite, the graded block on the other, each
            # nulling the shape it does not publish so a reader never meets
            # two score columns on one row.
            **item_score_fields,
            **batch_score_fields,
            # Nested so a row is self-describing: a greedy row and a future
            # sampled row can share `quality.jsonl` and stay distinguishable
            # without consulting git history, and adding a sampler key can never
            # collide with a scoring field. Each row records the parameters sent
            # to its own provider, never a merged union of both.
            "sampling": dict(sampling),
            "max_output_tokens": spec.max_output_tokens,
            "stop_sequences": list(spec.stop_sequences),
            "context_length": spec.context_length,
            "suite_id": spec.suite_id,
            "suite_version": spec.suite_version,
            "prompt_set_hash": spec.prompt_set_hash,
            "language": item["language"],
            "provenance": item["provenance"],
            "contamination_risk": item["contamination_risk"],
            "indicative": gate_result["indicative"],
            "indicative_reasons": list(gate_result["indicative_reasons"]),
            "retries": completions[index]["retries"],
            "resumed": resumed,
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

    print(f"model={model_id} provider={provider} {_headline(batch_score_fields)}")


def _headline(batch_score_fields: dict[str, Any]) -> str:
    """The one score an operator reads off stdout, named by what it measures.

    `accuracy=` on an exact-match suite and `suite_score=` on a graded one:
    the two are different statistics, and printing a chrF mean under the word
    "accuracy" would be the same mistake on stdout that the row contract
    refuses on disk.
    """
    accuracy = batch_score_fields.get("suite_accuracy")
    if accuracy is not None:
        return f"accuracy={accuracy:.2f}"
    return f"suite_score={batch_score_fields['suite_score']:.2f}"
