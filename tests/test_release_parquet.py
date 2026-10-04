"""The Parquet copies of the release tables, and the check that they equal the CSV.

The typing rules run everywhere. The tests that write and read Parquet need
`pyarrow`, which only the `release-build` job installs (the `release`
dependency group): they skip in the test matrix, and that job runs this file.
"""

from __future__ import annotations

import csv
import io
import re
import sys
from datetime import date
from pathlib import Path
from typing import Any

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import assemble_release_archive as release
import release_parquet as rp

from wave_local_ai_v2 import build_info, bundle_export, row_contract

REPO = release.REPO_ROOT
TAG = f"v{build_info.version()}"
TOP = release.archive_name(build_info.version())


@pytest.fixture(scope="module")
def exports() -> dict[str, bytes]:
    return release.export_files(REPO)


@pytest.fixture(scope="module")
def pa() -> Any:
    return pytest.importorskip("pyarrow")


@pytest.fixture(scope="module")
def copies(pa: Any, exports: dict[str, bytes]) -> dict[str, bytes]:
    return rp.build_copies(exports)


def _rows(data: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))


def _dictionary(*rows: tuple[str, str, str]) -> bytes:
    lines = ["table,column,unit", *(",".join(row) for row in rows)]
    return "\r\n".join(lines).encode("utf-8") + b"\r\n"


# --------------------------------------------------------------------------
# Typing, without pyarrow.
# --------------------------------------------------------------------------


def test_every_unit_the_dictionary_states_has_a_parquet_type(
    exports: dict[str, bytes],
) -> None:
    # A new unit fails the release build; this catches it on every pull
    # request, long before a tag. A record kind the bundle does not hold is
    # named on a row stating no unit (it is no column); a table column
    # stating none fails `test_every_table_column_is_typed` below.
    header, *rows = _rows(exports[bundle_export.DICTIONARY_FILE])
    units = {row[header.index("unit")] for row in rows} - {""}
    assert sorted(units - set(rp.UNIT_KINDS)) == []


def test_every_table_column_is_typed(exports: dict[str, bytes]) -> None:
    dictionary = exports[bundle_export.DICTIONARY_FILE]
    for table in bundle_export.TABLES:
        header = _rows(exports[f"{table}.csv"])[0]
        assert len(rp.column_kinds(table, header, dictionary)) == len(header)


def test_a_cpu_only_vram_cell_keeps_its_identifier_apart_from_a_failed_read(
    exports: dict[str, bytes],
) -> None:
    # The committed bundle holds cpu_only rows: their VRAM column is typed so
    # `not_applicable` stays itself, a number stays its text, and only an
    # empty cell (a failed read) becomes a null.
    table = "runtime_aggregates"
    header, *rows = _rows(exports[f"{table}.csv"])
    kinds = rp.column_kinds(table, header, exports[bundle_export.DICTIONARY_FILE])
    at = header.index("vram_used_mib")
    assert kinds[at] == rp.STRING
    cells = {row[at] for row in rows}
    assert row_contract.VRAM_NOT_APPLICABLE in cells
    for cell in cells:
        parsed = rp.parse_cell(kinds[at], cell, "vram_used_mib")
        assert parsed == (cell or None)
    assert rp.parse_cell(kinds[at], "", "vram_used_mib") is None


def test_a_column_without_an_entry_or_with_an_untyped_unit_is_refused() -> None:
    dictionary = _dictionary(("t", "a", "count"), ("t", "b", "furlongs"))
    with pytest.raises(rp.ParquetError, match=r"t\.c has no column dictionary"):
        rp.column_kinds("t", ["a", "c"], dictionary)
    with pytest.raises(rp.ParquetError, match="unit 'furlongs' has no Parquet type"):
        rp.column_kinds("t", ["a", "b"], dictionary)
    assert rp.column_kinds("t", ["a"], dictionary) == [rp.INTEGER]


@pytest.mark.parametrize(
    ("kind", "text", "value"),
    [
        (rp.BOOLEAN, "true", True),
        (rp.BOOLEAN, "false", False),
        (rp.INTEGER, "-12", -12),
        (rp.FLOAT, "0.000414", 0.000414),
        (rp.DATE, "2026-10-02", date(2026, 10, 2)),
        (rp.TIMESTAMP, "1970-01-01T00:00:00.000001+00:00", 1),
        (rp.STRING, "x", "x"),
    ],
)
def test_a_cell_parses_under_its_kind(kind: str, text: str, value: object) -> None:
    assert rp.parse_cell(kind, text, "w") == value
    assert rp.parse_cell(kind, "", "w") is None


@pytest.mark.parametrize(
    ("kind", "text"),
    [
        (rp.BOOLEAN, "True"),
        (rp.INTEGER, "1.0"),
        (rp.FLOAT, "one"),
        (rp.DATE, "02/10/2026"),
        (rp.TIMESTAMP, "2026-10-02T00:00:00"),
        (rp.TIMESTAMP, "2026-10-02T02:00:00+02:00"),
    ],
)
def test_a_cell_that_is_not_its_kind_is_refused(kind: str, text: str) -> None:
    with pytest.raises(
        rp.ParquetError, match=re.escape(f"w: {text!r} is not a {kind}")
    ):
        rp.parse_cell(kind, text, "w")


def test_a_csv_without_header_or_with_a_ragged_row_is_refused() -> None:
    with pytest.raises(rp.ParquetError, match="has no header"):
        rp.read_csv(b"", "t.csv")
    with pytest.raises(rp.ParquetError, match=r"rows \[2\] do not have 2 cells"):
        rp.read_csv(b"a,b\r\n1,2\r\n3\r\n", "t.csv")


# --------------------------------------------------------------------------
# Writing and checking, where pyarrow is available.
# --------------------------------------------------------------------------


def _rewrite(pa: Any, parquet: bytes, column: str, row: int, value: object) -> bytes:
    """`parquet` with one cell replaced, every type kept."""
    import pyarrow.parquet as pq

    table = pq.read_table(pa.BufferReader(parquet))
    i = table.column_names.index(column)
    values = table.column(i).to_pylist()
    values[row] = value
    field = table.schema.field(i)
    table = table.set_column(i, field, pa.array(values, type=field.type))
    sink = pa.BufferOutputStream()
    pq.write_table(table, sink)
    return bytes(sink.getvalue().to_pybytes())


FILLERS: dict[str, object] = {
    rp.BOOLEAN: True,
    rp.INTEGER: 0,
    rp.FLOAT: 0.0,
    rp.STRING: "",
}


def _empty_cell(data: bytes, kinds: list[str]) -> tuple[str, int, object]:
    """The first column and row where the CSV holds an empty cell, and a
    non-null value of that column's type."""
    header, *rows = _rows(data)
    for r, row in enumerate(rows):
        for column, kind, text in zip(header, kinds, row, strict=True):
            if text == "" and kind in FILLERS:
                return column, r, FILLERS[kind]
    raise AssertionError("no empty cell")


def test_every_copy_equals_its_csv(
    exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    problems, compared = rp.compare_copies({**exports, **copies})
    assert problems == []
    assert [line.split(":")[0] for line in compared] == [
        rp.parquet_name(table) for table in bundle_export.TABLES
    ]
    assert all(line.endswith("equal") for line in compared)


def test_two_writes_are_byte_identical(
    exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    assert rp.build_copies(exports) == copies


def test_one_altered_cell_fails_the_check(
    pa: Any, exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    name = rp.parquet_name(bundle_export.QUALITY_TABLE)
    altered = _rewrite(pa, copies[name], "run_id", 0, "tampered")
    problems, compared = rp.compare_copies({**exports, **copies, name: altered})
    header, first = _rows(exports["quality_items.csv"])[:2]
    held = first[header.index("run_id")]
    assert problems == [
        f"{name} row 1 column run_id holds 'tampered', the CSV {held!r}"
    ]
    assert len(compared) == len(bundle_export.TABLES) - 1


def test_a_value_where_the_csv_is_empty_fails_the_check(
    pa: Any, exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    table = bundle_export.RUNTIME_TABLE
    data = exports[f"{table}.csv"]
    kinds = rp.column_kinds(
        table, _rows(data)[0], exports[bundle_export.DICTIONARY_FILE]
    )
    column, row, filler = _empty_cell(data, kinds)
    name = rp.parquet_name(table)
    altered = _rewrite(pa, copies[name], column, row, filler)
    problems, _ = rp.compare_copies({**exports, **copies, name: altered})
    assert problems == [
        f"{name} row {row + 1} column {column} holds {filler!r}, the CSV ''"
    ]


def test_many_altered_cells_are_reported_up_to_a_cap(
    pa: Any, exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    name = rp.parquet_name(bundle_export.QUALITY_TABLE)
    altered = copies[name]
    for row in range(rp.MAX_CELLS_REPORTED + 2):
        altered = _rewrite(pa, altered, "run_id", row, f"tampered-{row}")
    problems, _ = rp.compare_copies({**exports, **copies, name: altered})
    assert len(problems) == rp.MAX_CELLS_REPORTED + 1
    assert problems[-1] == f"{name}: 2 more cell(s) differ"


def test_a_wrong_type_a_missing_row_or_other_columns_fail(
    pa: Any, exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    import pyarrow.parquet as pq

    name = rp.parquet_name(bundle_export.FICHE_TABLE)
    table = pq.read_table(pa.BufferReader(copies[name]))

    def written(changed: Any) -> bytes:
        sink = pa.BufferOutputStream()
        pq.write_table(changed, sink)
        return bytes(sink.getvalue().to_pybytes())

    as_text = table.cast(pa.schema([(f.name, pa.string()) for f in table.schema]))
    typed = [f.name for f in table.schema if f.type != pa.string()]
    problems = rp.check_parquet(
        bundle_export.FICHE_TABLE,
        exports["fiches.csv"],
        written(as_text),
        exports[bundle_export.DICTIONARY_FILE],
    )
    assert problems and len(problems) == len(typed)
    assert f"column {typed[0]} is string" in problems[0]

    problems = rp.check_parquet(
        bundle_export.FICHE_TABLE,
        exports["fiches.csv"],
        written(table.slice(1)),
        exports[bundle_export.DICTIONARY_FILE],
    )
    assert problems == [
        f"{name} has {table.num_rows - 1} rows, the CSV {table.num_rows}"
    ]

    problems = rp.check_parquet(
        bundle_export.FICHE_TABLE,
        exports["fiches.csv"],
        written(table.drop_columns([table.column_names[0]])),
        exports[bundle_export.DICTIONARY_FILE],
    )
    assert problems[0].startswith(f"{name} columns ")


def test_an_unreadable_or_missing_copy_fails(
    exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    name = rp.parquet_name(bundle_export.ROSTER_TABLE)
    problems, _ = rp.compare_copies({**exports, **copies, name: b"not parquet"})
    assert len(problems) == 1
    assert problems[0].startswith(f"{name} is not readable Parquet")

    missing = {**exports, **copies}
    del missing[name]
    problems, _ = rp.compare_copies(missing)
    assert problems == [f"{name} has no roster.csv to compare with, or is missing"]


def test_a_csv_cell_off_its_type_is_reported_not_raised(
    exports: dict[str, bytes], copies: dict[str, bytes]
) -> None:
    table = bundle_export.FICHE_TABLE
    rows = _rows(exports[f"{table}.csv"])
    kinds = rp.column_kinds(table, rows[0], exports[bundle_export.DICTIONARY_FILE])
    i = next(i for i, kind in enumerate(kinds) if kind in (rp.INTEGER, rp.FLOAT))
    rows[1][i] = "not a number"
    sink = io.StringIO(newline="")
    csv.writer(sink, lineterminator="\r\n").writerows(rows)
    edited = {**exports, **copies, f"{table}.csv": sink.getvalue().encode("utf-8")}
    problems, _ = rp.compare_copies(edited)
    assert problems == [f"fiches.csv {rows[0][i]}: 'not a number' is not a {kinds[i]}"]


# --------------------------------------------------------------------------
# The archive with its Parquet copies.
# --------------------------------------------------------------------------


@pytest.fixture(scope="module")
def commit() -> str:
    sha = release.head_commit(REPO)
    if sha is None:
        pytest.skip("git cannot name the checked-out commit")
    return sha


@pytest.fixture(scope="module")
def parquet_archive(
    pa: Any, commit: str, tmp_path_factory: pytest.TempPathFactory
) -> tuple[Path, list[str]]:
    return release.build(TAG, commit, tmp_path_factory.mktemp("dist"), parquet=True)


def test_the_archive_ships_one_copy_per_table_and_says_the_csv_is_right(
    parquet_archive: tuple[Path, list[str]],
) -> None:
    path, compared = parquet_archive
    files = release.read_zip(path, TOP)
    assert sorted(n for n in files if n.endswith(".parquet")) == sorted(
        rp.parquet_name(table) for table in bundle_export.TABLES
    )
    assert len(compared) == len(bundle_export.TABLES)
    readme = files["README.md"].decode("utf-8")
    assert "## Parquet copies" in readme
    assert "wherever the two could disagree, the CSV is right" in readme
    assert f"written with pyarrow {rp.pyarrow_version()}." in readme


def test_an_archive_with_an_altered_copy_fails_verify(
    pa: Any, parquet_archive: tuple[Path, list[str]], commit: str, tmp_path: Path
) -> None:
    path, _ = parquet_archive
    files = release.read_zip(path, TOP)
    name = rp.parquet_name(bundle_export.QUALITY_TABLE)
    files[name] = _rewrite(pa, files[name], "run_id", 0, "tampered")
    edited = tmp_path / f"{TOP}.zip"
    release.write_zip(edited, TOP, files)
    with pytest.raises(release.ArchiveError) as refused:
        release.verify(edited, TAG, commit, parquet=True)
    assert f"file {name} differs" in str(refused.value)
    assert f"{name} row 1 column run_id holds 'tampered'" in str(refused.value)


def test_the_command_prints_every_table_compared(
    pa: Any, commit: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = ["--tag", TAG, "--commit", commit, "--parquet"]
    assert release.main(["build", *argv, "--output-dir", str(tmp_path)]) == 0
    assert release.main(["verify", *argv, str(tmp_path / f"{TOP}.zip")]) == 0
    out = capsys.readouterr().out
    for table in bundle_export.TABLES:
        assert out.count(f"{rp.parquet_name(table)}: ") == 2
    assert "built and verified" in out
