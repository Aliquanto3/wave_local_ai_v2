"""Minimal Mistral chat-completions client: one prompt in, one completion out.

No SDK, no streaming, no retries -- `requests` only, matching this project's
existing HTTP pattern (`server.py`). Endpoint, headers, and request/response
shape confirmed against https://docs.mistral.ai/api/ (2026-08-21): POST
{model, messages} with a Bearer token, response has
choices[0].message.content. `mistral-small-latest` is Mistral's maintained
alias for its current small-tier model, chosen over a dated model id so this
client does not need updating every time Mistral rotates its small-tier model.
"""

from __future__ import annotations

from typing import Any

import requests

API_URL = "https://api.mistral.ai/v1/chat/completions"
MODEL = "mistral-small-latest"
REQUEST_TIMEOUT_S = 60


class MistralRequestError(RuntimeError):
    """Raised on a non-200 response or an unparseable response body."""


def complete_prompt(prompt: str, api_key: str) -> str:
    """Send one prompt to Mistral and return the raw completion text."""
    response = requests.post(
        API_URL,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={"model": MODEL, "messages": [{"role": "user", "content": prompt}]},
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
