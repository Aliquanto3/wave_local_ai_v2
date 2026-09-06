from pathlib import Path

import pytest

from wave_local_ai_v2 import judge
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
