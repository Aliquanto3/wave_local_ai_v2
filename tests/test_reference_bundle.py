"""The reference bundle is the unit an auditor is handed: runtime-reference.jsonl
+ quality-reference.jsonl + fiches/ + roster/models.json + suite-definitions/.
Every row's pointers must resolve inside that bundle -- this is the current-
schema bundle only, named explicitly, never a glob over every `*-reference*.jsonl`
(which would silently pull in the superseded `*.schema-1.jsonl` files).
"""

from __future__ import annotations

import json
from pathlib import Path

from wave_local_ai_v2 import fiche_registry, results, roster, row_contract, settings

RESULTS_DIR = Path("aidd_docs/results")
RUNTIME_REFERENCE_PATH = RESULTS_DIR / "runtime-reference.jsonl"
QUALITY_REFERENCE_PATH = RESULTS_DIR / "quality-reference.jsonl"
SUITE_DEFINITIONS_DIR = RESULTS_DIR / "suite-definitions"
SUPERSEDED_PATHS = (
    RESULTS_DIR / "runtime-reference.schema-1.jsonl",
    RESULTS_DIR / "quality-reference.schema-1.jsonl",
)


def _all_rows() -> list[dict[str, object]]:
    return results.read_rows(RUNTIME_REFERENCE_PATH) + results.read_rows(
        QUALITY_REFERENCE_PATH
    )


def test_every_row_resolves_its_fiche_hash() -> None:
    fiche_registry_dir = settings.DEFAULT_FICHE_REGISTRY_DIR
    for row in _all_rows():
        fiche_hash = row["fiche_hash"]
        assert isinstance(fiche_hash, str)
        assert (
            fiche_registry.read_fiche(fiche_hash, Path(fiche_registry_dir)) is not None
        ), f"row {row['run_id']!r} cites unresolved fiche_hash {fiche_hash!r}"


def test_every_row_resolves_its_roster_entry_id() -> None:
    loaded_roster = roster.load_roster(Path(settings.DEFAULT_ROSTER_PATH))
    for row in _all_rows():
        roster_entry_id = row["roster_entry_id"]
        assert roster_entry_id in loaded_roster.entries, (
            f"row {row['run_id']!r} cites unresolved roster_entry_id "
            f"{roster_entry_id!r}"
        )


def test_every_quality_row_resolves_its_suite_definition() -> None:
    quality_rows = results.read_rows(QUALITY_REFERENCE_PATH)
    for row in quality_rows:
        suite_id = row["suite_id"]
        snapshot_path = SUITE_DEFINITIONS_DIR / f"{suite_id}.json"
        assert snapshot_path.exists(), (
            f"row {row['run_id']!r} cites unresolved suite_id {suite_id!r}"
        )
        snapshot = json.loads(snapshot_path.read_text(encoding="utf-8"))
        assert snapshot["suite_id"] == suite_id
        assert snapshot["suite_version"] == row["suite_version"]
        # The hash, not the version, is what catches a suite edited without a
        # version bump -- the one drift `suite_version` alone cannot see.
        assert snapshot["prompt_set_hash"] == row["prompt_set_hash"]


def test_every_row_carries_the_current_schema_version() -> None:
    for row in _all_rows():
        assert row["schema_version"] == row_contract.SCHEMA_VERSION


def test_superseded_files_exist_and_are_not_the_current_schema() -> None:
    for path in SUPERSEDED_PATHS:
        assert path.exists(), f"expected superseded file at {path}"
        for row in results.read_rows(path):
            schema_version = row.get("schema_version")
            if schema_version is not None:
                assert schema_version != row_contract.SCHEMA_VERSION
