"""The published bundle as four flat tables: over the committed bundle, and over
small bundles built here to exercise absence, refusal and determinism.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path

import pytest

from wave_local_ai_v2 import bundle_export, row_contract
from wave_local_ai_v2.bundle_export import (
    DICTIONARY_FILE,
    MANIFEST_FILE,
    NOT_CARRIED_COLUMN,
    TABLES,
    BundlePaths,
    ExportError,
    FieldDoc,
    Source,
)

# Pinned here, like `tests/test_reference_bundle.py` pins it, rather than read
# from `row_contract.SCHEMA_VERSION`: the export must declare what it read.
PUBLISHED_BUNDLE_SCHEMA_VERSION = "7"
COMMITTED = bundle_export.default_bundle_paths()


def _read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _header(path: Path) -> list[str]:
    with path.open(encoding="utf-8", newline="") as handle:
        return next(csv.reader(handle))


@pytest.fixture(scope="module")
def committed_export(tmp_path_factory: pytest.TempPathFactory) -> Path:
    output_dir = tmp_path_factory.mktemp("export")
    bundle_export.export_bundle(COMMITTED, output_dir)
    return output_dir


# --------------------------------------------------------------------------
# Over the committed bundle.
# --------------------------------------------------------------------------


def test_four_tables_hold_one_row_per_bundle_record(committed_export: Path) -> None:
    roster_file = json.loads(COMMITTED.roster.read_text(encoding="utf-8"))
    expected = {
        "quality_items": len(
            COMMITTED.quality_rows.read_text(encoding="utf-8").splitlines()
        ),
        "runtime_aggregates": len(
            COMMITTED.runtime_rows.read_text(encoding="utf-8").splitlines()
        ),
        "fiches": len(list(COMMITTED.fiche_dir.glob("*.json"))),
        "roster": len(roster_file["entries"]),
    }

    for table, count in expected.items():
        assert len(_read_csv(committed_export / f"{table}.csv")) == count, table


def test_the_roster_table_holds_each_thinking_control_as_one_json_cell(
    committed_export: Path,
) -> None:
    # One column whatever the control's spelling: a flattened object would
    # add a column per family's argument names.
    entries = json.loads(COMMITTED.roster.read_text(encoding="utf-8"))["entries"]
    header = _header(committed_export / "roster.csv")

    assert [name for name in header if name.startswith("thinking_control")] == [
        "thinking_control"
    ]
    for row in _read_csv(committed_export / "roster.csv"):
        assert (
            json.loads(row["thinking_control"])
            == entries[row["entry_id"]]["thinking_control"]
        )


def test_the_manifest_declares_the_schema_the_bundle_carries(
    committed_export: Path,
) -> None:
    manifest = {row["part"]: row for row in _read_csv(committed_export / MANIFEST_FILE)}

    for part in ("runtime_rows", "quality_rows"):
        assert manifest[part]["version_field"] == "schema_version"
        assert manifest[part]["versions_read"] == PUBLISHED_BUNDLE_SCHEMA_VERSION
    assert manifest["quality_rows"]["versions_read"] != row_contract.SCHEMA_VERSION


def test_each_row_carries_its_own_schema_version_column(
    committed_export: Path,
) -> None:
    for table in ("quality_items", "runtime_aggregates"):
        rows = _read_csv(committed_export / f"{table}.csv")
        assert {row["schema_version"] for row in rows} == {
            PUBLISHED_BUNDLE_SCHEMA_VERSION
        }


def test_every_pointer_is_resolved_into_columns_of_its_row(
    committed_export: Path,
) -> None:
    fiches = {
        path.stem: json.loads(path.read_text(encoding="utf-8"))
        for path in COMMITTED.fiche_dir.glob("*.json")
    }
    entries = json.loads(COMMITTED.roster.read_text(encoding="utf-8"))["entries"]

    for table in ("quality_items", "runtime_aggregates"):
        for row in _read_csv(committed_export / f"{table}.csv"):
            fiche = fiches[row["fiche_hash"]]
            entry = entries[row["roster_entry_id"]]
            assert row["fiche_gpu_name"] == fiche["gpu_name"]
            assert row["fiche_llama_cpp_build"] == fiche["llama_cpp_build"]
            assert row["roster_entry_display_id"] == entry["display_id"]
            assert (
                row["roster_entry_architecture_kind"] == entry["architecture"]["kind"]
            )
            assert row["roster_file_version"] == "2"
    for row in _read_csv(committed_export / "quality_items.csv"):
        definition = json.loads(
            (
                COMMITTED.suite_definitions
                / f"{row['suite_id']}@{row['suite_version']}.json"
            ).read_text(encoding="utf-8")
        )
        assert row["suite_definition_prompt_set_hash"] == definition["prompt_set_hash"]
        assert row["suite_definition_max_output_tokens"] == str(
            definition["max_output_tokens"]
        )


def test_nested_fields_become_named_columns(committed_export: Path) -> None:
    quality = set(_header(committed_export / "quality_items.csv"))
    runtime = set(_header(committed_export / "runtime_aggregates.csv"))

    assert {
        "sampling_seed",
        "sampling_random_seed",
        "language_breakdown_en_accuracy",
        "language_breakdown_de_n",
        "failure_counts_unparseable",
        "verdict_verdict",
        "verdict_differing_fields",
    } <= quality
    assert {"sampling_min_p", "aggregation_ttft_ms", "verdict_ttft_ms_delta"} <= runtime
    assert "sampling" not in quality | runtime
    assert "verdict" not in quality | runtime


def test_per_repetition_arrays_stay_out_of_the_runtime_table(
    committed_export: Path,
) -> None:
    header = _header(committed_export / "runtime_aggregates.csv")
    rows = _read_csv(committed_export / "runtime_aggregates.csv")

    assert not {
        "repetitions",
        "warmup_repetitions",
        "verdict_reference_repetitions",
    } & set(header)
    assert [name for name in header if name.startswith("repetitions")] == [
        "repetitions_n"
    ]
    assert not any('{"index"' in cell for row in rows for cell in row.values() if cell)
    dictionary = _read_csv(committed_export / DICTIONARY_FILE)
    excluded = {
        entry["column"]
        for entry in dictionary
        if entry["carried"] == "false" and entry["table"] == "runtime_aggregates"
    }
    assert {"repetitions", "warmup_repetitions", "verdict_reference_repetitions"} <= (
        excluded
    )


def test_the_dictionary_and_the_tables_agree_both_ways(committed_export: Path) -> None:
    dictionary = _read_csv(committed_export / DICTIONARY_FILE)
    headers = {table: _header(committed_export / f"{table}.csv") for table in TABLES}

    for table in TABLES:
        described = [
            entry["column"]
            for entry in dictionary
            if entry["table"] == table and entry["carried"] == "true"
        ]
        assert described == headers[table], table
    every_header = {name for header in headers.values() for name in header}
    for entry in dictionary:
        if entry["carried"] == "true":
            assert entry["meaning"] and entry["unit"] and entry["source"], entry
            assert entry["empty_cell"], entry
        else:
            assert entry["carried"] == "false"
            assert entry["owner"], entry
            if entry["table"]:
                assert entry["column"] not in headers[entry["table"]], entry
            else:
                assert entry["column"] not in every_header, entry


def test_blocks_owned_elsewhere_are_named_with_their_owner(
    committed_export: Path,
) -> None:
    owners = {
        entry["column"]: entry["owner"]
        for entry in _read_csv(committed_export / DICTIONARY_FILE)
        if entry["carried"] == "false"
    }

    assert "a-score-is-published-with-its-interval" in owners["interval block"]
    assert "every-size-class-spans-two-families" in owners["roster licence block"]
    assert (
        "comparison-family-and-leader-set-records-read-as-a-fifth-table"
        in owners["comparison and family records"]
    )
    # Fields the row contract added after "7" are named, not silently absent.
    assert {"retries", "resumed", "thinking_policy", "prompt_variant_id"} <= set(owners)
    # The item licence and source are contract fields now, named as such
    # rather than as a block owned elsewhere.
    assert "item licence and source" not in owners
    assert {
        "suite_level",
        "item_licence",
        "item_source",
        "item_source_revision",
    } <= set(owners)


def test_accuracy_recomputed_from_the_quality_table_equals_the_published_values(
    committed_export: Path,
) -> None:
    batches: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in _read_csv(committed_export / "quality_items.csv"):
        batches[(row["run_id"], row["provider"], row["model_id"])].append(row)

    assert len(batches) == 4
    for key, rows in batches.items():
        correct = [row["correct"] == "true" for row in rows]
        assert {row["suite_accuracy"] for row in rows} == {
            repr(sum(correct) / len(correct))
        }, key
        by_language: dict[str, list[bool]] = defaultdict(list)
        for row in rows:
            by_language[row["language"]].append(row["correct"] == "true")
        for language, answers in by_language.items():
            published = {row[f"language_breakdown_{language}_accuracy"] for row in rows}
            assert published == {repr(sum(answers) / len(answers))}, (key, language)
            assert {row[f"language_breakdown_{language}_n"] for row in rows} == {
                str(len(answers))
            }


def test_the_export_changes_no_bundle_file(tmp_path: Path) -> None:
    def digest() -> dict[str, str]:
        files = [
            COMMITTED.runtime_rows,
            COMMITTED.quality_rows,
            COMMITTED.roster,
            *sorted(COMMITTED.fiche_dir.iterdir()),
            *sorted(COMMITTED.suite_definitions.iterdir()),
        ]
        return {
            path.as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
            for path in files
        }

    before = digest()
    bundle_export.export_bundle(COMMITTED, tmp_path)

    assert digest() == before


def test_the_command_uses_the_standard_library_alone() -> None:
    tree = ast.parse(Path(bundle_export.__file__).read_text(encoding="utf-8"))
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

    assert roots - {"__future__", "wave_local_ai_v2"} <= set(sys.stdlib_module_names)


def test_every_row_contract_field_is_described_or_excluded() -> None:
    contract = bundle_export.contract_fields("quality") | bundle_export.contract_fields(
        "runtime"
    )
    described = {path[0] for path in bundle_export.ROW_FIELDS if len(path) == 1}
    excluded = {"repetitions", "warmup_repetitions"}

    assert described | excluded == contract
    assert not described & excluded


# --------------------------------------------------------------------------
# Over a constructed bundle: the committed fiches, roster and suite
# definitions, with rows edited here.
# --------------------------------------------------------------------------


def _committed_rows(path: Path) -> list[dict[str, object]]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def _write_rows(path: Path, rows: list[dict[str, object]]) -> Path:
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    return path


def _bundle(
    tmp_path: Path,
    quality: list[dict[str, object]] | None = None,
    runtime: list[dict[str, object]] | None = None,
) -> BundlePaths:
    rows_dir = tmp_path / "rows"
    rows_dir.mkdir(exist_ok=True)
    if quality is None:
        quality = _committed_rows(COMMITTED.quality_rows)[:2]
    if runtime is None:
        runtime = _committed_rows(COMMITTED.runtime_rows)[:1]
    return BundlePaths(
        runtime_rows=_write_rows(rows_dir / "runtime.jsonl", runtime),
        quality_rows=_write_rows(rows_dir / "quality.jsonl", quality),
        fiche_dir=COMMITTED.fiche_dir,
        roster=COMMITTED.roster,
        suite_definitions=COMMITTED.suite_definitions,
    )


def _replace(paths: BundlePaths, **changes: Path) -> BundlePaths:
    fields = {
        "runtime_rows": paths.runtime_rows,
        "quality_rows": paths.quality_rows,
        "fiche_dir": paths.fiche_dir,
        "roster": paths.roster,
        "suite_definitions": paths.suite_definitions,
    }
    return BundlePaths(**{**fields, **changes})


def test_absence_and_a_recorded_null_are_told_apart(tmp_path: Path) -> None:
    first, second = _committed_rows(COMMITTED.quality_rows)[:2]
    first["cost_per_million_tokens"] = None
    del second["cost_per_million_tokens"]
    del second["fiche_hash"]
    del second["suite_version"]

    bundle_export.export_bundle(
        _bundle(tmp_path, quality=[first, second]), tmp_path / "out"
    )
    rows = _read_csv(tmp_path / "out" / "quality_items.csv")

    assert rows[0]["cost_per_million_tokens"] == ""
    assert rows[1]["cost_per_million_tokens"] == ""
    first_missing = json.loads(rows[0][NOT_CARRIED_COLUMN])
    second_missing = json.loads(rows[1][NOT_CARRIED_COLUMN])
    assert "cost_per_million_tokens" not in first_missing
    assert "cost_per_million_tokens" in second_missing
    # A row with no pointer leaves every resolved column empty and says so.
    assert rows[1]["fiche_gpu_name"] == ""
    assert "fiche_gpu_name" in second_missing
    assert "fiche_gpu_name" not in first_missing
    assert "suite_definition_prompt_set_hash" in second_missing


def test_a_recorded_null_pointer_is_not_reported_as_not_carried(
    tmp_path: Path,
) -> None:
    first, second = _committed_rows(COMMITTED.quality_rows)[:2]
    second["fiche_hash"] = None
    second["suite_version"] = None

    bundle_export.export_bundle(
        _bundle(tmp_path, quality=[first, second]), tmp_path / "out"
    )
    row = _read_csv(tmp_path / "out" / "quality_items.csv")[1]

    assert row["fiche_gpu_name"] == ""
    assert row["suite_definition_prompt_set_hash"] == ""
    missing = json.loads(row[NOT_CARRIED_COLUMN])
    assert "fiche_gpu_name" not in missing
    assert "suite_definition_prompt_set_hash" not in missing


def test_a_float_with_many_digits_round_trips(tmp_path: Path) -> None:
    first, second = _committed_rows(COMMITTED.quality_rows)[:2]
    first["energy_kwh"] = 0.1 + 0.2
    second["energy_kwh"] = 1.2345678901234567e-300

    bundle_export.export_bundle(
        _bundle(tmp_path, quality=[first, second]), tmp_path / "out"
    )
    rows = _read_csv(tmp_path / "out" / "quality_items.csv")

    assert float(rows[0]["energy_kwh"]) == 0.1 + 0.2
    assert float(rows[1]["energy_kwh"]) == 1.2345678901234567e-300


def test_two_runs_are_byte_identical_and_the_format_is_pinned(tmp_path: Path) -> None:
    paths = _bundle(tmp_path)
    bundle_export.export_bundle(paths, tmp_path / "a")
    bundle_export.export_bundle(paths, tmp_path / "b")

    names = sorted(path.name for path in (tmp_path / "a").iterdir())
    assert names == sorted(
        [f"{table}.csv" for table in TABLES] + [DICTIONARY_FILE, MANIFEST_FILE]
    )
    for name in names:
        first = (tmp_path / "a" / name).read_bytes()
        assert first == (tmp_path / "b" / name).read_bytes(), name
        assert not first.startswith(b"\xef\xbb\xbf")
        assert first.endswith(b"\r\n")


def test_the_declaration_follows_the_rows_it_read(tmp_path: Path) -> None:
    first, second = _committed_rows(COMMITTED.quality_rows)[:2]
    second["schema_version"] = "10"

    bundle_export.export_bundle(
        _bundle(tmp_path, quality=[first, second]), tmp_path / "out"
    )
    manifest = {row["part"]: row for row in _read_csv(tmp_path / "out" / MANIFEST_FILE)}

    assert manifest["quality_rows"]["versions_read"] == "7;10"
    assert bundle_export.declared_versions([{}, {"schema_version": "7"}]) == (
        "7;not_carried"
    )


def _refused_export(
    tmp_path: Path, rows: list[dict[str, object]], capsys: pytest.CaptureFixture[str]
) -> str:
    paths = _bundle(tmp_path, quality=rows)
    output_dir = tmp_path / "out"

    code = bundle_export.main(
        [
            "--output-dir",
            str(output_dir),
            "--runtime-rows",
            str(paths.runtime_rows),
            "--quality-rows",
            str(paths.quality_rows),
        ]
    )

    assert code == 1
    assert not output_dir.exists()
    return capsys.readouterr().err


@pytest.mark.parametrize(
    ("field", "value", "expected"),
    [
        ("fiche_hash", "0" * 64, "fiche_hash '000"),
        ("roster_entry_id", "no-such-entry", "roster_entry_id 'no-such-entry'"),
        ("mystery_field", 1, "`mystery_field` has no dictionary entry"),
        ("energy_kwh", float("nan"), "no CSV form"),
        ("sampling", 5, "one column cannot hold both"),
        ("suite_version", "999", "classification-support-routing@999"),
    ],
)
def test_a_bundle_that_cannot_be_exported_whole_is_refused(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    field: str,
    value: object,
    expected: str,
) -> None:
    first, second = _committed_rows(COMMITTED.quality_rows)[:2]
    second[field] = value

    assert expected in _refused_export(tmp_path, [first, second], capsys)


def test_the_command_writes_and_reports_each_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    paths = _bundle(tmp_path)

    code = bundle_export.main(
        [
            "--output-dir",
            str(tmp_path / "out"),
            "--runtime-rows",
            str(paths.runtime_rows),
            "--quality-rows",
            str(paths.quality_rows),
            "--fiche-dir",
            str(paths.fiche_dir),
            "--roster",
            str(paths.roster),
            "--suite-definitions",
            str(paths.suite_definitions),
        ]
    )

    assert code == 0
    assert "quality_items.csv (2 rows)" in capsys.readouterr().out


def test_the_output_directory_is_required() -> None:
    with pytest.raises(SystemExit):
        bundle_export.main([])


def test_writing_into_a_bundle_directory_is_refused(tmp_path: Path) -> None:
    paths = _bundle(tmp_path)

    with pytest.raises(ExportError, match="holds bundle files"):
        bundle_export.export_bundle(paths, paths.quality_rows.parent)


def test_unreadable_bundle_parts_are_refused(tmp_path: Path) -> None:
    paths = _bundle(tmp_path)
    broken_rows = tmp_path / "broken.jsonl"
    broken_rows.write_text("{not json\n", encoding="utf-8")
    broken_roster = tmp_path / "roster.json"
    broken_roster.write_text('{"roster_version": 1}', encoding="utf-8")
    bad_fiches = tmp_path / "bad-fiches"
    bad_fiches.mkdir()
    (bad_fiches / "bad.json").write_text("{not json", encoding="utf-8")
    list_fiches = tmp_path / "list-fiches"
    list_fiches.mkdir()
    (list_fiches / "list.json").write_text("[]", encoding="utf-8")
    suites = tmp_path / "suites"
    suites.mkdir()
    (suites / "classification-support-routing@2.json").write_text(
        "[]", encoding="utf-8"
    )
    cases = [
        (_replace(paths, runtime_rows=tmp_path / "absent.jsonl"), "no row file"),
        (_replace(paths, quality_rows=broken_rows), "not one JSON row per line"),
        (_replace(paths, fiche_dir=tmp_path / "absent"), "no fiche directory"),
        (_replace(paths, fiche_dir=bad_fiches), "is not JSON"),
        (_replace(paths, fiche_dir=list_fiches), "is not a JSON object"),
        (_replace(paths, roster=broken_roster), "roster"),
        (_replace(paths, suite_definitions=suites), "is not a JSON object"),
    ]

    for case, expected in cases:
        with pytest.raises(ExportError, match=expected):
            bundle_export.build_export(case)


# --------------------------------------------------------------------------
# The pieces, directly.
# --------------------------------------------------------------------------

_DOC = FieldDoc("A test field.", "text")


def test_two_source_paths_that_would_share_a_column_name_are_refused() -> None:
    source = Source(
        "",
        "test record",
        {("a_b",): _DOC, ("a", "b"): _DOC},
        {"a_b": 1, "a": {"b": 2}},
        "",
    )

    with pytest.raises(ExportError, match="would hold both"):
        bundle_export.build_table("t", [[source]])


def test_a_column_that_would_shadow_fields_not_carried_is_refused() -> None:
    source = Source(
        "", "test record", {(NOT_CARRIED_COLUMN,): _DOC}, {NOT_CARRIED_COLUMN: 1}, ""
    )

    with pytest.raises(ExportError, match="would hold both"):
        bundle_export.build_table("t", [[source]])


def test_cells_are_formatted_under_the_pinned_format() -> None:
    assert bundle_export.format_cell(None, "c") == ""
    assert bundle_export.format_cell(True, "c") == "true"
    assert bundle_export.format_cell(False, "c") == "false"
    assert bundle_export.format_cell(3, "c") == "3"
    assert bundle_export.format_cell(1.0, "c") == "1.0"
    assert bundle_export.format_cell(["a", "é"], "c") == '["a","é"]'
    assert bundle_export.format_cell({"k": 1}, "c") == '{"k":1}'
    with pytest.raises(ExportError, match="unsupported value type"):
        bundle_export.format_cell((1, 2), "c")
    with pytest.raises(ExportError, match="c:"):
        bundle_export.format_cell([float("inf")], "c")


def test_an_empty_bundle_writes_headers_only(tmp_path: Path) -> None:
    files = bundle_export.build_export(_bundle(tmp_path, quality=[], runtime=[]))

    assert files["quality_items.csv"] == [(NOT_CARRIED_COLUMN,)]
    assert files["runtime_aggregates.csv"] == [(NOT_CARRIED_COLUMN,)]


def test_a_contract_field_without_a_dictionary_entry_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bundle_export, "contract_fields", lambda kind: frozenset({"undescribed"})
    )
    table = bundle_export.Table("quality_items", (), ())

    with pytest.raises(ExportError, match="undescribed"):
        bundle_export._not_carried_by_contract("quality", table)
