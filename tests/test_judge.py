from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wave_local_ai_v2 import (
    google_client,
    judge,
    judge_backends,
    mistral_client,
    retry,
    row_contract,
)
from wave_local_ai_v2.agreement import DEFAULT_CONTESTED_THRESHOLD
from wave_local_ai_v2.judge import JudgeResponse, run_judge_call
from wave_local_ai_v2.judge_protocol import (
    OPEN_ENDED_QUALITY_1_TO_5,
    RUBRIC_KIND_CATEGORICAL,
    Rubric,
    render_judge_prompt,
)

CATEGORICAL_RUBRIC = Rubric(
    rubric_id="test-categorical",
    version="1",
    kind=RUBRIC_KIND_CATEGORICAL,
    scale=None,
    categories=frozenset({"adequate", "partial", "inadequate"}),
    text={"en": "Answer with exactly one of: adequate, partial, inadequate."},
)

RENDERED = render_judge_prompt(
    rubric=OPEN_ENDED_QUALITY_1_TO_5,
    language="en",
    item_prompt="Summarise this paragraph.",
    subject_output="A short summary.",
)


class _ScriptedBackend:
    """A JudgeBackend returning a fixed string, recording the prompt it saw."""

    def __init__(self, content: str) -> None:
        self._content = content
        self.prompts: list[str] = []

    def __call__(self, prompt: str) -> JudgeResponse:
        self.prompts.append(prompt)
        return JudgeResponse(
            content=self._content,
            model_id="judge-model-1",
            provider="stub",
            family="stub-family",
            tokens_in=120,
            tokens_out=3,
            retries=0,
        )


def test_a_scored_reply_is_recorded_with_its_raw_text() -> None:
    backend = _ScriptedBackend("4")

    record = run_judge_call(backend, RENDERED, OPEN_ENDED_QUALITY_1_TO_5)

    assert record["score"] == 4
    assert record["score"] in OPEN_ENDED_QUALITY_1_TO_5.scale
    assert record["failure_reason"] is None
    assert record["raw_text"] == "4"
    assert record["model_id"] == "judge-model-1"
    assert record["tokens_in"] == 120
    assert backend.prompts == [RENDERED["prompt"]]


def test_a_score_outside_the_scale_is_named_and_never_zero() -> None:
    record = run_judge_call(_ScriptedBackend("7"), RENDERED, OPEN_ENDED_QUALITY_1_TO_5)

    assert record["score"] is None
    assert record["failure_reason"] == "judge_score_out_of_scale"
    assert record["raw_text"] == "7"


def test_prose_with_no_score_is_unparseable_and_keeps_the_prose() -> None:
    prose = "The answer is broadly reasonable but I would not commit to a number."

    record = run_judge_call(
        _ScriptedBackend(prose), RENDERED, OPEN_ENDED_QUALITY_1_TO_5
    )

    assert record["score"] is None
    assert record["failure_reason"] == "judge_response_unparseable"
    assert record["raw_text"] == prose


def test_two_candidate_integers_are_unparseable() -> None:
    record = run_judge_call(
        _ScriptedBackend("4/5"), RENDERED, OPEN_ENDED_QUALITY_1_TO_5
    )

    assert record["score"] is None
    assert record["failure_reason"] == "judge_response_unparseable"


def test_an_empty_reply_is_named_empty() -> None:
    record = run_judge_call(_ScriptedBackend(""), RENDERED, OPEN_ENDED_QUALITY_1_TO_5)

    assert record["score"] is None
    assert record["failure_reason"] == "judge_response_empty"


def test_a_whitespace_only_reply_is_named_empty() -> None:
    record = run_judge_call(
        _ScriptedBackend("  \n "), RENDERED, OPEN_ENDED_QUALITY_1_TO_5
    )

    assert record["failure_reason"] == "judge_response_empty"


def test_a_categorical_reply_is_normalised_through_scoring() -> None:
    record = run_judge_call(_ScriptedBackend("partial"), RENDERED, CATEGORICAL_RUBRIC)

    assert record["score"] == "partial"
    assert record["failure_reason"] is None


def test_a_categorical_reply_outside_the_categories_is_unparseable() -> None:
    record = run_judge_call(_ScriptedBackend("excellent"), RENDERED, CATEGORICAL_RUBRIC)

    assert record["score"] is None
    assert record["failure_reason"] == "judge_response_unparseable"


def test_a_transport_failure_propagates_untouched() -> None:
    class _FailingBackend:
        def __call__(self, prompt: str) -> JudgeResponse:
            raise RuntimeError("provider exploded")

    with pytest.raises(RuntimeError, match="provider exploded"):
        run_judge_call(_FailingBackend(), RENDERED, OPEN_ENDED_QUALITY_1_TO_5)


def test_judge_module_names_no_provider_client() -> None:
    source = Path(judge.__file__).read_text(encoding="utf-8")

    assert "import mistral_client" not in source
    assert "import google_client" not in source
    assert "mistral_client." not in source
    assert "google_client." not in source


def test_the_call_record_field_set_matches_the_typed_dict() -> None:
    record = run_judge_call(_ScriptedBackend("3"), RENDERED, OPEN_ENDED_QUALITY_1_TO_5)

    assert set(record) == judge.JUDGE_CALL_RECORD_FIELDS


# --- Phase 3: family independence, the backends, and the judged block ---


MISTRAL_JUDGE_BODY = {
    "choices": [{"message": {"content": "4"}, "finish_reason": "stop"}],
    "usage": {"completion_tokens": 1, "prompt_tokens": 210, "total_tokens": 211},
}

GOOGLE_JUDGE_BODY = {
    "candidates": [
        {"content": {"parts": [{"text": "4"}]}, "finishReason": "STOP"},
    ],
    "usageMetadata": {
        "candidatesTokenCount": 1,
        "promptTokenCount": 190,
        "totalTokenCount": 191,
    },
    "modelVersion": "3.5-flash-lite-07-2026",
}


def _fixed_score_backend(provider: str, family: str, model_id: str, score: int):
    def call(prompt: str) -> JudgeResponse:
        return JudgeResponse(
            content=str(score),
            model_id=model_id,
            provider=provider,
            family=family,
            tokens_in=200,
            tokens_out=1,
            retries=0,
        )

    return call


def _mistral_judge(score: int = 4) -> judge.Judge:
    return judge.Judge(
        model_id="mistral-small-2603",
        provider="mistral",
        family="mistral",
        backend=_fixed_score_backend("mistral", "mistral", "mistral-small-2603", score),
    )


def _google_judge(score: int = 4) -> judge.Judge:
    return judge.Judge(
        model_id="gemini-3.5-flash-lite",
        provider="google",
        family="google",
        backend=_fixed_score_backend(
            "google", "google", "gemini-3.5-flash-lite", score
        ),
    )


def _judge_item(subject_family: str, subject_provider: str, judges: list[judge.Judge]):
    return judge.judge_item(
        subject_family=subject_family,
        subject_provider=subject_provider,
        subject_output="A short summary.",
        item_prompt="Summarise this paragraph.",
        item_language="en",
        rubric=OPEN_ENDED_QUALITY_1_TO_5,
        judges=judges,
        threshold=DEFAULT_CONTESTED_THRESHOLD,
    )


def test_the_mistral_backend_maps_a_normal_body_to_a_judge_response() -> None:
    backend = judge_backends.mistral_judge_backend(
        "fake-key",
        pacer=retry.Pacer(0.0),
        budget=retry.RetryBudget(2),
        temperature=0,
        random_seed=20260906,
        max_tokens=8,
    )

    with patch(
        "wave_local_ai_v2.mistral_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: MISTRAL_JUDGE_BODY),
    ):
        response = backend("judge this")

    assert response["provider"] == "mistral"
    assert response["family"] == "mistral"
    assert response["model_id"] == mistral_client.MODEL
    assert response["tokens_in"] == 210
    assert response["tokens_out"] == 1
    assert response["retries"] == 0


def test_the_google_backend_maps_its_own_body_to_the_same_shape() -> None:
    backend = judge_backends.google_judge_backend(
        "fake-key",
        pacer=retry.Pacer(0.0),
        budget=retry.RetryBudget(2),
        temperature=0,
        top_p=1,
        top_k=1,
        seed=20260906,
        max_tokens=8,
    )

    with patch(
        "wave_local_ai_v2.google_client.requests.post",
        return_value=MagicMock(status_code=200, json=lambda: GOOGLE_JUDGE_BODY),
    ):
        record = run_judge_call(backend, RENDERED, OPEN_ENDED_QUALITY_1_TO_5)

    # The same run_judge_call consumes both backends with no branch.
    assert record["provider"] == "google"
    assert record["model_id"] == google_client.MODEL
    assert record["score"] == 4
    assert record["tokens_in"] == 190


def test_an_exhausted_retry_budget_propagates_out_of_the_backend() -> None:
    backend = judge_backends.mistral_judge_backend(
        "fake-key",
        pacer=retry.Pacer(0.0),
        budget=retry.RetryBudget(0),
        temperature=0,
        random_seed=20260906,
        max_tokens=8,
    )

    with (
        patch(
            "wave_local_ai_v2.mistral_client.requests.post",
            return_value=MagicMock(status_code=429, text="slow down", headers={}),
        ),
        pytest.raises(retry.RetryBudgetExhausted),
    ):
        backend("judge this")


def test_judge_backends_is_the_only_judge_path_module_naming_a_client() -> None:
    judge_path = ("judge.py", "judge_protocol.py", "agreement.py", "judge_backends.py")
    source_dir = Path(judge.__file__).parent
    naming = {
        name
        for name in judge_path
        if "mistral_client" in (source_dir / name).read_text(encoding="utf-8")
        or "google_client" in (source_dir / name).read_text(encoding="utf-8")
    }

    assert naming == {"judge_backends.py"}


def test_a_judge_of_the_subjects_own_family_is_refused_before_any_call() -> None:
    with (
        patch("wave_local_ai_v2.mistral_client.requests.post") as post,
        pytest.raises(judge.JudgeFamilyCollisionError, match="mistral-small-2603"),
    ):
        _judge_item("mistral", "mistral", [_mistral_judge(), _google_judge()])

    assert post.call_count == 0


def test_a_local_subject_is_judged_by_both_families_with_an_agreement() -> None:
    block = _judge_item("qwen", "local", [_mistral_judge(4), _google_judge(4)])

    assert len(block["judges"]) == 2
    assert block["single_judge"] is False
    assert block["single_judge_reason"] is None
    assert block["agreement"] is not None
    assert block["agreement_statistic"] == "cohens_kappa_quadratic_weighted"
    assert block["judge_egress"]["providers"] == ["google", "mistral"]
    assert block["judge_egress"]["judge_call_count"] == 2
    assert block["judge_egress"]["generation_count"] == 1


def test_a_cloud_subject_is_judged_once_and_flagged() -> None:
    block = _judge_item("mistral", "mistral", [_google_judge(4)])

    assert len(block["judges"]) == 1
    assert block["agreement"] is None
    assert block["agreement_statistic"] is None
    assert block["single_judge"] is True
    assert block["single_judge_reason"] == "cloud_subject_other_family_only"
    assert block["judge_egress"]["judge_call_count"] == 1
    assert block["contested"] is False


def test_the_judged_block_carries_exactly_the_contracts_field_set() -> None:
    block = _judge_item("qwen", "local", [_mistral_judge(4), _google_judge(4)])

    assert set(block) == row_contract.JUDGED_FIELDS


def test_a_two_point_disagreement_is_contested_and_keeps_both_scores() -> None:
    block = _judge_item("qwen", "local", [_mistral_judge(2), _google_judge(4)])

    assert block["contested"] is True
    assert block["contested_reason"] == "ordinal_delta_above_threshold"
    assert [record["score"] for record in block["judges"]] == [2, 4]
    assert block["contested_threshold"] == {"max_ordinal_delta": 1}


def test_a_contested_item_is_excluded_from_the_headline() -> None:
    block = _judge_item("qwen", "local", [_mistral_judge(2), _google_judge(4)])

    assert block["judged_headline_score"] is None
    assert block["judged_headline_excluded_n"] == 1


def test_no_judge_at_all_is_refused_naming_the_subject() -> None:
    with pytest.raises(ValueError, match="mistral"):
        _judge_item("mistral", "mistral", [])


def test_more_than_two_judges_is_refused() -> None:
    with pytest.raises(ValueError, match="exactly two"):
        _judge_item(
            "qwen", "local", [_mistral_judge(4), _google_judge(4), _google_judge(3)]
        )


def test_the_judged_block_costs_each_judge_at_its_own_providers_rates() -> None:
    block = _judge_item("qwen", "local", [_mistral_judge(4), _google_judge(4)])
    per_provider = {
        entry["provider"]: entry for entry in block["judge_cost"]["per_provider"]
    }

    assert per_provider["mistral"]["list_price_input_per_million"] == 0.15
    assert per_provider["google"]["list_price_input_per_million"] == 0.30
    assert block["judge_cost"]["tokens_in_total"] == 400
