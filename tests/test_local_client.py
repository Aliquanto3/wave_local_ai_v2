"""The local chat client: response shaping, failure modes, and the one place
the thinking-policy argument is spelled.

Every HTTP call is stubbed. The live proof that these field names are b10537's
is `aidd_docs/tasks/2026_09/2026_09_06_local-chat-templated-quality-path/evidence.md`,
recorded against the running binary and deliberately not re-run in CI.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2 import local_client, prompt_provenance, row_contract

BASE = "http://127.0.0.1:8080"
TIMEOUT = 30.0
SAMPLING: dict[str, Any] = {"seed": 1, "temperature": 0}

_CHAT_BODY = {
    "choices": [
        {
            "finish_reason": "stop",
            "index": 0,
            "message": {"role": "assistant", "content": "billing"},
        }
    ],
    "usage": {"completion_tokens": 2, "prompt_tokens": 57, "total_tokens": 59},
}


def _response(payload: Any) -> MagicMock:
    return MagicMock(
        status_code=200, json=lambda: payload, raise_for_status=lambda: None
    )


def _post(payload: Any) -> Any:
    return patch(
        "wave_local_ai_v2.local_client.requests.post", return_value=_response(payload)
    )


def _get(payload: Any) -> Any:
    return patch(
        "wave_local_ai_v2.local_client.requests.get", return_value=_response(payload)
    )


def _complete(**overrides: Any) -> local_client.LocalCompletion:
    with _post(_CHAT_BODY):
        return local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_policy=row_contract.THINKING_POLICY_DISABLED,
            timeout=TIMEOUT,
            **overrides,
        )


def test_a_well_formed_chat_body_yields_the_five_fields() -> None:
    completion = _complete()

    assert completion["content"] == "billing"
    assert completion["finish_reason"] == "stop"
    assert completion["generated_tokens"] == 2
    assert completion["prompt_tokens"] == 57
    assert completion["endpoint"] == prompt_provenance.LOCAL_CHAT_ENDPOINT


def test_length_is_a_truncating_finish_reason_and_stop_is_not() -> None:
    assert "length" in local_client.TRUNCATING_FINISH_REASONS
    assert "stop" not in local_client.TRUNCATING_FINISH_REASONS


def test_an_empty_answer_is_returned_rather_than_refused() -> None:
    # What a thinking model that spent its whole cap reasoning actually
    # returns. It is a valid response and scores as `empty`; refusing it here
    # would abort a run over a real generation outcome.
    body = {
        "choices": [
            {
                "finish_reason": "length",
                "message": {"content": "", "reasoning_content": "Okay, let's see."},
            }
        ],
        "usage": {"completion_tokens": 32, "prompt_tokens": 57},
    }

    with _post(body):
        completion = local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_policy=row_contract.THINKING_POLICY_ALLOWED,
            timeout=TIMEOUT,
        )

    assert completion["content"] == ""
    assert completion["finish_reason"] == "length"
    assert completion["generated_tokens"] == 32


@pytest.mark.parametrize(
    "body",
    [
        {"usage": {}},
        {"choices": [], "usage": {}},
        {"choices": [{"message": {"content": None}}], "usage": {}},
        {"choices": [{"message": {"content": "billing"}}]},
    ],
    ids=["no_choices_key", "empty_choices", "non_text_content", "no_usage"],
)
def test_a_malformed_chat_body_raises_the_named_error(body: Any) -> None:
    with _post(body), pytest.raises(local_client.LocalRequestError):
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_policy=row_contract.THINKING_POLICY_DISABLED,
            timeout=TIMEOUT,
        )


def test_apply_template_returns_the_rendered_prompt() -> None:
    rendered = "<|im_start|>user\nhello<|im_end|>\n<|im_start|>assistant\n"

    with _post({"prompt": rendered}):
        assert (
            local_client.render_prompt(
                BASE,
                "hello",
                thinking_policy=row_contract.THINKING_POLICY_ALLOWED,
                timeout=TIMEOUT,
            )
            == rendered
        )


def test_apply_template_without_a_prompt_key_raises() -> None:
    with _post({"error": "nope"}), pytest.raises(local_client.LocalRequestError):
        local_client.render_prompt(
            BASE,
            "hello",
            thinking_policy=row_contract.THINKING_POLICY_ALLOWED,
            timeout=TIMEOUT,
        )


def test_props_returns_the_models_own_chat_template() -> None:
    with _get({"chat_template": "{% for m in messages %}{% endfor %}"}):
        assert local_client.chat_template(BASE, timeout=TIMEOUT).startswith("{% for")


@pytest.mark.parametrize(
    "payload",
    [{}, {"chat_template": ""}, {"chat_template": 3}],
    ids=["absent", "empty", "not_text"],
)
def test_props_without_a_usable_template_raises(payload: Any) -> None:
    with _get(payload), pytest.raises(local_client.LocalRequestError):
        local_client.chat_template(BASE, timeout=TIMEOUT)


def test_disabled_sends_the_thinking_kwargs_on_both_calls() -> None:
    expected = {"chat_template_kwargs": {"enable_thinking": False}}

    with _post(_CHAT_BODY) as post:
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_policy=row_contract.THINKING_POLICY_DISABLED,
            timeout=TIMEOUT,
        )
        chat_body = post.call_args.kwargs["json"]

    with _post({"prompt": "rendered"}) as post:
        local_client.render_prompt(
            BASE,
            "hello",
            thinking_policy=row_contract.THINKING_POLICY_DISABLED,
            timeout=TIMEOUT,
        )
        template_body = post.call_args.kwargs["json"]

    # Both, and identically: a prompt rendered under one policy and answered
    # under another would put a string on the row that the answering call
    # never used.
    assert chat_body["chat_template_kwargs"] == expected["chat_template_kwargs"]
    assert template_body["chat_template_kwargs"] == expected["chat_template_kwargs"]


def test_allowed_sends_the_thinking_kwargs_on_neither_call() -> None:
    with _post(_CHAT_BODY) as post:
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_policy=row_contract.THINKING_POLICY_ALLOWED,
            timeout=TIMEOUT,
        )
        assert "chat_template_kwargs" not in post.call_args.kwargs["json"]

    with _post({"prompt": "rendered"}) as post:
        local_client.render_prompt(
            BASE,
            "hello",
            thinking_policy=row_contract.THINKING_POLICY_ALLOWED,
            timeout=TIMEOUT,
        )
        assert "chat_template_kwargs" not in post.call_args.kwargs["json"]


def test_the_chat_request_carries_the_cap_and_every_pinned_sampler_key() -> None:
    with _post(_CHAT_BODY) as post:
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling={"seed": 1, "temperature": 0, "top_k": 0, "top_p": 1.0},
            thinking_policy=row_contract.THINKING_POLICY_DISABLED,
            timeout=TIMEOUT,
        )
        body = post.call_args.kwargs["json"]

    assert body["max_tokens"] == 32
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    for key in ("seed", "temperature", "top_k", "top_p"):
        assert key in body


def test_an_unknown_thinking_policy_raises_rather_than_sending_nothing() -> None:
    with pytest.raises(local_client.LocalRequestError, match="unknown thinking_policy"):
        local_client.render_prompt(
            BASE, "hello", thinking_policy="maybe", timeout=TIMEOUT
        )
