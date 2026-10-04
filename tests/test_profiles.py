"""The run profile registry: loader refusals, the resolution order, and the
shipped registry's declared set."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import machines, profiles, roster
from wave_local_ai_v2.profiles import ProfileError

FLAGSHIP = "qwen3.6-35b-a3b-ud-iq4xs"
DENSE = "qwen3-0.6b-q8"
LAPTOP = "laptop-mobile-gpu"
TOWER = "tower-desktop-gpu"
PRO_PC = "pro-pc-no-gpu"


def _fact(value: Any, source: str = "declared") -> dict[str, Any]:
    return {"value": value, "source": source, "read_from": "test"}


def _pending() -> dict[str, Any]:
    return {"value": None, "source": "not_yet_declared", "read_from": "awaits a read"}


REGISTRY: dict[str, Any] = {
    "registry_version": 1,
    "defaults": {
        LAPTOP: {
            "gpu": {"threads": _fact(8)},
            "cpu_only": {"n_gpu_layers": _fact(0), "threads": _fact(8)},
        },
        TOWER: {
            "gpu": {"threads": _fact(12)},
            "cpu_only": {"n_gpu_layers": _fact(0), "threads": _pending()},
        },
    },
    "entries": {
        FLAGSHIP: {
            LAPTOP: {"gpu": {"n_cpu_moe": _fact(37)}},
            TOWER: {"gpu": {"n_cpu_moe": _fact(20)}},
        }
    },
}


def _registry(
    tmp_path: Path, raw: dict[str, Any] | None = None
) -> profiles.ProfileRegistry:
    path = tmp_path / "profiles.json"
    path.write_text(json.dumps(REGISTRY if raw is None else raw), encoding="utf-8")
    return profiles.load_registry(path)


def _entry(entry_id: str = FLAGSHIP) -> roster.RosterEntry:
    loaded = roster.load_roster(Path("aidd_docs/roster/models.json"))
    return roster.resolve_entry(loaded, entry_id)


def test_entry_default_then_profile_then_operator(tmp_path: Path) -> None:
    registry = _registry(tmp_path)
    entry = _entry()

    as_declared = profiles.resolve(registry, entry, LAPTOP, "gpu")
    assert as_declared.profile_id == f"{FLAGSHIP}@{LAPTOP}/gpu"
    # -ngl: the roster's model-intrinsic default, no profile override.
    assert as_declared.n_gpu_layers == entry.server_flags["n_gpu_layers"]
    # n_cpu_moe: the entry's override of the (machine, mode) default.
    assert as_declared.n_cpu_moe == 37
    assert as_declared.threads == 8
    assert as_declared.overrides == {}

    overridden = profiles.resolve(
        registry, entry, LAPTOP, "gpu", operator_n_cpu_moe=30, operator_threads=6
    )
    assert overridden.profile_id == as_declared.profile_id
    assert (overridden.n_cpu_moe, overridden.threads) == (30, 6)
    assert overridden.overrides == {
        "n_cpu_moe": {"profile": 37, "operator": 30},
        "threads": {"profile": 8, "operator": 6},
    }


def test_cpu_only_profile_overrides_the_roster_ngl(tmp_path: Path) -> None:
    resolved = profiles.resolve(_registry(tmp_path), _entry(), LAPTOP, "cpu_only")
    assert resolved.n_gpu_layers == 0
    assert resolved.n_cpu_moe is None
    assert resolved.cpu_only


def test_an_entry_with_no_override_uses_the_machine_mode_default(
    tmp_path: Path,
) -> None:
    resolved = profiles.resolve(_registry(tmp_path), _entry(DENSE), TOWER, "gpu")
    assert resolved.profile_id == f"{DENSE}@{TOWER}/gpu"
    assert resolved.n_cpu_moe is None
    assert resolved.threads == 12


def test_a_missing_triple_is_refused_naming_it_and_the_declared_profiles(
    tmp_path: Path,
) -> None:
    with pytest.raises(ProfileError) as caught:
        profiles.resolve(_registry(tmp_path), _entry(), PRO_PC, "cpu_only")
    message = str(caught.value)
    assert (
        f"roster entry {FLAGSHIP!r}, machine {PRO_PC!r}, compute mode 'cpu_only'"
        in message
    )
    assert f"{FLAGSHIP}@{LAPTOP}/gpu" in message
    assert f"{FLAGSHIP}@{TOWER}/cpu_only" in message
    # A RosterError: every writer's existing handler refuses it.
    assert isinstance(caught.value, roster.RosterError)


def test_an_undeclared_value_refuses_unless_the_operator_overrides_it(
    tmp_path: Path,
) -> None:
    registry = _registry(tmp_path)
    with pytest.raises(
        ProfileError, match="no declared value for: threads.*SERVER_THREADS"
    ):
        profiles.resolve(registry, _entry(), TOWER, "cpu_only")

    resolved = profiles.resolve(
        registry, _entry(), TOWER, "cpu_only", operator_threads=16
    )
    assert resolved.threads == 16
    assert resolved.overrides == {
        "threads": {"profile": "not_yet_declared", "operator": 16}
    }


def test_an_undeclared_value_with_no_operator_variable_refuses(tmp_path: Path) -> None:
    raw = copy.deepcopy(REGISTRY)
    raw["defaults"][LAPTOP]["gpu"]["n_gpu_layers"] = _pending()
    with pytest.raises(
        ProfileError, match="no declared value for: n_gpu_layers"
    ) as caught:
        profiles.resolve(_registry(tmp_path, raw), _entry(), LAPTOP, "gpu")
    assert "SERVER_" not in str(caught.value)


def _broken(mutate: Any) -> dict[str, Any]:
    raw = copy.deepcopy(REGISTRY)
    mutate(raw)
    return raw


@pytest.mark.parametrize(
    ("mutate", "match"),
    [
        (lambda r: r.pop("entries"), "must be an object with"),
        (lambda r: r.update(registry_version="1"), "registry_version"),
        (lambda r: r.update(defaults={}), "declares nothing"),
        (lambda r: r.update(defaults=[]), "'defaults' must be an object"),
        (lambda r: r.update(entries=[]), "'entries' must be an object"),
        (lambda r: r["defaults"].update({LAPTOP: {}}), "non-empty object"),
        (lambda r: r["defaults"][LAPTOP].update(npu={}), "not a compute mode"),
        (lambda r: r["defaults"][LAPTOP].update(gpu=[]), "must be an object"),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].update(flash=_fact(1)),
            "not a profile setting",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].update(threads=8),
            "must be an object of",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].update(
                threads={"value": 8, "source": "declared", "read_from": " "}
            ),
            "read_from",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].update(threads=_fact(8, "guessed")),
            "'source'",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].update(
                threads=_fact(8, "not_yet_declared")
            ),
            "never published",
        ),
        (lambda r: r["defaults"][LAPTOP]["gpu"].update(threads=_fact(0)), "at least 1"),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].update(n_cpu_moe=_fact(True)),
            "at least 0",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["gpu"].pop("threads"),
            "declares no 'threads'",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["cpu_only"].update(n_cpu_moe=_fact(0)),
            "under 'cpu_only'",
        ),
        (
            lambda r: r["defaults"][LAPTOP]["cpu_only"].update(n_gpu_layers=_fact(99)),
            "every layer",
        ),
        (
            lambda r: r["entries"][FLAGSHIP].update(
                {PRO_PC: {"cpu_only": {"threads": _fact(4)}}}
            ),
            "no declared default profile",
        ),
        (
            lambda r: r["entries"][FLAGSHIP][TOWER].update(
                cpu_only={"n_cpu_moe": _fact(4)}
            ),
            "under 'cpu_only'",
        ),
    ],
)
def test_the_loader_refuses_a_malformed_registry(
    tmp_path: Path, mutate: Any, match: str
) -> None:
    with pytest.raises(ProfileError, match=match):
        _registry(tmp_path, _broken(mutate))


def test_the_loader_refuses_an_unreadable_file(tmp_path: Path) -> None:
    with pytest.raises(ProfileError, match="not readable"):
        profiles.load_registry(tmp_path / "absent.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{", encoding="utf-8")
    with pytest.raises(ProfileError, match="not valid JSON"):
        profiles.load_registry(bad)


def test_the_shipped_registry_declares_the_three_machines_profile_set() -> None:
    registry = profiles.tracked_registry()
    assert set(registry.defaults) == {
        (LAPTOP, "gpu"),
        (LAPTOP, "cpu_only"),
        (TOWER, "gpu"),
        (TOWER, "cpu_only"),
        (PRO_PC, "cpu_only"),
    }
    declared_machines = machines.declared_machine_ids()
    assert {machine for machine, _ in registry.defaults} == declared_machines
    shipped = roster.load_roster(Path("aidd_docs/roster/models.json"))
    # Every per-entry override names a roster entry.
    assert set(registry.entries) <= set(shipped.entries)
    # Only the flagship needs a per-entry value: no "per-entry everywhere".
    assert set(registry.entries) == {FLAGSHIP}


def test_the_shipped_laptop_profiles_resolve_and_the_others_await_a_read() -> None:
    flagship = _entry()
    gpu = profiles.resolve_for_run(
        flagship, LAPTOP, "gpu", operator_n_cpu_moe=None, operator_threads=None
    )
    assert (gpu.n_gpu_layers, gpu.n_cpu_moe, gpu.threads) == (99, 37, 8)
    for entry_id in (DENSE, FLAGSHIP):
        cpu = profiles.resolve_for_run(
            _entry(entry_id),
            LAPTOP,
            "cpu_only",
            operator_n_cpu_moe=None,
            operator_threads=None,
        )
        assert (cpu.n_gpu_layers, cpu.n_cpu_moe, cpu.threads) == (0, None, 8)
    for machine, mode in ((TOWER, "gpu"), (TOWER, "cpu_only"), (PRO_PC, "cpu_only")):
        with pytest.raises(ProfileError, match="awaits"):
            profiles.resolve_for_run(
                _entry(DENSE),
                machine,
                mode,
                operator_n_cpu_moe=None,
                operator_threads=None,
            )
    with pytest.raises(ProfileError, match="n_cpu_moe"):
        profiles.resolve_for_run(
            flagship, TOWER, "gpu", operator_n_cpu_moe=None, operator_threads=12
        )
