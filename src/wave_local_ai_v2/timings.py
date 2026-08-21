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


def read_process_rss(pid: int) -> int:
    """Return the process's resident set size in bytes."""
    return psutil.Process(pid).memory_info().rss
