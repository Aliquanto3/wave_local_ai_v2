# Recomputation from the exported tables alone (2026-10-02)

## Why not over the committed bundle

The committed bundle publishes nothing to recompute: its quality rows are at schema `7`
(no `score_interval`, which starts at `21`), and its four family records are all refusals on
`thinking_policy`, which those rows lack. Exporting it and running the reader:

```
$ uv run wave-local-ai-v2-export --output-dir <tmp>/committed
$ uv run python scripts/recompute_from_export.py <tmp>/committed
0 values recomputed (none), 0 differ
```

## The bundle recomputed

`build_published_bundle.py` (this folder) writes, into a scratch directory, the committed
quality rows with `thinking_policy` set to `disabled` and each batch's `score_interval`
block computed by `score_interval.interval_block` (the quality writer's function), plus one
family record of both local-vs-cloud pairs written by `comparison` (`compare_sides`,
`build_family_record`). Fiches, roster and suite definitions are the committed ones, read
in place. No committed file was written (`git status --short aidd_docs/results` empty).

```
$ uv run python <this folder>/build_published_bundle.py <tmp>/bundle
$ uv run wave-local-ai-v2-export --output-dir <tmp>/export --quality-rows <tmp>/bundle/rows/quality.jsonl \
    --runtime-rows <tmp>/bundle/rows/runtime.jsonl --comparisons-dir <tmp>/bundle/comparisons \
    --leader-sets-dir <tmp>/bundle/leader-sets
wrote .../quality_items.csv (80 rows)
wrote .../comparison_records.csv (3 rows)
...
$ uv run python scripts/recompute_from_export.py <tmp>/export
...
96 values recomputed (holm, interval, mcnemar), 0 differ
```

Exit code `0`. A second export of the same bundle is byte-identical file by file (`cmp`),
and a second reader run prints the same output. Full output, run ids shortened to eight
characters: [`recompute-output.txt`](./recompute-output.txt).

## What the reader recomputed

The reader (`scripts/recompute_from_export.py`) imports nothing from the project and reads
only `quality_items.csv` and `comparison_records.csv`.

| Batch | Suite interval (published = recomputed) | MDE | Language cells |
| ----- | --------------------------------------- | --- | -------------- |
| `5e13166d...` Qwen3.6-35B-A3B | [0.6, 0.95] | 0.175 | en [0.3, 0.9]; fr, de `zero_width` |
| `5e13166d...` mistral-small-2603 | [0.85, 1.0] | 0.07500000000000001 | de [0.4, 1.0]; en, fr `zero_width` |
| `d20afbda...` Qwen3.6-35B-A3B | [0.6, 0.95] | 0.175 | en [0.3, 0.9]; fr, de `zero_width` |
| `d20afbda...` mistral-small-2603 | [0.75, 1.0] | 0.125 | de [0.2, 1.0]; en, fr `zero_width` |

Each from the block's own seed, 10 000 resamples, 0.95, drawn one index at a time as the
dictionary's `score_interval_draw_procedure_id` entry states (the writer reads the same
stream in bulk). 4 batches x 4 cells (suite, en, fr, de) x 5 values (`n`, bounds, MDE,
null reason) = 80 interval values, all equal; plus 2 x 7 McNemar values and 2 adjusted
p-values = 96.

| Comparison (local vs cloud) | b / c | Paired n | McNemar p | Holm-adjusted p (m = 2) |
| --------------------------- | ----- | -------- | --------- | ----------------------- |
| run `5e13166d...` | 1 / 4 | 20 | 0.375 | 0.75 |
| run `d20afbda...` | 2 / 4 | 20 | 0.6875 | 0.75 |

Contingency, discordant n, paired n and p recomputed from the two sides' per-item `correct`
columns joined on `item_id`; the adjusted p from the family's raw p-values.
