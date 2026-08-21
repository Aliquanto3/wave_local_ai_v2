from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2.mistral_client import (
    API_URL,
    MODEL,
    MistralRequestError,
    complete_prompt,
)

SAMPLING = {"temperature": 0, "random_seed": 20260821}

SAMPLE_RESPONSE = {"choices": [{"message": {"content": "billing"}}]}


def test_complete_prompt_returns_content_and_sends_expected_request() -> None:
    with patch(
        "wave_local_ai_v2.mistral_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE),
    ) as post:
        result = complete_prompt("classify this", "fake-key", **SAMPLING)

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
        complete_prompt("classify this", "bad-key", **SAMPLING)


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
        complete_prompt("classify this", "fake-key", **SAMPLING)


def test_complete_prompt_pins_temperature_and_random_seed_in_the_request() -> None:
    with patch(
        "wave_local_ai_v2.mistral_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: SAMPLE_RESPONSE),
    ) as post:
        complete_prompt("classify this", "fake-key", temperature=0, random_seed=99)

    body = post.call_args.kwargs["json"]
    assert body["temperature"] == 0
    assert body["random_seed"] == 99


def test_model_id_is_dated_not_a_rotating_alias() -> None:
    # An alias silently re-points at a new model, which no seed can compensate
    # for: two runs either side of a rotation would disagree and the quality
    # score would stop being reproducible on model + prompt + seed.
    assert not MODEL.endswith("-latest")
