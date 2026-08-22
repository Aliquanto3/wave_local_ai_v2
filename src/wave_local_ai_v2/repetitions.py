"""The repetition loop: one warm-up, N counted repetitions, a cooldown between them.

Each request is built by the caller's `send` closure, which already carries
`cache_prompt: False` and the pinned seed (see `RUNTIME_SAMPLING` in
`__init__.py`) -- this module only sequences the calls and records their
outcome, it never builds the HTTP body itself.

A repetition's outcome is classified with the same four-way taxonomy
`scoring.py` already defines for quality rows -- reused rather than
reinvented, since a blank completion or an unparseable one means the same
thing in either harness. Only three of the four reasons are reachable here:
`FAILURE_REASON_TRUNCATED_MAX_TOKENS` is not. The runtime harness *chooses*
`FIXED_MAX_TOKENS` as its own measurement budget (`__init__.py`), so a
completion that stops there (`stop_type: "limit"`, probed live on this
build) is the intended end of a healthy repetition, not a truncation --
failing on it would fail every row this harness ever writes. The cap stays
disclosed as the row's `max_tokens` field, and `stop_type` /
`tokens_predicted` are recorded on every successful repetition so a
generation that ended early at EOS is visible in the raw list rather than
absorbed into a median without trace.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any, TypedDict

from wave_local_ai_v2.gpu import GpuStats
from wave_local_ai_v2.machine_state import MachineState
from wave_local_ai_v2.scoring import (
    FAILURE_REASON_EMPTY,
    FAILURE_REASON_TRUNCATED_CONTEXT,
    FAILURE_REASON_UNPARSEABLE,
)
from wave_local_ai_v2.timings import (
    MissingTimingsError,
    parse_generation_facts,
    parse_timings,
)

# `POST /slots/0?action=erase` returns 501 on this build unless the server is
# launched with `--slot-save-path`, which would change the validated baseline
# flag set (see plan.md's Resources table). Per-request `cache_prompt: False`
# was probed to force a full prefill instead, with no flag change: this
# constant names that choice on every written row.
SLOT_RESET_METHOD = "cache_prompt_false"

# The inter-repetition thermal protocol this increment runs: a fixed cooldown
# (`cooldown_s`, already shipped) between every counted repetition,
# unconditionally -- not conditioned on temperature and not skipped. A row
# declares this rather than leaving a reader to infer it from `cooldown_s`
# alone. `Literal["fixed_cooldown", "back_to_back", "cooldown_to_temp_ceiling"]`
# names the two postures a future increment could add: no cooldown at all
# (`back_to_back`), or a cooldown that runs until a temperature ceiling is
# reached rather than for a fixed duration (`cooldown_to_temp_ceiling`).
THERMAL_POSTURE_FIXED_COOLDOWN = "fixed_cooldown"

# The llama-server error shape probed live for a prompt exceeding the
# context: HTTP 400 with this `error.type`, not a `truncated: true`
# completion (see plan.md's Resources table). Public because the caller's
# `send` closure needs the same string to decide which 400 it may pass
# through to be classified here and which must raise as an HTTP error.
EXCEED_CONTEXT_ERROR_TYPE = "exceed_context_size_error"


class RepetitionFailure(RuntimeError):
    """Raised at the first failing repetition; the whole row fails with it.

    Not dropped and retried, not substituted with a value: `index` is 0 for
    a failing warm-up, 1-based for a failing counted repetition.
    """

    def __init__(self, index: int, reason: str) -> None:
        self.index = index
        self.reason = reason
        super().__init__(f"repetition {index} failed: {reason}")


class RepetitionResult(TypedDict):
    """One repetition's outcome: timings, resource reads, and generation facts."""

    index: int
    ttft_ms: float
    ttft_source: str
    prompt_tok_per_s: float
    gen_tok_per_s: float
    vram_used_mib: float | None
    gpu_draw_w: float | None
    process_rss_bytes: int | None
    machine_state: MachineState
    wall_clock_s: float
    stop_type: str | None
    tokens_predicted: int | None


def run_repetition_set(
    *,
    send: Callable[[], dict[str, Any]],
    read_gpu: Callable[[], GpuStats],
    read_rss: Callable[[], int | None],
    read_machine_state: Callable[[], MachineState],
    sleep: Callable[[float], None],
    warmup_count: int,
    count: int,
    cooldown_s: float,
) -> tuple[list[RepetitionResult], list[RepetitionResult]]:
    """Run the warm-up(s) then the counted repetitions, cooldown between them.

    Warm-ups all carry index 0; the counted list is 1-based and contiguous.
    The cooldown runs once after the last warm-up -- so the first counted
    repetition starts from the same posture as the rest -- and `count - 1`
    times between counted repetitions, never after the final one.
    """
    warmups = [
        _run_one(0, send, read_gpu, read_rss, read_machine_state)
        for _ in range(warmup_count)
    ]
    if warmup_count > 0:
        sleep(cooldown_s)

    counted: list[RepetitionResult] = []
    for index in range(1, count + 1):
        counted.append(_run_one(index, send, read_gpu, read_rss, read_machine_state))
        if index < count:
            sleep(cooldown_s)

    return warmups, counted


def _run_one(
    index: int,
    send: Callable[[], dict[str, Any]],
    read_gpu: Callable[[], GpuStats],
    read_rss: Callable[[], int | None],
    read_machine_state: Callable[[], MachineState],
) -> RepetitionResult:
    start = time.monotonic()
    response_json = send()
    wall_clock_s = time.monotonic() - start

    # Checked before the completion shape below: a context-exceeded refusal
    # has no `content` or `timings` block at all, so classifying it as
    # `empty` or `unparseable` first would hide the real reason.
    error = response_json.get("error")
    if isinstance(error, dict) and error.get("type") == EXCEED_CONTEXT_ERROR_TYPE:
        raise RepetitionFailure(index, FAILURE_REASON_TRUNCATED_CONTEXT)

    facts = parse_generation_facts(response_json)
    if facts["content"].strip() == "":
        raise RepetitionFailure(index, FAILURE_REASON_EMPTY)

    try:
        timings = parse_timings(response_json)
    except MissingTimingsError as exc:
        raise RepetitionFailure(index, FAILURE_REASON_UNPARSEABLE) from exc

    # One sample per repetition, taken here: the completion has already
    # returned, so decode has stopped. VRAM and RSS are allocation-level and
    # hold steady across the repetition, so this instant represents it; the
    # power reading does not, which is why `aggregation.AGGREGATION_LABELS`
    # labels `gpu_draw_w` a post-completion sample rather than a peak. Machine
    # state (temperatures, throttle reasons) is sampled the same way, for the
    # same reason.
    gpu_stats = read_gpu()
    rss_bytes = read_rss()
    machine_state = read_machine_state()

    return RepetitionResult(
        index=index,
        ttft_ms=timings["ttft_ms"],
        ttft_source=timings["ttft_source"],
        prompt_tok_per_s=timings["prompt_tok_per_s"],
        gen_tok_per_s=timings["gen_tok_per_s"],
        vram_used_mib=gpu_stats["vram_used_mib"],
        gpu_draw_w=gpu_stats["gpu_draw_w"],
        process_rss_bytes=rss_bytes,
        machine_state=machine_state,
        wall_clock_s=wall_clock_s,
        stop_type=facts["stop_type"],
        tokens_predicted=facts["tokens_predicted"],
    )
