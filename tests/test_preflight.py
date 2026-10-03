"""The pre-flight check: declared minimums against what the machine reports."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from store_fixtures import ROSTER_REQUIREMENTS

from wave_local_ai_v2 import machines, preflight, profiles, roster, row_contract
from wave_local_ai_v2.results import append_refusal, read_rows_from_floor

ENTRY_ID = "fake-entry"
LAPTOP = "laptop-mobile-gpu"
PRO_PC = "pro-pc-no-gpu"
TOWER = "tower-desktop-gpu"


def _fact(value: float | None) -> dict[str, Any]:
    if value is None:
        return {"value": None, "source": "not_yet_declared", "read_from": "awaits"}
    return {"value": value, "source": "declared", "read_from": f"peak {value}"}


def _requirements(
    *, ram: float | None = 8.0, vram: float | None = 4.0, disk: float | None = 2.0
) -> dict[str, Any]:
    return {
        "gpu": {"ram_gb": _fact(ram), "vram_gb": _fact(vram), "disk_gb": _fact(disk)},
        "cpu_only": {"ram_gb": _fact(ram), "disk_gb": _fact(disk)},
    }


def _raw_entry(requirements: Any = None) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "repo": "fake/repo",
        "revision": "main",
        "file": "fake.gguf",
        "display_id": "Fake",
        "quant": "Q8_0",
        "sha256": "0" * 64,
        "architecture": {"kind": "dense", "expert_count": 0, "active_params_b": 0.6},
        "server_flags": {
            "n_gpu_layers": 99,
            "context_size": 4096,
            "flash_attention": "on",
            "jinja": True,
            "parallel_slots": 1,
            "load_mode": "auto",
            "sampler": {
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0,
                "presence_penalty": 0,
            },
        },
    }
    if requirements is not None:
        entry["requirements"] = requirements
    return entry


def _entry(**requirements: float | None) -> roster.RosterEntry:
    return roster.parse_entry(ENTRY_ID, _raw_entry(_requirements(**requirements)))


def _profile(machine_id: str = LAPTOP, mode: str = "gpu") -> profiles.ResolvedProfile:
    return profiles.ResolvedProfile(
        profile_id=profiles.profile_id_for(ENTRY_ID, machine_id, mode),
        entry_id=ENTRY_ID,
        machine_id=machine_id,
        compute_mode=mode,
        n_gpu_layers=99 if mode == "gpu" else 0,
        n_cpu_moe=None,
        threads=8,
    )


def _machine(machine_id: str = LAPTOP) -> machines.MachineEntry:
    return machines.tracked_registry().entries[machine_id]


def _observing(
    ram: float | None = 32.0, vram: float | None = 5.1, disk: float | None = 100.0
):
    return lambda *_args: preflight.Observation(
        ram_gb=ram, vram_gb=vram, disk_free_gb=disk
    )


def _enforce(
    entry: roster.RosterEntry,
    tmp_path: Path,
    *,
    profile: profiles.ResolvedProfile | None = None,
    **observed: float | None,
) -> None:
    profile = profile or _profile()
    preflight.enforce(
        entry,
        _machine(profile.machine_id),
        profile,
        models_dir=tmp_path,
        refusals_dir=tmp_path / "refusals",
        observe_machine=_observing(**observed),
    )


def _records(tmp_path: Path, machine_id: str = LAPTOP) -> list[dict[str, Any]]:
    path = preflight.refusal_path(tmp_path / "refusals", machine_id)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text("utf-8").splitlines()]


# --- each requirement refuses alone, naming itself and the mode -------------


@pytest.mark.parametrize(
    ("observed", "requirement"),
    [
        ({"ram": 4.0}, "ram_gb"),
        ({"vram": 2.0}, "vram_gb"),
        ({"disk": 1.0}, "disk_gb"),
    ],
)
def test_each_requirement_refuses_alone_naming_itself_and_the_mode(
    tmp_path: Path, observed: dict[str, float], requirement: str
) -> None:
    with pytest.raises(preflight.RequirementRefusal) as refusal:
        _enforce(_entry(), tmp_path, **observed)  # type: ignore[arg-type]

    message = str(refusal.value)
    assert f"requires {requirement} >=" in message
    assert "compute mode 'gpu'" in message
    assert f"reports {next(iter(observed.values()))} GB" in message
    (record,) = _records(tmp_path)
    assert record["requirement"] == requirement


def test_the_first_failing_requirement_in_order_is_the_refusal(tmp_path: Path) -> None:
    with pytest.raises(preflight.RequirementRefusal) as refusal:
        _enforce(_entry(), tmp_path, ram=1.0, vram=1.0, disk=0.5)

    assert refusal.value.record["requirement"] == "ram_gb"
    assert len(_records(tmp_path)) == 1


def test_a_cpu_only_run_is_never_checked_against_vram(tmp_path: Path) -> None:
    _enforce(_entry(), tmp_path, profile=_profile(PRO_PC, "cpu_only"), vram=None)

    assert _records(tmp_path, PRO_PC) == []


# --- the check tests the declaration, not the machine -----------------------


def test_a_raised_declaration_refuses_and_the_lowered_one_runs_on_one_machine(
    tmp_path: Path,
) -> None:
    observed = {"ram": 16.0, "vram": 5.1, "disk": 50.0}

    with pytest.raises(preflight.RequirementRefusal):
        _enforce(_entry(ram=17.74), tmp_path, **observed)
    _enforce(_entry(ram=15.23), tmp_path, **observed)

    assert len(_records(tmp_path)) == 1


def test_a_requirement_not_yet_declared_is_not_checked_and_says_so(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _enforce(_entry(vram=None), tmp_path, vram=None)

    assert "vram_gb not checked under gpu" in capsys.readouterr().err


def test_a_declared_minimum_nothing_observed_stops_without_a_record(
    tmp_path: Path,
) -> None:
    with pytest.raises(preflight.PreflightError, match="reported no value"):
        _enforce(_entry(), tmp_path, ram=None)

    assert _records(tmp_path) == []


def test_weights_already_on_disk_need_no_free_disk(tmp_path: Path) -> None:
    _enforce(_entry(disk=10**6), tmp_path, disk=None)

    assert _records(tmp_path) == []


def test_an_entry_declaring_no_requirements_cannot_run(tmp_path: Path) -> None:
    entry = roster.parse_entry(ENTRY_ID, _raw_entry())

    with pytest.raises(preflight.PreflightError, match="declares no requirements"):
        _enforce(entry, tmp_path)


# --- the refusal record ------------------------------------------------------


def test_a_refusal_writes_exactly_one_record_carrying_every_field(
    tmp_path: Path,
) -> None:
    with (
        patch.object(preflight.provenance, "release_version", return_value="v1.2.3"),
        patch.object(preflight.provenance, "commit_sha", return_value="abc123"),
        pytest.raises(preflight.RequirementRefusal),
    ):
        _enforce(_entry(ram=64.0), tmp_path, ram=34.0)

    (record,) = _records(tmp_path)
    assert record.keys() == row_contract.REFUSAL_FIELDS
    assert record == {
        **record,
        "record_kind": "refusal",
        "refusal_contract_version": row_contract.REFUSAL_CONTRACT_VERSION,
        "roster_entry_id": ENTRY_ID,
        "machine_id": LAPTOP,
        "compute_mode": "gpu",
        "profile_id": f"{ENTRY_ID}@{LAPTOP}/gpu",
        "requirement": "ram_gb",
        "declared": 64.0,
        "observed": 34.0,
        "unit": "GB",
        "release_version": "v1.2.3",
        "commit_sha": "abc123",
    }
    assert record["refused_at"]


def test_a_refused_gpu_run_names_the_cpu_only_profile_and_runs_nothing(
    tmp_path: Path,
) -> None:
    with pytest.raises(preflight.RequirementRefusal) as refusal:
        _enforce(_entry(), tmp_path, ram=1.0)

    message = str(refusal.value)
    assert (
        f"A cpu_only profile exists for this entry on this machine ({ENTRY_ID}@{LAPTOP}/cpu_only)"
        in message
    )
    assert "set COMPUTE_MODE=cpu_only" in message
    assert refusal.value.record["compute_mode"] == "gpu"


def test_a_refused_gpu_run_with_no_cpu_only_profile_names_none(tmp_path: Path) -> None:
    registry = profiles.ProfileRegistry(
        registry_version=1,
        defaults={(LAPTOP, "gpu"): {}},
        entries={},
    )
    with pytest.raises(preflight.RequirementRefusal) as refusal:
        preflight.enforce(
            _entry(),
            _machine(),
            _profile(),
            models_dir=tmp_path,
            refusals_dir=tmp_path / "refusals",
            observe_machine=_observing(ram=1.0),
            profile_registry=registry,
        )

    assert "cpu_only" not in str(refusal.value)


def test_a_refused_cpu_only_run_offers_no_other_mode(tmp_path: Path) -> None:
    with pytest.raises(preflight.RequirementRefusal) as refusal:
        _enforce(
            _entry(ram=17.74), tmp_path, profile=_profile(PRO_PC, "cpu_only"), ram=16.9
        )

    assert "profile exists" not in str(refusal.value)
    (record,) = _records(tmp_path, PRO_PC)
    assert record["profile_id"] == f"{ENTRY_ID}@{PRO_PC}/cpu_only"


def _valid_record() -> dict[str, Any]:
    return {field: "x" for field in row_contract.REFUSAL_FIELDS} | {
        "record_kind": "refusal"
    }


def test_the_refusal_contract_refuses_a_missing_field_a_row_and_another_kind(
    tmp_path: Path,
) -> None:
    incomplete = _valid_record()
    del incomplete["profile_id"]
    with pytest.raises(row_contract.RowContractError, match="profile_id"):
        append_refusal(tmp_path / "r.jsonl", incomplete)
    with pytest.raises(row_contract.RowContractError, match="record_kind"):
        row_contract.validate_refusal(_valid_record() | {"record_kind": "runtime"})
    with pytest.raises(row_contract.RowContractError, match="never a row"):
        row_contract.validate_refusal(_valid_record() | {"schema_version": "26"})
    assert not (tmp_path / "r.jsonl").exists()


def test_a_refusal_record_is_never_read_as_a_runtime_row(tmp_path: Path) -> None:
    path = tmp_path / "refusals.jsonl"
    append_refusal(path, _valid_record())

    with pytest.raises(row_contract.RowContractError):
        row_contract.validate_row("runtime", _valid_record())
    assert read_rows_from_floor(path, "1").rows == []


# --- what the machine reports ------------------------------------------------


def test_observe_reads_total_ram_free_disk_and_the_declared_allocatable_vram(
    tmp_path: Path,
) -> None:
    with (
        patch.object(
            preflight.psutil,
            "virtual_memory",
            return_value=SimpleNamespace(total=34 * 10**9),
        ),
        patch.object(
            preflight.shutil, "disk_usage", return_value=SimpleNamespace(free=10**11)
        ),
    ):
        observed = preflight.observe(_machine(), "gpu", tmp_path, _entry())

    assert observed == preflight.Observation(
        ram_gb=34.0, vram_gb=5.1, disk_free_gb=100.0
    )


def test_observe_skips_disk_when_the_weights_are_present(tmp_path: Path) -> None:
    (tmp_path / "fake.gguf").write_text("")

    observed = preflight.observe(_machine(), "cpu_only", tmp_path, _entry())

    assert observed.disk_free_gb is None
    assert observed.vram_gb is None


def test_observe_reads_vram_only_when_a_minimum_is_declared(tmp_path: Path) -> None:
    with patch.object(preflight, "_allocatable_vram_gb") as read_vram:
        observed = preflight.observe(_machine(), "gpu", tmp_path, _entry(vram=None))

    read_vram.assert_not_called()
    assert observed.vram_gb is None


def test_vram_falls_back_to_nvml_where_no_allocatable_value_is_declared() -> None:
    fake_pynvml = MagicMock()
    fake_pynvml.nvmlDeviceGetMemoryInfo.return_value = SimpleNamespace(total=8 * 10**9)
    with (
        patch.dict("sys.modules", {"pynvml": fake_pynvml}),
        patch.object(preflight, "nvml_device") as device,
    ):
        device.return_value.__enter__.return_value = "handle"
        assert preflight._allocatable_vram_gb(_machine(TOWER)) == 8.0


def test_vram_is_unobserved_when_nvml_fails() -> None:
    with patch.object(preflight, "nvml_device", side_effect=RuntimeError("no nvml")):
        assert preflight._allocatable_vram_gb(_machine(TOWER)) is None


def test_unreadable_ram_and_disk_are_unobserved(tmp_path: Path) -> None:
    with patch.object(preflight.psutil, "virtual_memory", side_effect=RuntimeError):
        assert preflight._total_ram_gb() is None
    assert preflight._free_disk_gb(tmp_path / "absent") is None


# --- the requirement loader --------------------------------------------------


def _load(tmp_path: Path, entry: dict[str, Any]) -> roster.RosterFile:
    path = tmp_path / "roster.json"
    path.write_text(json.dumps({"roster_version": 1, "entries": {ENTRY_ID: entry}}))
    return roster.load_roster(path)


def test_a_roster_entry_missing_its_requirements_is_refused(tmp_path: Path) -> None:
    with pytest.raises(
        roster.RosterError, match="missing required field.*requirements"
    ):
        _load(tmp_path, _raw_entry())


def _broken(path: str, value: Any) -> dict[str, Any]:
    requirements = copy.deepcopy(ROSTER_REQUIREMENTS)
    *parents, last = path.split(".")
    block = requirements
    for key in parents:
        block = block[key]
    if value is KeyError:
        del block[last]
    else:
        block[last] = value
    return requirements


@pytest.mark.parametrize(
    ("path", "value", "named"),
    [
        ("cpu_only", KeyError, "requirements.cpu_only"),
        ("gpu.disk_gb", KeyError, "requirements.gpu.disk_gb"),
        ("cpu_only.vram_gb", _fact(4.0), "unknown field"),
        ("gpu.ram_gb", {"value": 1.0}, "exactly value, source, read_from"),
        ("gpu.ram_gb.value", 0, "positive number"),
        ("gpu.ram_gb.value", True, "positive number"),
        ("gpu.ram_gb.read_from", " ", "non-empty string"),
        ("gpu.ram_gb.source", "guessed", "one of"),
        (
            "gpu.vram_gb",
            {"value": 4.0, "source": "not_yet_declared", "read_from": "awaits"},
            "never published",
        ),
        ("gpu", [], "must be an object"),
    ],
)
def test_a_malformed_requirement_is_refused_by_name(
    tmp_path: Path, path: str, value: Any, named: str
) -> None:
    with pytest.raises(roster.RosterError, match=named):
        _load(tmp_path, _raw_entry(_broken(path, value)))


def test_a_requirements_block_that_is_not_an_object_is_refused(tmp_path: Path) -> None:
    with pytest.raises(roster.RosterError, match="'requirements' must be an object"):
        _load(tmp_path, _raw_entry([]))


def test_every_shipped_entry_declares_both_modes_with_a_source() -> None:
    loaded = roster.load_roster(Path("aidd_docs/roster/models.json"))

    for entry in loaded.entries.values():
        assert entry.requirements is not None
        for mode, names in roster.REQUIREMENTS_BY_MODE.items():
            assert tuple(entry.requirements[mode]) == names
            for fact in entry.requirements[mode].values():
                assert fact["read_from"].strip()
            # RAM and disk are calibrated; VRAM awaits a per-process peak.
            assert entry.requirements[mode]["ram_gb"]["source"] == "declared"
            assert entry.requirements[mode]["disk_gb"]["source"] == "declared"


def test_the_shipped_gpu_ram_minimums_are_the_published_peaks() -> None:
    loaded = roster.load_roster(Path("aidd_docs/roster/models.json"))
    published = [
        json.loads(line)
        for line in Path("aidd_docs/results/runtime-reference.jsonl")
        .read_text("utf-8")
        .splitlines()
    ]
    flagship = "qwen3.6-35b-a3b-ud-iq4xs"
    peak = max(row["process_rss_bytes"] for row in published)

    declared = loaded.entries[flagship].requirements["gpu"]["ram_gb"]["value"]  # type: ignore[index]
    assert declared == pytest.approx(peak / 10**9, abs=0.01)
    for entry in loaded.entries.values():
        assert entry.bytes_on_disk is not None
        disk = entry.requirements["gpu"]["disk_gb"]["value"]  # type: ignore[index]
        assert disk == pytest.approx(entry.bytes_on_disk / 10**9, abs=0.01)
