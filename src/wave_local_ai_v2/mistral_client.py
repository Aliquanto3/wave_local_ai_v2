"""Minimal Mistral chat-completions client: one prompt in, one completion out.

No SDK, no streaming, no retries -- `requests` only, matching this project's
existing HTTP pattern (`server.py`). Endpoint, headers, and request/response
shape confirmed against https://docs.mistral.ai/api/ (2026-08-21): POST
{model, messages} with a Bearer token, response has
choices[0].message.content, choices[0].finish_reason and
usage.completion_tokens. `complete_prompt` returns all four as a
`MistralCompletion`.

`usage.prompt_tokens` and `usage.total_tokens` confirmed present alongside
`usage.completion_tokens`, OpenAI-compatible naming, on 2026-08-26.

The model id is deliberately dated, not the `mistral-small-latest` alias.
`architecture.md` defines a quality score as reproducible on model + prompt +
seed: behind an alias the model silently rotates, and no seed can make two runs
either side of a rotation agree. A dated id turns that into an explicit,
reviewable edit. `mistral-small-2603` was read from a live `GET /v1/models`
on 2026-08-21 -- note the docs' models-overview page rendered this id as
`mistral-small-4-0-26-03`, which does not exist on the API, so confirm any
replacement against the live endpoint rather than the documentation.
"""

from __future__ import annotations

from typing import Any, TypedDict

import requests

CHAT_COMPLETIONS_URL = "https://api.mistral.ai/v1/chat/completions"
MODELS_URL = "https://api.mistral.ai/v1/models"
MODEL = "mistral-small-2603"
REQUEST_TIMEOUT_S = 60
# Shorter than a completion's budget on purpose: the catalog check exists to
# fail fast, before the quality CLI pays for a full llama-server lifecycle. A
# listing allowed to hang for a completion's 60s would defeat the point.
CATALOG_TIMEOUT_S = 15
# The two `finish_reason` values that mean the generation was cut short rather
# than finished. Mistral's enum is `stop | length | model_length | error |
# tool_calls` (mistralai/client-python, ChatCompletionChoiceFinishReason):
# `length` is the caller's `max_tokens` cap, `model_length` the model's own
# context limit. Reading only `length` would publish a context-truncated
# generation as unparseable output, which is exactly the distinction the
# failure taxonomy exists to make.
TRUNCATING_FINISH_REASONS = frozenset({"length", "model_length"})


class MistralRequestError(RuntimeError):
    """Raised on a non-200 response or an unparseable response body."""


class MistralCompletion(TypedDict):
    """One completion returned by `complete_prompt`."""

    content: str
    endpoint: str
    finish_reason: str
    generated_tokens: int
    prompt_tokens: int | None
    total_tokens: int | None


class ModelUnavailableError(MistralRequestError):
    """Raised when a model id is absent from the live catalog.

    A subclass, not a sibling: every existing `except MistralRequestError`
    around a Mistral call keeps catching it without being widened.
    """


class RetryableRequestError(MistralRequestError):
    """Raised on a 429 or 5xx: worth retrying, unlike every other non-200 status.

    A subclass, not a sibling, for the same reason as `ModelUnavailableError`:
    every existing `except MistralRequestError` keeps catching it. Carries
    `status_code` and `retry_after_s` so a caller's `is_retryable`/
    `retry_hint_s` (`retry.call_with_retry`) can decide without re-parsing
    the response.
    """

    def __init__(
        self, message: str, *, status_code: int, retry_after_s: float | None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after_s = retry_after_s


def _mistral_retry_hint(response: requests.Response) -> float | None:
    """Read the standard `Retry-After` header (integer seconds), if present.

    Not a live-confirmed Mistral behavior the way Google's `RetryInfo` is --
    no memory file documents whether Mistral sends this header on a 429.
    Absence just means `None`, falling back to backoff-only retry.
    """
    raw = response.headers.get("Retry-After")
    if raw is None:
        return None
    try:
        return float(raw)
    except ValueError:
        return None


def complete_prompt(
    prompt: str, api_key: str, *, temperature: float, random_seed: int, max_tokens: int
) -> MistralCompletion:
    """Send one prompt to Mistral and return the completion and the endpoint called.

    `temperature`, `random_seed` and `max_tokens` are required keyword arguments
    rather than defaulted ones: a quality score is only reproducible when the
    sampler is pinned (`architecture.md`: "quality scores are reproducible
    (model + prompt + seed)"), so every caller has to state what it asked for
    instead of inheriting whatever Mistral's per-model default happens to be
    that week. Mistral names the seed field `random_seed`, not `seed`.

    `max_tokens` is required for the same reason and one more: the suite
    declares one generation cap for every model it compares
    (`classification_suite.MAX_OUTPUT_TOKENS`), and each row publishes that cap
    as what the row ran under. Defaulting it here, or omitting it from the body,
    would let the cloud model generate uncapped while its rows still claimed the
    local model's `n_predict` limit.
    """
    response = requests.post(
        CHAT_COMPLETIONS_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "random_seed": random_seed,
            "max_tokens": max_tokens,
        },
        timeout=REQUEST_TIMEOUT_S,
    )

    if response.status_code != 200:
        if response.status_code == 429 or response.status_code >= 500:
            raise RetryableRequestError(
                f"Mistral request failed with status {response.status_code}: "
                f"{response.text[:500]}",
                status_code=response.status_code,
                retry_after_s=_mistral_retry_hint(response),
            )
        raise MistralRequestError(
            f"Mistral request failed with status {response.status_code}: "
            f"{response.text[:500]}"
        )

    response_json: dict[str, Any] = response.json()
    try:
        content: Any = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MistralRequestError(
            f"unexpected Mistral response shape: {response_json!r}"
        ) from exc
    if not isinstance(content, str):
        # Mistral returns content null on tool-call and refusal finish reasons.
        # A present-but-non-text content (null, object) would only fail further
        # down in normalize_label, as an uncaught AttributeError. Same rule and
        # same wording as the local path's guard in quality_cli.
        raise MistralRequestError(f"unexpected Mistral content type: {content!r}")

    try:
        finish_reason: Any = response_json["choices"][0]["finish_reason"]
        generated_tokens: Any = response_json["usage"]["completion_tokens"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MistralRequestError(
            f"unexpected Mistral response shape: {response_json!r}"
        ) from exc
    # Same rule as the content guard above: a present-but-wrong-typed value has
    # to fail here, at the provider boundary the CLI catches, rather than
    # further down. A null finish_reason would silently read as "not
    # truncated", and a non-numeric token count would only surface as an
    # uncaught TypeError inside score_item's comparison.
    if not isinstance(finish_reason, str):
        raise MistralRequestError(
            f"unexpected Mistral finish_reason type: {finish_reason!r}"
        )
    if not isinstance(generated_tokens, int) or isinstance(generated_tokens, bool):
        raise MistralRequestError(
            f"unexpected Mistral completion_tokens type: {generated_tokens!r}"
        )

    # .get, not [...]: unlike completion_tokens (load-bearing for score_item),
    # these two are not required to make a completion usable, so an absent
    # key degrades to None rather than raising. A present-but-wrong-typed
    # value still fails here, at the provider boundary.
    usage = response_json["usage"]
    prompt_tokens: Any = usage.get("prompt_tokens")
    if prompt_tokens is not None and (
        not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool)
    ):
        raise MistralRequestError(
            f"unexpected Mistral prompt_tokens type: {prompt_tokens!r}"
        )
    total_tokens: Any = usage.get("total_tokens")
    if total_tokens is not None and (
        not isinstance(total_tokens, int) or isinstance(total_tokens, bool)
    ):
        raise MistralRequestError(
            f"unexpected Mistral total_tokens type: {total_tokens!r}"
        )

    return MistralCompletion(
        content=content,
        endpoint=CHAT_COMPLETIONS_URL,
        finish_reason=finish_reason,
        generated_tokens=generated_tokens,
        prompt_tokens=prompt_tokens,
        total_tokens=total_tokens,
    )


def check_model_available(api_key: str, model: str = MODEL) -> str | None:
    """Confirm `model` is on the live catalog; return a deprecation notice or None.

    Absence and deprecation are deliberately not the same outcome. An absent id
    guarantees the next completion request fails, so this raises. A deprecated
    id still answers until its retirement date, so failing here would break a
    run that is currently fine, up to ten days early on the dates Mistral is
    publishing today; the caller gets a notice to surface and decides for
    itself. The returned string is a warning, never an error.

    Matching is by `id` alone, never by an entry's `aliases`: a rotating alias
    is what the dated `MODEL` exists to avoid, so an alias handed to this check
    is reported absent rather than quietly accepted.
    """
    response = requests.get(
        MODELS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=CATALOG_TIMEOUT_S,
    )

    if response.status_code != 200:
        raise MistralRequestError(
            f"Mistral model catalog request failed with status "
            f"{response.status_code}: {response.text[:500]}"
        )

    # The body is guarded as a whole, not just its `data` key: a 200 carrying a
    # JSON array or null would make `.get` raise AttributeError, which is not in
    # the caller's `except` tuple and would surface as a traceback.
    response_json: Any = response.json()
    entries = response_json.get("data") if isinstance(response_json, dict) else None
    if not isinstance(entries, list):
        raise MistralRequestError(
            f"unexpected Mistral catalog response shape: {response_json!r}"
        )

    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == model:
            return _deprecation_notice(entry, model)

    raise ModelUnavailableError(
        f"Mistral model {model!r} is not on the live catalog "
        f"({len(entries)} models listed). Confirm the id against "
        f"{MODELS_URL} and update mistral_client.MODEL."
    )


def _deprecation_notice(entry: dict[str, Any], model: str) -> str | None:
    deprecation = entry.get("deprecation")
    if not deprecation:
        return None
    replacement = entry.get("deprecation_replacement_model") or "none published"
    return (
        f"warning: Mistral model {model!r} is deprecated as of {deprecation}; "
        f"replacement: {replacement}. Quality rows written after that date will "
        f"not be reproducible against this id."
    )
