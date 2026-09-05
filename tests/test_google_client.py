from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2.google_client import (
    CATALOG_TIMEOUT_S,
    MODEL,
    REQUEST_TIMEOUT_S,
    ContextWindowExceededError,
    GoogleBlockedError,
    GoogleRequestError,
    ModelUnavailableError,
    check_context_fits,
    check_model_available,
    complete_prompt,
)

# The endpoints as recorded live on 2026-08-27, spelled out rather than
# imported: comparing a recorded call argument to the module constant that
# produced it passes for any value that constant holds, including the other
# endpoint's.
EXPECTED_GENERATE_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-3.5-flash-lite:generateContent"
)
EXPECTED_CATALOG_URL = (
    "https://generativelanguage.googleapis.com/v1/models/gemini-3.5-flash-lite"
)
EXPECTED_COUNT_TOKENS_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-3.5-flash-lite:countTokens"
)

SAMPLING = {"temperature": 0, "top_p": 1, "top_k": 1, "seed": 20260827}
# Deliberately not the suite's own value: a value the module could never have
# hardcoded proves the caller's cap is what reaches the request body.
MAX_TOKENS = 17


def _generate(
    *, finish_reason="STOP", text="billing", candidates_tokens=3, **overrides
):
    body = {
        "candidates": [
            {
                "content": {"parts": [{"text": text}]},
                "finishReason": finish_reason,
            }
        ],
        "usageMetadata": {
            "candidatesTokenCount": candidates_tokens,
            "promptTokenCount": 12,
            "totalTokenCount": 12 + candidates_tokens,
        },
        "modelVersion": "3.5-flash-lite-07-2026",
    }
    body.update(overrides)
    return body


def _catalog_entry(**overrides) -> dict:
    entry = {
        "name": f"models/{MODEL}",
        "version": "3.5-flash-lite-07-2026",
        "inputTokenLimit": 1_048_576,
    }
    entry.update(overrides)
    return entry


def test_complete_prompt_returns_content_and_sends_expected_request() -> None:
    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: _generate()),
    ) as post:
        result = complete_prompt(
            "classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS
        )

    assert result["content"] == "billing"
    assert result["endpoint"] == EXPECTED_GENERATE_URL
    assert result["finish_reason"] == "STOP"
    assert result["generated_tokens"] == 3
    assert result["prompt_tokens"] == 12
    assert result["total_tokens"] == 15
    assert result["model_version"] == "3.5-flash-lite-07-2026"

    args, kwargs = post.call_args
    assert args[0] == EXPECTED_GENERATE_URL
    assert kwargs["headers"]["x-goog-api-key"] == "fake-key"
    assert kwargs["json"]["contents"] == [
        {"role": "user", "parts": [{"text": "classify this"}]}
    ]
    config = kwargs["json"]["generationConfig"]
    assert config["temperature"] == 0
    assert config["topP"] == 1
    assert config["topK"] == 1
    assert config["seed"] == 20260827
    assert config["maxOutputTokens"] == MAX_TOKENS
    assert config["candidateCount"] == 1
    assert "thinkingConfig" not in kwargs["json"]
    assert "stopSequences" not in kwargs["json"]


def test_complete_prompt_raises_on_non_200_status() -> None:
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(
                status_code=401,
                text="unauthorized",
                json=lambda: {"error": {"details": []}},
            ),
        ),
        pytest.raises(GoogleRequestError, match="401"),
    ):
        complete_prompt("classify this", "bad-key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_complete_prompt_surfaces_the_retry_delay_on_a_429() -> None:
    body = {
        "error": {
            "status": "RESOURCE_EXHAUSTED",
            "details": [
                {
                    "@type": "type.googleapis.com/google.rpc.RetryInfo",
                    "retryDelay": "31s",
                }
            ],
        }
    }
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=429, text="", json=lambda: body),
        ),
        pytest.raises(GoogleRequestError, match="31s"),
    ):
        complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_complete_prompt_generated_tokens_defaults_to_zero_when_absent() -> None:
    # candidatesTokenCount is absent, not zero, per the decision file -- a
    # client copied from mistral_client's subscript would raise here.
    body = _generate(text="", candidates_tokens=0)
    del body["usageMetadata"]["candidatesTokenCount"]
    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: body),
    ):
        result = complete_prompt(
            "classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS
        )

    assert result["generated_tokens"] == 0
    assert result["content"] == ""


def test_complete_prompt_tolerates_a_content_object_with_no_parts_key() -> None:
    body = _generate()
    body["candidates"][0]["content"] = {}
    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: body),
    ):
        result = complete_prompt(
            "classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS
        )

    assert result["content"] == ""


def test_complete_prompt_returns_max_tokens_finish_reason_verbatim() -> None:
    # Truncation cause is decided from finishReason directly by the caller
    # (phase 2), never from generated_tokens >= max_output_tokens here --
    # Google can report fewer output tokens than the cap it enforced.
    body = _generate(finish_reason="MAX_TOKENS", candidates_tokens=4)
    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: body),
    ):
        result = complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=8)

    assert result["finish_reason"] == "MAX_TOKENS"
    assert result["generated_tokens"] == 4


def test_complete_prompt_raises_blocked_error_on_safety_finish_reason() -> None:
    body = _generate(finish_reason="SAFETY")
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=200, json=lambda: body),
        ),
        pytest.raises(GoogleBlockedError, match="SAFETY"),
    ):
        complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS)


@pytest.mark.parametrize("finish_reason", ["OTHER", "MALFORMED_FUNCTION_CALL"])
def test_complete_prompt_raises_blocked_error_on_unmapped_finish_reason(
    finish_reason,
) -> None:
    body = _generate(finish_reason=finish_reason)
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=200, json=lambda: body),
        ),
        pytest.raises(GoogleBlockedError, match=finish_reason),
    ):
        complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_complete_prompt_raises_on_non_string_finish_reason() -> None:
    body = _generate()
    body["candidates"][0]["finishReason"] = None
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=200, json=lambda: body),
        ),
        pytest.raises(GoogleRequestError, match="finishReason"),
    ):
        complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_complete_prompt_raises_on_non_int_token_count() -> None:
    body = _generate()
    body["usageMetadata"]["candidatesTokenCount"] = "3"
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=200, json=lambda: body),
        ),
        pytest.raises(GoogleRequestError, match="candidatesTokenCount"),
    ):
        complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_complete_prompt_raises_on_missing_candidates() -> None:
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(
                status_code=200, json=lambda: {"no_candidates": True}
            ),
        ),
        pytest.raises(GoogleRequestError),
    ):
        complete_prompt("classify this", "fake-key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_check_model_available_returns_version_and_input_token_limit() -> None:
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.get",
            return_value=MagicMock(status_code=200, json=lambda: _catalog_entry()),
        ) as get,
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=200, json=lambda: _generate()),
        ) as post,
    ):
        info = check_model_available("fake-key")

    assert info == {"version": "3.5-flash-lite-07-2026", "input_token_limit": 1_048_576}
    get_args, get_kwargs = get.call_args
    assert get_args[0] == EXPECTED_CATALOG_URL
    assert get_kwargs["headers"]["x-goog-api-key"] == "fake-key"
    assert get_kwargs["timeout"] == CATALOG_TIMEOUT_S
    assert CATALOG_TIMEOUT_S < REQUEST_TIMEOUT_S
    post_args, _ = post.call_args
    assert post_args[0] == EXPECTED_GENERATE_URL


def test_check_model_available_raises_when_absent_from_the_catalog() -> None:
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.get",
            return_value=MagicMock(status_code=404, text="not found"),
        ),
        pytest.raises(ModelUnavailableError, match=MODEL),
    ):
        check_model_available("fake-key")


def test_check_model_available_raises_when_the_probe_404s() -> None:
    # Presence on the catalog does not mean the model answers: a retired
    # model still has a full catalog entry and 404s on generateContent.
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.get",
            return_value=MagicMock(status_code=200, json=lambda: _catalog_entry()),
        ),
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(status_code=404, text="no longer available"),
        ),
        pytest.raises(ModelUnavailableError, match=MODEL) as exc_info,
    ):
        check_model_available("fake-key")

    # Both endpoints, so the message says what was checked and what refused --
    # asserting only the generate URL would pass on a message that never named
    # the catalog the model was found on.
    assert EXPECTED_CATALOG_URL in str(exc_info.value)
    assert EXPECTED_GENERATE_URL in str(exc_info.value)


def test_model_unavailable_is_caught_by_the_existing_handler() -> None:
    # quality_cli.main excepts GoogleRequestError; the subclass keeps that
    # handler correct without widening it.
    assert issubclass(ModelUnavailableError, GoogleRequestError)
    assert issubclass(ContextWindowExceededError, GoogleRequestError)
    assert issubclass(GoogleBlockedError, GoogleRequestError)


def test_check_context_fits_raises_when_the_token_count_exceeds_the_limit() -> None:
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(
                status_code=200, json=lambda: {"totalTokens": 2_000_000}
            ),
        ) as post,
        pytest.raises(ContextWindowExceededError, match="2000000"),
    ):
        check_context_fits(
            "a very long prompt", "fake-key", input_token_limit=1_048_576
        )

    args, _ = post.call_args
    assert args[0] == EXPECTED_COUNT_TOKENS_URL


def test_check_context_fits_does_not_raise_when_the_prompt_fits() -> None:
    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: {"totalTokens": 100}),
    ):
        check_context_fits("short", "fake-key", input_token_limit=1_048_576)


def test_check_context_fits_never_calls_generate_content() -> None:
    calls = []
    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        side_effect=lambda url, **kwargs: (
            calls.append(url)
            or MagicMock(status_code=200, json=lambda: {"totalTokens": 100})
        ),
    ):
        check_context_fits("short", "fake-key", input_token_limit=1_048_576)

    assert calls == [EXPECTED_COUNT_TOKENS_URL]


def test_complete_prompt_raises_on_non_200_and_malformed_bodies() -> None:
    with (
        patch(
            "wave_local_ai_v2.google_client.requests.post",
            return_value=MagicMock(
                status_code=401, text="", json=lambda: {"error": {"details": []}}
            ),
        ),
        pytest.raises(GoogleRequestError, match="401"),
    ):
        complete_prompt("x", "key", **SAMPLING, max_tokens=MAX_TOKENS)


def test_model_id_is_pinned_not_the_floating_alias() -> None:
    assert MODEL != "gemini-flash-lite-latest"
