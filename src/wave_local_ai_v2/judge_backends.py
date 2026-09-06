"""The provider bindings for the judge path, and nothing else.

This is the only judge-path module that imports `mistral_client` or
`google_client`. `judge.py`, `judge_protocol.py` and `agreement.py` stay
provider-agnostic, so adding a third judge provider, or swapping one out,
reopens this file and no other -- the same one-module-per-provider discipline
the two clients themselves already follow.

Neither backend catches its provider's errors. A transport failure or an
exhausted retry budget propagates to the caller, which owns the "skip that
provider, one stderr line, the run continues" contract
(`quality_cli._try_run_cloud_provider`).
"""

from __future__ import annotations

import time

from wave_local_ai_v2 import google_client, judge, mistral_client, retry, roster

# The first backoff delay when the provider sends no retry hint of its own.
# Same value and same role as `quality_cli._RETRY_BASE_DELAY_S`.
_RETRY_BASE_DELAY_S = 1.0

PROVIDER_MISTRAL = "mistral"
PROVIDER_GOOGLE = "google"


def mistral_judge_backend(
    api_key: str,
    *,
    pacer: retry.Pacer,
    budget: retry.RetryBudget,
    temperature: float,
    random_seed: int,
    max_tokens: int,
) -> judge.JudgeBackend:
    """Bind Mistral to `judge.JudgeBackend`, paced and retried per batch.

    A closure over one `Pacer` and one `RetryBudget`, the established shape
    for a per-batch pair (`quality_cli._make_mistral_complete_item`): the
    budget is batch-scoped, so every judge call in a batch draws from the same
    pool rather than getting its own.
    """

    def _is_retryable(exc: Exception) -> bool:
        return isinstance(exc, mistral_client.RetryableRequestError)

    def _retry_hint_s(exc: Exception) -> float | None:
        return (
            exc.retry_after_s
            if isinstance(exc, mistral_client.RetryableRequestError)
            else None
        )

    def call(prompt: str) -> judge.JudgeResponse:
        pacer.wait()
        response, retries_taken = retry.call_with_retry(
            lambda: mistral_client.complete_prompt(
                prompt,
                api_key,
                temperature=temperature,
                random_seed=random_seed,
                max_tokens=max_tokens,
            ),
            is_retryable=_is_retryable,
            retry_hint_s=_retry_hint_s,
            budget=budget,
            base_delay_s=_RETRY_BASE_DELAY_S,
            sleep=time.sleep,
        )
        return judge.JudgeResponse(
            content=response["content"],
            model_id=mistral_client.MODEL,
            provider=PROVIDER_MISTRAL,
            family=roster.FAMILY_MISTRAL,
            tokens_in=response["prompt_tokens"],
            tokens_out=response["generated_tokens"],
            retries=retries_taken,
        )

    return call


def google_judge_backend(
    api_key: str,
    *,
    pacer: retry.Pacer,
    budget: retry.RetryBudget,
    temperature: float,
    top_p: float,
    top_k: int,
    seed: int,
    max_tokens: int,
) -> judge.JudgeBackend:
    """Bind Google AI Studio to `judge.JudgeBackend`, paced and retried per batch.

    Deliberately does not call `google_client.check_context_fits`: the judge
    prompt's context pre-flight is the caller's decision, and paying a second
    request per judge call is a free-tier cost this has no evidence to
    justify. The subject batch's own pre-flight (`quality_cli`) is unchanged.
    """

    def _is_retryable(exc: Exception) -> bool:
        return isinstance(exc, google_client.RetryableRequestError)

    def _retry_hint_s(exc: Exception) -> float | None:
        return (
            exc.retry_after_s
            if isinstance(exc, google_client.RetryableRequestError)
            else None
        )

    def call(prompt: str) -> judge.JudgeResponse:
        pacer.wait()
        response, retries_taken = retry.call_with_retry(
            lambda: google_client.complete_prompt(
                prompt,
                api_key,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                seed=seed,
                max_tokens=max_tokens,
            ),
            is_retryable=_is_retryable,
            retry_hint_s=_retry_hint_s,
            budget=budget,
            base_delay_s=_RETRY_BASE_DELAY_S,
            sleep=time.sleep,
        )
        return judge.JudgeResponse(
            content=response["content"],
            model_id=google_client.MODEL,
            provider=PROVIDER_GOOGLE,
            family=roster.FAMILY_GOOGLE,
            tokens_in=response["prompt_tokens"],
            tokens_out=response["generated_tokens"],
            retries=retries_taken,
        )

    return call
