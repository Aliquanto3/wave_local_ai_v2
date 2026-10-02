"""Parse llama-server completion timings and read process RSS.

The `timings` object's field names below (`prompt_ms`, `prompt_per_second`,
`predicted_per_second`) match the llama.cpp server's documented response shape
as of build b10537. Confirm against a live response before trusting a mismatch
silently — a shape change here means the harness needs updating, not a
best-effort fallback.
"""

from __future__ import annotations

from typing import Any, TypedDict

import psutil


class MissingTimingsError(RuntimeError):
    """Raised when a llama-server response has no usable `timings` block."""


# Both named now even though only the first is reachable today: this
# harness's only call path reads `timings["prompt_ms"]` straight from
# llama-server's response (`server_reported`). `client_measured` names the
# independent, wall-clock TTFT that was tried and reverted (see
# `__init__.py`'s streaming-TTFT comment) -- naming it here means the row
# contract's future acceptance of it needs no new constant later.
TTFT_SOURCE_SERVER_REPORTED = "server_reported"
TTFT_SOURCE_CLIENT_MEASURED = "client_measured"


class Timings(TypedDict):
    ttft_ms: float
    prompt_tok_per_s: float
    gen_tok_per_s: float
    ttft_source: str


class GenerationFacts(TypedDict):
    """What a repetition is judged on, beyond the timing numbers.

    Every field tolerates an absent key as `None` rather than raising: this is
    read from a response that already parsed as JSON, and a shape drift here
    should surface as a visible `None` on the row, not a crashed run.
    """

    stop_type: str | None
    tokens_predicted: int | None
    tokens_evaluated: int | None
    truncated: bool | None
    content: str


# What one quality item's own generation reports, as a row publishes it
# (schema "18"). Not the runtime protocol's figure: one generation per item,
# no warm-up exclusion, no repetitions -- Methodology 6's aggregate is the
# runtime row's `ttft_ms`, measured on a fixed prompt. The label every row
# carries for that distinction:
ITEM_MEASUREMENT_SINGLE_GENERATION = "single_generation"

# Why an item's value is null. Never a zero: an unreported count is unknown.
# - the engine's response did not carry the value (or carried no number);
# - the cloud provider reports no such value for a call;
# - no generation call was made for the item (a context pre-flight refused it).
ITEM_NULL_NOT_REPORTED_BY_ENGINE = "not_reported_by_engine"
ITEM_NULL_NOT_REPORTED_BY_PROVIDER = "not_reported_by_provider"
ITEM_NULL_NO_GENERATION_CALL = "no_generation_call"
ITEM_NULL_REASONS = frozenset(
    {
        ITEM_NULL_NOT_REPORTED_BY_ENGINE,
        ITEM_NULL_NOT_REPORTED_BY_PROVIDER,
        ITEM_NULL_NO_GENERATION_CALL,
    }
)


class ItemMeasurement(TypedDict):
    """One item's own generation figures, each a value or null with a reason.

    `ttft_ms` is the engine's `timings.prompt_ms` for this one request, the
    same quantity and `ttft_source` label the runtime row's `ttft_ms` uses.
    `prompt_tokens_cached` is the engine's `timings.cache_n`: llama-server
    reuses a prompt prefix shared with the previous request, and `prompt_ms`
    then covers only the uncached tokens, so a reader needs the count to read
    the TTFT.
    """

    tokens_in: int | None
    tokens_in_null_reason: str | None
    tokens_out: int | None
    tokens_out_null_reason: str | None
    ttft_ms: float | None
    ttft_ms_null_reason: str | None
    ttft_source: str | None
    prompt_tokens_cached: int | None
    prompt_tokens_cached_null_reason: str | None


def _count(container: Any, key: str) -> int | None:
    value = container.get(key) if isinstance(container, dict) else None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None
    return value


def parse_item_measurement(response_json: dict[str, Any]) -> ItemMeasurement:
    """One item's tokens, TTFT and cached prompt tokens off a chat response.

    Confirmed live on b10537 (2026-10-02): `/v1/chat/completions` returns
    `usage.prompt_tokens`, `usage.completion_tokens` and a `timings` block
    with `prompt_ms` and `cache_n`. Each value the response does not carry
    as a number is null with `not_reported_by_engine` -- never a zero, and
    never a crashed run over one column.
    """
    usage = response_json.get("usage")
    timings = response_json.get("timings")
    tokens_in = _count(usage, "prompt_tokens")
    tokens_out = _count(usage, "completion_tokens")
    cached = _count(timings, "cache_n")
    raw_ttft = timings.get("prompt_ms") if isinstance(timings, dict) else None
    ttft_ms = (
        float(raw_ttft)
        if isinstance(raw_ttft, int | float)
        and not isinstance(raw_ttft, bool)
        and raw_ttft >= 0
        else None
    )

    def reason(value: object) -> str | None:
        return ITEM_NULL_NOT_REPORTED_BY_ENGINE if value is None else None

    return ItemMeasurement(
        tokens_in=tokens_in,
        tokens_in_null_reason=reason(tokens_in),
        tokens_out=tokens_out,
        tokens_out_null_reason=reason(tokens_out),
        ttft_ms=ttft_ms,
        ttft_ms_null_reason=reason(ttft_ms),
        ttft_source=TTFT_SOURCE_SERVER_REPORTED if ttft_ms is not None else None,
        prompt_tokens_cached=cached,
        prompt_tokens_cached_null_reason=reason(cached),
    )


def parse_generation_facts(response_json: dict[str, Any]) -> GenerationFacts:
    """Extract the generation facts a repetition's outcome is classified on.

    `tokens_evaluated` is the prompt-token count: confirmed live on build
    b10537 (2026-08-26) as the top-level `tokens_evaluated` field, equal to
    `timings.prompt_n` on the same response -- either would do, this one is
    read because it sits alongside `tokens_predicted` at the top level.
    """
    return GenerationFacts(
        stop_type=response_json.get("stop_type"),
        tokens_predicted=response_json.get("tokens_predicted"),
        tokens_evaluated=response_json.get("tokens_evaluated"),
        truncated=response_json.get("truncated"),
        content=response_json.get("content", ""),
    )


def parse_timings(response_json: dict[str, Any]) -> Timings:
    """Extract TTFT, prompt tok/s, and generation tok/s from a completion response."""
    timings = response_json.get("timings")
    if not isinstance(timings, dict):
        raise MissingTimingsError(
            "response has no 'timings' object; check --jinja / server config"
        )

    try:
        return Timings(
            ttft_ms=float(timings["prompt_ms"]),
            prompt_tok_per_s=float(timings["prompt_per_second"]),
            gen_tok_per_s=float(timings["predicted_per_second"]),
            ttft_source=TTFT_SOURCE_SERVER_REPORTED,
        )
    except KeyError as exc:
        raise MissingTimingsError(f"timings object is missing field {exc}") from exc


def read_process_rss(pid: int) -> int | None:
    """Return the process's resident set size in bytes, or None if unreadable.

    None means the process could not be read -- it exited between the completion
    response and this call, or the OS denied access -- never that RSS was zero.
    Degrading here is deliberate: by this point the measurement has already
    succeeded, and aborting the run would throw away a good row over one column.
    `psutil.Error` is the base of both `NoSuchProcess` and `AccessDenied`.
    """
    try:
        rss: int = psutil.Process(pid).memory_info().rss
    except psutil.Error:
        return None
    return rss
