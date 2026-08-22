"""The statistics a repetition set is aggregated with, and the declaration of
which measurement gets which one.

`AGGREGATION_LABELS` is the single source both `__init__.py` (to build the
row) and `row_contract.py` (to gate it) read from: a measurement added to
`AGGREGATED_TIMING_METRICS` or `PEAK_METRICS` without a matching label here
fails `MEASUREMENT_FIELDS`'s consumers rather than silently publishing an
unlabelled number.
"""

from __future__ import annotations

import statistics
from typing import Any

from wave_local_ai_v2.repetitions import RepetitionResult


class AggregationError(RuntimeError):
    """Raised when a statistic is asked to summarize too few samples."""


# The three server-reported timing metrics a repetition set publishes as a
# median, each with its mean and sample sd alongside it.
AGGREGATED_TIMING_METRICS = ("ttft_ms", "prompt_tok_per_s", "gen_tok_per_s")

# The three resource-usage channels a repetition set summarizes as a maximum.
# Each contributes exactly one sample per repetition, read immediately after
# that repetition's completion returns (`repetitions._run_one`) -- so the
# maximum is over N post-completion instants, not a continuous trace.
PEAK_METRICS = ("vram_used_mib", "process_rss_bytes", "gpu_draw_w")

# The one metric among AGGREGATED_TIMING_METRICS whose spread can set
# `unreliable`: excess variance in generation throughput is what the story
# asks the flag to name. `ttft_ms` and `prompt_tok_per_s` still carry their
# own spread on the row (criterion 7 states the statistic identically for all
# three) but never influence the flag.
UNRELIABLE_SPREAD_METRIC = "gen_tok_per_s"

# One entry per measurement a runtime row publishes, naming the statistic
# behind it. `MEASUREMENT_FIELDS` is what `row_contract.validate_row` checks
# a row's `aggregation` block against.
#
# `vram_used_mib` and `process_rss_bytes` are allocation-level: they hold
# steady for the whole repetition, so one sample per repetition does measure
# the repetition and their maximum is a true peak. Power is instantaneous and
# falls as soon as decode stops, so `gpu_draw_w`'s maximum over the same
# post-completion instants is NOT the run's peak draw and must not claim to
# be -- its label names what was actually sampled.
AGGREGATION_LABELS: dict[str, str] = {
    **{metric: "median" for metric in AGGREGATED_TIMING_METRICS},
    **{
        f"{metric}_spread": "sample_sd_over_median"
        for metric in AGGREGATED_TIMING_METRICS
    },
    "vram_used_mib": "peak_over_counted_repetitions",
    "process_rss_bytes": "peak_over_counted_repetitions",
    "gpu_draw_w": "max_post_completion_sample_over_counted_repetitions",
    "wall_clock_s": "total_over_counted_repetitions",
    "energy_kwh": "total_over_counted_repetitions_including_cooldowns",
}

MEASUREMENT_FIELDS = frozenset(AGGREGATION_LABELS)


def median(values: list[float]) -> float:
    """Return the median. On an even count, the mean of the two middle values."""
    return statistics.median(values)


def mean(values: list[float]) -> float:
    """Return the arithmetic mean."""
    return statistics.mean(values)


def sample_sd(values: list[float]) -> float:
    """Return the sample standard deviation (N-1 form).

    Raises `AggregationError` on fewer than two values: a single sample has
    no defined spread, and returning 0.0 would silently claim perfect
    reproducibility that was never measured.
    """
    if len(values) < 2:
        raise AggregationError(
            f"sample_sd needs at least 2 values, got {len(values)}: "
            "the sample sd is undefined below N=2"
        )
    return statistics.stdev(values)


def spread(sd: float, median_value: float) -> float:
    """Return the sample sd over the median, a scale-free variance measure.

    Raises `AggregationError` on a zero median rather than fabricating `0.0`
    or `inf`: a zero-median timing metric is a different failure than "no
    spread", and it is named the same way `sample_sd` names its own
    undefined case.
    """
    if median_value == 0:
        raise AggregationError(
            "spread is undefined against a median of 0: a timing metric that "
            "medians to zero is a broken measurement, not an absence of spread"
        )
    return sd / median_value


def unreliable(spread_value: float, threshold: float) -> bool:
    """True when `spread_value` exceeds `threshold`."""
    return spread_value > threshold


def peak(values: list[float | None]) -> float | None:
    """Return the maximum of `values`, ignoring `None` samples.

    Returns `None` only when every sample is `None` -- a channel that never
    read is absent, not zero.
    """
    real_values = [v for v in values if v is not None]
    if not real_values:
        return None
    return max(real_values)


def aggregate_timings(
    counted: list[RepetitionResult], *, threshold: float
) -> dict[str, Any]:
    """Aggregate the counted repetitions' timing metrics into medians +- spread.

    Returns, per metric in `AGGREGATED_TIMING_METRICS`, the metric itself
    (the median), `f"{metric}_mean"`, `f"{metric}_sd"` and `f"{metric}_spread"`,
    plus `repetitions_n` and `unreliable` (set only from
    `UNRELIABLE_SPREAD_METRIC`'s spread against `threshold`).
    """
    result: dict[str, Any] = {}
    for metric in AGGREGATED_TIMING_METRICS:
        values = [rep[metric] for rep in counted]  # type: ignore[literal-required]
        metric_median = median(values)
        metric_sd = sample_sd(values)
        result[metric] = metric_median
        result[f"{metric}_mean"] = mean(values)
        result[f"{metric}_sd"] = metric_sd
        result[f"{metric}_spread"] = spread(metric_sd, metric_median)
    result["repetitions_n"] = len(counted)
    result["unreliable"] = unreliable(
        result[f"{UNRELIABLE_SPREAD_METRIC}_spread"], threshold
    )
    return result
