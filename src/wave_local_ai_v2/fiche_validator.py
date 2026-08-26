"""`wave-local-ai-v2-validate`: prove an edited or missing fiche invalidates
the rows citing it.

Reads published artifacts only -- every result row and every stored fiche --
and recomputes nothing about the run itself: no server launch, no roster
load beyond what parsing JSON needs.
"""

from __future__ import annotations

import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, TypedDict

from wave_local_ai_v2 import fiche_registry, results
from wave_local_ai_v2.row_contract import FICHE_HASH_SCHEMA_VERSION
from wave_local_ai_v2.settings import (
    SettingsError,
    fiche_registry_dir_from_env,
    load_settings,
)


class _RowIssue(TypedDict):
    results_path: str
    run_id: str | None
    position: int
    fiche_path: str


class _MissingIssue(_RowIssue):
    fiche_hash: str | None


class _EditedIssue(_RowIssue):
    changed_fields: list[str]


class _LegacyIssue(TypedDict):
    results_path: str
    run_id: str | None
    position: int
    schema_version: str | None


class ValidationReport(TypedDict):
    rows_checked: int
    edited: list[_EditedIssue]
    missing: list[_MissingIssue]
    legacy: list[_LegacyIssue]


def _predates_fiche_hash_contract(schema_version: object) -> bool:
    """True when `schema_version` is below `FICHE_HASH_SCHEMA_VERSION`.

    `None` (no `schema_version` key at all) always predates it -- that key
    itself postdates the fiche-hash contract. An unparseable value can't be
    proven to predate it, so it is not treated as legacy: it stays subject to
    the ordinary `missing`/`edited` checks below.
    """
    if schema_version is None:
        return True
    try:
        return int(schema_version) < int(FICHE_HASH_SCHEMA_VERSION)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return False


def validate_bundle(results_paths: list[Path], registry_dir: Path) -> ValidationReport:
    """Check every row of every path in `results_paths` against `registry_dir`.

    Row positions are 0-based and restart at each file, so every issue also
    carries the `results_path` it was read from -- `fiche_path` points into
    the registry, not at the results file, and the default invocation checks
    two files at once. A row whose `schema_version` predates
    `FICHE_HASH_SCHEMA_VERSION` is reported under the non-fatal `legacy`
    class rather than `missing`, even when it carries no `fiche_hash` at all:
    the fiche-hash contract did not apply to it, so its absence is not an
    integrity failure.
    """
    rows_checked = 0
    edited: list[_EditedIssue] = []
    missing: list[_MissingIssue] = []
    legacy: list[_LegacyIssue] = []

    for path in results_paths:
        results_path = str(path)
        for position, row in enumerate(results.read_rows(path)):
            rows_checked += 1
            run_id = row.get("run_id")
            schema_version = row.get("schema_version")

            if _predates_fiche_hash_contract(schema_version):
                legacy.append(
                    _LegacyIssue(
                        results_path=results_path,
                        run_id=run_id,
                        position=position,
                        schema_version=schema_version,
                    )
                )
                continue

            fiche_hash = row.get("fiche_hash")
            fiche_path = str(registry_dir / f"{fiche_hash}.json")

            if fiche_hash is None:
                missing.append(
                    _MissingIssue(
                        results_path=results_path,
                        run_id=run_id,
                        position=position,
                        fiche_path=fiche_path,
                        fiche_hash=fiche_hash,
                    )
                )
                continue

            verification = fiche_registry.verify_fiche(fiche_hash, registry_dir)
            if verification["status"] == "missing":
                missing.append(
                    _MissingIssue(
                        results_path=results_path,
                        run_id=run_id,
                        position=position,
                        fiche_path=fiche_path,
                        fiche_hash=fiche_hash,
                    )
                )
            elif verification["status"] == "edited":
                edited.append(
                    _EditedIssue(
                        results_path=results_path,
                        run_id=run_id,
                        position=position,
                        fiche_path=fiche_path,
                        changed_fields=verification["changed_fields"],
                    )
                )

    return ValidationReport(
        rows_checked=rows_checked, edited=edited, missing=missing, legacy=legacy
    )


def main() -> None:
    try:
        _run()
    except (SettingsError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    argv = sys.argv[1:]
    if argv:
        results_paths = [Path(arg) for arg in argv]
        for path in results_paths:
            # An explicitly named path that is absent is a typo, not zero
            # rows: `results.read_rows` would return `[]` and this command
            # would report a clean bill of health for a file it never opened.
            if not path.exists():
                raise FileNotFoundError(f"results file not found: {path}")
        # Deliberately not a full `load_settings()`: this form checks a
        # published artifact, so it must not require SLM_MODELS_DIR and
        # LLAMA_SERVER_PATH to exist on the machine running the check.
        registry_dir = fiche_registry_dir_from_env()
    else:
        settings = load_settings()
        results_paths = [settings.results_path, settings.quality_results_path]
        registry_dir = settings.fiche_registry_dir

    report = validate_bundle(results_paths, registry_dir)

    print(f"checked {report['rows_checked']} row(s)")
    _print_issues("edited", report["edited"])
    _print_issues("missing", report["missing"])
    if report["legacy"]:
        print(f"legacy (pre-fiche-hash, not fatal): {len(report['legacy'])}")

    if report["edited"] or report["missing"]:
        sys.exit(1)
    sys.exit(0)


def _print_issues(label: str, issues: Sequence[Mapping[str, Any]]) -> None:
    if not issues:
        return
    print(f"{label} ({len(issues)}):")
    for issue in issues:
        print(f"  {issue}")


if __name__ == "__main__":
    main()
