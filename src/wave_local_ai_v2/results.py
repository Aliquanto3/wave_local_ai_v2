"""Append-only JSONL results store for runtime rows."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def append_row(path: Path, row: dict[str, Any]) -> None:
    """Append one row as a JSON line, creating parent directories if needed."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(row) + "\n")


def read_rows(path: Path) -> list[dict[str, Any]]:
    """Read all rows back from the results store. Returns an empty list if absent."""
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]
