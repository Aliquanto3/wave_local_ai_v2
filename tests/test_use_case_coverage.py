import copy
import json
from pathlib import Path

import pytest

from wave_local_ai_v2 import suite_registry, use_case_coverage
from wave_local_ai_v2.use_case_coverage import CoverageRefusal

_CLASSIFICATION = "classification-support-routing"
_TRANSLATION = "translation-business-short-form"
_REWRITING = "fixture-rewriting"


def _suite(suite_id: str, task_suite: str) -> dict:
    return {
        "suite_id": suite_id,
        "suite_version": "1",
        "task_suite": task_suite,
        "scoring_rule": "exact_label_match",
        "max_output_tokens": 8,
        "stop_sequences": [],
        "context_length": 2048,
        "thinking_policy": "disabled",
        "items": [
            {
                "item_id": f"item-{language}",
                "prompt": f"Rewrite ({language}).",
                "expected_label": "billing",
                "language": language,
                "provenance": "hand_written",
                "contamination_risk": False,
            }
            for language in ("en", "fr", "de")
        ],
    }


def _register(tmp_path: Path, suite_id: str, task_suite: str) -> None:
    path = tmp_path / f"{suite_id}.json"
    path.write_text(json.dumps(_suite(suite_id, task_suite)), encoding="utf-8")
    suite_registry.register(path)


@pytest.fixture
def rewriting_suite(tmp_path):
    _register(tmp_path, _REWRITING, "rewriting")
    yield _REWRITING
    suite_registry.unregister(_REWRITING)


_OUT_OF_SCOPE = {
    "state": "out-of-scope-this-release",
    "reason": "fixture: not built in this release",
}

# Every state in one record, every suite id resolvable once the fixture
# rewriting suite is registered.
_COMPLETE = {
    "entries": [
        {
            "use_case": "classification",
            "state": "exercised",
            "suite_ids": [_CLASSIFICATION],
        },
        {"use_case": "translation", "state": "exercised", "suite_ids": [_TRANSLATION]},
        {"use_case": "document-comparison", **_OUT_OF_SCOPE},
        {"use_case": "text-rewriting", "state": "exercised", "suite_ids": [_REWRITING]},
        {"use_case": "code-generation", **_OUT_OF_SCOPE},
        {"use_case": "agentic-planning", **_OUT_OF_SCOPE},
        {"use_case": "agentic-tool-calling", **_OUT_OF_SCOPE},
        {"use_case": "web-research", **_OUT_OF_SCOPE},
        {"use_case": "rag-answer-generation", **_OUT_OF_SCOPE},
        {
            "use_case": "multilingual-en-fr-de",
            "state": "covered-by-dimension",
            "suite_ids": [_CLASSIFICATION, _TRANSLATION, _REWRITING],
        },
    ]
}


def _complete() -> dict:
    return copy.deepcopy(_COMPLETE)


def _edit_in(data: dict, use_case: str, **changes: object) -> dict:
    for entry in data["entries"]:
        if entry["use_case"] == use_case:
            entry.update(changes)
    return data


def _edit(use_case: str, **changes: object) -> dict:
    return _edit_in(_complete(), use_case, **changes)


def _without(use_case: str) -> dict:
    data = _complete()
    data["entries"] = [e for e in data["entries"] if e["use_case"] != use_case]
    return data


def _refusal(data: object) -> list[str]:
    with pytest.raises(CoverageRefusal) as refused:
        use_case_coverage.gate_record(data)
    return refused.value.failures


def _write(tmp_path: Path, data: object, name: str = "record.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


# --- the gate ---------------------------------------------------------------


def test_a_complete_record_passes_in_prd_order(rewriting_suite) -> None:
    data = _complete()
    data["entries"].reverse()
    entries = use_case_coverage.gate_record(data)
    assert [entry["use_case"] for entry in entries] == list(use_case_coverage.USE_CASES)


@pytest.mark.parametrize("use_case", use_case_coverage.USE_CASES)
def test_removing_any_entry_refuses_naming_that_use_case(
    rewriting_suite, use_case
) -> None:
    assert _refusal(_without(use_case)) == [f"{use_case}: missing from the record"]


@pytest.mark.parametrize(
    "blank", [{"state": None}, {"state": ""}], ids=["null", "empty"]
)
def test_a_blank_state_refuses_naming_the_entry(rewriting_suite, blank) -> None:
    assert _refusal(_edit("code-generation", **blank)) == [
        "code-generation: has no state"
    ]


def test_an_absent_state_refuses_naming_the_entry(rewriting_suite) -> None:
    data = _complete()
    del data["entries"][4]["state"]
    assert _refusal(data) == ["code-generation: has no state"]


def test_an_unknown_state_refuses_naming_it(rewriting_suite) -> None:
    (failure,) = _refusal(_edit("web-research", state="planned"))
    assert failure.startswith("web-research: state 'planned' is not one of")


@pytest.mark.parametrize("use_case", ["classification", "multilingual-en-fr-de"])
def test_an_unregistered_suite_refuses_naming_the_entry_and_the_suite(
    rewriting_suite, use_case
) -> None:
    data = _edit(use_case, suite_ids=[_CLASSIFICATION, "no-such-suite"])
    assert _refusal(data) == [
        f"{use_case}: suite 'no-such-suite' does not resolve in the registry"
    ]


def test_a_suite_the_gate_refuses_does_not_resolve(
    rewriting_suite, tmp_path, monkeypatch
) -> None:
    refused = _suite("gate-refused", "rewriting")
    del refused["items"][0]["language"]
    path = _write(tmp_path, refused, name="gate-refused.json")
    resolve = suite_registry.resolve

    # A shipped file the suite gate refuses: resolving it loads it, and the
    # load raises the gate's own refusal.
    def resolve_with_refused(suite_id: str) -> suite_registry.SuiteDefinition:
        if suite_id == "gate-refused":
            return suite_registry.load_definition(path)
        return resolve(suite_id)

    monkeypatch.setattr(suite_registry, "resolve", resolve_with_refused)
    data = _edit("text-rewriting", suite_ids=["gate-refused"])
    assert _refusal(data) == [
        "text-rewriting: suite 'gate-refused' does not resolve in the registry"
    ]


@pytest.mark.parametrize("suite_ids", [[], None, "not-a-list", [""]])
def test_a_suite_state_with_no_suite_id_refuses(rewriting_suite, suite_ids) -> None:
    assert _refusal(_edit("translation", suite_ids=suite_ids)) == [
        "translation: state exercised names no suite id"
    ]


@pytest.mark.parametrize("reason", [None, "", "   "], ids=["null", "empty", "blank"])
def test_an_out_of_scope_entry_without_a_reason_refuses(
    rewriting_suite, reason
) -> None:
    assert _refusal(_edit("web-research", reason=reason)) == [
        "web-research: state out-of-scope-this-release has no reason"
    ]


def test_an_out_of_scope_entry_with_its_reason_absent_refuses(rewriting_suite) -> None:
    data = _complete()
    del data["entries"][7]["reason"]
    assert _refusal(data) == [
        "web-research: state out-of-scope-this-release has no reason"
    ]


def test_three_failing_entries_are_all_named(rewriting_suite) -> None:
    data = _without("agentic-planning")
    for entry in data["entries"]:
        if entry["use_case"] == "document-comparison":
            entry["state"] = None
        if entry["use_case"] == "rag-answer-generation":
            entry["reason"] = ""
    assert _refusal(data) == [
        "document-comparison: has no state",
        "agentic-planning: missing from the record",
        "rag-answer-generation: state out-of-scope-this-release has no reason",
    ]


def test_registering_a_suite_never_makes_a_use_case_exercised(
    rewriting_suite, tmp_path
) -> None:
    data = _edit("code-generation", state=None)
    del data["entries"][4]["reason"]
    _register(tmp_path, "fixture-code-generation", "code-generation")
    try:
        assert _refusal(data) == ["code-generation: has no state"]
    finally:
        suite_registry.unregister("fixture-code-generation")


def test_an_entry_mixing_both_states_fields_refuses(rewriting_suite) -> None:
    data = _edit("classification", reason="also out of scope")
    data = _edit_in(data, "web-research", suite_ids=[_CLASSIFICATION])
    assert _refusal(data) == [
        (
            "classification: state exercised carries a reason, which only "
            "out-of-scope-this-release declares"
        ),
        (
            "web-research: state out-of-scope-this-release names suite ids, "
            "which it cannot carry"
        ),
    ]


def test_an_unknown_or_duplicated_or_unnamed_entry_refuses(rewriting_suite) -> None:
    data = _complete()
    data["entries"] += [
        {"use_case": "multilingual", **_OUT_OF_SCOPE},
        copy.deepcopy(data["entries"][0]),
        {"state": "exercised", "suite_ids": [_CLASSIFICATION]},
        "not-an-object",
    ]
    assert _refusal(data) == [
        "multilingual: not a PRD use case",
        "classification: declared more than once",
        "entry 13: names no use case",
        "entry 14: names no use case",
    ]


@pytest.mark.parametrize("data", [[], {}, {"entries": {}}])
def test_a_record_without_an_entries_list_refuses(data) -> None:
    assert _refusal(data) == ["the record holds no 'entries' list"]


# --- the committed record ---------------------------------------------------


def test_the_committed_record_declares_all_ten_use_cases() -> None:
    record = use_case_coverage.load_record(use_case_coverage.default_record())
    assert [entry["use_case"] for entry in record["entries"]] == list(
        use_case_coverage.USE_CASES
    )


def test_the_multilingual_entry_is_a_dimension_of_three_suites() -> None:
    record = use_case_coverage.load_record(use_case_coverage.default_record())
    (multilingual,) = [
        e for e in record["entries"] if e["use_case"] == "multilingual-en-fr-de"
    ]
    assert multilingual["state"] == "covered-by-dimension"
    assert multilingual["suite_ids"] == [
        _CLASSIFICATION,
        _TRANSLATION,
        "rewriting-business-email",
    ]


# --- the publish command ----------------------------------------------------


def test_the_command_publishes_a_complete_record(
    rewriting_suite, tmp_path, capsys
) -> None:
    output = tmp_path / "results" / "use-case-coverage.json"
    record = _write(tmp_path, _complete())
    assert (
        use_case_coverage.main(["--record", str(record), "--output", str(output)]) == 0
    )
    published = json.loads(output.read_text(encoding="utf-8"))
    assert published == {"use_cases": _COMPLETE["entries"]}
    assert capsys.readouterr().out.strip() == str(output)


def test_the_command_refuses_and_writes_nothing(
    rewriting_suite, tmp_path, capsys
) -> None:
    output = tmp_path / "use-case-coverage.json"
    record = _write(tmp_path, _without("web-research"))
    assert (
        use_case_coverage.main(["--record", str(record), "--output", str(output)]) == 1
    )
    assert not output.exists()
    assert "- web-research: missing from the record" in capsys.readouterr().err


def test_the_command_refuses_a_record_that_is_not_json(tmp_path, capsys) -> None:
    output = tmp_path / "use-case-coverage.json"
    record = tmp_path / "record.json"
    record.write_text("{not json", encoding="utf-8")
    assert (
        use_case_coverage.main(["--record", str(record), "--output", str(output)]) == 1
    )
    assert not output.exists()
    assert "is not JSON" in capsys.readouterr().err


def test_run_today_the_command_refuses_naming_what_is_not_yet_covered(
    tmp_path, capsys
) -> None:
    output = tmp_path / "use-case-coverage.json"
    assert use_case_coverage.main(["--output", str(output)]) == 1
    assert not output.exists()
    unresolved = "suite 'rewriting-business-email' does not resolve in the registry"
    assert capsys.readouterr().err.splitlines()[1:] == [
        "- document-comparison: has no state",
        f"- text-rewriting: {unresolved}",
        "- code-generation: has no state",
        "- agentic-planning: has no state",
        "- agentic-tool-calling: has no state",
        "- web-research: has no state",
        "- rag-answer-generation: has no state",
        f"- multilingual-en-fr-de: {unresolved}",
    ]
