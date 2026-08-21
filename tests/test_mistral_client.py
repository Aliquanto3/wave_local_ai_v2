from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2.mistral_client import (
    API_URL,
    MODEL,
    MistralRequestError,
    complete_prompt,
)

SAMPLE_RESPONSE = {"choices": [{"message": {"content": "billing"}}]}


def test_complete_prompt_returns_content_and_sends_expected_request() -> None:
    with patch(
        "wave_local_ai_v2.mistral_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE),
    ) as post:
        result = complete_prompt("classify this", "fake-key")

    assert result == "billing"
    args, kwargs = post.call_args
    assert args[0] == API_URL
    assert kwargs["headers"]["Authorization"] == "Bearer fake-key"
    assert kwargs["json"]["model"] == MODEL
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "classify this"}]


def test_complete_prompt_raises_on_non_200_status() -> None:
    with (
        patch(
            "wave_local_ai_v2.mistral_client.requests.post",
            return_value=MagicMock(status_code=401, text="unauthorized"),
        ),
        pytest.raises(MistralRequestError, match="401"),
    ):
        complete_prompt("classify this", "bad-key")


def test_complete_prompt_raises_on_malformed_response_body() -> None:
    with (
        patch(
            "wave_local_ai_v2.mistral_client.requests.post",
            return_value=MagicMock(
                status_code=200, json=lambda: {"no_choices_here": True}
            ),
        ),
        pytest.raises(MistralRequestError),
    ):
        complete_prompt("classify this", "fake-key")
