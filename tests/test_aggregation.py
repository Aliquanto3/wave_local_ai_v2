import pytest

from wave_local_ai_v2.aggregation import (
    AGGREGATED_TIMING_METRICS,
    AGGREGATION_LABELS,
    MEASUREMENT_FIELDS,
    PEAK_METRICS,
    AggregationError,
    aggregate_timings,
    mean,
    median,
    peak,
    sample_sd,
)


def test_median_of_odd_count_is_the_middle_value() -> None:
    assert median([1.0, 5.0, 3.0]) == 3.0


def test_median_of_even_count_is_the_mean_of_the_two_middle_values() -> None:
    assert median([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_mean_of_known_set() -> None:
    assert mean([1.0, 2.0, 3.0, 4.0]) == 2.5


def test_sample_sd_of_known_set() -> None:
    # N-1 form: stdev([2, 4, 4, 4, 5, 5, 7, 9]) == 2.13809...
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    assert sample_sd(values) == pytest.approx(2.13809, rel=1e-4)


def test_sample_sd_raises_on_a_single_value() -> None:
    with pytest.raises(AggregationError):
        sample_sd([1.0])


def test_sample_sd_raises_on_an_empty_list() -> None:
    with pytest.raises(AggregationError):
        sample_sd([])


def test_peak_returns_the_maximum_not_the_last_sample() -> None:
    assert peak([10.0, 30.0, 20.0]) == 30.0


def test_peak_returns_none_when_every_sample_is_none() -> None:
    assert peak([None, None]) is None


def test_peak_ignores_individual_nones_when_a_real_reading_exists() -> None:
    assert peak([None, 5.0, None, 15.0]) == 15.0


def _rep(index: int, ttft: float, prompt_tps: float, gen_tps: float) -> dict:
    return {
        "index": index,
        "ttft_ms": ttft,
        "prompt_tok_per_s": prompt_tps,
        "gen_tok_per_s": gen_tps,
        "vram_used_mib": 3000.0 + index,
        "gpu_draw_w": 40.0 + index,
        "process_rss_bytes": 500_000_000 + index,
        "wall_clock_s": 5.0,
        "stop_type": "limit",
        "tokens_predicted": 128,
    }


def test_aggregate_timings_matches_hand_computed_medians_means_and_sds() -> None:
    counted = [
        _rep(1, 100.0, 270.0, 24.0),
        _rep(2, 110.0, 280.0, 25.0),
        _rep(3, 120.0, 290.0, 26.0),
        _rep(4, 130.0, 300.0, 27.0),
        _rep(5, 140.0, 310.0, 28.0),
    ]

    aggregated = aggregate_timings(counted)

    assert aggregated["ttft_ms"] == 120.0
    assert aggregated["ttft_ms_mean"] == 120.0
    assert aggregated["ttft_ms_sd"] == pytest.approx(15.811, rel=1e-3)
    assert aggregated["prompt_tok_per_s"] == 290.0
    assert aggregated["gen_tok_per_s"] == 26.0
    assert aggregated["repetitions_n"] == 5


def test_aggregate_timings_takes_the_mean_of_the_two_middle_values_on_even_n() -> None:
    counted = [
        _rep(1, 100.0, 270.0, 24.0),
        _rep(2, 110.0, 280.0, 25.0),
        _rep(3, 120.0, 290.0, 26.0),
        _rep(4, 130.0, 300.0, 27.0),
    ]

    aggregated = aggregate_timings(counted)

    assert aggregated["ttft_ms"] == 115.0
    assert aggregated["repetitions_n"] == 4


def test_aggregation_labels_cover_every_declared_measurement() -> None:
    for metric in AGGREGATED_TIMING_METRICS:
        assert AGGREGATION_LABELS[metric] == "median"
    for metric in PEAK_METRICS:
        assert metric in AGGREGATION_LABELS
    assert AGGREGATION_LABELS["vram_used_mib"] == "peak_over_counted_repetitions"
    assert AGGREGATION_LABELS["process_rss_bytes"] == "peak_over_counted_repetitions"
    assert AGGREGATION_LABELS["wall_clock_s"] == "total_over_counted_repetitions"
    assert (
        AGGREGATION_LABELS["energy_kwh"]
        == "total_over_counted_repetitions_including_cooldowns"
    )
    assert MEASUREMENT_FIELDS == frozenset(AGGREGATION_LABELS)


def test_power_is_not_labelled_a_peak_because_it_is_sampled_after_decode() -> None:
    # One NVML read per repetition, taken once the completion has returned:
    # allocation-level channels hold steady across a repetition so their max
    # is a real peak, but power has already fallen by then.
    assert AGGREGATION_LABELS["gpu_draw_w"] == (
        "max_post_completion_sample_over_counted_repetitions"
    )
