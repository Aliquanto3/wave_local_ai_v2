import pytest

from wave_local_ai_v2.prompt_provenance import (
    LOCAL_COMPLETION_ENDPOINT,
    PROMPT_CAPTURE_CAPTURED,
    TEMPLATE_ID_MISTRAL_CHAT_MESSAGE,
    TEMPLATE_ID_NONE,
    is_consistent,
    template_hash,
)
from wave_local_ai_v2.row_contract import RowContractError, validate_row

_OTHER_ENDPOINT = "https://api.mistral.ai/v1/chat/completions"

_MINIMAL_QUALITY_ROW = {
    "schema_version": "1",
    "run_id": "run-1",
    "captured_at": "2026-08-22T00:00:00+00:00",
    "release_version": "v0.1.0",
    "commit_sha": "deadbeef",
    "tree_dirty": False,
    "prompt_template_hash": None,
    "prompt_capture": PROMPT_CAPTURE_CAPTURED,
    "model_id": "Qwen3.6-35B-A3B",
    "provider": "local",
    "task_suite": "classification",
    "item_id": "billing-01",
    "prompt": "hello",
    "expected_label": "billing",
    "predicted_label": "billing",
    "correct": True,
    "suite_accuracy": 1.0,
    "sampling": {"seed": 1},
    "max_output_tokens": 32,
    "stop_sequences": [],
    "context_length": 32768,
    "suite_id": "classification-support-routing",
    "suite_version": "1",
    "prompt_set_hash": "deadbeef",
    "language": "en",
    "provenance": "hand_written",
    "contamination_risk": False,
    "indicative": True,
    "indicative_reasons": [],
    "failure_reason": None,
    "failure_counts": {
        "empty": 0,
        "unparseable": 0,
        "truncated_max_tokens": 0,
        "truncated_context": 0,
    },
}


def test_none_is_consistent_with_the_raw_local_endpoint() -> None:
    assert is_consistent(LOCAL_COMPLETION_ENDPOINT, TEMPLATE_ID_NONE) is True


def test_none_is_inconsistent_with_a_non_raw_endpoint() -> None:
    assert is_consistent(_OTHER_ENDPOINT, TEMPLATE_ID_NONE) is False


def test_a_named_template_is_consistent_with_a_non_raw_endpoint() -> None:
    assert is_consistent(_OTHER_ENDPOINT, TEMPLATE_ID_MISTRAL_CHAT_MESSAGE) is True


def test_template_hash_of_none_is_none() -> None:
    assert template_hash(None) is None


def test_template_hash_is_stable_for_a_fixed_string() -> None:
    assert template_hash("fixed") == template_hash("fixed")


def test_writer_gate_refuses_the_inconsistent_pair() -> None:
    row = {
        **_MINIMAL_QUALITY_ROW,
        "endpoint": _OTHER_ENDPOINT,
        "prompt_template_id": TEMPLATE_ID_NONE,
    }

    with pytest.raises(RowContractError):
        validate_row("quality", row)
