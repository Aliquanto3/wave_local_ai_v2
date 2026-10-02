from unittest.mock import patch

import psutil
import pytest

from wave_local_ai_v2.timings import (
    ITEM_NULL_NOT_REPORTED_BY_ENGINE,
    TTFT_SOURCE_SERVER_REPORTED,
    MissingTimingsError,
    parse_generation_facts,
    parse_item_measurement,
    parse_timings,
    read_process_rss,
)

SAMPLE_RESPONSE = {
    "content": "hello",
    "timings": {
        "prompt_n": 128,
        "prompt_ms": 457.1,
        "prompt_per_second": 280.0,
        "predicted_n": 64,
        "predicted_ms": 2461.5,
        "predicted_per_second": 26.0,
    },
}


def test_parse_timings_extracts_expected_fields() -> None:
    timings = parse_timings(SAMPLE_RESPONSE)

    assert timings["ttft_ms"] == 457.1
    assert timings["prompt_tok_per_s"] == 280.0
    assert timings["gen_tok_per_s"] == 26.0
    assert timings["ttft_source"] == TTFT_SOURCE_SERVER_REPORTED
    assert timings["ttft_source"] == "server_reported"


def test_parse_timings_raises_named_error_when_timings_missing() -> None:
    with pytest.raises(MissingTimingsError):
        parse_timings({"content": "hello"})


def test_parse_timings_raises_named_error_on_partial_timings() -> None:
    with pytest.raises(MissingTimingsError):
        parse_timings({"timings": {"prompt_ms": 1.0}})


def test_parse_generation_facts_reads_tokens_evaluated() -> None:
    facts = parse_generation_facts(
        {
            "content": "hello",
            "stop_type": "limit",
            "tokens_predicted": 64,
            "tokens_evaluated": 512,
            "truncated": False,
        }
    )

    assert facts["tokens_evaluated"] == 512


def test_parse_generation_facts_defaults_tokens_evaluated_to_none_when_absent() -> None:
    facts = parse_generation_facts({"content": "hello"})

    assert facts["tokens_evaluated"] is None


def test_read_process_rss_returns_positive_integer() -> None:
    import os

    rss = read_process_rss(os.getpid())

    assert isinstance(rss, int)
    assert rss > 0


def test_read_process_rss_returns_none_when_the_process_is_gone() -> None:
    with patch(
        "wave_local_ai_v2.timings.psutil.Process",
        side_effect=psutil.NoSuchProcess(pid=1234),
    ):
        assert read_process_rss(1234) is None


def test_read_process_rss_returns_none_when_access_is_denied() -> None:
    with patch(
        "wave_local_ai_v2.timings.psutil.Process",
        side_effect=psutil.AccessDenied(pid=1234),
    ):
        assert read_process_rss(1234) is None


# The `/v1/chat/completions` body b10537 returned live (2026-10-02) for the
# second item of a batch: 6 of its 25 prompt tokens came from the cache.
CHAT_RESPONSE = {
    "usage": {"completion_tokens": 3, "prompt_tokens": 25, "total_tokens": 28},
    "timings": {
        "cache_n": 6,
        "prompt_n": 19,
        "prompt_ms": 9.195,
        "predicted_n": 3,
        "predicted_ms": 12.285,
    },
}


def test_parse_item_measurement_reads_the_items_own_figures() -> None:
    measurement = parse_item_measurement(CHAT_RESPONSE)

    assert measurement == {
        "tokens_in": 25,
        "tokens_in_null_reason": None,
        "tokens_out": 3,
        "tokens_out_null_reason": None,
        "ttft_ms": 9.195,
        "ttft_ms_null_reason": None,
        "ttft_source": TTFT_SOURCE_SERVER_REPORTED,
        "prompt_tokens_cached": 6,
        "prompt_tokens_cached_null_reason": None,
    }


def test_an_unreported_value_is_null_with_its_reason_never_zero() -> None:
    measurement = parse_item_measurement({"usage": {"completion_tokens": 3}})

    assert measurement["tokens_out"] == 3
    for value, reason in (
        ("tokens_in", "tokens_in_null_reason"),
        ("ttft_ms", "ttft_ms_null_reason"),
        ("prompt_tokens_cached", "prompt_tokens_cached_null_reason"),
    ):
        assert measurement[value] is None
        assert measurement[reason] == ITEM_NULL_NOT_REPORTED_BY_ENGINE
    assert measurement["ttft_source"] is None


@pytest.mark.parametrize(
    "timings_block",
    [
        {"prompt_ms": "9.1", "cache_n": -1},
        {"prompt_ms": True, "cache_n": 1.5},
        {"prompt_ms": -2.0, "cache_n": None},
        "not an object",
    ],
)
def test_a_non_numeric_engine_value_is_unreported(timings_block) -> None:
    measurement = parse_item_measurement(
        {"usage": {"prompt_tokens": False}, "timings": timings_block}
    )

    assert measurement["ttft_ms"] is None
    assert measurement["prompt_tokens_cached"] is None
    assert measurement["tokens_in"] is None
    assert measurement["ttft_ms_null_reason"] == ITEM_NULL_NOT_REPORTED_BY_ENGINE


def test_an_integer_prompt_ms_is_published_as_a_float() -> None:
    measurement = parse_item_measurement({"timings": {"prompt_ms": 12}})

    assert measurement["ttft_ms"] == 12.0
    assert isinstance(measurement["ttft_ms"], float)
