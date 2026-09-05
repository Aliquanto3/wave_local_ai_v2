"""Minimal Google AI Studio (Gemini) client: one prompt in, one completion out.

No SDK, no streaming, no retries -- `requests` only, matching this project's
existing HTTP pattern (`mistral_client.py`, `server.py`). Every non-obvious
fact cited below is confirmed against the live API on 2026-08-27, distilled in
`aidd_docs/memory/external/google-ai-studio-api.md`, with the captured
requests/responses in `aidd_docs/tasks/2026_08/2026_08_26_google-ai-studio-spike/decision.md`.

The model id is deliberately the pinned release id, not the `-latest` alias
(`gemini-flash-lite-latest`), for the same reproducibility reason
`mistral_client.MODEL` is dated. Google publishes no dated build id: the
catalog's `version` field is the read-only build snapshot this client reads
and the caller publishes on the row, so a silent rotation to a later build
shows up as a changed field instead of disappearing behind an alias.

Presence on the catalog does not mean the model answers: a retired model still
returns a full `GET /models/{id}` entry and then 404s on `generateContent`.
`check_model_available` therefore probes `generateContent` for real, not just
catalog membership.
"""

from __future__ import annotations

from typing import Any, TypedDict

import requests

BASE_URL = "https://generativelanguage.googleapis.com/v1"
MODEL = "gemini-3.5-flash-lite"
CATALOG_URL = f"{BASE_URL}/models/{MODEL}"
GENERATE_URL = f"{BASE_URL}/models/{MODEL}:generateContent"
COUNT_TOKENS_URL = f"{BASE_URL}/models/{MODEL}:countTokens"
REQUEST_TIMEOUT_S = 60
# Shorter than a completion's budget on purpose, same reasoning as
# mistral_client.CATALOG_TIMEOUT_S: the catalog/probe check exists to fail
# fast, before the quality CLI pays for a full run.
CATALOG_TIMEOUT_S = 15

# The full finishReason enum (21 values), from the decision file. MAX_TOKENS
# is the caller's cap; the fifteen blocked/error values mean the provider
# refused rather than answered. Every other non-STOP value has no honest
# taxonomy home either, so it is treated the same as blocked for the purpose
# of raising -- there is no third bucket to maintain.
_TRUNCATING_FINISH_REASONS = frozenset({"MAX_TOKENS"})
_BLOCKED_FINISH_REASONS = frozenset(
    {
        "SAFETY",
        "RECITATION",
        "LANGUAGE",
        "BLOCKLIST",
        "PROHIBITED_CONTENT",
        "SPII",
        "IMAGE_SAFETY",
        "IMAGE_PROHIBITED_CONTENT",
        "IMAGE_RECITATION",
        "ESCALATION",
    }
)
_OK_FINISH_REASONS = frozenset({"STOP"}) | _TRUNCATING_FINISH_REASONS


class GoogleRequestError(RuntimeError):
    """Raised on a non-200 response or an unparseable response body."""


class ModelUnavailableError(GoogleRequestError):
    """Raised when the model id is absent from the catalog or unreachable.

    A subclass, not a sibling: every existing `except GoogleRequestError`
    around a Google call keeps catching it without being widened.
    """


class ContextWindowExceededError(GoogleRequestError):
    """Raised when a prompt's token count exceeds the model's input limit.

    Also a subclass of GoogleRequestError, same reasoning as
    ModelUnavailableError.
    """


class GoogleBlockedError(GoogleRequestError):
    """Raised when generation stopped for a reason the taxonomy has no value for.

    Covers every `finishReason` in `_BLOCKED_FINISH_REASONS` and every value
    outside `{"STOP", "MAX_TOKENS"}`. Publishing `empty` for these would claim
    the model said nothing when the provider actually refused; this names the
    `finishReason` verbatim instead.
    """


class GoogleCompletion(TypedDict):
    """One completion returned by `complete_prompt`."""

    content: str
    endpoint: str
    finish_reason: str
    generated_tokens: int
    prompt_tokens: int | None
    total_tokens: int | None
    model_version: str | None


class GoogleModelInfo(TypedDict):
    """The catalog facts `check_model_available` confirms and returns."""

    version: str
    input_token_limit: int


def complete_prompt(
    prompt: str,
    api_key: str,
    *,
    temperature: float,
    top_p: float,
    top_k: int,
    seed: int,
    max_tokens: int,
) -> GoogleCompletion:
    """Send one prompt to Google AI Studio and return the completion.

    Every sampling field is a required keyword argument, never defaulted --
    same rule and same reason as `mistral_client.complete_prompt`'s
    docstring: a quality score is only reproducible when the sampler is
    pinned, and the provider's own per-model defaults are not this project's
    to inherit silently.

    `seed` matters more here than on Mistral: temperature 0 alone is not
    reproducible on this provider (confirmed live -- five different answers
    with no seed, five byte-identical answers with one), so dropping it
    silently drops reproducibility.

    Deliberately absent from the request body: `thinkingConfig` (rejected on
    this model) and `stopSequences` (indistinguishable from a chosen-empty
    answer on the row). Both per the decision file.
    """
    response = requests.post(
        GENERATE_URL,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "topP": top_p,
                "topK": top_k,
                "seed": seed,
                "maxOutputTokens": max_tokens,
                "candidateCount": 1,
            },
        },
        timeout=REQUEST_TIMEOUT_S,
    )

    if response.status_code != 200:
        raise GoogleRequestError(
            f"Google request failed with status {response.status_code}: "
            f"{_retry_hint(response)}{response.text[:500]}"
        )

    response_json: dict[str, Any] = response.json()
    try:
        candidate: Any = response_json["candidates"][0]
    except (KeyError, IndexError, TypeError) as exc:
        raise GoogleRequestError(
            f"unexpected Google response shape: {response_json!r}"
        ) from exc

    # `content` can be `{}` with no `parts` key at all, and `parts` can be an
    # empty list -- text extraction tolerates both and never indexes parts[0].
    content_obj = candidate.get("content", {}) if isinstance(candidate, dict) else {}
    parts = content_obj.get("parts") if isinstance(content_obj, dict) else None
    try:
        content = "".join(part.get("text", "") for part in (parts or []))
    except (AttributeError, TypeError) as exc:
        raise GoogleRequestError(
            f"unexpected Google content shape: {response_json!r}"
        ) from exc

    finish_reason: Any = (
        candidate.get("finishReason") if isinstance(candidate, dict) else None
    )
    if not isinstance(finish_reason, str):
        raise GoogleRequestError(
            f"unexpected Google finishReason type: {finish_reason!r}"
        )
    if finish_reason not in _OK_FINISH_REASONS:
        raise GoogleBlockedError(
            f"Google generation stopped with finishReason {finish_reason!r}"
        )

    usage = response_json.get("usageMetadata", {})
    if not isinstance(usage, dict):
        raise GoogleRequestError(f"unexpected Google usageMetadata shape: {usage!r}")

    # .get(..., 0), not [...]: candidatesTokenCount is absent, not zero, when
    # nothing was generated -- unlike Mistral's completion_tokens, which is
    # always sent.
    generated_tokens: Any = usage.get("candidatesTokenCount", 0)
    if not isinstance(generated_tokens, int) or isinstance(generated_tokens, bool):
        raise GoogleRequestError(
            f"unexpected Google candidatesTokenCount type: {generated_tokens!r}"
        )

    prompt_tokens: Any = usage.get("promptTokenCount")
    if prompt_tokens is not None and (
        not isinstance(prompt_tokens, int) or isinstance(prompt_tokens, bool)
    ):
        raise GoogleRequestError(
            f"unexpected Google promptTokenCount type: {prompt_tokens!r}"
        )
    total_tokens: Any = usage.get("totalTokenCount")
    if total_tokens is not None and (
        not isinstance(total_tokens, int) or isinstance(total_tokens, bool)
    ):
        raise GoogleRequestError(
            f"unexpected Google totalTokenCount type: {total_tokens!r}"
        )

    model_version: Any = response_json.get("modelVersion")
    if model_version is not None and not isinstance(model_version, str):
        raise GoogleRequestError(
            f"unexpected Google modelVersion type: {model_version!r}"
        )

    return GoogleCompletion(
        content=content,
        endpoint=GENERATE_URL,
        finish_reason=finish_reason,
        generated_tokens=generated_tokens,
        prompt_tokens=prompt_tokens,
        total_tokens=total_tokens,
        model_version=model_version,
    )


def check_model_available(api_key: str, model: str = MODEL) -> GoogleModelInfo:
    """Confirm `model` is on the catalog and actually answers, then return its facts.

    Two checks, not one: the catalog listing a model is necessary but not
    sufficient (a retired model still has a full catalog entry and 404s on
    `generateContent`), so this also fires a one-token probe. No deprecation
    field exists in this catalog -- unlike `mistral_client`'s notice, there is
    nothing softer to return; absence at either step raises.
    """
    catalog_url = f"{BASE_URL}/models/{model}"
    response = requests.get(
        catalog_url,
        headers={"x-goog-api-key": api_key},
        timeout=CATALOG_TIMEOUT_S,
    )

    if response.status_code != 200:
        raise ModelUnavailableError(
            f"Google model {model!r} is not on the catalog "
            f"(status {response.status_code} from {catalog_url})."
        )

    entry: Any = response.json()
    if not isinstance(entry, dict) or "name" not in entry:
        raise ModelUnavailableError(
            f"Google model {model!r} catalog entry is missing or malformed: "
            f"{entry!r} from {catalog_url}."
        )

    version = entry.get("version")
    input_token_limit = entry.get("inputTokenLimit")
    if not isinstance(version, str) or not isinstance(input_token_limit, int):
        raise GoogleRequestError(
            f"unexpected Google catalog entry shape for {model!r}: {entry!r}"
        )

    generate_url = f"{BASE_URL}/models/{model}:generateContent"
    probe = requests.post(
        generate_url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={
            "contents": [{"role": "user", "parts": [{"text": "ping"}]}],
            "generationConfig": {
                "temperature": 0,
                "maxOutputTokens": 1,
                "candidateCount": 1,
            },
        },
        timeout=CATALOG_TIMEOUT_S,
    )
    if probe.status_code == 404:
        raise ModelUnavailableError(
            f"Google model {model!r} is on the catalog ({CATALOG_URL}) but no "
            f"longer available to new users ({generate_url} returned 404)."
        )
    if probe.status_code not in (200, 400):
        # A probe capped at maxOutputTokens=1 is expected to succeed (200); a
        # 400 on the probe body itself is not availability's failure to
        # report, so only a hard non-200/400 (e.g. auth) is raised as
        # unavailable-adjacent here. Anything else surfaces at the real call.
        raise ModelUnavailableError(
            f"Google model {model!r} generateContent probe failed with status "
            f"{probe.status_code} from {generate_url}."
        )

    return GoogleModelInfo(version=version, input_token_limit=input_token_limit)


def check_context_fits(
    prompt: str, api_key: str, input_token_limit: int, model: str = MODEL
) -> None:
    """Raise `ContextWindowExceededError` when `prompt` exceeds `input_token_limit`.

    Free-tier context overflow never surfaces as a `generateContent`
    `finishReason`: a prompt over the context window necessarily exceeds the
    input-tokens-per-minute quota first, so the 429 always fires before any
    context-limit signal could. This pre-flight is the only place
    `truncated_context` can honestly originate from for this provider; it
    never calls `generateContent`.
    """
    count_url = f"{BASE_URL}/models/{model}:countTokens"
    response = requests.post(
        count_url,
        headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
        json={"contents": [{"role": "user", "parts": [{"text": prompt}]}]},
        timeout=CATALOG_TIMEOUT_S,
    )

    if response.status_code != 200:
        raise GoogleRequestError(
            f"Google countTokens request failed with status "
            f"{response.status_code}: {response.text[:500]}"
        )

    response_json: Any = response.json()
    total_tokens = (
        response_json.get("totalTokens") if isinstance(response_json, dict) else None
    )
    if not isinstance(total_tokens, int) or isinstance(total_tokens, bool):
        raise GoogleRequestError(
            f"unexpected Google countTokens response shape: {response_json!r}"
        )

    if total_tokens > input_token_limit:
        raise ContextWindowExceededError(
            f"prompt token count {total_tokens} exceeds model {model!r}'s "
            f"input_token_limit of {input_token_limit}"
        )


def _retry_hint(response: requests.Response) -> str:
    """Extract the `RetryInfo.retryDelay` string from a 429 body, when present.

    There is no `Retry-After` header on this provider -- the wait hint, when
    Google sends one at all, is in `error.details[]` at the entry whose
    `@type` is `type.googleapis.com/google.rpc.RetryInfo`. Absence is not an
    error: no retry is attempted here, this only enriches the message.
    """
    try:
        body: Any = response.json()
    except ValueError:
        return ""
    if not isinstance(body, dict):
        return ""
    details = (
        body.get("error", {}).get("details", [])
        if isinstance(body.get("error"), dict)
        else []
    )
    if not isinstance(details, list):
        return ""
    for detail in details:
        if (
            isinstance(detail, dict)
            and detail.get("@type") == "type.googleapis.com/google.rpc.RetryInfo"
        ):
            retry_delay = detail.get("retryDelay")
            if isinstance(retry_delay, str):
                return f"retry after {retry_delay}; "
    return ""
