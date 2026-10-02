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

from wave_local_ai_v2 import local_client, prompt_provenance, roster, row_contract

BASE = "http://127.0.0.1:8080"
TIMEOUT = 30.0
SAMPLING: dict[str, Any] = {"seed": 1, "temperature": 0}
# The control the four shipped Qwen entries declare.
QWEN_CONTROL: dict[str, Any] = {"chat_template_kwargs": {"enable_thinking": False}}

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
            thinking_kwargs=QWEN_CONTROL,
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
            thinking_kwargs={},
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
            thinking_kwargs=QWEN_CONTROL,
            timeout=TIMEOUT,
        )


def test_apply_template_returns_the_rendered_prompt() -> None:
    rendered = "<|im_start|>user\nhello<|im_end|>\n<|im_start|>assistant\n"

    with _post({"prompt": rendered}):
        assert (
            local_client.render_prompt(
                BASE,
                "hello",
                thinking_kwargs={},
                timeout=TIMEOUT,
            )
            == rendered
        )


def test_apply_template_without_a_prompt_key_raises() -> None:
    with _post({"error": "nope"}), pytest.raises(local_client.LocalRequestError):
        local_client.render_prompt(
            BASE,
            "hello",
            thinking_kwargs={},
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


def test_the_chat_request_carries_the_cap_and_every_pinned_sampler_key() -> None:
    with _post(_CHAT_BODY) as post:
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling={"seed": 1, "temperature": 0, "top_k": 0, "top_p": 1.0},
            thinking_kwargs=QWEN_CONTROL,
            timeout=TIMEOUT,
        )
        body = post.call_args.kwargs["json"]

    assert body["max_tokens"] == 32
    assert body["messages"] == [{"role": "user", "content": "hello"}]
    for key in ("seed", "temperature", "top_k", "top_p"):
        assert key in body


# --------------------------------------------------------------------------
# The thinking control: the entry's declaration, never a module default.
# --------------------------------------------------------------------------

TEMPLATE = "{% for m in messages %}<|im_start|>{{ m.content }}{% endfor %}"


def _entry(**declared: Any) -> roster.RosterEntry:
    return roster.RosterEntry(
        entry_id="fake-entry",
        repo="fake/repo",
        revision="main",
        file="fake.gguf",
        display_id="Fake",
        quant="Q8_0",
        sha256="0" * 64,
        architecture=roster.Architecture(
            kind="dense", expert_count=0, active_params_b=0.6
        ),
        server_flags={},
        validated_host={},
        **declared,
    )


def _render_router(*, honours_control: bool) -> Any:
    """A stubbed `/apply-template` whose output does or does not move with the
    control, and a chat endpoint that counts as a call if it is ever reached."""

    def route(url: str, *args: Any, **kwargs: Any) -> MagicMock:
        body = kwargs["json"]
        if url.endswith(prompt_provenance.LOCAL_APPLY_TEMPLATE_ENDPOINT):
            rendered = f"<|im_start|>user\n{body['messages'][0]['content']}"
            if honours_control and "chat_template_kwargs" in body:
                rendered += "\n<think>\n\n</think>\n\n"
            return _response({"prompt": rendered})
        return _response(_CHAT_BODY)

    return route


@pytest.mark.parametrize(
    "declared",
    [{}, {"thinking_control": "none"}, {"thinking_control": QWEN_CONTROL}],
    ids=["undeclared", "none", "object"],
)
def test_allowed_sends_nothing_whatever_the_entry_declares(declared: Any) -> None:
    assert (
        local_client.thinking_kwargs(
            row_contract.THINKING_POLICY_ALLOWED, _entry(**declared)
        )
        == {}
    )


def test_disabled_sends_the_entrys_declared_control_as_a_copy() -> None:
    control = {"reasoning_effort": "none"}

    kwargs = local_client.thinking_kwargs(
        row_contract.THINKING_POLICY_DISABLED, _entry(thinking_control=control)
    )

    assert kwargs == control
    assert kwargs is not control


def test_disabled_sends_nothing_for_an_entry_declaring_none() -> None:
    assert (
        local_client.thinking_kwargs(
            row_contract.THINKING_POLICY_DISABLED,
            _entry(thinking_control=roster.THINKING_CONTROL_NONE),
        )
        == {}
    )


def test_disabled_refuses_an_entry_that_declares_no_control() -> None:
    # No fallback to the Qwen spelling: it is the one a non-Qwen template
    # would silently ignore.
    with pytest.raises(
        local_client.LocalRequestError,
        match="'fake-entry' declares no thinking_control",
    ):
        local_client.thinking_kwargs(row_contract.THINKING_POLICY_DISABLED, _entry())


def test_disabled_refuses_a_malformed_control_built_in_code() -> None:
    with pytest.raises(local_client.LocalRequestError, match="malformed"):
        local_client.thinking_kwargs(
            row_contract.THINKING_POLICY_DISABLED, _entry(thinking_control="off")
        )


def test_an_unknown_thinking_policy_raises_rather_than_sending_nothing() -> None:
    with pytest.raises(local_client.LocalRequestError, match="unknown thinking_policy"):
        local_client.thinking_kwargs("maybe", _entry(thinking_control=QWEN_CONTROL))


def test_the_declared_control_is_what_both_calls_send() -> None:
    control = {"reasoning_effort": "none"}

    with _post(_CHAT_BODY) as post:
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_kwargs=control,
            timeout=TIMEOUT,
        )
        chat_body = post.call_args.kwargs["json"]
    with _post({"prompt": "rendered"}) as post:
        local_client.render_prompt(
            BASE, "hello", thinking_kwargs=control, timeout=TIMEOUT
        )
        template_body = post.call_args.kwargs["json"]

    # Both, and identically: a prompt rendered under one control and answered
    # under another would put a string on the row the answering call never used.
    for body in (chat_body, template_body):
        assert body["reasoning_effort"] == "none"
        assert "chat_template_kwargs" not in body


def test_no_control_sends_no_thinking_argument_on_either_call() -> None:
    with _post(_CHAT_BODY) as post:
        local_client.complete_chat(
            BASE,
            "hello",
            max_tokens=32,
            sampling=SAMPLING,
            thinking_kwargs={},
            timeout=TIMEOUT,
        )
        assert "chat_template_kwargs" not in post.call_args.kwargs["json"]
    with _post({"prompt": "rendered"}) as post:
        local_client.render_prompt(BASE, "hello", thinking_kwargs={}, timeout=TIMEOUT)
        assert "chat_template_kwargs" not in post.call_args.kwargs["json"]


def test_a_control_the_template_ignores_is_refused_before_any_generation() -> None:
    with (
        patch(
            "wave_local_ai_v2.local_client.requests.post",
            side_effect=_render_router(honours_control=False),
        ) as post,
        pytest.raises(local_client.ThinkingControlRefused) as refused,
    ):
        local_client.verify_thinking_control(
            BASE,
            _entry(thinking_control=QWEN_CONTROL),
            chat_template=TEMPLATE,
            timeout=TIMEOUT,
        )

    message = str(refused.value)
    assert "'fake-entry'" in message
    assert '{"chat_template_kwargs": {"enable_thinking": false}}' in message
    assert prompt_provenance.template_hash(TEMPLATE) in message
    # Two renders and nothing else: no generation was asked for.
    urls = [call.args[0] for call in post.call_args_list]
    assert urls == [f"{BASE}{prompt_provenance.LOCAL_APPLY_TEMPLATE_ENDPOINT}"] * 2
    bodies = [call.kwargs["json"] for call in post.call_args_list]
    assert bodies[0]["chat_template_kwargs"] == QWEN_CONTROL["chat_template_kwargs"]
    assert "chat_template_kwargs" not in bodies[1]
    for body in bodies:
        assert body["messages"] == [
            {"role": "user", "content": local_client.THINKING_PROBE_MESSAGE}
        ]


def test_a_control_that_changes_the_render_passes_with_both_strings() -> None:
    with patch(
        "wave_local_ai_v2.local_client.requests.post",
        side_effect=_render_router(honours_control=True),
    ):
        probe = local_client.verify_thinking_control(
            BASE,
            _entry(thinking_control=QWEN_CONTROL),
            chat_template=TEMPLATE,
            timeout=TIMEOUT,
        )

    assert probe["with_control"] != probe["without_control"]
    assert probe["with_control"].endswith("<think>\n\n</think>\n\n")


@pytest.mark.parametrize(
    "declared",
    [{}, {"thinking_control": "none"}],
    ids=["undeclared", "none"],
)
def test_only_an_object_control_can_be_verified(declared: Any) -> None:
    with (
        patch("wave_local_ai_v2.local_client.requests.post") as post,
        pytest.raises(local_client.LocalRequestError, match="no request arguments"),
    ):
        local_client.verify_thinking_control(
            BASE, _entry(**declared), chat_template=TEMPLATE, timeout=TIMEOUT
        )
    assert post.call_count == 0


def _probe(message: Any) -> str:
    with _post({"choices": [{"message": message}]}) as post:
        reasoning = local_client.probe_reasoning(BASE, max_tokens=64, timeout=TIMEOUT)
    body = post.call_args.kwargs["json"]
    assert body["messages"][0]["content"] == local_client.THINKING_PROBE_MESSAGE
    assert "chat_template_kwargs" not in body
    return reasoning


def test_probe_reasoning_returns_the_reasoning_a_generation_carried() -> None:
    assert _probe({"content": "ready", "reasoning_content": "Hmm."}) == "Hmm."
    assert _probe({"content": "<think>x</think>ready"}) == "<think>x</think>ready"
    assert _probe({"content": "ready", "reasoning_content": " "}) == ""
    assert _probe({"content": None}) == ""


def test_probe_reasoning_refuses_a_body_with_no_message() -> None:
    with (
        _post({"choices": []}),
        pytest.raises(local_client.LocalRequestError, match="response shape"),
    ):
        local_client.probe_reasoning(BASE, max_tokens=64, timeout=TIMEOUT)
