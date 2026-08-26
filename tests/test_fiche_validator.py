import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from wave_local_ai_v2.fiche_registry import verify_fiche, write_fiche
from wave_local_ai_v2.fiche_validator import main, validate_bundle
from wave_local_ai_v2.row_contract import FICHE_HASH_SCHEMA_VERSION
from wave_local_ai_v2.settings import Settings

FICHE = {
    "cpu": "x",
    "ram_gb": 32.0,
    "gpu_name": "y",
    "gpu_driver_version": "1.2.3",
    "os": "z",
    "cuda_ceiling": "12.4",
    "llama_cpp_build": "b10537",
    "roster_entry_id": "fake-entry",
    "model_sha256": "0" * 64,
    "quant": "UD-IQ4_XS",
    "flags": ["-ngl", "99"],
}


def _write_rows(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


def _git_tracked_registry(tmp_path: Path) -> tuple[Path, str]:
    """A registry dir that is itself a git repo, one fiche committed."""
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    fiche_hash = write_fiche(FICHE, registry_dir)

    _git("init", cwd=registry_dir)
    _git("config", "user.email", "test@example.com", cwd=registry_dir)
    _git("config", "user.name", "Test", cwd=registry_dir)
    _git("add", "-A", cwd=registry_dir)
    _git("commit", "-m", "commit fiche", cwd=registry_dir)
    return registry_dir, fiche_hash


def test_verify_fiche_returns_missing_for_an_unwritten_hash(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"

    result = verify_fiche("deadbeef" * 8, registry_dir)

    assert result["status"] == "missing"
    assert result["changed_fields"] == []


def test_verify_fiche_returns_ok_for_an_untouched_written_fiche(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = write_fiche(FICHE, registry_dir)

    result = verify_fiche(fiche_hash, registry_dir)

    assert result["status"] == "ok"
    assert result["changed_fields"] == []


def test_verify_fiche_names_the_changed_field_inside_a_committed_git_repo(
    tmp_path,
) -> None:
    registry_dir, fiche_hash = _git_tracked_registry(tmp_path)
    fiche_path = registry_dir / f"{fiche_hash}.json"
    edited = {**FICHE, "gpu_name": "edited-in-place"}
    fiche_path.write_text(json.dumps(edited, sort_keys=True), encoding="utf-8")

    result = verify_fiche(fiche_hash, registry_dir)

    assert result["status"] == "edited"
    assert result["changed_fields"] == ["gpu_name"]


def test_verify_fiche_degrades_outside_git(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = write_fiche(FICHE, registry_dir)
    fiche_path = registry_dir / f"{fiche_hash}.json"
    edited = {**FICHE, "gpu_name": "edited-in-place"}
    fiche_path.write_text(json.dumps(edited, sort_keys=True), encoding="utf-8")

    result = verify_fiche(fiche_hash, registry_dir)

    assert result["status"] == "edited"
    assert len(result["changed_fields"]) == 1
    assert result["changed_fields"][0].startswith("unavailable:")


def test_validator_over_a_clean_bundle_reports_zero_issues(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = write_fiche(FICHE, registry_dir)
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": fiche_hash,
            }
            for _ in range(3)
        ],
    )

    report = validate_bundle([results_path], registry_dir)

    assert report["rows_checked"] == 3
    assert report["edited"] == []
    assert report["missing"] == []
    assert report["legacy"] == []


def test_validator_names_the_citing_row_when_a_fiche_is_edited(tmp_path) -> None:
    registry_dir, fiche_hash = _git_tracked_registry(tmp_path)
    fiche_path = registry_dir / f"{fiche_hash}.json"
    edited = {**FICHE, "gpu_name": "edited-in-place"}
    fiche_path.write_text(json.dumps(edited, sort_keys=True), encoding="utf-8")
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": fiche_hash,
            }
        ],
    )

    report = validate_bundle([results_path], registry_dir)

    assert report["missing"] == []
    assert len(report["edited"]) == 1
    issue = report["edited"][0]
    assert issue["run_id"] == "run-1"
    assert issue["position"] == 0
    assert issue["changed_fields"] == ["gpu_name"]


def test_validator_reports_missing_class_for_an_absent_hash(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": "deadbeef" * 8,
            }
        ],
    )

    report = validate_bundle([results_path], registry_dir)

    assert report["edited"] == []
    assert len(report["missing"]) == 1
    assert report["missing"][0]["run_id"] == "run-1"


def test_validator_treats_a_current_schema_row_with_no_fiche_hash_key_as_missing(
    tmp_path,
) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [{"run_id": "run-1", "schema_version": FICHE_HASH_SCHEMA_VERSION}],
    )

    report = validate_bundle([results_path], registry_dir)

    assert len(report["missing"]) == 1
    assert report["edited"] == []
    assert report["legacy"] == []


def test_validator_reports_a_pre_contract_row_as_legacy_not_missing(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {"run_id": "run-old", "schema_version": "2"},
            {"run_id": "run-older"},  # no schema_version key at all
        ],
    )

    report = validate_bundle([results_path], registry_dir)

    assert report["missing"] == []
    assert report["edited"] == []
    assert len(report["legacy"]) == 2
    assert {issue["run_id"] for issue in report["legacy"]} == {"run-old", "run-older"}


def test_main_exits_zero_over_a_bundle_of_only_legacy_rows(
    tmp_path, monkeypatch, capsys
) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(results_path, [{"run_id": "run-old", "schema_version": "2"}])
    fake_settings = Settings(
        slm_models_dir=tmp_path,
        llama_server_path=tmp_path / "llama-server.exe",
        results_path=results_path,
        quality_results_path=tmp_path / "unused-quality.jsonl",
        fiche_registry_dir=registry_dir,
    )
    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-validate"])

    with (
        patch(
            "wave_local_ai_v2.fiche_validator.load_settings",
            return_value=fake_settings,
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    out = capsys.readouterr().out
    assert exit_info.value.code == 0
    assert "legacy (pre-fiche-hash, not fatal): 1" in out


def test_validator_over_an_empty_results_file_reports_zero_rows(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"

    report = validate_bundle([tmp_path / "absent.jsonl"], registry_dir)

    assert report["rows_checked"] == 0
    assert report["edited"] == []
    assert report["missing"] == []


def test_main_exits_zero_over_a_clean_bundle(tmp_path, monkeypatch, capsys) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = write_fiche(FICHE, registry_dir)
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": fiche_hash,
            }
        ],
    )
    fake_settings = Settings(
        slm_models_dir=tmp_path,
        llama_server_path=tmp_path / "llama-server.exe",
        results_path=results_path,
        quality_results_path=tmp_path / "quality.jsonl",
        fiche_registry_dir=registry_dir,
    )
    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-validate"])

    with (
        patch(
            "wave_local_ai_v2.fiche_validator.load_settings",
            return_value=fake_settings,
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    assert exit_info.value.code == 0
    assert "checked 1 row(s)" in capsys.readouterr().out


def test_main_exits_one_and_names_the_class_when_a_hash_is_missing(
    tmp_path, monkeypatch, capsys
) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": "deadbeef" * 8,
            }
        ],
    )
    fake_settings = Settings(
        slm_models_dir=tmp_path,
        llama_server_path=tmp_path / "llama-server.exe",
        results_path=results_path,
        quality_results_path=tmp_path / "quality.jsonl",
        fiche_registry_dir=registry_dir,
    )
    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-validate"])

    with (
        patch(
            "wave_local_ai_v2.fiche_validator.load_settings",
            return_value=fake_settings,
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    out = capsys.readouterr().out
    assert exit_info.value.code == 1
    assert "missing (1):" in out


def test_main_checks_an_explicit_path_without_a_local_model_install(
    tmp_path, monkeypatch
) -> None:
    registry_dir = tmp_path / "fiches"
    fiche_hash = write_fiche(FICHE, registry_dir)
    results_path = tmp_path / "runtime.jsonl"
    _write_rows(
        results_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": fiche_hash,
            }
        ],
    )
    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-validate", str(results_path)])

    with (
        # Story 15: this form reads published artifacts only, so it must not
        # need SLM_MODELS_DIR / LLAMA_SERVER_PATH to exist on this machine.
        patch(
            "wave_local_ai_v2.fiche_validator.load_settings",
            side_effect=AssertionError("load_settings must not be called"),
        ),
        patch(
            "wave_local_ai_v2.fiche_validator.fiche_registry_dir_from_env",
            return_value=registry_dir,
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    assert exit_info.value.code == 0


def test_main_refuses_an_explicit_path_that_does_not_exist(
    tmp_path, monkeypatch, capsys
) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    absent = tmp_path / "typo.jsonl"
    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-validate", str(absent)])

    with (
        patch(
            "wave_local_ai_v2.fiche_validator.fiche_registry_dir_from_env",
            return_value=registry_dir,
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    # A named-but-absent file is a typo, not a clean bill of health.
    assert exit_info.value.code == 1
    assert "results file not found" in capsys.readouterr().err


def test_every_issue_names_the_results_file_it_came_from(tmp_path) -> None:
    registry_dir = tmp_path / "fiches"
    registry_dir.mkdir()
    runtime_path = tmp_path / "runtime.jsonl"
    quality_path = tmp_path / "quality.jsonl"
    _write_rows(
        runtime_path,
        [
            {
                "run_id": "run-1",
                "schema_version": FICHE_HASH_SCHEMA_VERSION,
                "fiche_hash": "deadbeef" * 8,
            }
        ],
    )
    _write_rows(quality_path, [{"run_id": "run-old", "schema_version": "2"}])

    report = validate_bundle([runtime_path, quality_path], registry_dir)

    # Positions restart per file, so the path is what tells the two apart.
    assert report["missing"][0]["results_path"] == str(runtime_path)
    assert report["missing"][0]["position"] == 0
    assert report["legacy"][0]["results_path"] == str(quality_path)
    assert report["legacy"][0]["position"] == 0


def test_main_wraps_settings_error_as_one_line(monkeypatch, capsys) -> None:
    from wave_local_ai_v2.settings import SettingsError

    monkeypatch.setattr("sys.argv", ["wave-local-ai-v2-validate"])

    with (
        patch(
            "wave_local_ai_v2.fiche_validator.load_settings",
            side_effect=SettingsError("SLM_MODELS_DIR is not set"),
        ),
        pytest.raises(SystemExit) as exit_info,
    ):
        main()

    assert exit_info.value.code == 1
    assert "error: SLM_MODELS_DIR is not set" in capsys.readouterr().err
