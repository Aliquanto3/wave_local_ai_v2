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


class Timings(TypedDict):
    ttft_ms: float
    prompt_tok_per_s: float
    gen_tok_per_s: float


class GenerationFacts(TypedDict):
    """What a repetition is judged on, beyond the timing numbers.

    Every field tolerates an absent key as `None` rather than raising: this is
    read from a response that already parsed as JSON, and a shape drift here
    should surface as a visible `None` on the row, not a crashed run.
    """

    stop_type: str | None
    tokens_predicted: int | None
    truncated: bool | None
    content: str


def parse_generation_facts(response_json: dict[str, Any]) -> GenerationFacts:
    """Extract the generation facts a repetition's outcome is classified on."""
    return GenerationFacts(
        stop_type=response_json.get("stop_type"),
        tokens_predicted=response_json.get("tokens_predicted"),
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
