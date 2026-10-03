"""The engine registry: the shipped entry, every refusal, and the path-free
configuration hash."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import engines, prompt_provenance

SHIPPED = Path(engines.DEFAULT_REGISTRY_PATH)


def _raw() -> dict[str, Any]:
    raw: dict[str, Any] = json.loads(SHIPPED.read_text(encoding="utf-8"))
    return raw


def _write(tmp_path: Path, raw: Any) -> Path:
    path = tmp_path / "engines.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def _entry(raw: dict[str, Any]) -> dict[str, Any]:
    entry: dict[str, Any] = raw["engines"]["llama.cpp"]
    return entry


def test_the_shipped_registry_holds_llama_cpp_as_its_one_reference_engine() -> None:
    registry = engines.load_registry(SHIPPED)

    assert sorted(registry.entries) == ["llama.cpp"]
    engine = engines.reference_engine(registry)
    assert engine.engine_id == "llama.cpp"
    assert engine.lifecycle == engines.LIFECYCLE_SPAWNED
    assert (engine.host, engine.default_port) == ("127.0.0.1", 8080)
    assert engine.thinking_switch == {"request_field": "chat_template_kwargs"}
    assert engines.tracked_reference_engine() == engine
    assert engines.registered_engine_ids() == frozenset({"llama.cpp"})


def test_the_shipped_endpoints_are_the_ones_the_local_client_calls() -> None:
    engine = engines.tracked_reference_engine()

    assert engine.endpoints["chat"] == prompt_provenance.LOCAL_CHAT_ENDPOINT
    assert (
        engine.endpoints["prompt_rendering"]
        == prompt_provenance.LOCAL_APPLY_TEMPLATE_ENDPOINT
    )


def test_every_shipped_default_is_marked_declared_or_engine_reported() -> None:
    engine = engines.tracked_reference_engine()

    sources = {d["source"] for d in engine.configuration_defaults.values()}
    assert sources == {engines.SOURCE_DECLARED, engines.SOURCE_ENGINE_REPORTED}


@pytest.mark.parametrize("field", engines.REQUIRED_FIELDS[""])
def test_an_entry_missing_a_top_level_field_is_refused_naming_it(
    tmp_path: Path, field: str
) -> None:
    raw = _raw()
    del _entry(raw)[field]

    with pytest.raises(engines.EngineRegistryError, match=f"missing.*{field}"):
        engines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize(
    ("block", "field"),
    [
        (block, field)
        for block, fields in engines.REQUIRED_FIELDS.items()
        if block
        for field in fields
    ],
)
def test_an_entry_missing_a_nested_field_is_refused_naming_its_path(
    tmp_path: Path, block: str, field: str
) -> None:
    raw = _raw()
    del _entry(raw)[block][field]

    with pytest.raises(engines.EngineRegistryError, match=f"{block}\\.{field}"):
        engines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize("field", engines.DEFAULT_FIELDS)
def test_a_default_missing_its_mark_or_value_is_refused(
    tmp_path: Path, field: str
) -> None:
    raw = _raw()
    del _entry(raw)["configuration_defaults"]["batch_size"][field]

    with pytest.raises(
        engines.EngineRegistryError,
        match=f"configuration_defaults\\.batch_size\\.{field}",
    ):
        engines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (
            lambda e: e["configuration_defaults"]["batch_size"].update(
                source="guessed"
            ),
            "source",
        ),
        (lambda e: e.update(lifecycle="daemon"), "lifecycle"),
        (lambda e: e.update(reference="yes"), "reference"),
        (lambda e: e["build_probe"].update(method="constant"), "build_probe.method"),
        (lambda e: e.update(default_port=0), "default_port"),
        (lambda e: e.update(default_port=True), "default_port"),
        (lambda e: e.update(host=""), "host"),
        (lambda e: e["endpoints"].update(chat=""), "endpoints.chat"),
        (lambda e: e.update(thinking_switch={}), "thinking_switch"),
        (lambda e: e.update(thinking_switch="off"), "thinking_switch"),
        (
            lambda e: e["config_normalisation"].update(location_flags="--host"),
            "location_flags",
        ),
        (lambda e: e.update(configuration_defaults={}), "configuration_defaults"),
        (lambda e: e["configuration_defaults"].update(batch_size=2048), "batch_size"),
        (
            lambda e: e["configuration_defaults"]["batch_size"].update(read_from=""),
            "read_from",
        ),
        (lambda e: e.update(endpoints=[]), "endpoints"),
    ],
)
def test_a_malformed_field_is_refused_naming_it(
    tmp_path: Path, mutate: Any, match: str
) -> None:
    raw = _raw()
    mutate(_entry(raw))

    with pytest.raises(engines.EngineRegistryError, match=match):
        engines.load_registry(_write(tmp_path, raw))


def test_a_switch_of_none_loads(tmp_path: Path) -> None:
    raw = _raw()
    _entry(raw)["thinking_switch"] = engines.THINKING_SWITCH_NONE

    engine = engines.reference_engine(engines.load_registry(_write(tmp_path, raw)))

    assert engine.thinking_switch == engines.THINKING_SWITCH_NONE


def test_the_shipped_llama_cpp_entry_carries_gbnf_in_the_grammar_field() -> None:
    engine = engines.tracked_reference_engine()

    assert engine.constraint_mechanisms == {"gbnf": "grammar"}


def test_an_entry_declaring_no_constraint_mechanism_loads_empty(tmp_path: Path) -> None:
    raw = _raw()
    _entry(raw)["constraint_mechanisms"] = {}

    engine = engines.reference_engine(engines.load_registry(_write(tmp_path, raw)))

    assert engine.constraint_mechanisms == {}


@pytest.mark.parametrize(
    ("mechanisms", "match"),
    [
        (["gbnf"], "'constraint_mechanisms' must be an object"),
        ({"json_schema": {"request_field": "x", "read_from": "y"}}, "json_schema"),
        ({"gbnf": {"request_field": "grammar"}}, "constraint_mechanisms.gbnf"),
        (
            {"gbnf": {"request_field": "", "read_from": "y"}},
            "constraint_mechanisms.gbnf.request_field",
        ),
        (
            {"gbnf": {"request_field": "grammar", "read_from": " "}},
            "constraint_mechanisms.gbnf.read_from",
        ),
    ],
)
def test_a_malformed_constraint_mechanism_is_refused_naming_it(
    tmp_path: Path, mechanisms: Any, match: str
) -> None:
    raw = _raw()
    _entry(raw)["constraint_mechanisms"] = mechanisms

    with pytest.raises(engines.EngineRegistryError, match=match):
        engines.load_registry(_write(tmp_path, raw))


def test_a_registry_without_exactly_one_reference_is_refused(tmp_path: Path) -> None:
    raw = _raw()
    second = copy.deepcopy(_entry(raw))
    raw["engines"]["ollama"] = second

    with pytest.raises(engines.EngineRegistryError, match="exactly one reference"):
        engines.load_registry(_write(tmp_path, raw))

    second["reference"] = False
    _entry(raw)["reference"] = False
    with pytest.raises(engines.EngineRegistryError, match="exactly one reference"):
        engines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize(
    ("content", "match"),
    [
        ("{not json", "not valid JSON"),
        (json.dumps({"engines": {}}), "'registry_version' and 'engines'"),
        (json.dumps({"registry_version": "1", "engines": {"a": {}}}), "integer"),
        (json.dumps({"registry_version": 1, "engines": {}}), "non-empty"),
        (
            json.dumps({"registry_version": 1, "engines": {"a": []}}),
            "must be an object",
        ),
    ],
)
def test_a_malformed_file_is_refused(tmp_path: Path, content: str, match: str) -> None:
    path = tmp_path / "engines.json"
    path.write_text(content, encoding="utf-8")

    with pytest.raises(engines.EngineRegistryError, match=match):
        engines.load_registry(path)


def test_an_unreadable_file_is_refused(tmp_path: Path) -> None:
    with pytest.raises(engines.EngineRegistryError, match="not readable"):
        engines.load_registry(tmp_path / "absent.json")


def test_resolve_engine_names_an_unknown_id() -> None:
    registry = engines.tracked_registry()

    assert engines.resolve_engine(registry, "llama.cpp").engine_id == "llama.cpp"
    with pytest.raises(engines.EngineRegistryError, match="'ollama'.*llama.cpp"):
        engines.resolve_engine(registry, "ollama")


def _flags(model_path: str, host: str = "127.0.0.1", port: str = "8080") -> list[str]:
    return ["-m", model_path, "-ngl", "99", "-t", "8", "--host", host, "--port", port]


def test_the_config_hash_is_identical_for_two_model_directories() -> None:
    engine = engines.tracked_reference_engine()

    first = engines.config_hash(engine, _flags("D:/ia/models/a.gguf"), "qwen3-0.6b-q8")
    second = engines.config_hash(engine, _flags("/srv/models/a.gguf"), "qwen3-0.6b-q8")

    assert first == second
    assert engines.normalise_config(engine, _flags("D:/x.gguf"), "qwen3-0.6b-q8") == [
        "-m",
        "roster:qwen3-0.6b-q8",
        "-ngl",
        "99",
        "-t",
        "8",
    ]


def test_the_config_hash_ignores_host_and_port_but_not_a_flag() -> None:
    engine = engines.tracked_reference_engine()
    base = engines.config_hash(engine, _flags("a.gguf"), "e")

    assert engines.config_hash(engine, _flags("a.gguf", "0.0.0.0", "9090"), "e") == base
    changed = _flags("a.gguf")
    changed[5] = "4"
    assert engines.config_hash(engine, changed, "e") != base
    assert engines.config_hash(engine, _flags("a.gguf"), "other-entry") != base


def test_flags_without_a_model_path_cannot_be_normalised() -> None:
    engine = engines.tracked_reference_engine()

    with pytest.raises(engines.EngineRegistryError, match="'-m'"):
        engines.config_hash(engine, ["-ngl", "99"], "e")


def test_fiche_fields_probe_the_build_through_the_entry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    engine = engines.tracked_reference_engine()
    probed: list[Path] = []

    def probe(server_path: Path) -> str:
        probed.append(server_path)
        return "b10537"

    monkeypatch.setitem(engines._BUILD_PROBES, "version_flag", probe)

    fields = engines.fiche_fields(
        engine, Path("llama-server.exe"), _flags("a.gguf"), "e"
    )

    assert probed == [Path("llama-server.exe")]
    assert fields == {
        "engine_id": "llama.cpp",
        "engine_build": "b10537",
        "engine_config_hash": engines.config_hash(engine, _flags("a.gguf"), "e"),
    }
    assert engines.base_url(engine) == "http://127.0.0.1:8080"
