import copy
import json
from pathlib import Path

import pytest

from wave_local_ai_v2 import scoring_rules, suite_registry, suite_snapshot
from wave_local_ai_v2.suite_gate import SuiteGateError
from wave_local_ai_v2.suite_registry import SuiteRegistryError

# Today's identities, pinned as literals: the migration onto data must move
# neither the version nor the prompt-set hash of either shipped suite.
_SHIPPED = {
    "classification-support-routing": (
        "3",
        "d41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a",  # pragma: allowlist secret
    ),
    "translation-business-short-form": (
        "2",
        "16150e4406042a8940093740640627b7ce4ce9e80ae64bc080b7b4d80f6f7574",  # pragma: allowlist secret
    ),
}

_VALID = {
    "suite_id": "fixture-suite",
    "suite_version": "1",
    "task_suite": "classification",
    "scoring_rule": "exact_label_match",
    "max_output_tokens": 8,
    "stop_sequences": [],
    "context_length": 2048,
    "thinking_policy": "disabled",
    "items": [
        {
            "item_id": f"item-{language}",
            "prompt": f"Classify ({language}).",
            "expected_label": "billing",
            "language": language,
            "provenance": "hand_written",
            "contamination_risk": False,
        }
        for language in ("en", "fr", "de")
    ],
}


def _write(tmp_path: Path, data: object, name: str = "fixture-suite.json") -> Path:
    path = tmp_path / name
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _variant(**changes: object) -> dict:
    data = copy.deepcopy(_VALID)
    data.update(changes)
    return data


@pytest.fixture
def registered():
    ids: list[str] = []
    yield ids
    for suite_id in ids:
        suite_registry.unregister(suite_id)


# --- the two shipped suites ---------------------------------------------------


def test_the_shipped_suites_are_the_registered_ones() -> None:
    assert suite_registry.registered_ids() == sorted(_SHIPPED)


@pytest.mark.parametrize("suite_id", sorted(_SHIPPED))
def test_a_shipped_suite_keeps_its_version_and_prompt_set_hash(suite_id) -> None:
    definition = suite_registry.resolve(suite_id)

    assert (definition.suite_version, definition.prompt_set_hash) == _SHIPPED[suite_id]
    assert definition.prompt_set_hash == suite_registry.prompt_set_hash(
        definition.items
    )
    assert definition.gate["indicative"] is False


def test_resolving_twice_returns_the_one_cached_definition() -> None:
    first = suite_registry.resolve("classification-support-routing")

    assert suite_registry.resolve("classification-support-routing") is first


def test_a_resolved_item_cannot_be_edited_in_place() -> None:
    item = suite_registry.resolve("classification-support-routing").items[0]

    with pytest.raises(TypeError):
        item["prompt"] = "edited"  # type: ignore[index]


def test_regenerating_the_snapshots_reproduces_the_committed_files(
    tmp_path, monkeypatch
) -> None:
    """Byte for byte, through the exporter's own entry point. Line endings
    are folded on both sides: a Windows checkout may hold CRLF, and the
    exporter writes the platform newline."""
    monkeypatch.setattr(suite_snapshot, "SUITE_DEFINITIONS_DIR", tmp_path)

    suite_snapshot.main()

    for suite_id, (version, _) in _SHIPPED.items():
        name = suite_snapshot.snapshot_filename(suite_id, version)
        committed = (Path("aidd_docs/results/suite-definitions") / name).read_bytes()
        regenerated = (tmp_path / name).read_bytes()
        assert regenerated.replace(b"\r\n", b"\n") == committed.replace(b"\r\n", b"\n")


# --- refusals ---------------------------------------------------------------


def test_an_unregistered_id_is_refused_naming_the_registered_ones() -> None:
    with pytest.raises(SuiteRegistryError) as exc:
        suite_registry.resolve("no-such-suite")

    message = str(exc.value)
    assert "'no-such-suite' is not registered" in message
    for suite_id in _SHIPPED:
        assert suite_id in message


def test_an_unknown_scoring_rule_is_refused_naming_the_rule(tmp_path) -> None:
    path = _write(tmp_path, _variant(scoring_rule="bleu_against_reference"))

    with pytest.raises(SuiteRegistryError) as exc:
        suite_registry.load_definition(path)

    assert "'bleu_against_reference'" in str(exc.value)
    assert "does not know" in str(exc.value)


@pytest.mark.parametrize("missing", ["language", "provenance"])
def test_an_item_missing_its_tag_is_refused_by_the_gate_at_load(
    tmp_path, missing
) -> None:
    data = _variant()
    del data["items"][1][missing]
    path = _write(tmp_path, data)

    with pytest.raises(SuiteGateError, match=f"missing '{missing}'"):
        suite_registry.load_definition(path)


def test_a_definition_the_gate_refuses_is_never_registered(
    tmp_path, registered
) -> None:
    data = _variant()
    data["items"][0]["contamination_risk"] = True
    path = _write(tmp_path, data)

    with pytest.raises(SuiteGateError):
        suite_registry.register(path)

    assert "fixture-suite" not in suite_registry.registered_ids()


@pytest.mark.parametrize(
    ("changes", "named"),
    [
        ({"suite_id": ""}, "suite_id"),
        ({"suite_version": 3}, "suite_version"),
        ({"max_output_tokens": 0}, "max_output_tokens"),
        ({"max_output_tokens": True}, "max_output_tokens"),
        ({"context_length": "32768"}, "context_length"),
        ({"stop_sequences": "###"}, "stop_sequences"),
        ({"stop_sequences": [1]}, "stop_sequences"),
        ({"thinking_policy": "sometimes"}, "thinking_policy"),
        ({"items": []}, "items"),
        ({"items": ["not an object"]}, "items"),
        ({"prompt_set_hash": "abc"}, "prompt_set_hash"),
    ],
)
def test_a_malformed_core_key_is_refused_naming_it(tmp_path, changes, named) -> None:
    path = _write(tmp_path, _variant(**changes))

    with pytest.raises(SuiteRegistryError, match=named):
        suite_registry.load_definition(path)


def test_a_missing_core_key_is_refused_naming_it(tmp_path) -> None:
    data = _variant()
    del data["context_length"]

    with pytest.raises(SuiteRegistryError, match="missing context_length"):
        suite_registry.load_definition(_write(tmp_path, data))


def test_an_item_without_an_id_or_a_prompt_is_refused(tmp_path) -> None:
    no_id = _variant()
    del no_id["items"][0]["item_id"]
    blank_prompt = _variant()
    blank_prompt["items"][0]["prompt"] = "  "

    with pytest.raises(SuiteRegistryError, match="item_id"):
        suite_registry.load_definition(_write(tmp_path, no_id))
    with pytest.raises(SuiteRegistryError, match="has no prompt"):
        suite_registry.load_definition(_write(tmp_path, blank_prompt))


def test_a_duplicated_item_id_is_refused(tmp_path) -> None:
    data = _variant()
    data["items"][1]["item_id"] = data["items"][0]["item_id"]

    with pytest.raises(SuiteRegistryError, match="twice"):
        suite_registry.load_definition(_write(tmp_path, data))


def test_a_file_that_is_not_a_json_object_is_refused(tmp_path) -> None:
    not_json = tmp_path / "broken.json"
    not_json.write_text("{", encoding="utf-8")

    with pytest.raises(SuiteRegistryError, match="is not JSON"):
        suite_registry.load_definition(not_json)
    with pytest.raises(SuiteRegistryError, match="not a JSON object"):
        suite_registry.load_definition(_write(tmp_path, [1, 2]))


def test_a_registered_id_cannot_be_registered_twice(tmp_path, registered) -> None:
    shipped = _variant(suite_id="classification-support-routing")

    with pytest.raises(SuiteRegistryError, match="already registered"):
        suite_registry.register(_write(tmp_path, shipped))


def test_a_shipped_file_whose_id_differs_from_its_name_is_refused(
    tmp_path, monkeypatch
) -> None:
    _write(tmp_path, _variant(suite_id="another-id"), name="fixture-suite.json")
    monkeypatch.setattr(suite_registry, "_built_in_dir", lambda: tmp_path)
    monkeypatch.setattr(suite_registry, "_LOADED", {})

    with pytest.raises(SuiteRegistryError, match="file name and the id must match"):
        suite_registry.resolve("fixture-suite")


# --- registration and the open shape ---------------------------------------


def test_a_registered_suite_resolves_and_scores_by_its_named_rule(
    tmp_path, registered
) -> None:
    definition = suite_registry.register(_write(tmp_path, _VALID))
    registered.append(definition.suite_id)

    assert suite_registry.resolve("fixture-suite") is definition
    assert "fixture-suite" in suite_registry.registered_ids()
    # Three items is below the gate's minimum: indicative, not refused.
    assert definition.gate["indicative"] is True
    completion = {
        "content": "billing",
        "truncated": False,
        "generated_tokens": 1,
        "truncation_reason": None,
    }
    per_item, batch = definition.score_batch([completion] * 3)
    assert [row["correct"] for row in per_item] == [True, True, True]
    assert batch["suite_accuracy"] == 1.0


def test_unregister_drops_only_a_run_time_registration(tmp_path) -> None:
    suite_registry.register(_write(tmp_path, _VALID))
    suite_registry.unregister("fixture-suite")
    suite_registry.unregister("classification-support-routing")

    assert suite_registry.registered_ids() == sorted(_SHIPPED)


def test_the_interval_epics_fields_are_additions_to_the_one_shape(
    tmp_path, registered
) -> None:
    """Declared level, source, licence, source revision, content hash and
    selection rule: carried as data on the suite and on each item, and
    exported in the snapshot, with no second shape and no loader change."""
    data = _variant(
        level="publication",
        source="example-dataset",
        source_revision="abc123",
        selection_rule={"seed": 1, "n": 3},
    )
    for item in data["items"]:
        item["licence"] = "CC-BY-4.0"
        item["content_hash"] = "sha256:00"
    definition = suite_registry.register(_write(tmp_path, data))
    registered.append(definition.suite_id)

    assert dict(definition.extra) == {
        "level": "publication",
        "source": "example-dataset",
        "source_revision": "abc123",
        "selection_rule": {"seed": 1, "n": 3},
    }
    assert all(item["licence"] == "CC-BY-4.0" for item in definition.items)
    snapshot = suite_snapshot.build_snapshot(definition)
    assert snapshot["level"] == "publication"
    assert snapshot["items"][0]["content_hash"] == "sha256:00"


def test_every_shipped_rule_is_named_in_the_rule_table() -> None:
    for suite_id in _SHIPPED:
        rule = suite_registry.resolve(suite_id).scoring_rule
        assert rule in scoring_rules.SCORING_RULES
