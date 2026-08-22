from unittest.mock import MagicMock

import pytest

from wave_local_ai_v2.repetitions import (
    RepetitionFailure,
    RepetitionResult,
    run_repetition_set,
)

SAMPLE_RESPONSE = {
    "content": "hello",
    "timings": {
        "prompt_ms": 457.1,
        "prompt_per_second": 280.0,
        "predicted_per_second": 26.0,
    },
    "stop_type": "limit",
    "tokens_predicted": 128,
}


def _stub_reads():
    read_gpu = MagicMock(return_value={"vram_used_mib": 3161.0, "gpu_draw_w": 45.0})
    read_rss = MagicMock(return_value=500_000_000)
    read_machine_state = MagicMock(
        return_value={
            "gpu_temp_c": 68.0,
            "gpu_throttle_reasons": [],
            "cpu_temp_c": None,
            "cpu_temp_source": "unavailable",
        }
    )
    return read_gpu, read_rss, read_machine_state


def test_issues_one_warmup_then_n_counted_requests_in_order() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()
    sleep = MagicMock()

    warmups, counted = run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=sleep,
        warmup_count=1,
        count=5,
        cooldown_s=10.0,
    )

    assert send.call_count == 6
    assert len(warmups) == 1
    assert len(counted) == 5


def test_counted_indices_are_contiguous_and_warmup_carries_index_zero() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()

    warmups, counted = run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=MagicMock(),
        warmup_count=1,
        count=5,
        cooldown_s=10.0,
    )

    assert [w["index"] for w in warmups] == [0]
    assert [c["index"] for c in counted] == [1, 2, 3, 4, 5]


def test_cooldown_runs_after_warmup_and_between_counted_not_after_last() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()
    sleep = MagicMock()

    run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=sleep,
        warmup_count=1,
        count=5,
        cooldown_s=10.0,
    )

    # 1 after the last warm-up + (5 - 1) between counted repetitions.
    assert sleep.call_count == 5
    sleep.assert_called_with(10.0)


def test_no_cooldown_after_warmup_when_warmup_count_is_zero() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()
    sleep = MagicMock()

    run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=sleep,
        warmup_count=0,
        count=2,
        cooldown_s=10.0,
    )

    assert sleep.call_count == 1


def test_repetition_count_of_two_issues_two_counted_and_one_cooldown() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()
    sleep = MagicMock()

    _, counted = run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=sleep,
        warmup_count=1,
        count=2,
        cooldown_s=10.0,
    )

    assert [c["index"] for c in counted] == [1, 2]
    # 1 after the warm-up + (2 - 1) between the two counted repetitions.
    assert sleep.call_count == 2


def test_repetition_result_carries_generation_facts_and_resource_reads() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()

    _, counted = run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=MagicMock(),
        warmup_count=0,
        count=1,
        cooldown_s=10.0,
    )

    result: RepetitionResult = counted[0]
    assert result["ttft_ms"] == 457.1
    assert result["ttft_source"] == "server_reported"
    assert result["prompt_tok_per_s"] == 280.0
    assert result["gen_tok_per_s"] == 26.0
    assert result["vram_used_mib"] == 3161.0
    assert result["gpu_draw_w"] == 45.0
    assert result["process_rss_bytes"] == 500_000_000
    assert result["stop_type"] == "limit"
    assert result["tokens_predicted"] == 128
    assert result["wall_clock_s"] >= 0.0
    assert result["machine_state"] == read_machine_state.return_value


def test_every_repetition_carries_machine_state_called_once_each() -> None:
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()

    warmups, counted = run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=MagicMock(),
        warmup_count=1,
        count=2,
        cooldown_s=10.0,
    )

    assert all(
        rep["machine_state"] == read_machine_state.return_value for rep in warmups
    )
    assert all(
        rep["machine_state"] == read_machine_state.return_value for rep in counted
    )
    # 1 warm-up + 2 counted repetitions -> exactly 3 reads, one per repetition.
    assert read_machine_state.call_count == 3


def test_blank_content_fails_the_repetition_with_reason_empty() -> None:
    send = MagicMock(return_value={**SAMPLE_RESPONSE, "content": "   "})
    read_gpu, read_rss, read_machine_state = _stub_reads()

    with pytest.raises(RepetitionFailure) as exc_info:
        run_repetition_set(
            send=send,
            read_gpu=read_gpu,
            read_rss=read_rss,
            read_machine_state=read_machine_state,
            sleep=MagicMock(),
            warmup_count=0,
            count=1,
            cooldown_s=10.0,
        )

    assert exc_info.value.index == 1
    assert exc_info.value.reason == "empty"
    assert str(exc_info.value) == "repetition 1 failed: empty"


def test_unusable_timings_fails_the_repetition_with_reason_unparseable() -> None:
    send = MagicMock(return_value={"content": "hello"})
    read_gpu, read_rss, read_machine_state = _stub_reads()

    with pytest.raises(RepetitionFailure) as exc_info:
        run_repetition_set(
            send=send,
            read_gpu=read_gpu,
            read_rss=read_rss,
            read_machine_state=read_machine_state,
            sleep=MagicMock(),
            warmup_count=0,
            count=1,
            cooldown_s=10.0,
        )

    assert exc_info.value.index == 1
    assert exc_info.value.reason == "unparseable"


def test_exceed_context_size_error_fails_with_reason_truncated_context() -> None:
    send = MagicMock(
        return_value={
            "error": {
                "type": "exceed_context_size_error",
                "n_prompt_tokens": 6001,
                "n_ctx": 4096,
            }
        }
    )
    read_gpu, read_rss, read_machine_state = _stub_reads()

    with pytest.raises(RepetitionFailure) as exc_info:
        run_repetition_set(
            send=send,
            read_gpu=read_gpu,
            read_rss=read_rss,
            read_machine_state=read_machine_state,
            sleep=MagicMock(),
            warmup_count=0,
            count=1,
            cooldown_s=10.0,
        )

    assert exc_info.value.index == 1
    assert exc_info.value.reason == "truncated_context"


def test_a_generation_stopped_at_the_token_cap_is_not_a_failure() -> None:
    # stop_type "limit" (SAMPLE_RESPONSE) is the runtime harness's intended
    # stop, not a truncation -- it must run to completion with no failure.
    send = MagicMock(return_value=SAMPLE_RESPONSE)
    read_gpu, read_rss, read_machine_state = _stub_reads()

    _, counted = run_repetition_set(
        send=send,
        read_gpu=read_gpu,
        read_rss=read_rss,
        read_machine_state=read_machine_state,
        sleep=MagicMock(),
        warmup_count=0,
        count=1,
        cooldown_s=10.0,
    )

    assert counted[0]["stop_type"] == "limit"


def test_failure_at_repetition_3_stops_the_run_before_4_and_5() -> None:
    responses = [
        SAMPLE_RESPONSE,
        SAMPLE_RESPONSE,
        {**SAMPLE_RESPONSE, "content": ""},
        SAMPLE_RESPONSE,
        SAMPLE_RESPONSE,
    ]
    send = MagicMock(side_effect=responses)
    read_gpu, read_rss, read_machine_state = _stub_reads()

    with pytest.raises(RepetitionFailure) as exc_info:
        run_repetition_set(
            send=send,
            read_gpu=read_gpu,
            read_rss=read_rss,
            read_machine_state=read_machine_state,
            sleep=MagicMock(),
            warmup_count=0,
            count=5,
            cooldown_s=10.0,
        )

    assert exc_info.value.index == 3
    # Repetitions 4 and 5 were never requested: exactly 3 calls were made.
    assert send.call_count == 3


def test_a_failing_warmup_fails_the_row_with_index_zero_and_no_retry() -> None:
    send = MagicMock(return_value={**SAMPLE_RESPONSE, "content": ""})
    read_gpu, read_rss, read_machine_state = _stub_reads()

    with pytest.raises(RepetitionFailure) as exc_info:
        run_repetition_set(
            send=send,
            read_gpu=read_gpu,
            read_rss=read_rss,
            read_machine_state=read_machine_state,
            sleep=MagicMock(),
            warmup_count=1,
            count=5,
            cooldown_s=10.0,
        )

    assert exc_info.value.index == 0
    assert exc_info.value.reason == "empty"
    assert send.call_count == 1
