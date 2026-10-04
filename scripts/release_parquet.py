"""Typed Parquet copies of the release tables, and the check that they equal the CSV.

The CSV tables are the contract; Parquet is a release-time convenience for a
reader loading them into a dataframe or a columnar engine. This module writes
one Parquet file per table and reads each back to compare it with its CSV cell
by cell, under the type the column dictionary gives each column:

- a column's type comes from its dictionary `unit` through `UNIT_KINDS`; a
  unit missing from that table fails the build rather than ship a column
  silently mistyped;
- every empty CSV cell is a Parquet null, whatever the type;
- the check does not trust the writer: it requires the same columns in the
  same order, each with the dictionary's Arrow type, the same row count, and
  each cell equal to the CSV cell parsed under that type.

`pyarrow` is imported only inside the functions that need it: it is installed
by the `release-build` job alone (the `release` dependency group), never by the test
matrix nor the published image. `scripts/assemble_release_archive.py
--parquet` is the one caller.
"""

from __future__ import annotations

import csv
import io
import math
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from typing import Any

from wave_local_ai_v2 import bundle_export

BOOLEAN = "boolean"
INTEGER = "integer"
FLOAT = "float"
DATE = "date"
TIMESTAMP = "timestamp"
STRING = "string"

# Every unit the column dictionary states, and the Parquet type its column
# takes. A new unit fails the build until it is typed here.
UNIT_KINDS: Mapping[str, str] = {
    "boolean": BOOLEAN,
    "count": INTEGER,
    "integer": INTEGER,
    "tokens": INTEGER,
    "parameters": INTEGER,
    "bytes": INTEGER,
    "number": FLOAT,
    "ratio": FLOAT,
    "ratio, 0..1": FLOAT,
    "probability, 0..1": FLOAT,
    "score": FLOAT,
    "score points": FLOAT,
    "the suite's score scale (suite_accuracy or suite_score, 0..1)": FLOAT,
    "as agreement_statistic states": FLOAT,
    "seconds": FLOAT,
    "milliseconds": FLOAT,
    "tokens per second": FLOAT,
    "watts": FLOAT,
    "kWh": FLOAT,
    "kg CO2e": FLOAT,
    "kg CO2e per kWh": FLOAT,
    "EUR per kWh": FLOAT,
    "currency (cost_currency)": FLOAT,
    "currency per million tokens": FLOAT,
    "GB": FLOAT,
    "GB (10^9 bytes)": FLOAT,
    # A cpu_only row's VRAM is the identifier `not_applicable`, never a number
    # and never empty (empty is a failed read on a gpu row): a string column
    # keeps the three apart, where a float column would fold it into null.
    bundle_export.VRAM_UNIT: STRING,
    "billions of parameters": FLOAT,
    "date, YYYY-MM-DD": DATE,
    "ISO 8601 date": DATE,
    "ISO 8601 timestamp, UTC offset": TIMESTAMP,
    "identifier": STRING,
    "text": STRING,
    "path": STRING,
    "URL": STRING,
    "URL or path": STRING,
    "SHA-256, lowercase hex": STRING,
    "git SHA-1, hex": STRING,
    "ISO 4217 code": STRING,
    "ISO 639-1 code": STRING,
    "SPDX licence identifier": STRING,
    "JSON array": STRING,
    "JSON object": STRING,
    "JSON object, or the identifier none": STRING,
    "JSON array of column names, in column order": STRING,
    "JSON array of language codes; [] when the card names none of the three": (STRING),
    # Fiche fields of every shape (CPU name, RAM in GB) share one column.
    "as the fiche field": STRING,
}

COMPRESSION = "snappy"
MAX_CELLS_REPORTED = 10
_INTEGER_RE = re.compile(r"^-?\d+$")
_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


class ParquetError(Exception):
    """A table cannot be typed, written or read back."""


def parquet_name(table: str) -> str:
    return f"{table}.parquet"


def pyarrow_version() -> str:
    import pyarrow

    return str(pyarrow.__version__)


# --------------------------------------------------------------------------
# The CSV side: rows, the dictionary's types, a cell parsed under its type.
# --------------------------------------------------------------------------


def read_csv(data: bytes, name: str) -> tuple[list[str], list[list[str]]]:
    rows = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
    if not rows:
        raise ParquetError(f"{name} has no header")
    header, body = rows[0], rows[1:]
    ragged = [i + 1 for i, row in enumerate(body) if len(row) != len(header)]
    if ragged:
        raise ParquetError(f"{name} rows {ragged} do not have {len(header)} cells")
    return header, body


def column_kinds(table: str, header: Sequence[str], dictionary: bytes) -> list[str]:
    """Each column's kind, from the unit `column_dictionary.csv` gives it."""
    dictionary_header, rows = read_csv(dictionary, bundle_export.DICTIONARY_FILE)
    at = {name: i for i, name in enumerate(dictionary_header)}
    units = {
        row[at["column"]]: row[at["unit"]] for row in rows if row[at["table"]] == table
    }
    kinds = []
    for column in header:
        if column not in units:
            raise ParquetError(f"{table}.{column} has no column dictionary entry")
        kind = UNIT_KINDS.get(units[column])
        if kind is None:
            raise ParquetError(
                f"{table}.{column}: unit {units[column]!r} has no Parquet type "
                "(add it to UNIT_KINDS)"
            )
        kinds.append(kind)
    return kinds


def parse_cell(kind: str, text: str, where: str) -> Any:
    """The CSV cell as a value of its kind; an empty cell is None. Timestamps
    must carry the +00:00 offset and become UTC microseconds since the epoch,
    so no time-zone database is read."""
    if text == "":
        return None
    try:
        if kind == BOOLEAN:
            return {"true": True, "false": False}[text]
        if kind == INTEGER:
            if not _INTEGER_RE.match(text):
                raise ValueError(text)
            return int(text)
        if kind == FLOAT:
            return float(text)
        if kind == DATE:
            return date.fromisoformat(text)
        if kind == TIMESTAMP:
            moment = datetime.fromisoformat(text)
            # The dictionary's unit is a UTC timestamp: a missing or non-zero
            # offset is a CSV the Parquet copy could only silently normalize.
            if moment.utcoffset() != timedelta(0):
                raise ValueError(f"{text} is not at UTC offset +00:00")
            return (moment - _EPOCH) // timedelta(microseconds=1)
    except (KeyError, ValueError) as error:
        raise ParquetError(f"{where}: {text!r} is not a {kind}") from error
    return text


def _same(expected: Any, actual: Any) -> bool:
    if isinstance(expected, float) and isinstance(actual, float):
        return expected == actual or (math.isnan(expected) and math.isnan(actual))
    return type(expected) is type(actual) and expected == actual


# --------------------------------------------------------------------------
# The Parquet side.
# --------------------------------------------------------------------------


def _arrow_type(kind: str) -> Any:
    import pyarrow as pa

    return {
        BOOLEAN: pa.bool_(),
        INTEGER: pa.int64(),
        FLOAT: pa.float64(),
        DATE: pa.date32(),
        TIMESTAMP: pa.timestamp("us", tz="UTC"),
        STRING: pa.string(),
    }[kind]


def write_parquet(table: str, data: bytes, dictionary: bytes) -> bytes:
    """`table`'s CSV as Parquet, each column typed from the dictionary."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    name = f"{table}.csv"
    header, rows = read_csv(data, name)
    kinds = column_kinds(table, header, dictionary)
    arrays = []
    for i, (column, kind) in enumerate(zip(header, kinds, strict=True)):
        values = [parse_cell(kind, row[i], f"{name} {column}") for row in rows]
        raw_type = pa.int64() if kind == TIMESTAMP else _arrow_type(kind)
        arrays.append(pa.array(values, type=raw_type).cast(_arrow_type(kind)))
    schema = pa.schema(
        [pa.field(c, _arrow_type(k)) for c, k in zip(header, kinds, strict=True)]
    )
    sink = pa.BufferOutputStream()
    pq.write_table(
        pa.Table.from_arrays(arrays, schema=schema), sink, compression=COMPRESSION
    )
    return bytes(sink.getvalue().to_pybytes())


def check_parquet(
    table: str, data: bytes, parquet: bytes, dictionary: bytes
) -> list[str]:
    """Every way `parquet` is not `table`'s CSV under the dictionary's types."""
    import pyarrow as pa
    import pyarrow.parquet as pq

    name = parquet_name(table)
    header, rows = read_csv(data, f"{table}.csv")
    kinds = column_kinds(table, header, dictionary)
    try:
        read = pq.read_table(pa.BufferReader(parquet))
    except (pa.ArrowException, OSError) as error:
        return [f"{name} is not readable Parquet: {error}"]
    if read.column_names != header:
        return [f"{name} columns {read.column_names} are not the CSV's {header}"]
    problems = [
        f"{name} column {column} is {read.schema.field(column).type}, "
        f"the dictionary types it {_arrow_type(kind)}"
        for column, kind in zip(header, kinds, strict=True)
        if read.schema.field(column).type != _arrow_type(kind)
    ]
    if read.num_rows != len(rows):
        problems.append(f"{name} has {read.num_rows} rows, the CSV {len(rows)}")
    if problems:
        return problems
    cells = []
    for i, (column, kind) in enumerate(zip(header, kinds, strict=True)):
        stored = read.column(column)
        if kind == TIMESTAMP:
            stored = stored.cast(pa.int64())
        for r, (row, actual) in enumerate(zip(rows, stored.to_pylist(), strict=True)):
            expected = parse_cell(kind, row[i], f"{table}.csv {column}")
            if not _same(expected, actual):
                cells.append(
                    f"{name} row {r + 1} column {column} holds {actual!r}, "
                    f"the CSV {row[i]!r}"
                )
    if len(cells) > MAX_CELLS_REPORTED:
        extra = len(cells) - MAX_CELLS_REPORTED
        cells = [*cells[:MAX_CELLS_REPORTED], f"{name}: {extra} more cell(s) differ"]
    return cells


# --------------------------------------------------------------------------
# All tables at once, as the archive script uses them.
# --------------------------------------------------------------------------


def build_copies(files: Mapping[str, bytes]) -> dict[str, bytes]:
    """One Parquet file per table in `files` (the export, by file name)."""
    dictionary = files[bundle_export.DICTIONARY_FILE]
    return {
        parquet_name(table): write_parquet(table, files[f"{table}.csv"], dictionary)
        for table in bundle_export.TABLES
    }


def compare_copies(files: Mapping[str, bytes]) -> tuple[list[str], list[str]]:
    """Check each table's Parquet copy in `files` against its CSV: the problems
    found, and one line per table compared and equal."""
    dictionary = files[bundle_export.DICTIONARY_FILE]
    problems: list[str] = []
    compared: list[str] = []
    for table in bundle_export.TABLES:
        csv_name, name = f"{table}.csv", parquet_name(table)
        if csv_name not in files or name not in files:
            problems.append(f"{name} has no {csv_name} to compare with, or is missing")
            continue
        try:
            found = check_parquet(table, files[csv_name], files[name], dictionary)
        except ParquetError as error:
            found = [str(error)]
        if found:
            problems += found
            continue
        header, rows = read_csv(files[csv_name], csv_name)
        compared.append(
            f"{name}: {len(rows)} rows x {len(header)} columns compared with "
            f"{csv_name} cell by cell under the dictionary's types: equal"
        )
    return problems, compared
