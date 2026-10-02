"""The agentic harness a quality row was produced under (Methodology 23).

The candidate set is closed at five: `direct` -- plain client calls with no
framework -- as the reference, and `smolagents`, `langgraph`, `pydantic-ai`
and `llamaindex` as comparators. Widening it is a PRD change, so the writer
gate (`row_contract.validate_row`) refuses any other id rather than this
module offering an extension point. Only `direct` is implemented here; the
four framework adapters are later stories and none of their packages is a
dependency of this project.

Every row names three things: the harness id, the harness's own version read
from the installed package when the row is written (never declared), and its
per-call prompt overhead. The overhead rule is the owner's (Q33 (a)): per
call, the token count of what the engine finally received minus the token
count of the item's own rendered prompt, both under the tokenizer the row
already names. The item's own tool definitions, as rendered under `direct`,
are part of the item, not of the overhead. A harness that rewrites the
item's prompt rather than wrapping it makes the subtraction meaningless and
is recorded unmeasurable -- never zero, since a zero reads as a measurement.
"""

from __future__ import annotations

from importlib import metadata
from typing import Any, TypedDict

from wave_local_ai_v2 import timings

HARNESS_DIRECT = "direct"
HARNESS_SMOLAGENTS = "smolagents"
HARNESS_LANGGRAPH = "langgraph"
HARNESS_PYDANTIC_AI = "pydantic-ai"
HARNESS_LLAMAINDEX = "llamaindex"

# Each candidate's id to the installed distribution its version is read from.
# `direct`'s calls go through `requests` and nothing else: that client is the
# harness, and this project's own version is already the row's
# `release_version`. The four framework distributions are named, not
# installed: a row naming one whose package is absent is refused at the
# version read rather than written with a guessed version.
HARNESS_DISTRIBUTIONS: dict[str, str] = {
    HARNESS_DIRECT: "requests",
    HARNESS_SMOLAGENTS: "smolagents",
    HARNESS_LANGGRAPH: "langgraph",
    HARNESS_PYDANTIC_AI: "pydantic-ai",
    HARNESS_LLAMAINDEX: "llama-index-core",
}
HARNESS_IDS: frozenset[str] = frozenset(HARNESS_DISTRIBUTIONS)

# Why a row's overhead is null. Never a zero in their place.
# - the harness rewrites the item's prompt rather than wrapping it, or the
#   engine received fewer tokens than the item's own prompt, which no wrapper
#   can produce: the subtraction measures nothing;
# - no count of the item's own prompt exists under the row's tokenizer (a
#   cloud subject: its tokenizer is reachable only through a provider call
#   this project does not make);
# - or the engine's own count is null, for the reason it carries
#   (`timings.ITEM_NULL_REASONS`).
OVERHEAD_UNMEASURABLE = "unmeasurable"
OVERHEAD_ITEM_PROMPT_NOT_COUNTED = "item_prompt_not_counted"
OVERHEAD_NULL_REASONS: frozenset[str] = frozenset(
    {
        OVERHEAD_UNMEASURABLE,
        OVERHEAD_ITEM_PROMPT_NOT_COUNTED,
        *timings.ITEM_NULL_REASONS,
    }
)
OVERHEAD_KEYS: frozenset[str] = frozenset({"tokens", "null_reason"})


class HarnessError(ValueError):
    """A harness outside the closed set, or one whose package is not installed."""


class PromptOverhead(TypedDict):
    """One call's prompt overhead: a token count, or null with its reason."""

    tokens: int | None
    null_reason: str | None


def harness_version(harness_id: str) -> str:
    """The installed version of `harness_id`'s package, read now.

    Read at every call, never cached or declared: the row states the version
    that actually ran.
    """
    if harness_id not in HARNESS_IDS:
        raise HarnessError(
            f"unknown harness {harness_id!r}: one of {', '.join(sorted(HARNESS_IDS))}"
        )
    distribution = HARNESS_DISTRIBUTIONS[harness_id]
    try:
        return metadata.version(distribution)
    except metadata.PackageNotFoundError as exc:
        raise HarnessError(
            f"harness {harness_id!r} has no installed {distribution!r} package "
            "to read its version from"
        ) from exc


def prompt_overhead(
    *,
    engine_prompt_tokens: int | None,
    engine_null_reason: str | None,
    item_prompt_tokens: int | None,
    wraps_item_prompt: bool,
) -> PromptOverhead:
    """One call's overhead under the rule: engine count minus item count.

    `engine_prompt_tokens` is what the engine reported receiving (the row's
    `item_tokens_in`, with `engine_null_reason` its null reason);
    `item_prompt_tokens` is the item's own rendered prompt -- tool
    definitions included -- counted under the same tokenizer, or `None` when
    no such count exists. `wraps_item_prompt` is False for a harness that
    rewrites the item's prompt, which the rule cannot measure.
    """
    if not wraps_item_prompt:
        return _null(OVERHEAD_UNMEASURABLE)
    if engine_prompt_tokens is None:
        if (
            engine_null_reason is None
            or engine_null_reason not in timings.ITEM_NULL_REASONS
        ):
            raise ValueError(
                f"a null engine count needs its reason, got {engine_null_reason!r}"
            )
        return _null(engine_null_reason)
    if item_prompt_tokens is None:
        return _null(OVERHEAD_ITEM_PROMPT_NOT_COUNTED)
    overhead = engine_prompt_tokens - item_prompt_tokens
    if overhead < 0:
        # A wrapper only adds: fewer tokens than the item's own prompt means
        # the engine did not receive the item as rendered.
        return _null(OVERHEAD_UNMEASURABLE)
    return PromptOverhead(tokens=overhead, null_reason=None)


def _null(reason: str) -> PromptOverhead:
    return PromptOverhead(tokens=None, null_reason=reason)


def row_fields(harness_id: str, overhead: PromptOverhead) -> dict[str, Any]:
    """The three harness fields one quality row carries (schema "20")."""
    return {
        "harness_id": harness_id,
        "harness_version": harness_version(harness_id),
        "harness_prompt_overhead": dict(overhead),
    }
