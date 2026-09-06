"""Append-only JSONL results store for runtime rows."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import row_contract
from wave_local_ai_v2.row_contract import RowKind


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


def rows_for_run(path: Path, run_id: str) -> list[dict[str, Any]]:
    """Return every row of the store at `path` whose `run_id` matches.

    An absent store and a `run_id` no row carries both return an empty list --
    both mean "nothing to skip" to a `--resume` caller, never an error.
    """
    return [row for row in read_rows(path) if row.get("run_id") == run_id]


def resume_skip_reason(
    path: Path, run_id: str, provider: str, item_count: int
) -> str | None:
    """Why `--resume` must not re-run this `(run_id, provider)` batch, or None to run it.

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

    `path` and `item_count` are the caller's: the two CLIs that write quality
    rows keep their own store and their own batch size, and the "never
    re-pay, never duplicate" rule is one rule over both.
    """
    written_items = {
        row.get("item_id")
        for row in rows_for_run(path, run_id)
        if row.get("provider") == provider
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
