"""The local llama-server chat path, as a client beside `mistral_client` and
`google_client`.

Three calls against one running server: read the loaded model's chat template
(`/props`), render an item's prompt through it (`/apply-template`), and ask for
the answer (`/v1/chat/completions`). The two suites' subject generation goes
through here; the runtime benchmark deliberately does not, because its number is
raw generation throughput against a fixed prompt reproduced from
`context_input/baseline_qwen36.md`, and templating it would change the token
count it measures and break its reproduction verdict against every published
runtime row.

Why the chat endpoint at all: `/completion` sends a prompt byte-for-byte, so a
chat-tuned model is asked to *continue* the item text rather than answer it.
That is the local-subject-prompts-are-never-chat-templated defect, and this
module is its fix.

Why `thinking_policy` is a parameter and not a default: probed live on
`b10537-bf0040e15`, both `Qwen3-0.6B` and `Qwen3.6-35B-A3B` spend their entire
generation cap in `reasoning_content` and return `content: ""` when asked
through their own template with no policy sent. The same call with
`chat_template_kwargs: {"enable_thinking": false}` answers in two tokens. So
the argument decides whether a score exists, which makes it the suite's to
declare rather than this module's to assume.

Of the four reasoning controls b10537 documents, `chat_template_kwargs` is the
one used, and the choice is evidence-backed rather than stylistic:
`reasoning_budget: 0` had no effect as a request parameter, `reasoning_format:
"none"` only stops the envelope being parsed out of `content`, and
`reasoning_effort: "none"` worked on both models tested while their own
`chat_template_caps` reports `supports_reasoning_effort: false` -- a benchmark
should not rest on a capability the server says is absent.

No retry logic lives here. The local path has no retryable error type, and a
second retry policy beside `retry.py` would be one too many.
"""

from __future__ import annotations

from typing import Any, TypedDict

import requests

from wave_local_ai_v2 import prompt_provenance, row_contract

# `finish_reason` values that mean the answer was cut short rather than
# completed. Named here for the same reason `mistral_client` and
# `google_client` name their own: the truncation decision is read off the
# provider's own field, never inferred from a token count.
TRUNCATING_FINISH_REASONS = frozenset({"length"})


class LocalRequestError(RuntimeError):
    """Raised when a local llama-server response has no usable content."""


class LocalCompletion(TypedDict):
    """One item's generation from the local chat endpoint."""

    content: str
    finish_reason: str | None
    generated_tokens: int
    prompt_tokens: int
    endpoint: str


def _thinking_kwargs(thinking_policy: str) -> dict[str, Any]:
    """The request arguments `thinking_policy` maps to, for both call shapes.

    The one place the argument's spelling exists. `allowed` sends nothing,
    which is the server's own default, rather than sending an explicit
    `enable_thinking: true` a template might not declare.
    """
    if thinking_policy == row_contract.THINKING_POLICY_DISABLED:
        return {"chat_template_kwargs": {"enable_thinking": False}}
    if thinking_policy == row_contract.THINKING_POLICY_ALLOWED:
        return {}
    raise LocalRequestError(
        f"unknown thinking_policy {thinking_policy!r}: expected one of "
        f"{sorted(row_contract.THINKING_POLICIES)}"
    )


def _post_json(url: str, body: dict[str, Any], timeout: float) -> dict[str, Any]:
    response = requests.post(url, json=body, timeout=timeout)
    response.raise_for_status()
    payload: Any = response.json()
    if not isinstance(payload, dict):
        raise LocalRequestError(f"unexpected response shape from {url}: {payload!r}")
    return payload


def chat_template(base_url: str, *, timeout: float) -> str:
    """Return the loaded model's own Jinja chat template, from `/props`.

    This string is what `prompt_template_hash` is taken over, so a row states
    which template rendered it and the hash moves when the model does.
    """
    response = requests.get(f"{base_url}/props", timeout=timeout)
    response.raise_for_status()
    payload: Any = response.json()
    template = payload.get("chat_template") if isinstance(payload, dict) else None
    if not isinstance(template, str) or not template:
        raise LocalRequestError(f"/props carries no usable chat_template: {template!r}")
    return template


def render_prompt(
    base_url: str, prompt: str, *, thinking_policy: str, timeout: float
) -> str:
    """Return `prompt` as the chat endpoint will render it, from `/apply-template`.

    The chat response echoes the rendered prompt nowhere, so the string a row
    publishes has to come from here. The policy is sent on this call too: with
    thinking disabled the template appends an empty `<think></think>` block,
    so omitting it would store a string the answering call never used. That is
    also why the row records `prompt_capture` as reconstructed rather than
    captured -- same server, same template, same arguments, but a different
    request from the one that produced the answer.

    `/apply-template` honouring `chat_template_kwargs` is undocumented in
    b10537's server README (which lists `messages` as its only option) and was
    verified live against the binary.
    """
    payload = _post_json(
        f"{base_url}{prompt_provenance.LOCAL_APPLY_TEMPLATE_ENDPOINT}",
        {
            "messages": [{"role": "user", "content": prompt}],
            **_thinking_kwargs(thinking_policy),
        },
        timeout,
    )
    rendered = payload.get("prompt")
    if not isinstance(rendered, str):
        raise LocalRequestError(
            f"unexpected /apply-template response shape: {payload!r}"
        )
    return rendered


def complete_chat(
    base_url: str,
    prompt: str,
    *,
    max_tokens: int,
    sampling: dict[str, Any],
    thinking_policy: str,
    timeout: float,
) -> LocalCompletion:
    """Ask the loaded model to answer `prompt` through its own chat template."""
    payload = _post_json(
        f"{base_url}{prompt_provenance.LOCAL_CHAT_ENDPOINT}",
        {
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            **sampling,
            **_thinking_kwargs(thinking_policy),
        },
        timeout,
    )
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        raise LocalRequestError(
            f"unexpected /v1/chat/completions response shape: {payload!r}"
        )
    choice = choices[0]
    message = choice.get("message") if isinstance(choice, dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        # A thinking model that spent its whole cap reasoning returns an empty
        # string here, which is a valid response and scores as `empty`. Only a
        # missing or non-text content is a malformed body.
        raise LocalRequestError(f"unexpected chat content type: {content!r}")
    usage = payload.get("usage")
    if not isinstance(usage, dict):
        raise LocalRequestError(f"chat response carries no usage block: {payload!r}")
    return LocalCompletion(
        content=content,
        finish_reason=choice.get("finish_reason"),
        generated_tokens=usage.get("completion_tokens", 0),
        prompt_tokens=usage.get("prompt_tokens", 0),
        endpoint=prompt_provenance.LOCAL_CHAT_ENDPOINT,
    )
