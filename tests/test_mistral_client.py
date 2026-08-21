from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2.mistral_client import (
    CATALOG_TIMEOUT_S,
    MODEL,
    REQUEST_TIMEOUT_S,
    MistralRequestError,
    ModelUnavailableError,
    check_model_available,
    complete_prompt,
)

# The endpoints as recorded live on 2026-08-21, spelled out rather than imported:
# comparing a recorded call argument to the module constant that produced it
# passes for any value that constant holds, including the other endpoint's.
EXPECTED_CHAT_COMPLETIONS_URL = "https://api.mistral.ai/v1/chat/completions"
EXPECTED_MODELS_URL = "https://api.mistral.ai/v1/models"

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
    assert args[0] == EXPECTED_CHAT_COMPLETIONS_URL
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


# Mirrors the live GET /v1/models shape recorded in the plan's Resources table
# on 2026-08-21: a `data` list whose entries carry `id`, `deprecation` (an
# ISO-8601 timestamp or null) and `deprecation_replacement_model`.
def _catalog(*entries: dict) -> dict:
    return {"object": "list", "data": list(entries)}


CURRENT_ENTRY = {
    "id": MODEL,
    "deprecation": None,
    "deprecation_replacement_model": None,
}
DEPRECATED_ENTRY = {
    "id": "mistral-medium-2505",
    "deprecation": "2026-08-31T12:00:00Z",
    "deprecation_replacement_model": "mistral-medium-3-5",
}


def _patch_catalog(body, status_code: int = 200, text: str = ""):
    return patch(
        "wave_local_ai_v2.mistral_client.requests.get",
        return_value=MagicMock(
            status_code=status_code, json=MagicMock(return_value=body), text=text
        ),
    )


def test_check_model_available_returns_no_notice_for_a_current_model() -> None:
    with _patch_catalog(_catalog(DEPRECATED_ENTRY, CURRENT_ENTRY)) as get:
        assert check_model_available("fake-key") is None

    assert get.call_count == 1
    args, kwargs = get.call_args
    assert args[0] == EXPECTED_MODELS_URL
    assert kwargs["headers"]["Authorization"] == "Bearer fake-key"
    assert kwargs["timeout"] == CATALOG_TIMEOUT_S
    assert CATALOG_TIMEOUT_S < REQUEST_TIMEOUT_S


def test_check_model_available_reports_the_date_and_replacement_when_deprecated() -> (
    None
):
    with _patch_catalog(_catalog(DEPRECATED_ENTRY)):
        notice = check_model_available("fake-key", model="mistral-medium-2505")

    assert notice is not None
    assert "mistral-medium-2505" in notice
    assert "2026-08-31T12:00:00Z" in notice
    assert "mistral-medium-3-5" in notice


def test_check_model_available_raises_when_the_id_is_absent() -> None:
    with (
        _patch_catalog(_catalog(DEPRECATED_ENTRY)),
        pytest.raises(ModelUnavailableError, match="mistral-small-2603"),
    ):
        check_model_available("fake-key", model="mistral-small-2603")


def test_model_unavailable_is_caught_by_the_existing_handler() -> None:
    # quality_cli.main already excepts MistralRequestError; the subclass keeps
    # that handler correct without widening it. Stated directly rather than
    # re-run through a mocked catalog: the absent-id test above already covers
    # that path, and the class statement is the whole of this contract.
    assert issubclass(ModelUnavailableError, MistralRequestError)


def test_check_model_available_raises_on_non_200_status() -> None:
    with (
        _patch_catalog(
            None, status_code=401, text='{"detail":"Invalid API Key"}'
        ) as get,
        pytest.raises(MistralRequestError, match="401"),
    ):
        check_model_available("bad-key")

    # A 401 body is valid JSON, so "it raised" alone would not prove the client
    # stopped at the status line rather than searching an error body for models.
    get.return_value.json.assert_not_called()


def test_check_model_available_raises_on_a_catalog_without_a_data_list() -> None:
    # The bare list stands for a body that is not a mapping at all, where the
    # `data` lookup itself would raise AttributeError instead of MistralRequestError.
    for body in ({"object": "list"}, {"object": "list", "data": "not-a-list"}, []):
        with (
            _patch_catalog(body),
            pytest.raises(MistralRequestError),
        ):
            check_model_available("fake-key")


def test_complete_prompt_rejects_a_null_content() -> None:
    # Mistral returns content null on tool-call and refusal finish reasons.
    # Reaching normalize_label with it would raise AttributeError, outside the
    # CLI's except tuple, as a raw traceback.
    with (
        patch(
            "wave_local_ai_v2.mistral_client.requests.post",
            return_value=MagicMock(
                status_code=200,
                json=lambda: {"choices": [{"message": {"content": None}}]},
            ),
        ),
        pytest.raises(MistralRequestError, match="unexpected Mistral content"),
    ):
        complete_prompt("x", "key", temperature=0, random_seed=1)
