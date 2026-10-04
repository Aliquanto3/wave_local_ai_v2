"""The merge that derives the published bundle from every machine's location."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from wave_local_ai_v2 import bundle_merge, machine_results, profiles, settings
from wave_local_ai_v2.bundle_merge import BundlePaths, MergeRefusal

DECLARED = frozenset({"laptop-mobile-gpu", "tower-desktop-gpu", "pro-pc-no-gpu"})
LAPTOP = "laptop-mobile-gpu"
TOWER = "tower-desktop-gpu"


def _append(path: Path, *records: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.writelines(json.dumps(record) + "\n" for record in records)


def _refusal(machine_id: str) -> dict[str, Any]:
    return {
        "record_kind": "refusal",
        "roster_entry_id": "qwen3-0.6b-q8",
        "machine_id": machine_id,
        "profile_id": f"qwen3-0.6b-q8@{machine_id}/gpu",
        "refused_at": "2026-10-02T00:00:00+00:00",
    }


def _two_machines(root: Path) -> None:
    laptop = machine_results.location(root, LAPTOP)
    tower = machine_results.location(root, TOWER)
    _append(laptop.runtime, {"run_id": "l1", "machine_id": LAPTOP, "fiche_hash": "a"})
    _append(
        laptop.quality,
        {"run_id": "l2", "machine_id": LAPTOP, "fiche_hash": "a", "item_id": "i1"},
        {
            "run_id": "c1",
            "machine_id": "not_applicable",
            "fiche_hash": "a",
            "provider": "mistral",
            "item_id": "i1",
        },
    )
    _append(laptop.refusals, _refusal(LAPTOP))
    _append(tower.runtime, {"run_id": "t1", "machine_id": TOWER, "fiche_hash": "b"})


def _paths(directory: Path) -> BundlePaths:
    return bundle_merge.bundle_paths_from_env(directory)


def test_two_machines_merge_into_one_deterministic_bundle(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _two_machines(root)

    first = bundle_merge.collect(root, DECLARED)
    bundle_merge.write(first, _paths(tmp_path / "a"))
    bundle_merge.write(bundle_merge.collect(root, DECLARED), _paths(tmp_path / "b"))

    for name in ("runtime", "quality", "refusals"):
        file = f"{name}-reference.jsonl"
        assert (tmp_path / "a" / file).read_bytes() == (
            tmp_path / "b" / file
        ).read_bytes()
    runtime = (tmp_path / "a" / "runtime-reference.jsonl").read_text("utf-8")
    assert [json.loads(line)["run_id"] for line in runtime.splitlines()] == ["l1", "t1"]
    assert bundle_merge.check(first, _paths(tmp_path / "a")) == []


def test_refusal_records_go_only_into_the_refusals_file(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _two_machines(root)

    bundle = bundle_merge.collect(root, DECLARED)

    assert len(bundle.lines["refusals"]) == 1
    for kind in ("runtime", "quality"):
        assert all('"record_kind"' not in line for line in bundle.lines[kind])


def test_a_collision_is_refused_naming_both_rows_ids_and_hash(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _two_machines(root)
    _append(
        machine_results.location(root, TOWER).runtime,
        {"run_id": "t2", "machine_id": TOWER, "fiche_hash": "a"},
    )

    with pytest.raises(MergeRefusal) as refused:
        bundle_merge.collect(root, DECLARED)

    message = str(refused.value)
    for expected in ("'a'", "'l1'", "'t2'", repr(LAPTOP), repr(TOWER), "not choose"):
        assert expected in message


def test_a_cloud_row_citing_its_machines_fiche_is_no_collision(
    tmp_path: Path,
) -> None:
    root = tmp_path / "machines"
    _two_machines(root)
    assert len(bundle_merge.collect(root, DECLARED).lines["quality"]) == 2


def test_an_undeclared_machine_id_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _append(
        machine_results.location(root, LAPTOP).runtime,
        {"run_id": "x", "machine_id": "garage-box", "fiche_hash": "a"},
    )
    with pytest.raises(MergeRefusal, match="'garage-box', which is not a declared"):
        bundle_merge.collect(root, DECLARED)


def test_a_location_of_an_undeclared_machine_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _append(
        machine_results.location(root, "garage-box").runtime,
        {"run_id": "x", "machine_id": "garage-box"},
    )
    with pytest.raises(MergeRefusal, match="'garage-box'.*no declared machine"):
        bundle_merge.collect(root, DECLARED)


def test_a_row_filed_in_another_machines_location_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _append(
        machine_results.location(root, LAPTOP).runtime,
        {"run_id": "x", "machine_id": TOWER},
    )
    with pytest.raises(MergeRefusal, match="filed in 'laptop-mobile-gpu'"):
        bundle_merge.collect(root, DECLARED)


def test_a_misfiled_refusal_record_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _append(machine_results.location(root, LAPTOP).refusals, _refusal(TOWER))
    with pytest.raises(MergeRefusal, match="refusal record"):
        bundle_merge.collect(root, DECLARED)


def test_one_run_in_two_locations_is_refused(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    cloud = {"run_id": "c1", "machine_id": "not_applicable", "provider": "mistral"}
    _append(machine_results.location(root, LAPTOP).quality, cloud)
    _append(machine_results.location(root, TOWER).quality, cloud)
    with pytest.raises(MergeRefusal, match="'c1' is in both"):
        bundle_merge.collect(root, DECLARED)


def test_a_hand_edited_bundle_fails_the_check(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _two_machines(root)
    bundle = bundle_merge.collect(root, DECLARED)
    paths = _paths(tmp_path / "bundle")
    bundle_merge.write(bundle, paths)

    paths.runtime.write_text(
        paths.runtime.read_text("utf-8").replace('"l1"', '"l9"'), encoding="utf-8"
    )
    paths.refusals.unlink()

    problems = bundle_merge.check(bundle, paths)
    assert any("runtime-reference.jsonl differs" in p for p in problems)
    assert any("refusals-reference.jsonl is missing" in p for p in problems)


def test_crlf_line_endings_do_not_fail_the_check(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _two_machines(root)
    bundle = bundle_merge.collect(root, DECLARED)
    paths = _paths(tmp_path / "bundle")
    bundle_merge.write(bundle, paths)
    paths.runtime.write_bytes(paths.runtime.read_bytes().replace(b"\n", b"\r\n"))

    assert bundle_merge.check(bundle, paths) == []


def test_unresolved_refusals_names_entry_machine_and_profile() -> None:
    registry = profiles.tracked_registry()
    good = _refusal(LAPTOP)
    good["profile_id"] = profiles.declared_profiles(registry, "qwen3-0.6b-q8")[0]
    bad = dict(good, roster_entry_id="ghost", machine_id="garage-box")

    problems = bundle_merge.unresolved_refusals(
        [good, bad],
        roster_entry_ids=["qwen3-0.6b-q8"],
        profile_registry=registry,
        declared=DECLARED,
    )

    assert len(problems) == 3
    assert "roster entry" in problems[0]
    assert "'garage-box'" in problems[1]
    assert "profile_id" in problems[2]


def test_the_cli_writes_then_checks_then_refuses(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = tmp_path / "machines"
    _two_machines(root)
    monkeypatch.setenv("MACHINE_RESULTS_ROOT", str(root))
    bundle_dir = str(tmp_path / "bundle")

    bundle_merge.main(["--bundle-dir", bundle_dir])
    assert "bundle written" in capsys.readouterr().out
    bundle_merge.main(["--check", "--bundle-dir", bundle_dir])
    assert "equals the merge" in capsys.readouterr().out

    (tmp_path / "bundle" / "quality-reference.jsonl").write_text("", encoding="utf-8")
    with pytest.raises(SystemExit) as exited:
        bundle_merge.main(["--check", "--bundle-dir", bundle_dir])
    assert exited.value.code == 1

    _append(
        machine_results.location(root, TOWER).runtime,
        {"run_id": "t2", "machine_id": TOWER, "fiche_hash": "a"},
    )
    with pytest.raises(SystemExit) as exited:
        bundle_merge.main(["--bundle-dir", bundle_dir])
    assert exited.value.code == 1
    assert "fiche hash collision" in capsys.readouterr().err


def test_paths_come_from_the_environment_without_a_bundle_dir(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setenv("REFUSALS_REFERENCE_PATH", str(tmp_path / "r.jsonl"))
    paths = bundle_merge.bundle_paths_from_env(None)
    assert paths.refusals == tmp_path / "r.jsonl"
    assert paths.runtime == Path(settings.DEFAULT_RUNTIME_REFERENCE_PATH)


def test_a_row_without_a_run_id_is_refused_naming_it(tmp_path: Path) -> None:
    root = tmp_path / "machines"
    _append(
        machine_results.location(root, LAPTOP).runtime,
        {"machine_id": LAPTOP, "fiche_hash": "a"},
    )
    with pytest.raises(MergeRefusal, match="runtime row in .* carries no run_id"):
        bundle_merge.collect(root, DECLARED)
