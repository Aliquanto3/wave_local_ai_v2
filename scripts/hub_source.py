"""What every public-benchmark loader shares: the Hub, the source table, its hash.

A publication suite's loader (`scripts/minds14_suite.py`,
`scripts/wmt24pp_suite.py`) fetches one benchmark at a pinned Hugging Face
revision, checks each file against the hash the Hub's tree listing records
for it, maps its rows onto the source table `subset_replay` reads, and
records that table's SHA-256 in the suite definition. The pieces below are
the ones that do not depend on the benchmark.

The table is written sorted by (source, stable key), as compact sorted-key
JSON in UTF-8 with `\\n` line ends, so its SHA-256 is the same on every
machine that reads the same revision.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import suite_gate

TREE_URL = "https://huggingface.co/api/datasets/{repo}/tree/{revision}?recursive=true"
RESOLVE_URL = "https://huggingface.co/datasets/{repo}/resolve/{revision}/{path}"
_LICENCE_FILE_STEMS = ("license", "licence", "copying")


class LoaderError(RuntimeError):
    """Raised when the source cannot be fetched, verified or mapped."""


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def git_blob_sha1(data: bytes) -> str:
    """The git object id of `data` as a blob: what the Hub lists as a non-LFS
    file's `oid`."""
    header = b"blob %d\0" % len(data)
    return hashlib.sha1(header + data, usedforsecurity=False).hexdigest()


def fetch_tree(repo: str, revision: str) -> list[dict[str, Any]]:
    """The Hub's recursive file listing of `repo` at `revision`."""
    response = requests.get(TREE_URL.format(repo=repo, revision=revision), timeout=60)
    response.raise_for_status()
    tree: list[dict[str, Any]] = response.json()
    return tree


def licence_files(tree: Sequence[Mapping[str, Any]]) -> list[str]:
    """Every file in the tree listing whose name is a licence file's."""
    return sorted(
        str(entry["path"])
        for entry in tree
        if entry.get("type") == "file"
        and str(entry["path"])
        .rsplit("/", 1)[-1]
        .lower()
        .startswith(_LICENCE_FILE_STEMS)
    )


def table_text(rows: Sequence[Mapping[str, Any]], stable_key: str) -> str:
    """The JSONL table: rows sorted by (source, stable key), compact sorted-key
    JSON."""
    ordered = sorted(rows, key=lambda row: (row["source"], str(row[stable_key])))
    return "".join(
        json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
        for row in ordered
    )


def verify_table(table: str, recorded_sha256: str) -> str | None:
    """Why a re-fetched table is not the recorded one, or None."""
    actual = sha256_hex(table.encode("utf-8"))
    if actual == recorded_sha256:
        return None
    return (
        f"the re-fetched table hashes to {actual}, the suite records "
        f"{recorded_sha256}: the source moved at its pinned revision, or the "
        "loader maps it differently"
    )


def certifies_at_publication(
    items: list[dict[str, Any]], size: int, size_target_reason: str
) -> bool:
    """Whether a draw certifies at the publication level (a draw's `accept`)."""
    try:
        suite_gate.gate_suite(
            items,
            level=suite_gate.LEVEL_PUBLICATION,
            size_target=size,
            size_target_reason=size_target_reason,
        )
    except suite_gate.SuiteGateError:
        return False
    return True


def write_text(path: Path, text: str) -> None:
    """`text` as UTF-8 with its own line ends, whatever the platform's."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(text.encode("utf-8"))


def definition_text(definition: Mapping[str, Any]) -> str:
    return json.dumps(definition, ensure_ascii=False, indent=2) + "\n"
