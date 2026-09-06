"""Append-only JSONL results store for runtime rows."""

from __future__ import annotations

import json
import uuid
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import row_contract
from wave_local_ai_v2.row_contract import RowKind

# The three reasons a stored line is reported rather than rendered. Finite and
# named, like `row_contract`'s own reason strings: a reader meeting an
# `unreadable` entry never has to guess which of several conditions produced
# it, and no fourth reason can be invented at a call site.
UNREADABLE_BELOW_FLOOR = "below_schema_floor"
# The line cannot be *placed* relative to the floor: it carries no
# `schema_version` key at all, or carries one that is not a decimal integer.
# Both are the same fact to a reader -- there is no version to compare -- and
# the entry keeps whatever the line actually held, so "no comparable version"
# never has to be taken on trust.
UNREADABLE_NO_SCHEMA_VERSION = "no_comparable_schema_version"
UNREADABLE_UNPARSABLE_LINE = "unparsable_line"
UNREADABLE_REASONS: frozenset[str] = frozenset(
    {
        UNREADABLE_BELOW_FLOOR,
        UNREADABLE_NO_SCHEMA_VERSION,
        UNREADABLE_UNPARSABLE_LINE,
    }
)


@dataclass(frozen=True)
class UnreadableRows:
    """How many stored lines one `(schema_version, reason)` pair accounts for.

    `schema_version` is `None` when the line carries none -- never coerced to
    a version it does not claim.
    """

    schema_version: str | None
    count: int
    reason: str


@dataclass(frozen=True)
class StoreRead:
    """One read of a store: the rows a reader may render, and what it may not.

    The two halves are the whole point: a line below the floor, carrying no
    version, or not parsable as JSON is *reported*, not filtered away, so a
    view built on this can name an absence instead of showing a shorter table
    than the file holds.
    """

    rows: list[dict[str, Any]]
    unreadable: list[UnreadableRows]


def new_run_id() -> str:
    """Return a fresh identifier for one CLI invocation.

    Every row a run writes carries this id, so the rows of one session can be
    selected back out of an append-only store. Without it two runs of the same
    model against the same store are indistinguishable.
    """
    return uuid.uuid4().hex


def captured_at() -> str:
    """Return the current UTC instant as an ISO-8601 string.

    Paired with `new_run_id`: the id says which run wrote a row, this says when.
    UTC, not local time, so rows written on two machines stay orderable.
    """
    return datetime.now(UTC).isoformat()


def append_row(path: Path, kind: RowKind, row: dict[str, Any]) -> None:
    """Append one row as a JSON line, creating parent directories if needed.

    Gated on `row_contract.validate_row`: an incomplete row raises
    `RowContractError` and nothing is written -- no partial line, no empty
    file created if `path` didn't already exist.
    """
    row_contract.validate_row(kind, row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def read_rows(path: Path, schema_version: str | None = None) -> list[dict[str, Any]]:
    """Read all rows back from the results store. Returns an empty list if absent.

    With `schema_version` given, only rows whose `schema_version` field equals
    it are returned -- rows of several versions can coexist in one store.
    """
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    if schema_version is None:
        return rows
    return [row for row in rows if row.get("schema_version") == schema_version]


def read_rows_from_floor(path: Path, minimum_schema_version: str) -> StoreRead:
    """Read a store, selecting rows at or above `minimum_schema_version`.

    Unlike `read_rows`, nothing is silently dropped: a row below the floor, a
    row carrying no comparable `schema_version`, and a line that is not JSON
    at all each land in `unreadable`, aggregated into one entry per
    `(schema_version, reason)` pair. An absent file is an empty `StoreRead`,
    matching `read_rows`'s "an absent store is not an error" contract.

    Versions are compared as **integers**, never as strings: `"10"` sorts
    before `"7"` lexically, and the gap this service actually spans -- the
    published bundle at `"7"` against the live stores at `"11"` -- crosses
    exactly that boundary, so a string comparison would class every live row
    as below the bundle's floor. `tests/test_reference_bundle.py` carries the
    same trap in a comment on its own version check.

    Never raises on stored content: a `json.JSONDecodeError` escaping here
    would take down a read-only service on one hand-edited line.
    """
    if not path.exists():
        return StoreRead(rows=[], unreadable=[])

    floor = _as_schema_int(minimum_schema_version)
    if floor is None:
        raise ValueError(
            f"minimum_schema_version={minimum_schema_version!r} is not an integer"
        )

    rows: list[dict[str, Any]] = []
    counts: Counter[tuple[str | None, str]] = Counter()
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                parsed = json.loads(line)
            except json.JSONDecodeError:
                counts[(None, UNREADABLE_UNPARSABLE_LINE)] += 1
                continue
            if not isinstance(parsed, dict):
                counts[(None, UNREADABLE_UNPARSABLE_LINE)] += 1
                continue
            raw_version = parsed.get("schema_version")
            version = None if raw_version is None else str(raw_version)
            numeric = None if version is None else _as_schema_int(version)
            if numeric is None:
                counts[(version, UNREADABLE_NO_SCHEMA_VERSION)] += 1
            elif numeric < floor:
                counts[(version, UNREADABLE_BELOW_FLOOR)] += 1
            else:
                rows.append(parsed)

    unreadable = [
        UnreadableRows(schema_version=version, count=count, reason=reason)
        for (version, reason), count in sorted(counts.items(), key=_unreadable_sort_key)
    ]
    return StoreRead(rows=rows, unreadable=unreadable)


def _as_schema_int(version: str) -> int | None:
    """`version` as an integer, or `None` when it is not a decimal integer."""
    try:
        return int(version)
    except ValueError:
        return None


def _unreadable_sort_key(
    item: tuple[tuple[str | None, str], int],
) -> tuple[int, int, str, str]:
    """Order unreadable entries: numeric version ascending, `None` last.

    Deterministic on purpose -- two reads of one store must produce
    byte-identical output, so a response can be diffed across runs.
    """
    (version, reason), _count = item
    if version is None:
        return (2, 0, "", reason)
    numeric = _as_schema_int(version)
    if numeric is None:
        return (1, 0, version, reason)
    return (0, numeric, "", reason)


def rows_for_run(path: Path, run_id: str) -> list[dict[str, Any]]:
    """Return every row of the store at `path` whose `run_id` matches.

    An absent store and a `run_id` no row carries both return an empty list --
    both mean "nothing to skip" to a `--resume` caller, never an error.
    """
    return [row for row in read_rows(path) if row.get("run_id") == run_id]


def resume_skip_reason(
    path: Path, run_id: str, provider: str, item_count: int, *, task_suite: str
) -> str | None:
    """Why `--resume` must not re-run this batch, or None to run it.

    Used only under `--resume`: a fresh run never has any prior rows for its
    own (freshly minted) run_id, so this is never called there.

    Distinct item_ids, not a row count: the question is which of the batch's
    `item_count` items this `(run_id, provider)` pair already owns. Three
    cases, because a batch is skipped for two different reasons and re-run for
    one:

    - none of them: nothing was ever written, re-run the batch from item 1.
    - all of them: the batch already cost what it cost, never pay again.
    - some of them: re-running would append a second row for every item
      already on disk, and `append_row` only ever appends -- so the pair
      `(run_id, provider, item_id)` would stop being unique and a reader
      (`verdict.select_quality_references` included) would meet the same item
      twice. `plan.md`'s Decision holds that a partial batch is unreachable
      (a mid-batch failure never reaches the row writer), but nothing
      enforces it: rows are appended one by one, so an interrupt or a disk
      failure part-way through leaves exactly this state. Refuse it rather
      than duplicate; per-item resume is out of scope by that same Decision.

    The triple a resume reasons about is `(run_id, provider, task_suite)`,
    not the pair it used to be: one store now holds rows from more than one
    suite, so a `run_id` is not evidence about a suite it was never run
    under. Without the third element, `--resume <classification-run-id>
    --suite translation` would find a complete classification batch and skip
    a translation batch that never ran.

    `path`, `item_count` and `task_suite` are the caller's: the two CLIs that
    write quality rows keep their own store, their own batch size and their
    own suite name, and the "never re-pay, never duplicate" rule is one rule
    over all of them.
    """
    written_items = {
        row.get("item_id")
        for row in rows_for_run(path, run_id)
        if row.get("provider") == provider and row.get("task_suite") == task_suite
    }
    if not written_items:
        return None
    if len(written_items) >= item_count:
        return f"run {run_id} already complete"
    return (
        f"run {run_id} is partially written "
        f"({len(written_items)}/{item_count} items); "
        f"re-running would duplicate them"
    )
