"""A bundle that publishes an interval and a tested comparison, built from the
superseded schema-"7" rows by the writers' own code, and that superseded
bundle itself.

The schema-"7" rows predate schema "21" and their four family records all
refuse on `thinking_policy`, which those rows lack. So the rows here are those
rows with the one generation constraint they lack set, and each batch's
`score_interval` block computed the way the quality writer computes it
(`score_interval.interval_block` over the batch's items); the family record is
written by `comparison` itself. The committed files are read, never written.
Lives beside the tests because the recomputation evidence builds the same
bundle.

`SCHEMA_7` is the bundle as published before the 2026-10-04 republication:
its rows `git mv`-renamed to `*-reference.schema-7.jsonl` and the records
computed over them kept in `comparisons.schema-7/` and `leader-sets.schema-7/`.
Tests whose subject is a known, fixed set of real rows read it; the current
bundle is `bundle_export.default_bundle_paths()`.
"""

from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import bundle_export, comparison, score_interval

_CURRENT = bundle_export.default_bundle_paths()
_RESULTS = _CURRENT.runtime_rows.parent
SCHEMA_7 = bundle_export.BundlePaths(
    runtime_rows=_RESULTS / "runtime-reference.schema-7.jsonl",
    quality_rows=_RESULTS / "quality-reference.schema-7.jsonl",
    fiche_dir=_CURRENT.fiche_dir,
    roster=_CURRENT.roster,
    suite_definitions=_CURRENT.suite_definitions,
    comparisons_dir=_RESULTS / "comparisons.schema-7",
    leader_sets_dir=_RESULTS / "leader-sets.schema-7",
)
LOCAL_MODEL = "Qwen3.6-35B-A3B"
CLOUD_MODEL = "mistral-small-2603"
ROWS_SOURCE = "rows/quality.jsonl"


def published_rows() -> list[dict[str, Any]]:
    """The committed quality rows, each batch carrying its interval block."""
    rows = [
        json.loads(line)
        for line in SCHEMA_7.quality_rows.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    batches: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        row["thinking_policy"] = "disabled"
        batches[(row["run_id"], row["model_id"])].append(row)
    for batch in batches.values():
        block = score_interval.interval_block(
            [{"item_id": row["item_id"], "language": row["language"]} for row in batch],
            [score_interval.item_value(row) for row in batch],
        )
        for row in batch:
            row["score_interval"] = block
    return rows


def build_bundle(directory: Path) -> bundle_export.BundlePaths:
    """The bundle on disk: these rows, one family of every local-vs-cloud pair."""
    rows = published_rows()
    rows_dir = directory / "rows"
    comparisons_dir = directory / "comparisons"
    for path in (rows_dir, comparisons_dir, directory / "leader-sets"):
        path.mkdir(parents=True, exist_ok=True)
    quality = rows_dir / "quality.jsonl"
    quality.write_text("".join(json.dumps(row) + "\n" for row in rows), "utf-8")
    runtime = rows_dir / "runtime.jsonl"
    runtime.write_bytes(SCHEMA_7.runtime_rows.read_bytes())
    members = []
    for run_id in sorted({row["run_id"] for row in rows}):
        reference = comparison.Side(run_id, {"model_id": LOCAL_MODEL})
        candidate = comparison.Side(run_id, {"model_id": CLOUD_MODEL})
        members.append(
            comparison.compare_sides(
                comparison.select_side(rows, reference),
                comparison.select_side(rows, candidate),
                reference,
                candidate,
            )
        )
    family = comparison.build_family_record(
        members, alpha=comparison.DEFAULT_ALPHA, rows_source=ROWS_SOURCE
    )
    comparison.default_output_path(family, comparisons_dir).write_text(
        comparison.record_text(family), encoding="utf-8", newline="\n"
    )
    return bundle_export.BundlePaths(
        runtime_rows=runtime,
        quality_rows=quality,
        fiche_dir=SCHEMA_7.fiche_dir,
        roster=SCHEMA_7.roster,
        suite_definitions=SCHEMA_7.suite_definitions,
        comparisons_dir=comparisons_dir,
        leader_sets_dir=directory / "leader-sets",
    )
