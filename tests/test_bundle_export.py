"""The published bundle as four flat tables: over the committed bundle, and over
small bundles built here to exercise absence, refusal and determinism.
"""

from __future__ import annotations

import ast
import csv
import dataclasses
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pytest
from published_bundle_fixtures import SCHEMA_7

from wave_local_ai_v2 import (
    bundle_export,
    comparison,
    leader_set,
    row_contract,
    score_interval,
)
from wave_local_ai_v2.bundle_export import (
    DICTIONARY_FILE,
    MANIFEST_FILE,
    NOT_CARRIED,
    NOT_CARRIED_COLUMN,
    TABLES,
    BundlePaths,
    ExportError,
    FieldDoc,
    Source,
)

# The export's mechanics are pinned over a fixed set of real rows: the
# superseded schema-"7" bundle (`published_bundle_fixtures.SCHEMA_7`), which
# no later run changes. The schema is pinned rather than read from
# `row_contract.SCHEMA_VERSION`: the export must declare what it read. The
# current bundle's own export is asserted in `test_the_current_bundle_exports`.
PUBLISHED_BUNDLE_SCHEMA_VERSION = "7"
COMMITTED = SCHEMA_7


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
        cell = row["thinking_control"]
        # An object is one JSON cell; a model that does not reason declares
        # the identifier `none`, carried as it is.
        value = cell if cell == "none" else json.loads(cell)
        assert value == entries[row["entry_id"]]["thinking_control"]


def test_the_manifest_declares_the_schema_the_bundle_carries(
    committed_export: Path,
) -> None:
    manifest = {row["part"]: row for row in _read_csv(committed_export / MANIFEST_FILE)}

    for part in ("runtime_rows", "quality_rows"):
        assert manifest[part]["version_field"] == "schema_version"
        assert manifest[part]["versions_read"] == PUBLISHED_BUNDLE_SCHEMA_VERSION
    assert manifest["quality_rows"]["versions_read"] != row_contract.SCHEMA_VERSION


def test_the_current_bundle_exports(tmp_path: Path) -> None:
    # The republished bundle carries what the schema-7 fixture never did: a
    # cloud batch's retry budget keyed by provider, kept as one JSON cell,
    # and a suite definition declaring its level and divergence tolerance.
    bundle_export.export_bundle(bundle_export.default_bundle_paths(), tmp_path)
    manifest = {row["part"]: row for row in _read_csv(tmp_path / MANIFEST_FILE)}
    quality = _read_csv(tmp_path / "quality_items.csv")

    for part in ("runtime_rows", "quality_rows"):
        assert manifest[part]["versions_read"] == "30"
    assert {row["retry_budget"] for row in quality} == {"{}", '{"mistral":4}'}
    assert {row["suite_definition_divergence_tolerance_value"] for row in quality} == {
        "0.1"
    }


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
    roster_file = json.loads(COMMITTED.roster.read_text(encoding="utf-8"))
    entries = roster_file["entries"]

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
            # The version the export resolved against, not the one the row
            # was produced under: it follows the file.
            assert row["roster_file_version"] == str(roster_file["roster_version"])
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

    # No row of the committed bundle carries the interval (schema "21"): the
    # contract field is named, with the epic that defines it, and no
    # owned-elsewhere "interval block" entry contradicts a bundle that has it.
    assert "a-score-is-published-with-its-interval" in owners["score_interval"]
    assert "interval block" not in owners
    # The roster licence block is carried now, as roster-table columns.
    assert "roster licence block" not in owners
    roster_header = set(_header(committed_export / "roster.csv"))
    assert {
        "licence_id",
        "licence_client_commercial_use",
        "licence_read_on",
        "licence_source_url",
        "language_claim_languages",
        "language_claim_source_url",
        "language_claim_read_on",
        "language_claim_statement",
    } <= roster_header
    # The comparison, family and leader-set records are the fifth table now,
    # and the committed bundle holds all three kinds.
    assert "comparison and family records" not in owners
    assert not {name for name in owners if name.endswith(" records")}
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
        # Schema "16": where the subject prompt went.
        "subject_egress",
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
            *sorted(COMMITTED.comparisons_dir.iterdir()),
            *sorted(COMMITTED.leader_sets_dir.iterdir()),
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
    # A constructed bundle holds no analysis record unless a test writes one.
    comparisons_dir = tmp_path / "comparisons"
    leader_sets_dir = tmp_path / "leader-sets"
    comparisons_dir.mkdir(exist_ok=True)
    leader_sets_dir.mkdir(exist_ok=True)
    return BundlePaths(
        runtime_rows=_write_rows(rows_dir / "runtime.jsonl", runtime),
        quality_rows=_write_rows(rows_dir / "quality.jsonl", quality),
        fiche_dir=COMMITTED.fiche_dir,
        roster=COMMITTED.roster,
        suite_definitions=COMMITTED.suite_definitions,
        comparisons_dir=comparisons_dir,
        leader_sets_dir=leader_sets_dir,
    )


def _replace(paths: BundlePaths, **changes: Path) -> BundlePaths:
    return dataclasses.replace(paths, **changes)


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
    # Analysis records included, so the fifth table is held to it too.
    paths, _ = _constructed_records_bundle(tmp_path)
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
            "--comparisons-dir",
            str(paths.comparisons_dir),
            "--leader-sets-dir",
            str(paths.leader_sets_dir),
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
            "--comparisons-dir",
            str(paths.comparisons_dir),
            "--leader-sets-dir",
            str(paths.leader_sets_dir),
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
        (
            _replace(paths, comparisons_dir=paths.quality_rows),
            "is not a record directory",
        ),
        (_replace(paths, comparisons_dir=bad_fiches), "is not JSON"),
        (_replace(paths, comparisons_dir=list_fiches), "not a comparison_family"),
        (
            _replace(paths, leader_sets_dir=COMMITTED.comparisons_dir),
            "not a leader_set",
        ),
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
    assert files["comparison_records.csv"] == [(NOT_CARRIED_COLUMN,)]


def test_a_contract_field_without_a_dictionary_entry_is_refused(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        bundle_export, "contract_fields", lambda kind: frozenset({"undescribed"})
    )
    table = bundle_export.Table("quality_items", (), ())

    with pytest.raises(ExportError, match="undescribed"):
        bundle_export._not_carried_by_contract("quality", table)


# --------------------------------------------------------------------------
# The fifth table: comparison-family, comparison and leader-set records.
# --------------------------------------------------------------------------

_RECORD_SOURCES = {
    "comparison-family record": "family",
    "comparison (a member of the family record)": "comparison",
    "leader-set record": "leader_set",
    "leader-set subject": "subject",
}
_TESTED_RUN = "5e13166da0654390a7d63f346ea5d4f1"  # pragma: allowlist secret
_REFUSED_RUN = "d20afbda710c40378e6ad5ca8d9b6558"  # pragma: allowlist secret
_LOCAL_MODEL = "Qwen3.6-35B-A3B"
_CLOUD_MODEL = "mistral-small-2603"


def _record_columns(dictionary: list[dict[str, str]]) -> dict[str, tuple[str, ...]]:
    """Each record column of the fifth table: which record part, which path."""
    columns: dict[str, tuple[str, ...]] = {}
    for entry in dictionary:
        if entry["table"] != "comparison_records" or entry["carried"] != "true":
            continue
        label, _, path = entry["source"].partition(" `")
        if label in _RECORD_SOURCES:
            columns[entry["column"]] = (_RECORD_SOURCES[label], *path[:-1].split("."))
    return columns


def _row_records(
    rows: list[dict[str, str]], paths: BundlePaths
) -> list[dict[str, dict[str, object]]]:
    """The record parts each table row was read from, rebuilt from the files."""
    position: dict[tuple[str, str], int] = defaultdict(int)
    parts: list[dict[str, dict[str, object]]] = []
    for row in rows:
        kind, name = row["record_kind"], row["record_file"]
        is_family = kind in ("comparison_family", "comparison")
        directory = paths.comparisons_dir if is_family else paths.leader_sets_dir
        record = json.loads((directory / name).read_text(encoding="utf-8"))
        part: dict[str, dict[str, object]]
        if is_family:
            part = {"family": {k: v for k, v in record.items() if k != "members"}}
            if kind == "comparison":
                part["comparison"] = record["members"][position[(kind, name)]]
        else:
            part = {"leader_set": {k: v for k, v in record.items() if k != "subjects"}}
            if kind == "leader_set_subject":
                part["subject"] = record["subjects"][position[(kind, name)]]
        position[(kind, name)] += 1
        parts.append(part)
    return parts


def _assert_the_table_is_the_records(output_dir: Path, paths: BundlePaths) -> None:
    """Every record value is a cell, and every cell is a record value."""
    columns = _record_columns(_read_csv(output_dir / DICTIONARY_FILE))
    rows = _read_csv(output_dir / "comparison_records.csv")
    assert rows
    for row, parts in zip(rows, _row_records(rows, paths), strict=True):
        not_carried = json.loads(row[NOT_CARRIED_COLUMN])
        context = f"{row['record_kind']} in {row['record_file']}"
        # Nothing computed: each cell is the value its record holds there.
        for column, (part, *path) in columns.items():
            value = bundle_export._read_path(
                parts.get(part, NOT_CARRIED), tuple(path), context
            )
            assert row[column] == bundle_export.format_cell(value, context), column
            assert (value is NOT_CARRIED) == (column in not_carried), column
        # Nothing absent: each value the record holds has its column, a null
        # where other records hold an object being the null of its sub-columns.
        held = set(columns.values())
        for part, record in parts.items():
            for path in bundle_export._leaf_paths(record, (), frozenset(), frozenset()):
                key = (part, *path)
                assert key in held or (
                    bundle_export._read_path(record, path, context) is None
                    and any(column[: len(key)] == key for column in held)
                ), (context, key)


def _side(run_id: str, model_id: str) -> comparison.Side:
    return comparison.Side(run_id, {"model_id": model_id})


def _constructed_records_bundle(tmp_path: Path) -> tuple[BundlePaths, dict[str, str]]:
    """A tested comparison, a refused one, a family of two superseded by a family
    of three, and a leader set, each written by the analysis code itself."""
    rows = _committed_rows(COMMITTED.quality_rows)
    for row in rows:
        if row["run_id"] == _TESTED_RUN:
            # The one generation constraint the committed rows lack.
            row["thinking_policy"] = "disabled"
    paths = _bundle(tmp_path, quality=rows)
    pairs = [
        (_side(_TESTED_RUN, _LOCAL_MODEL), _side(_TESTED_RUN, _CLOUD_MODEL)),
        (_side(_REFUSED_RUN, _LOCAL_MODEL), _side(_REFUSED_RUN, _CLOUD_MODEL)),
        (_side(_TESTED_RUN, _LOCAL_MODEL), _side(_REFUSED_RUN, _LOCAL_MODEL)),
    ]
    members = [
        comparison.compare_sides(
            comparison.select_side(rows, reference),
            comparison.select_side(rows, candidate),
            reference,
            candidate,
        )
        for reference, candidate in pairs
    ]
    source = "rows/quality.jsonl"
    family_of_two = comparison.build_family_record(
        members[:2], alpha=0.05, rows_source=source
    )
    family_of_three = comparison.build_family_record(
        members,
        alpha=0.05,
        rows_source=source,
        supersedes=[family_of_two["family_id"]],
    )
    for record in (family_of_two, family_of_three):
        path = comparison.default_output_path(record, paths.comparisons_dir)
        path.write_text(comparison.record_text(record), encoding="utf-8", newline="\n")
    code = leader_set.publish(
        rows,
        rows_source=source,
        records_dir=paths.comparisons_dir,
        leader_sets_dir=paths.leader_sets_dir,
        fiche_registry_dir=COMMITTED.fiche_dir,
        alpha=0.05,
        echo=lambda _: None,
    )
    assert code == 0
    return paths, {
        "two": family_of_two["family_id"],
        "three": family_of_three["family_id"],
    }


def test_the_fifth_table_flattens_every_record_kind(tmp_path: Path) -> None:
    paths, ids = _constructed_records_bundle(tmp_path)
    output_dir = tmp_path / "out"
    bundle_export.export_bundle(paths, output_dir)
    rows = _read_csv(output_dir / "comparison_records.csv")

    assert Counter(row["record_kind"] for row in rows) == {
        "comparison_family": 2,
        "comparison": 5,
        "leader_set": 1,
        "leader_set_subject": 2,
    }
    _assert_the_table_is_the_records(output_dir, paths)

    comparisons = [row for row in rows if row["record_kind"] == "comparison"]
    tested = [r for r in comparisons if r["comparison_comparison_kind"] == "test"]
    assert len(tested) == 2
    for row in tested:
        assert row["comparison_test"] == "mcnemar_exact"
        assert row["comparison_raw_p_value"] == row["comparison_result_p_value"]
    # A refusal is a visible row: its reasons are cells, its p is empty.
    refused = [r for r in comparisons if r["comparison_comparison_kind"] == "refusal"]
    assert len(refused) == 3
    for row in refused:
        assert row["comparison_adjusted_p_value"] == ""
        assert row["comparison_adjusted_p_value_null_reason"] == "comparison_refused"
        assert "thinking_policy" in row["comparison_refusal"]
        assert row["comparison_verdict"] == "not comparable"
    # Each comparison names the family holding it.
    assert Counter(r["family_family_id"] for r in comparisons) == {
        ids["two"]: 2,
        ids["three"]: 3,
    }
    # The superseded family stays a row; the superseding row names it.
    families = {
        row["family_family_id"]: row
        for row in rows
        if row["record_kind"] == "comparison_family"
    }
    assert json.loads(families[ids["three"]]["family_supersedes"]) == [
        {"family_id": ids["two"]}
    ]
    assert json.loads(families[ids["two"]]["family_supersedes"]) == []
    # The leader set reads the current family; a not compared subject says why.
    leader = next(row for row in rows if row["record_kind"] == "leader_set")
    assert leader["leader_set_family_id"] == ids["three"]
    assert leader["leader_set_incomplete"] == "true"
    subjects = {
        row["subject_status"]: row
        for row in rows
        if row["record_kind"] == "leader_set_subject"
    }
    assert set(subjects) == {"member", "not compared"}
    assert "thinking_policy" in subjects["not compared"]["subject_not_compared_reason"]


def test_the_fifth_table_over_the_committed_bundle(committed_export: Path) -> None:
    families = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(COMMITTED.comparisons_dir.glob("*.json"))
    ]
    leader_sets = [
        json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(COMMITTED.leader_sets_dir.glob("*.json"))
    ]
    rows = _read_csv(committed_export / "comparison_records.csv")

    assert len(rows) == sum(1 + len(r["members"]) for r in families) + sum(
        1 + len(r["subjects"]) for r in leader_sets
    )
    _assert_the_table_is_the_records(committed_export, COMMITTED)
    dictionary = _read_csv(committed_export / DICTIONARY_FILE)
    # Every kind is held, so none is named as not carried.
    assert not [
        entry
        for entry in dictionary
        if entry["table"] == "comparison_records" and entry["carried"] == "false"
    ]
    # The statistics epic owns the definition of every record column.
    record_columns = _record_columns(dictionary)
    for entry in dictionary:
        if entry["table"] == "comparison_records" and entry["column"] in record_columns:
            assert "a-score-is-published-with-its-interval" in entry["owner"]
    manifest = {row["part"]: row for row in _read_csv(committed_export / MANIFEST_FILE)}
    assert manifest["comparison_families"]["entries_read"] == str(len(families))
    assert manifest["comparison_families"]["versions_read"] == "1;2"
    assert manifest["leader_sets"]["entries_read"] == str(len(leader_sets))


def test_record_kinds_the_bundle_does_not_hold_are_named(tmp_path: Path) -> None:
    files = bundle_export.build_export(_bundle(tmp_path))
    not_carried = {
        entry[1]: entry
        for entry in files[DICTIONARY_FILE][1:]
        if entry[0] == "comparison_records" and entry[2] == "false"
    }

    assert files["comparison_records.csv"] == [(NOT_CARRIED_COLUMN,)]
    assert set(not_carried) == {
        "comparison_family records",
        "comparison records",
        "leader_set records",
    }
    for entry in not_carried.values():
        assert "a-score-is-published-with-its-interval" in entry[-1]


def test_a_record_citing_what_the_bundle_does_not_hold_is_refused(
    tmp_path: Path,
) -> None:
    paths, ids = _constructed_records_bundle(tmp_path)
    without_older = tmp_path / "without-older"
    without_older.mkdir()
    for path in paths.comparisons_dir.glob("*.json"):
        if ids["two"][:12] not in path.name:
            (without_older / path.name).write_bytes(path.read_bytes())
    without_families = tmp_path / "without-families"
    without_families.mkdir()
    one_row = _write_rows(
        tmp_path / "rows" / "one.jsonl", _committed_rows(COMMITTED.quality_rows)[:1]
    )
    # A set of one cites no family; this one cites a record nobody holds.
    unknown_older = tmp_path / "unknown-older"
    unknown_older.mkdir()
    for path in paths.leader_sets_dir.glob("*.json"):
        record = json.loads(path.read_text(encoding="utf-8"))
        record["family_id"] = None
        record["supersedes"] = [{"leader_set_id": "not-in-the-bundle"}]
        (unknown_older / path.name).write_text(json.dumps(record), encoding="utf-8")
    cases = [
        (_replace(paths, comparisons_dir=without_older), "supersedes"),
        (_replace(paths, leader_sets_dir=unknown_older), "not-in-the-bundle"),
        (_replace(paths, comparisons_dir=without_families), "family_id"),
        (_replace(paths, quality_rows=one_row), "run_id"),
    ]

    for case, expected in cases:
        with pytest.raises(ExportError, match=expected):
            bundle_export.build_export(case)


def test_every_member_field_the_analysis_writes_is_described() -> None:
    rows = _committed_rows(COMMITTED.quality_rows)
    reference = _side(_TESTED_RUN, _LOCAL_MODEL)
    candidate = _side(_TESTED_RUN, _CLOUD_MODEL)
    energy = comparison.compare_sides(
        comparison.select_side(rows, reference),
        comparison.select_side(rows, candidate),
        reference,
        candidate,
        quantity="energy_kwh",
    )
    results = [
        comparison.mcnemar_exact([(True, False), (False, True), (True, True)]),
        comparison.mcnemar_exact([]),
        comparison.wilcoxon_signed_rank([0.5, -0.25, 0.0, 1.0]),
        comparison.wilcoxon_signed_rank([0.0, 0.0]),
        comparison.wilcoxon_signed_rank([]),
    ]

    for member in [energy, *({**energy, "result": result} for result in results)]:
        for path in bundle_export._leaf_paths(member, (), frozenset(), frozenset()):
            assert bundle_export.lookup_doc(
                comparison.COMPARISON_RECORD_FIELDS, path
            ), path


_RECORD_DEFINITIONS = {
    "family": comparison.FAMILY_RECORD_FIELDS,
    "comparison": comparison.COMPARISON_RECORD_FIELDS,
    "leader_set": leader_set.LEADER_SET_RECORD_FIELDS,
    "subject": leader_set.SUBJECT_RECORD_FIELDS,
}


def _disagreements(dictionary: list[dict[str, str]]) -> list[str]:
    """Record columns whose dictionary entry differs from the record definition."""
    columns = _record_columns(dictionary)
    wrong: list[str] = []
    for entry in dictionary:
        if entry["table"] != "comparison_records" or entry["column"] not in columns:
            continue
        part, *path = columns[entry["column"]]
        definition = bundle_export.lookup_doc(_RECORD_DEFINITIONS[part], tuple(path))
        module = "comparison.py" if part in ("family", "comparison") else "leader_set"
        if (
            definition is None
            or entry["meaning"] != definition.meaning
            or entry["unit"] != definition.unit
            or (definition.empty or "Otherwise the record holds null.")
            not in entry["empty_cell"]
            or module not in entry["owner"]
            or "a-score-is-published-with-its-interval" not in entry["owner"]
        ):
            wrong.append(entry["column"])
    return wrong


def test_record_columns_state_the_record_definitions(tmp_path: Path) -> None:
    paths, _ = _constructed_records_bundle(tmp_path)
    dictionary = [
        dict(zip(bundle_export.DICTIONARY_HEADER, entry, strict=True))
        for entry in bundle_export.build_export(paths)[DICTIONARY_FILE][1:]
    ]
    columns = _record_columns(dictionary)

    assert {part for part, *_ in columns.values()} == set(_RECORD_DEFINITIONS)
    assert _disagreements(dictionary) == []
    # A null reason is stated beside the row-kind case, not in place of it.
    entry = next(e for e in dictionary if e["column"] == "comparison_result_p_value")
    assert entry["empty_cell"].startswith("Not a comparison row")
    assert "p_value_null_reason" in entry["empty_cell"]
    # An entry redefined in the export would be caught, whichever cell moved.
    for cell in ("meaning", "unit", "empty_cell", "owner"):
        altered = [dict(e) for e in dictionary]
        target = next(e for e in altered if e["column"] == "comparison_verdict")
        target[cell] = "redefined in the export"
        assert _disagreements(altered) == ["comparison_verdict"], cell


def test_the_export_reads_the_record_definitions_it_does_not_redefine() -> None:
    sources = bundle_export._record_row("comparison", "f.json")[1:]
    assert all(
        source.registry is registry
        for source, registry in zip(sources, _RECORD_DEFINITIONS.values(), strict=True)
    )


def _named(module: object, prefix: str) -> set[str]:
    return {
        value
        for name, value in vars(module).items()
        if name.startswith(prefix) and isinstance(value, str)
    }


@pytest.mark.parametrize(
    ("registry", "path", "values"),
    [
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("refusal",),
            _named(comparison, "REFUSAL_"),
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("comparison_kind",),
            _named(comparison, "KIND_"),
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("verdict",),
            _named(comparison, "VERDICT_") - {comparison.VERDICT_RULE},
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("result", "direction"),
            _named(comparison, "DIRECTION_"),
        ),
        (comparison.COMPARISON_RECORD_FIELDS, ("test",), _named(comparison, "TEST_")),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("scoring_kind",),
            _named(comparison, "SCORING_KIND_"),
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("result", "p_value_null_reason"),
            {
                comparison.NULL_PAIRED_N_BELOW_MINIMUM,
                comparison.NULL_NO_DISCORDANT_PAIRS,
                comparison.NULL_ALL_DIFFERENCES_ZERO,
            },
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("result", "effect_size_null_reason"),
            {
                comparison.NULL_PAIRED_N_BELOW_MINIMUM,
                comparison.NULL_ODDS_RATIO_EMPTY_CELL,
                comparison.NULL_ALL_DIFFERENCES_ZERO,
            },
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("adjusted_p_value_null_reason",),
            {comparison.NULL_COMPARISON_REFUSED, comparison.NULL_NO_PAIRED_TEST},
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("batch_values", "difference_null_reason"),
            {comparison.NULL_NO_SINGLE_BATCH_VALUE},
        ),
        (
            comparison.COMPARISON_RECORD_FIELDS,
            ("compared_quantity",),
            set(comparison.QUANTITIES) - {comparison.QUANTITY_SCORE},
        ),
        (
            leader_set.SUBJECT_RECORD_FIELDS,
            ("status",),
            _named(leader_set, "STATUS_"),
        ),
        (leader_set.SUBJECT_RECORD_FIELDS, ("role",), _named(leader_set, "ROLE_")),
    ],
)
def test_every_value_a_record_field_takes_is_named_in_its_definition(
    registry: dict[tuple[str, ...], FieldDoc],
    path: tuple[str, ...],
    values: set[str],
) -> None:
    assert values
    meaning = registry[path].meaning
    assert not [value for value in values if value not in meaning]


def test_every_null_reason_the_analysis_writes_is_defined() -> None:
    reasons = _named(comparison, "NULL_")
    defined = " ".join(
        doc.meaning
        for path, doc in comparison.COMPARISON_RECORD_FIELDS.items()
        if path[-1].endswith("null_reason")
    )
    assert not [reason for reason in reasons if reason not in defined]


def test_a_bundle_without_record_directories_holds_no_record(tmp_path: Path) -> None:
    paths = _replace(
        _bundle(tmp_path),
        comparisons_dir=tmp_path / "no-comparisons",
        leader_sets_dir=tmp_path / "no-leader-sets",
    )
    output_dir = tmp_path / "out"
    bundle_export.export_bundle(paths, output_dir)

    assert _header(output_dir / "comparison_records.csv") == [NOT_CARRIED_COLUMN]
    assert not _read_csv(output_dir / "comparison_records.csv")
    assert {
        entry["column"]
        for entry in _read_csv(output_dir / DICTIONARY_FILE)
        if entry["table"] == "comparison_records" and entry["carried"] == "false"
    } == {"comparison_family records", "comparison records", "leader_set records"}
    manifest = {row["part"]: row for row in _read_csv(output_dir / MANIFEST_FILE)}
    for part, directory in (
        ("comparison_families", paths.comparisons_dir),
        ("leader_sets", paths.leader_sets_dir),
    ):
        assert manifest[part]["path"] == directory.as_posix()
        assert manifest[part]["entries_read"] == "0"
    assert not paths.comparisons_dir.exists()


@pytest.mark.parametrize(
    ("kind", "key", "value", "expected"),
    [
        ("family", "members", {"not": "a list"}, "`members` is not a list"),
        ("family", "members", ["not an object"], "`members` is not a list"),
        ("family", "supersedes", "not-a-list", "`supersedes` is not a list"),
        ("family", "family_id", None, "`family_id` is not an id"),
        ("family", "members", [{"reference_run_id": ["x"]}], "reference_run_id"),
        ("leader", "subjects", [1], "`subjects` is not a list"),
        ("leader", "supersedes", [None], "`supersedes` is not a list"),
        ("leader", "leader_set_id", 7, "`leader_set_id` is not an id"),
        ("leader", "family_id", {"id": 1}, "family_id"),
    ],
)
def test_a_malformed_record_is_refused_by_name(
    tmp_path: Path, kind: str, key: str, value: object, expected: str
) -> None:
    paths, _ = _constructed_records_bundle(tmp_path)
    directory = paths.comparisons_dir if kind == "family" else paths.leader_sets_dir
    target = min(directory.glob("*.json"))
    record = json.loads(target.read_text(encoding="utf-8"))
    record[key] = value
    target.write_text(json.dumps(record), encoding="utf-8")

    with pytest.raises(ExportError, match=f"record {target.name}: .*{expected}"):
        bundle_export.build_export(paths)


def test_a_row_carrying_its_interval_exports_every_cell_described(
    tmp_path: Path,
) -> None:
    first, second, third = _committed_rows(COMMITTED.quality_rows)[:3]
    items = [{"item_id": f"i{index}", "language": "en"} for index in range(20)]
    block = score_interval.interval_block(items, [1.0] * 16 + [0.0] * 4)
    first["score_interval"] = block
    # A partial batch records the block as null; a row written before schema
    # "21" (the committed rows) does not carry it at all.
    second["score_interval"] = None
    assert "score_interval" not in third

    bundle_export.export_bundle(
        _bundle(tmp_path, quality=[first, second, third]), tmp_path / "out"
    )
    rows = _read_csv(tmp_path / "out" / "quality_items.csv")
    dictionary = {
        entry["column"]: entry
        for entry in _read_csv(tmp_path / "out" / DICTIONARY_FILE)
        if entry["table"] == "quality_items"
    }
    interval_columns = [c for c in rows[0] if c.startswith("score_interval_")]

    for column in (
        "score_interval_seed",
        "score_interval_generator_library",
        "score_interval_draw_procedure_id",
        "score_interval_suite_lower",
        "score_interval_suite_minimum_detectable_effect",
        "score_interval_by_language_en_upper",
        "score_interval_by_language_de_null_reason",
    ):
        assert column in dictionary, column
    assert float(rows[0]["score_interval_suite_lower"]) == block["suite"]["lower"]
    assert rows[0]["score_interval_by_language_de_null_reason"] == "no_items"
    assert json.loads(rows[0][NOT_CARRIED_COLUMN]) == []
    # Empty, never zero, on both interval-less rows; only the row that does
    # not carry the field lists its columns as not carried.
    for row in rows[1:]:
        assert {row[column] for column in interval_columns} == {""}
    assert not set(interval_columns) & set(json.loads(rows[1][NOT_CARRIED_COLUMN]))
    assert set(interval_columns) <= set(json.loads(rows[2][NOT_CARRIED_COLUMN]))
    for column in interval_columns:
        empty_cell = dictionary[column]["empty_cell"]
        assert "before schema 21" in empty_cell, column
        assert "never back-filled" in empty_cell.lower(), column
    # The block is carried, so nothing in the dictionary calls it absent.
    assert not [
        entry
        for entry in dictionary.values()
        if entry["carried"] == "false" and "interval" in entry["column"]
    ]


def test_the_interval_columns_agree_with_the_block_they_describe() -> None:
    registry = bundle_export.ROW_FIELDS
    paths = [
        *((key,) for key in score_interval.HEADER_KEYS - {"generator"}),
        *(("generator", key) for key in score_interval.GENERATOR_KEYS),
        *(("suite", key) for key in score_interval.CELL_KEYS),
        *(("by_language", "en", key) for key in score_interval.CELL_KEYS),
    ]

    for path in paths:
        assert bundle_export.lookup_doc(registry, ("score_interval", *path)), path
    assert str(score_interval.CONFIDENCE_LEVEL) in (
        registry[("score_interval", "confidence_level")].meaning
    )
    assert str(score_interval.RESAMPLES) in (
        registry[("score_interval", "resamples")].meaning
    )
    assert score_interval.METHOD_PERCENTILE in (
        registry[("score_interval", "method")].meaning
    )
    assert score_interval.DRAW_PROCEDURE_ID in (
        registry[("score_interval", "draw_procedure_id")].meaning
    )
    for cell in (("suite",), ("by_language", "en")):
        doc = bundle_export.lookup_doc(
            registry, ("score_interval", *cell, "null_reason")
        )
        assert doc is not None
        assert not [
            reason
            for reason in score_interval.NULL_REASONS
            if reason not in doc.meaning
        ]
