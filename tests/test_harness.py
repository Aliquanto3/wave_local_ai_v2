from importlib import metadata

import pytest

from wave_local_ai_v2 import harness, timings


def test_the_candidate_set_is_closed_at_methodology_23s_five() -> None:
    assert harness.HARNESS_IDS == {
        "direct",
        "smolagents",
        "langgraph",
        "pydantic-ai",
        "llamaindex",
    }


def test_directs_version_is_the_installed_client_read_now() -> None:
    assert harness.harness_version("direct") == metadata.version("requests")


def test_the_version_is_read_at_every_call_not_declared(monkeypatch) -> None:
    read: list[str] = []

    def fake_version(distribution: str) -> str:
        read.append(distribution)
        return f"9.9.{len(read)}"

    monkeypatch.setattr(harness.metadata, "version", fake_version)

    assert harness.harness_version("direct") == "9.9.1"
    assert harness.harness_version("direct") == "9.9.2"
    assert read == ["requests", "requests"]


def test_an_unknown_harness_has_no_version() -> None:
    with pytest.raises(harness.HarnessError, match="unknown harness 'crewai'"):
        harness.harness_version("crewai")


def test_a_framework_whose_package_is_absent_is_refused_not_guessed(
    monkeypatch,
) -> None:
    monkeypatch.setitem(
        harness.HARNESS_DISTRIBUTIONS, "langgraph", "no-such-distribution-here"
    )

    with pytest.raises(harness.HarnessError, match="no installed"):
        harness.harness_version("langgraph")


def test_directs_overhead_is_engine_minus_item_never_a_constant() -> None:
    # Two different measurements, two different values: the overhead is read
    # off the counts, not written as zero.
    assert harness.prompt_overhead(
        engine_prompt_tokens=27,
        engine_null_reason=None,
        item_prompt_tokens=27,
        wraps_item_prompt=True,
    ) == {"tokens": 0, "null_reason": None}
    assert harness.prompt_overhead(
        engine_prompt_tokens=31,
        engine_null_reason=None,
        item_prompt_tokens=27,
        wraps_item_prompt=True,
    ) == {"tokens": 4, "null_reason": None}


def test_tool_definitions_count_in_the_item_not_in_the_overhead() -> None:
    # Measured live on b10537: one tool definition renders into the item's own
    # prompt (19 tokens without it, 158 with it), and the engine received 158.
    with_tools = harness.prompt_overhead(
        engine_prompt_tokens=158,
        engine_null_reason=None,
        item_prompt_tokens=158,
        wraps_item_prompt=True,
    )

    assert with_tools == {"tokens": 0, "null_reason": None}


def test_a_harness_that_rewrites_the_prompt_is_unmeasurable_not_zero() -> None:
    assert harness.prompt_overhead(
        engine_prompt_tokens=27,
        engine_null_reason=None,
        item_prompt_tokens=27,
        wraps_item_prompt=False,
    ) == {"tokens": None, "null_reason": "unmeasurable"}


def test_an_engine_that_received_less_than_the_item_is_unmeasurable() -> None:
    assert harness.prompt_overhead(
        engine_prompt_tokens=20,
        engine_null_reason=None,
        item_prompt_tokens=27,
        wraps_item_prompt=True,
    ) == {"tokens": None, "null_reason": "unmeasurable"}


def test_an_item_with_no_count_under_the_rows_tokenizer_is_not_zero() -> None:
    assert harness.prompt_overhead(
        engine_prompt_tokens=120,
        engine_null_reason=None,
        item_prompt_tokens=None,
        wraps_item_prompt=True,
    ) == {"tokens": None, "null_reason": "item_prompt_not_counted"}


@pytest.mark.parametrize("reason", sorted(timings.ITEM_NULL_REASONS))
def test_a_null_engine_count_passes_its_own_reason_through(reason) -> None:
    assert harness.prompt_overhead(
        engine_prompt_tokens=None,
        engine_null_reason=reason,
        item_prompt_tokens=27,
        wraps_item_prompt=True,
    ) == {"tokens": None, "null_reason": reason}


@pytest.mark.parametrize("reason", [None, "zero"])
def test_a_null_engine_count_without_its_reason_is_refused(reason) -> None:
    with pytest.raises(ValueError, match="needs its reason"):
        harness.prompt_overhead(
            engine_prompt_tokens=None,
            engine_null_reason=reason,
            item_prompt_tokens=27,
            wraps_item_prompt=True,
        )


def test_the_row_block_is_exactly_the_three_fields() -> None:
    overhead = harness.prompt_overhead(
        engine_prompt_tokens=27,
        engine_null_reason=None,
        item_prompt_tokens=27,
        wraps_item_prompt=True,
    )

    assert harness.row_fields("direct", overhead) == {
        "harness_id": "direct",
        "harness_version": metadata.version("requests"),
        "harness_prompt_overhead": {"tokens": 0, "null_reason": None},
    }
