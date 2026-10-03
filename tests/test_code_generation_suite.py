"""The code-generation suite: its data, and scoring by planted generations.

Every generation here is planted and scored through the registered suite's
own rule (`SuiteDefinition.score_batch`), with the autouse fake sandbox
(`conftest.FakeSandbox`) deciding each run: no container starts and no
generated code runs on the host.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import (
    code_generation_suite,
    code_sandbox,
    read_model,
    row_contract,
    suite_gate,
    suite_registry,
    use_case_coverage,
)

SUITE_ID = "code-generation-python-javascript"
_CORRECT = "def chunk(items, size):\n    return items\n"


def _completion(content: str, **overrides: Any) -> dict[str, Any]:
    return {
        "content": content,
        "truncated": False,
        "generated_tokens": 40,
        "truncation_reason": None,
        **overrides,
    }


@pytest.fixture
def suite() -> suite_registry.SuiteDefinition:
    return suite_registry.resolve(SUITE_ID)


# --- the suite's data ---------------------------------------------------------


def test_the_suite_tags_both_languages_and_each_instruction_language(suite) -> None:
    languages = [item["programming_language"] for item in suite.items]

    assert len(suite.items) >= suite_gate.MIN_SUITE_ITEMS
    assert set(languages) == {"python", "javascript"}
    assert suite.scoring_rule == "unit_tests_pass"
    for share in suite.gate["language_shares"].values():
        assert share >= suite_gate.MIN_LANGUAGE_SHARE
    for item in suite.items:
        assert item["tests"].strip()
        assert item["provenance"] == "hand_written"
        assert item["contamination_risk"] is False
        assert item["licence"] == suite_gate.HAND_WRITTEN_LICENCE


def test_javascript_tests_use_only_node_built_ins(suite) -> None:
    for item in suite.items:
        if item["programming_language"] == "javascript":
            imports = [
                line for line in item["tests"].splitlines() if line.startswith("import")
            ]
            assert all(
                '"node:' in line or '"./solution.mjs"' in line for line in imports
            )


def test_the_coverage_record_names_the_suite_for_code_generation() -> None:
    record = json.loads(
        (
            Path(use_case_coverage.__file__).parent / use_case_coverage.RECORD_FILENAME
        ).read_text(encoding="utf-8")
    )
    entry = next(e for e in record["entries"] if e["use_case"] == "code-generation")

    assert entry == {
        "use_case": "code-generation",
        "state": "exercised",
        "suite_ids": [SUITE_ID],
    }


def test_a_code_suite_whose_items_cannot_be_scored_is_refused(tmp_path) -> None:
    data = json.loads(
        (
            Path(suite_registry.__file__).parent / "suite_data" / f"{SUITE_ID}.json"
        ).read_text(encoding="utf-8")
    )
    data["suite_id"] = "broken-code-suite"
    for item in data["items"]:
        item["programming_language"] = "python"
    data["items"][0].pop("tests")
    data["items"][1]["programming_language"] = "rust"
    path = tmp_path / "broken.json"
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(suite_registry.SuiteRegistryError) as refusal:
        suite_registry.load_definition(path)

    message = str(refusal.value)
    assert "carries no tests" in message
    assert "'rust'" in message
    assert "no item is tagged javascript" in message


# --- the preflight -------------------------------------------------------------


def test_the_preflight_checks_the_sandbox_for_every_tagged_language(
    suite, fake_sandbox
) -> None:
    suite.preflight()

    assert fake_sandbox.checked == [("python", "javascript")]


def test_a_suite_with_no_sandboxed_rule_has_nothing_to_preflight(fake_sandbox) -> None:
    suite_registry.resolve("translation-business-short-form").preflight()

    assert fake_sandbox.checked == []


def test_with_no_container_runtime_the_suite_refuses_and_runs_nothing(
    suite, monkeypatch
) -> None:
    runs: list[Any] = []
    monkeypatch.setattr(code_sandbox, "active_runner", code_sandbox.DockerSandbox)
    monkeypatch.setattr(code_sandbox.shutil, "which", lambda name: None)
    monkeypatch.setattr(code_sandbox.subprocess, "run", lambda *a, **k: runs.append(a))

    with pytest.raises(code_sandbox.SandboxUnavailable):
        suite.preflight()
    with pytest.raises(code_sandbox.SandboxUnavailable):
        suite.score_batch([_completion(_CORRECT)] * len(suite.items))

    assert runs == []


# --- scoring planted generations -------------------------------------------------


def _score(suite, fake_sandbox, content_by_item: dict[str, dict[str, Any]]):
    completions = [
        content_by_item.get(item["item_id"], _completion("```python\nx = 1\n```"))
        for item in suite.items
    ]
    return suite.score_batch(completions)


def test_a_planted_correct_generation_scores_1_and_a_failing_one_0(
    suite, fake_sandbox
) -> None:
    fake_sandbox.outcomes[_CORRECT] = code_sandbox.STATUS_PASSED
    per_item, batch = _score(
        suite,
        fake_sandbox,
        {"py-en-04": _completion(f"Here it is:\n```python\n{_CORRECT}```\nDone.")},
    )
    by_id = {item["item_id"]: fields for item, fields in zip(suite.items, per_item)}

    assert by_id["py-en-04"]["item_score"] == 1.0
    assert by_id["py-en-04"]["failure_reason"] is None
    assert by_id["py-en-01"]["item_score"] == 0.0
    assert by_id["py-en-01"]["failure_reason"] == "tests_failed"
    # The failures stay in the denominator.
    assert batch["suite_score"] == pytest.approx(1 / len(suite.items))
    assert batch["failure_counts"]["tests_failed"] == len(suite.items) - 1
    # The tests ran against the fenced code only, never the prose around it.
    assert ("python", _CORRECT, suite.items[3]["tests"]) in fake_sandbox.runs


@pytest.mark.parametrize(
    ("completion", "reason", "runs"),
    [
        (_completion("   "), "empty", 0),
        (_completion("```python\n\n```"), "empty", 0),
        (_completion("```python\ndef f(:"), "unparseable", 0),
        (
            _completion("def f():", truncated=True, generated_tokens=512),
            "truncated_max_tokens",
            0,
        ),
        (
            _completion("def f():", truncated=True, generated_tokens=10),
            "truncated_context",
            0,
        ),
        (
            _completion(
                "def f():",
                truncated=True,
                generated_tokens=10,
                truncation_reason="truncated_max_tokens",
            ),
            "truncated_max_tokens",
            0,
        ),
        (_completion("def f(:\n"), "compile_error", 1),
        (_completion("while True: pass\n"), "timeout", 1),
    ],
)
def test_every_failed_generation_scores_0_and_names_its_reason(
    suite, fake_sandbox, completion, reason, runs
) -> None:
    fake_sandbox.outcomes["def f(:\n"] = code_sandbox.STATUS_COMPILE_ERROR
    fake_sandbox.outcomes["while True: pass\n"] = code_sandbox.STATUS_TIMEOUT
    item = suite.items[0]

    fields = code_generation_suite.score_item(
        item, completion, max_output_tokens=512, runner=fake_sandbox
    )

    assert (fields["item_score"], fields["failure_reason"]) == (0.0, reason)
    assert len(fake_sandbox.runs) == runs
    assert fields["sandbox"]["network"] == "none"


def test_a_sandbox_lost_mid_batch_stops_scoring(suite, fake_sandbox) -> None:
    def gone(*args: Any) -> None:
        raise code_sandbox.SandboxUnavailable("sandbox gone")

    fake_sandbox.run = gone  # type: ignore[method-assign]

    with pytest.raises(code_sandbox.SandboxUnavailable):
        _score(suite, fake_sandbox, {})


def test_extract_code_takes_the_first_fence_or_the_whole_answer() -> None:
    assert code_generation_suite.extract_code("```js\na\n```\n```js\nb\n```") == "a\n"
    assert code_generation_suite.extract_code("x = 1") == "x = 1"
    assert code_generation_suite.extract_code("```python\nx = 1") is None


# --- the published rows and the per-language read ---------------------------------


def test_the_breakdown_has_a_cell_only_for_tagged_languages(
    suite, fake_sandbox
) -> None:
    _, batch = _score(suite, fake_sandbox, {})
    row = {"programming_language_breakdown": batch["programming_language_breakdown"]}

    assert set(batch["programming_language_breakdown"]) == {"python", "javascript"}
    assert read_model.programming_language_score(row, "python") == {
        "score": 0.0,
        "n": 12,
    }
    assert read_model.programming_language_score(row, "rust") is None
    assert read_model.programming_language_score({}, "python") is None


def test_a_suite_tagging_one_language_answers_nothing_for_the_other(suite) -> None:
    python_items = [i for i in suite.items if i["programming_language"] == "python"]
    per_item = [{"item_score": 1.0, "failure_reason": None} for _ in python_items]

    batch = code_generation_suite.aggregate(python_items, per_item)

    assert set(batch["programming_language_breakdown"]) == {"python"}
    row = {"programming_language_breakdown": batch["programming_language_breakdown"]}
    assert read_model.programming_language_score(row, "javascript") is None


def test_per_item_and_batch_fields_carry_the_whole_code_block(
    suite, fake_sandbox
) -> None:
    per_item, batch = _score(suite, fake_sandbox, {})

    for fields in per_item:
        assert row_contract.CODE_FIELDS - {"programming_language_breakdown"} <= set(
            fields
        )
        assert row_contract.GRADED_FIELDS - {"suite_score", "score_breakdown"} <= set(
            fields
        )
        assert fields["reference_output"] in {item["tests"] for item in suite.items}
    assert {"suite_score", "score_breakdown", "programming_language_breakdown"} <= set(
        batch
    )
    assert batch["suite_accuracy"] is None and batch["language_breakdown"] is None
