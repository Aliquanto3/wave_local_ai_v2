"""Minimal Mistral chat-completions client: one prompt in, one completion out.

No SDK, no streaming, no retries -- `requests` only, matching this project's
existing HTTP pattern (`server.py`). Endpoint, headers, and request/response
shape confirmed against https://docs.mistral.ai/api/ (2026-08-21): POST
{model, messages} with a Bearer token, response has
choices[0].message.content.

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

from typing import Any

import requests

CHAT_COMPLETIONS_URL = "https://api.mistral.ai/v1/chat/completions"
MODELS_URL = "https://api.mistral.ai/v1/models"
MODEL = "mistral-small-2603"
REQUEST_TIMEOUT_S = 60
# Shorter than a completion's budget on purpose: the catalog check exists to
# fail fast, before the quality CLI pays for a full llama-server lifecycle. A
# listing allowed to hang for a completion's 60s would defeat the point.
CATALOG_TIMEOUT_S = 15


class MistralRequestError(RuntimeError):
    """Raised on a non-200 response or an unparseable response body."""


class ModelUnavailableError(MistralRequestError):
    """Raised when a model id is absent from the live catalog.

    A subclass, not a sibling: every existing `except MistralRequestError`
    around a Mistral call keeps catching it without being widened.
    """


def complete_prompt(
    prompt: str, api_key: str, *, temperature: float, random_seed: int
) -> str:
    """Send one prompt to Mistral and return the raw completion text.

    `temperature` and `random_seed` are required keyword arguments rather than
    defaulted ones: a quality score is only reproducible when the sampler is
    pinned (`architecture.md`: "quality scores are reproducible (model + prompt
    + seed)"), so every caller has to state what it asked for instead of
    inheriting whatever Mistral's per-model default happens to be that week.
    Mistral names the field `random_seed`, not `seed`.
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
        },
        timeout=REQUEST_TIMEOUT_S,
    )

    if response.status_code != 200:
        raise MistralRequestError(
            f"Mistral request failed with status {response.status_code}: "
            f"{response.text[:500]}"
        )

    response_json: dict[str, Any] = response.json()
    try:
        content: str = response_json["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise MistralRequestError(
            f"unexpected Mistral response shape: {response_json!r}"
        ) from exc
    return content


def check_model_available(api_key: str, model: str = MODEL) -> str | None:
    """Confirm `model` is on the live catalog; return a deprecation notice or None.

    Absence and deprecation are deliberately not the same outcome. An absent id
    guarantees the next completion request fails, so this raises. A deprecated
    id still answers until its retirement date, so failing here would break a
    run that is currently fine, up to ten days early on the dates Mistral is
    publishing today; the caller gets a notice to surface and decides for
    itself. The returned string is a warning, never an error.
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

    response_json: dict[str, Any] = response.json()
    entries = response_json.get("data")
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
