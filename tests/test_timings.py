from unittest.mock import patch

import psutil
import pytest

from wave_local_ai_v2.timings import (
    TTFT_SOURCE_SERVER_REPORTED,
    MissingTimingsError,
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
