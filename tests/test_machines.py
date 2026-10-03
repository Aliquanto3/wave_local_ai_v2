"""The declared machine registry: the shipped entries and every refusal."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import machines

SHIPPED = Path(machines.DEFAULT_REGISTRY_PATH)
PRD_MACHINES = ["laptop-mobile-gpu", "pro-pc-no-gpu", "tower-desktop-gpu"]


def _raw() -> dict[str, Any]:
    raw: dict[str, Any] = json.loads(SHIPPED.read_text(encoding="utf-8"))
    return raw


def _write(tmp_path: Path, raw: Any) -> Path:
    path = tmp_path / "machines.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    return path


def test_the_shipped_registry_declares_the_three_prd_machines() -> None:
    registry = machines.load_registry(SHIPPED)

    assert sorted(registry.entries) == PRD_MACHINES
    assert machines.declared_machine_ids() == frozenset(PRD_MACHINES)
    assert registry.entries["laptop-mobile-gpu"].gpu_present is True
    assert registry.entries["tower-desktop-gpu"].gpu_present is True
    assert registry.entries["pro-pc-no-gpu"].gpu_present is False


def test_every_shipped_fact_is_marked_and_an_unread_one_carries_no_value() -> None:
    registry = machines.load_registry(SHIPPED)

    for entry in registry.entries.values():
        assert set(entry.facts) == set(machines.REQUIRED_FACTS)
        for fact in entry.facts.values():
            assert fact["source"] in machines.FACT_SOURCES
            assert fact["read_from"].strip()
            if fact["source"] == machines.SOURCE_NOT_YET_DECLARED:
                assert fact["value"] is None


def test_the_laptop_declares_its_memory_generation_and_speed() -> None:
    laptop = machines.tracked_registry().entries["laptop-mobile-gpu"]

    assert laptop.facts["memory_type"]["value"] == "DDR4"
    assert laptop.facts["memory_rated_speed_mts"]["value"] == 3200
    assert laptop.facts["memory_type"]["source"] == machines.SOURCE_DECLARED


@pytest.mark.parametrize("fact", machines.REQUIRED_FACTS)
def test_an_entry_missing_a_fact_refuses_naming_it(tmp_path: Path, fact: str) -> None:
    raw = _raw()
    del raw["machines"]["laptop-mobile-gpu"]["facts"][fact]

    with pytest.raises(machines.MachineRegistryError, match=f"facts.{fact}"):
        machines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize("field", ["description", "facts"])
def test_an_entry_missing_a_block_refuses_naming_it(tmp_path: Path, field: str) -> None:
    raw = _raw()
    del raw["machines"]["pro-pc-no-gpu"][field]

    with pytest.raises(machines.MachineRegistryError, match=field):
        machines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda f: f.pop("read_from"), "missing read_from"),
        (lambda f: f.update(source="guessed"), "'source' must be one of"),
        (lambda f: f.update(read_from=" "), "'read_from' must be"),
        (
            lambda f: f.update(source="not_yet_declared", value="DDR4"),
            "carries a value",
        ),
        (lambda f: f.update(value=None), "declared with no value"),
    ],
)
def test_a_malformed_fact_refuses(tmp_path: Path, mutate: Any, match: str) -> None:
    raw = _raw()
    mutate(raw["machines"]["laptop-mobile-gpu"]["facts"]["memory_type"])

    with pytest.raises(machines.MachineRegistryError, match=match):
        machines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize(
    "gpu_present",
    [
        {"value": None, "source": "not_yet_declared", "read_from": "awaits"},
        {"value": "yes", "source": "declared", "read_from": "a note"},
    ],
)
def test_gpu_presence_must_be_a_declared_boolean(
    tmp_path: Path, gpu_present: dict[str, Any]
) -> None:
    raw = _raw()
    raw["machines"]["tower-desktop-gpu"]["facts"]["gpu_present"] = gpu_present

    with pytest.raises(machines.MachineRegistryError, match="gpu_present"):
        machines.load_registry(_write(tmp_path, raw))


def test_a_gpu_fact_declared_null_is_refused_on_a_machine_with_a_gpu(
    tmp_path: Path,
) -> None:
    raw = _raw()
    raw["machines"]["laptop-mobile-gpu"]["facts"]["gpu_model"] = {
        "value": None,
        "source": "declared",
        "read_from": "nothing",
    }

    with pytest.raises(machines.MachineRegistryError, match="gpu_model"):
        machines.load_registry(_write(tmp_path, raw))


@pytest.mark.parametrize(
    ("raw", "match"),
    [
        ([], "must be an object with"),
        ({"registry_version": True, "machines": {"a": {}}}, "must be an integer"),
        ({"registry_version": 1, "machines": {}}, "non-empty object"),
        ({"registry_version": 1, "machines": {"a": []}}, "must be an object"),
    ],
)
def test_a_malformed_registry_refuses(tmp_path: Path, raw: Any, match: str) -> None:
    with pytest.raises(machines.MachineRegistryError, match=match):
        machines.load_registry(_write(tmp_path, raw))


def test_a_malformed_entry_shape_refuses(tmp_path: Path) -> None:
    raw = _raw()
    entry = copy.deepcopy(raw["machines"]["laptop-mobile-gpu"])
    for field, value, match in [
        ("description", "", "'description' must be"),
        ("facts", [], "'facts' must be an object"),
    ]:
        broken = _raw()
        broken["machines"]["laptop-mobile-gpu"] = {**entry, field: value}
        with pytest.raises(machines.MachineRegistryError, match=match):
            machines.load_registry(_write(tmp_path, broken))
    broken = _raw()
    broken["machines"]["laptop-mobile-gpu"]["facts"]["os"] = "Windows"
    with pytest.raises(machines.MachineRegistryError, match="must be an object"):
        machines.load_registry(_write(tmp_path, broken))


def test_an_unreadable_or_invalid_file_refuses(tmp_path: Path) -> None:
    with pytest.raises(machines.MachineRegistryError, match="not readable"):
        machines.load_registry(tmp_path / "absent.json")
    path = tmp_path / "machines.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(machines.MachineRegistryError, match="not valid JSON"):
        machines.load_registry(path)


def test_resolve_machine_names_the_declared_ids() -> None:
    registry = machines.tracked_registry()

    assert machines.resolve_machine(registry, "pro-pc-no-gpu").machine_id == (
        "pro-pc-no-gpu"
    )
    with pytest.raises(machines.MachineRegistryError, match="laptop-mobile-gpu"):
        machines.resolve_machine(registry, "my-box")


def test_only_a_declared_gpu_less_machine_declares_no_gpu(monkeypatch) -> None:
    assert machines.declares_no_gpu("pro-pc-no-gpu") is True
    assert machines.declares_no_gpu("laptop-mobile-gpu") is False
    assert machines.declares_no_gpu("undeclared") is False
    assert machines.declares_no_gpu(None) is False

    def broken() -> machines.MachineRegistry:
        raise machines.MachineRegistryError("unreadable")

    monkeypatch.setattr(machines, "tracked_registry", broken)
    assert machines.declares_no_gpu("pro-pc-no-gpu") is False
