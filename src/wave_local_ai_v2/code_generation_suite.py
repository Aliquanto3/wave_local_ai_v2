"""Code-generation task suite: what its scoring needs.

The suite itself is data (`suite_data/code-generation-python-javascript.json`),
resolved by id through `suite_registry` and scored by the `unit_tests_pass`
rule (`scoring_rules.py`). Each item asks for one function in Python or
JavaScript, its instructions written in English, French or German, and
carries the tests the generated code must pass and its programming-language
tag.

Scoring is deterministic and judge-free: an item scores 1.0 when every one
of its tests passes inside the sandbox (`code_sandbox.py`) and 0.0
otherwise. Every zero names its reason and stays in the denominator
(Methodology 9): `empty`, `truncated_max_tokens`/`truncated_context`,
`unparseable` (a code fence opened and never closed), `compile_error`,
`tests_failed` or `timeout`.

The code is the first fenced block of the answer when it holds one, else the
whole answer. Nothing else is stripped or repaired: any further extraction
would be a scoring choice the published row could not show.

Rows publish the graded block (the tests are the `reference_output` the
score was computed against) plus the code block: the item's
`programming_language`, the `sandbox` and caps it ran under, and the batch's
`programming_language_breakdown`, which holds a cell only for a language
the suite tags -- asking it for any other language answers nothing.
"""

from __future__ import annotations

import re
from collections.abc import Mapping, Sequence
from typing import Any

from wave_local_ai_v2 import code_sandbox, score_interval
from wave_local_ai_v2.scoring import (
    FAILURE_REASON_EMPTY,
    FAILURE_REASON_TRUNCATED_CONTEXT,
    FAILURE_REASON_TRUNCATED_MAX_TOKENS,
    FAILURE_REASON_UNPARSEABLE,
    GradedItem,
    score_graded_suite_by_language,
)

METRIC_ID = "unit_tests_pass"
METRIC_VERSION = "1"
METRIC_PARAMS: Mapping[str, str] = {"pass_rule": "every_test_passes"}

FAILURE_REASON_COMPILE_ERROR = code_sandbox.STATUS_COMPILE_ERROR
FAILURE_REASON_TESTS_FAILED = code_sandbox.STATUS_TESTS_FAILED
FAILURE_REASON_TIMEOUT = code_sandbox.STATUS_TIMEOUT
FAILURE_REASONS = (
    FAILURE_REASON_EMPTY,
    FAILURE_REASON_UNPARSEABLE,
    FAILURE_REASON_TRUNCATED_MAX_TOKENS,
    FAILURE_REASON_TRUNCATED_CONTEXT,
    FAILURE_REASON_COMPILE_ERROR,
    FAILURE_REASON_TESTS_FAILED,
    FAILURE_REASON_TIMEOUT,
)

_FENCE = "```"
_FENCED_BLOCK = re.compile(r"```[^\n]*\n(.*?)```", re.DOTALL)


def item_problems(items: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every reason these items cannot form a code-generation suite."""
    problems = []
    for item in items:
        if item.get("programming_language") not in code_sandbox.PROGRAMMING_LANGUAGES:
            problems.append(
                f"item {item['item_id']!r} has programming_language "
                f"{item.get('programming_language')!r}, not one of "
                f"{', '.join(code_sandbox.PROGRAMMING_LANGUAGES)}"
            )
        tests = item.get("tests")
        if not (isinstance(tests, str) and tests.strip()):
            problems.append(f"item {item['item_id']!r} carries no tests")
    tagged = {item.get("programming_language") for item in items}
    for language in code_sandbox.PROGRAMMING_LANGUAGES:
        if language not in tagged:
            problems.append(f"no item is tagged {language}")
    return problems


def tagged_languages(items: Sequence[Mapping[str, Any]]) -> tuple[str, ...]:
    """The programming languages the suite tags, in the declared order."""
    tagged = {item["programming_language"] for item in items}
    return tuple(lang for lang in code_sandbox.PROGRAMMING_LANGUAGES if lang in tagged)


def preflight(items: Sequence[Mapping[str, Any]]) -> None:
    """Refuse the suite before any process starts unless its sandbox can run."""
    code_sandbox.active_runner().check_available(tagged_languages(items))


def extract_code(content: str) -> str | None:
    """The first fenced block, else the whole answer; None for an open fence."""
    match = _FENCED_BLOCK.search(content)
    if match is not None:
        return match.group(1)
    if _FENCE in content:
        return None
    return content


def _failure_before_run(
    completion: Mapping[str, Any], max_output_tokens: int
) -> tuple[str | None, str | None]:
    """(code, None) when the answer can be run, else (None, its reason)."""
    content = completion["content"]
    if content.strip() == "":
        return None, FAILURE_REASON_EMPTY
    if completion["truncated"]:
        reason = completion["truncation_reason"]
        if reason is None:
            reason = (
                FAILURE_REASON_TRUNCATED_MAX_TOKENS
                if completion["generated_tokens"] >= max_output_tokens
                else FAILURE_REASON_TRUNCATED_CONTEXT
            )
        return None, reason
    code = extract_code(content)
    if code is None:
        return None, FAILURE_REASON_UNPARSEABLE
    if code.strip() == "":
        return None, FAILURE_REASON_EMPTY
    return code, None


def score_item(
    item: Mapping[str, Any],
    completion: Mapping[str, Any],
    *,
    max_output_tokens: int,
    runner: code_sandbox.SandboxRunner,
) -> dict[str, Any]:
    """One item's row fields: the graded block plus the code block."""
    language = item["programming_language"]
    code, failure_reason = _failure_before_run(completion, max_output_tokens)
    if code is not None:
        outcome = runner.run(language, code, item["tests"])
        if outcome.status != code_sandbox.STATUS_PASSED:
            failure_reason = outcome.status
    return {
        "expected_label": None,
        "predicted_label": None,
        "correct": None,
        "failure_reason": failure_reason,
        "item_score": 0.0 if failure_reason is not None else 1.0,
        "subject_output": completion["content"],
        "reference_output": item["tests"],
        "metric_id": METRIC_ID,
        "metric_version": METRIC_VERSION,
        "metric_params": dict(METRIC_PARAMS),
        "programming_language": language,
        "sandbox": runner.describe(language),
    }


def programming_language_breakdown(
    items: Sequence[Mapping[str, Any]], per_item: Sequence[Mapping[str, Any]]
) -> dict[str, dict[str, Any]]:
    """Score and n per tagged programming language; no cell for any other."""
    breakdown: dict[str, dict[str, Any]] = {}
    for language in tagged_languages(items):
        scores = [
            fields["item_score"]
            for item, fields in zip(items, per_item, strict=True)
            if item["programming_language"] == language
        ]
        breakdown[language] = {"score": sum(scores) / len(scores), "n": len(scores)}
    return breakdown


def aggregate(
    items: Sequence[Mapping[str, Any]], per_item: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    """The batch fields over `items`, paired by position with `per_item`."""
    scores = [fields["item_score"] for fields in per_item]
    failure_counts = dict.fromkeys(FAILURE_REASONS, 0)
    for fields in per_item:
        if fields["failure_reason"] is not None:
            failure_counts[fields["failure_reason"]] += 1
    graded = [
        GradedItem(
            item_id=item["item_id"],
            item_score=fields["item_score"],
            failure_reason=fields["failure_reason"],
        )
        for item, fields in zip(items, per_item, strict=True)
    ]
    return {
        "suite_accuracy": None,
        "language_breakdown": None,
        "suite_score": sum(scores) / len(scores) if scores else 0.0,
        "score_breakdown": score_graded_suite_by_language(items, graded),  # type: ignore[arg-type]
        "programming_language_breakdown": programming_language_breakdown(
            items, per_item
        ),
        "failure_counts": failure_counts,
        "score_interval": score_interval.interval_block(items, scores),
    }
