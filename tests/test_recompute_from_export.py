"""A reader holding only the exported tables recomputes what they publish.

`scripts/recompute_from_export.py` imports nothing from the project; these
tests run it over the export of a bundle that publishes intervals and a
family of McNemar comparisons, and check it lands on every published value
and catches one that was changed.
"""

from __future__ import annotations

import ast
import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import recompute_from_export as reader
from published_bundle_fixtures import SCHEMA_7, build_bundle

from wave_local_ai_v2 import bundle_export


@pytest.fixture(scope="module")
def export_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    root = tmp_path_factory.mktemp("published")
    output = root / "export"
    bundle_export.export_bundle(build_bundle(root / "bundle"), output)
    return output


@pytest.fixture(scope="module")
def checks(export_dir: Path) -> list[reader.Check]:
    return reader.recompute(export_dir)


def _rows(export_dir: Path, name: str) -> list[dict[str, str]]:
    with (export_dir / name).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def test_the_reader_imports_nothing_from_the_project() -> None:
    tree = ast.parse(Path(reader.__file__).read_text(encoding="utf-8"))
    roots = {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }

    assert roots - {"__future__"} <= set(sys.stdlib_module_names)


def test_every_published_interval_and_comparison_is_recomputed(
    checks: list[reader.Check], export_dir: Path
) -> None:
    quality = _rows(export_dir, reader.QUALITY_TABLE)
    records = _rows(export_dir, reader.RECORDS_TABLE)
    tested = [
        r
        for r in records
        if r["record_kind"] == "comparison" and r["comparison_test"] == "mcnemar_exact"
    ]
    by_field = {(check.subject, check.field): check for check in checks}

    assert [check for check in checks if not check.matches] == []
    # Four batches, each a suite cell and one cell per language column.
    batches = {(row["run_id"], row["model_id"]) for row in quality}
    interval_subjects = {c.subject for c in checks if c.subject.startswith("interval")}
    assert len(batches) == len(interval_subjects) == 4
    assert any(
        field == "score_interval_suite_lower" and check.published
        for (_, field), check in by_field.items()
    )
    # Both comparisons are tests, recomputed, and adjusted over a family of two.
    assert len(tested) == 2
    assert {c.field for c in checks if c.subject.startswith("mcnemar")} >= {
        "comparison_result_p_value",
        "comparison_paired_n",
        "comparison_result_contingency_reference_only_correct",
    }
    assert len([c for c in checks if c.subject.startswith("holm")]) == 2


def test_a_changed_published_value_is_caught(export_dir: Path) -> None:
    quality = _rows(export_dir, reader.QUALITY_TABLE)
    records = _rows(export_dir, reader.RECORDS_TABLE)
    tested = next(r for r in records if r["comparison_test"] == "mcnemar_exact")
    tested["comparison_result_p_value"] = "0.5"
    batch = [r for r in quality if r["run_id"] == quality[0]["run_id"]]
    batch = [r for r in batch if r["model_id"] == quality[0]["model_id"]]
    for row in batch:
        row["score_interval_suite_upper"] = "0.99"

    changed = [
        check
        for check in reader.check_intervals(batch)
        + reader.check_mcnemar(quality, records)
        if not check.matches
    ]

    assert {check.field for check in changed} == {
        "score_interval_suite_upper",
        "comparison_result_p_value",
    }


def test_a_procedure_the_reader_does_not_implement_is_refused(
    export_dir: Path,
) -> None:
    rows = _rows(export_dir, reader.QUALITY_TABLE)
    for row in rows:
        row["score_interval_draw_procedure_id"] = "another-procedure/2"

    refused = reader.check_intervals(rows)

    assert refused and all(
        check.field == "procedure" and not check.matches for check in refused
    )


def test_two_blocks_on_one_batch_are_reported(export_dir: Path) -> None:
    rows = _rows(export_dir, reader.QUALITY_TABLE)
    batch = [r for r in rows if r["run_id"] == rows[0]["run_id"]]
    batch = [r for r in batch if r["model_id"] == rows[0]["model_id"]]
    batch[0]["score_interval_seed"] = "1"

    (check,) = reader.check_intervals(batch)

    assert (check.field, check.matches) == ("block", False)


def test_the_command_reports_each_value_and_its_exit_code(
    export_dir: Path, tmp_path: Path
) -> None:
    lines: list[str] = []
    assert reader.main([str(export_dir)], echo=lines.append) == 0
    assert lines[-1].endswith("0 differ")
    assert all(line.startswith("match") for line in lines[:-1])

    # A record table with one changed p-value fails the command.
    (tmp_path / reader.QUALITY_TABLE).write_bytes(
        (export_dir / reader.QUALITY_TABLE).read_bytes()
    )
    records = _rows(export_dir, reader.RECORDS_TABLE)
    next(r for r in records if r["comparison_result_p_value"])[
        "comparison_result_p_value"
    ] = "0.5"
    with (tmp_path / reader.RECORDS_TABLE).open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    lines.clear()
    assert reader.main([str(tmp_path)], echo=lines.append) == 1
    assert any(line.startswith("MISMATCH") for line in lines)


def test_an_export_without_published_statistics_has_nothing_to_recompute(
    tmp_path: Path,
) -> None:
    # The superseded schema-7 rows predate the interval block and their
    # family records refuse every pair: nothing is published to recompute.
    bundle_export.export_bundle(SCHEMA_7, tmp_path)

    assert reader.recompute(tmp_path) == []


def test_the_committed_bundle_recomputes_to_every_published_value(
    tmp_path: Path,
) -> None:
    bundle_export.export_bundle(bundle_export.default_bundle_paths(), tmp_path)

    checks = reader.recompute(tmp_path)

    assert checks
    assert [check for check in checks if not check.matches] == []
