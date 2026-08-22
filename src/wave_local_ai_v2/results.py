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
