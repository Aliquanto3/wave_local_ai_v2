"""Promotion of named runs into a machine's tracked results location."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import machine_results
from wave_local_ai_v2.machine_results import PromotionError

DECLARED = frozenset({"laptop-mobile-gpu", "tower-desktop-gpu"})
LAPTOP = "laptop-mobile-gpu"
TOWER = "tower-desktop-gpu"


def _row(
    run_id: str, machine_id: str, fiche: str | None, **extra: Any
) -> dict[str, Any]:
    return {"run_id": run_id, "machine_id": machine_id, "fiche_hash": fiche, **extra}


def _append(path: Path, *rows: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.writelines(json.dumps(row) + "\n" for row in rows)


class Live:
    def __init__(self, tmp_path: Path) -> None:
        self.runtime = tmp_path / "live" / "runtime.jsonl"
        self.quality = tmp_path / "live" / "quality.jsonl"
        self.fiches = tmp_path / "live" / "fiches"
        self.root = tmp_path / "machines"
        self.tracked = tmp_path / "tracked-fiches"

    def fiche(self, name: str, content: str = '{"cpu": "x"}') -> None:
        self.fiches.mkdir(parents=True, exist_ok=True)
        (self.fiches / f"{name}.json").write_text(content, encoding="utf-8")

    def promote(
        self, machine_id: str, *run_ids: str
    ) -> machine_results.PromotionResult:
        return machine_results.promote(
            machine_id,
            list(run_ids),
            live_stores={"runtime": self.runtime, "quality": self.quality},
            live_fiche_dir=self.fiches,
            root=self.root,
            tracked_fiche_dir=self.tracked,
            declared=DECLARED,
        )


@pytest.fixture
def live(tmp_path: Path) -> Live:
    store = Live(tmp_path)
    store.fiche("aaa")
    store.fiche("bbb")
    _append(store.runtime, _row("r1", LAPTOP, "aaa"), _row("r2", TOWER, "bbb"))
    _append(
        store.quality,
        _row("r1", LAPTOP, "aaa", item_id="i1", provider="local"),
        _row("c1", "not_applicable", "aaa", item_id="i1", provider="mistral"),
    )
    return store


def test_a_named_run_lands_in_its_machines_location_with_its_fiches(
    live: Live,
) -> None:
    outcome = live.promote(LAPTOP, "r1", "c1")

    location = machine_results.location(live.root, LAPTOP)
    assert len(location.runtime.read_text("utf-8").splitlines()) == 1
    assert len(location.quality.read_text("utf-8").splitlines()) == 2
    assert outcome.rows_added == {"runtime": 1, "quality": 2}
    assert (live.tracked / "aaa.json").read_bytes() == (
        live.fiches / "aaa.json"
    ).read_bytes()
    assert not (live.tracked / "bbb.json").exists()


def test_the_promoted_lines_are_the_live_lines_byte_for_byte(live: Live) -> None:
    live.promote(LAPTOP, "r1")

    location = machine_results.location(live.root, LAPTOP)
    live_line = live.runtime.read_text("utf-8").splitlines()[0]
    assert location.runtime.read_text("utf-8") == live_line + "\n"


def test_a_row_of_another_machine_is_refused_naming_it(live: Live) -> None:
    with pytest.raises(PromotionError, match=r"'r2'.*'tower-desktop-gpu'.*not"):
        live.promote(LAPTOP, "r1", "r2")
    assert not live.root.exists()
    assert not live.tracked.exists()


def test_a_row_with_no_machine_id_is_refused(live: Live) -> None:
    _append(live.runtime, {"run_id": "old", "fiche_hash": "aaa"})
    with pytest.raises(PromotionError, match="machine_id None"):
        live.promote(LAPTOP, "old")


def test_an_unknown_run_id_is_refused_naming_it(live: Live) -> None:
    with pytest.raises(PromotionError, match="'nope'"):
        live.promote(LAPTOP, "r1", "nope")
    assert not live.root.exists()


def test_an_undeclared_machine_is_refused(live: Live) -> None:
    with pytest.raises(PromotionError, match="not a declared machine"):
        live.promote("garage-box", "r1")


def test_promoting_twice_is_idempotent(live: Live) -> None:
    live.promote(LAPTOP, "r1")
    location = machine_results.location(live.root, LAPTOP)
    before = location.runtime.read_bytes(), location.quality.read_bytes()

    outcome = live.promote(LAPTOP, "r1")

    assert (location.runtime.read_bytes(), location.quality.read_bytes()) == before
    assert outcome.rows_added == {"runtime": 0, "quality": 0}
    assert outcome.rows_already_present == 2
    assert outcome.fiches_already_present == ["aaa"]


def test_a_fiche_missing_from_the_live_registry_is_refused(live: Live) -> None:
    _append(live.runtime, _row("r3", LAPTOP, "zzz"))
    with pytest.raises(PromotionError, match="'zzz'.*not in the live registry"):
        live.promote(LAPTOP, "r3")


def test_a_differing_tracked_fiche_is_refused_never_overwritten(live: Live) -> None:
    live.tracked.mkdir(parents=True)
    (live.tracked / "aaa.json").write_text("{}", encoding="utf-8")
    with pytest.raises(PromotionError, match="never overwritten"):
        live.promote(LAPTOP, "r1")
    assert (live.tracked / "aaa.json").read_text("utf-8") == "{}"
    assert not live.root.exists()


def test_the_cli_promotes_from_the_configured_stores(
    live: Live, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        machine_results.machines, "declared_machine_ids", lambda: DECLARED
    )
    monkeypatch.setenv("RUNTIME_RESULTS_PATH", str(live.runtime))
    monkeypatch.setenv("QUALITY_RESULTS_PATH", str(live.quality))
    monkeypatch.setenv("FICHE_REGISTRY_DIR", str(live.fiches))
    monkeypatch.setenv("MACHINE_RESULTS_ROOT", str(live.root))
    monkeypatch.setenv("TRACKED_FICHE_REGISTRY_DIR", str(live.tracked))
    monkeypatch.setenv("MACHINE_ID", LAPTOP)

    machine_results.main(["--run-id", "r1"])

    assert "1 runtime row(s), 1 quality row(s) added" in capsys.readouterr().out
    with pytest.raises(SystemExit) as exited:
        machine_results.main(["--run-id", "nope"])
    assert exited.value.code == 1
    assert "promotion refused" in capsys.readouterr().err


def test_the_cli_refuses_without_a_machine(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(machine_results, "load_dotenv", lambda: None)
    monkeypatch.delenv("MACHINE_ID", raising=False)
    with pytest.raises(SystemExit) as exited:
        machine_results.main(["--run-id", "r1"])
    assert exited.value.code == 1
    assert "no machine named" in capsys.readouterr().err
