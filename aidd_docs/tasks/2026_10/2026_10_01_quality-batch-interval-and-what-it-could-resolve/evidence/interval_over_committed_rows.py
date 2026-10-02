"""Compute the interval block over the committed classification batches.

An analysis over existing rows: nothing is written back to the store. Run
from the worktree root:

    uv run python aidd_docs/tasks/2026_10/2026_10_01_quality-batch-interval-and-what-it-could-resolve/evidence/interval_over_committed_rows.py
"""

from __future__ import annotations

import json
from pathlib import Path

from wave_local_ai_v2 import score_interval

STORE = Path("aidd_docs/results/quality-reference.jsonl")
SUITE_ID = "classification-support-routing"


def main() -> None:
    rows = [
        json.loads(line)
        for line in STORE.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    batches: dict[tuple[str, str], list[dict]] = {}
    for row in rows:
        if row.get("suite_id") == SUITE_ID:
            batches.setdefault((row["run_id"], row["provider"]), []).append(row)

    for (run_id, provider), batch in batches.items():
        values = [score_interval.item_value(row) for row in batch]
        block = score_interval.interval_block(batch, values)
        # The three invariants, on an in-memory copy carrying the block.
        score_interval.check_batch_invariants(
            [{**row, "score_interval": block} for row in batch]
        )
        assert score_interval.replay(block, batch, values) == block
        suite = block["suite"]
        print(
            f"run {run_id[:8]} {provider:<8} {batch[0]['model_id']:<20} "
            f"n={suite['n']} accuracy={batch[0]['suite_accuracy']:.2f} "
            f"interval=[{suite['lower']:.3f}, {suite['upper']:.3f}] "
            f"mde={suite['minimum_detectable_effect']:.3f}"
        )
        for language, cell in block["by_language"].items():
            published = batch[0]["language_breakdown"][language]
            if cell["null_reason"] is None:
                shown = (
                    f"[{cell['lower']:.3f}, {cell['upper']:.3f}] "
                    f"mde={cell['minimum_detectable_effect']:.3f}"
                )
            else:
                shown = f"null_reason={cell['null_reason']}"
            print(
                f"    {language} n={cell['n']} "
                f"accuracy={published['accuracy']:.3f} {shown}"
            )
    print(
        f"seed={score_interval.DEFAULT_SEED} resamples={score_interval.RESAMPLES} "
        f"method={score_interval.METHOD_PERCENTILE} "
        f"procedure={score_interval.DRAW_PROCEDURE_ID} "
        f"generator={block['generator']}"
    )


if __name__ == "__main__":
    main()
