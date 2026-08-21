# Committed results evidence

The two `*-reference.jsonl` files in this directory are the acceptance evidence
behind the branch's headline claims. They are curated snapshots: no CLI ever
writes to them, and nothing appends to them on a benchmark run.

The two files the CLIs actually append to, `runtime.jsonl` and `quality.jsonl`,
are per-machine output and stay untracked (`.gitignore`). Tracking them instead
would dirty the working tree on every run and would ship rows that do not belong
to any acceptance criterion.

## `runtime-reference.jsonl`

Two rows, copied from lines 4 and 5 of this machine's `runtime.jsonl`.

| Claim they support | Value |
| ------------------ | ----- |
| Generation throughput | `gen_tok_per_s` 26.046 and 25.484 |
| Prompt throughput | `prompt_tok_per_s` 255.93 and 259.25 |

Produced on 2026-08-21 (file written 18:14 local time), on branch
`feat/runtime-measurement-harness` at tip `597596f`, by
`uv run wave-local-ai-v2` against a local llama-server (build `b10537`,
`Qwen3.6-35B-A3B-UD-IQ4_XS`). Every row carries its own hardware fiche and flag
list, so the numbers are falsifiable against the machine that produced them.

**Deliberately excluded**: rows 6 to 9 of the live store. They come from the
reverted streaming experiment, and their `gen_tok_per_s` of 17-18 was measured
while this machine's GPU was in `sw_thermal_slowdown`. Keeping them next to the
acceptance rows with nothing to distinguish them would misrepresent the spread.
Rows 1 to 3 predate the fixed prompt's final length and are excluded for the
same reason: their `prompt_tok_per_s` (76 to 233) was measured at a different
prompt length and is not comparable.

## `quality-reference.jsonl`

All 40 rows of this machine's `quality.jsonl`: two consecutive runs per model,
ten classification items each.

| Model | Provider | Accuracy, run 1 | Accuracy, run 2 |
| ----- | -------- | --------------- | --------------- |
| `Qwen3.6-35B-A3B` | local | 0.60 | 0.60 |
| `mistral-small-2603` | mistral | 1.00 | 1.00 |

Produced on 2026-08-21 (file written 21:56 local time), on branch
`feat/runtime-measurement-harness` at tip `77a1c2e`, by
`uv run wave-local-ai-v2-quality`.

These rows support the reproducibility claim, not an accuracy claim: across the
two runs, every item's `predicted_label` is identical for both models, which is
what a pinned sampler (temperature 0, fixed seed) is there to guarantee. The
local model's four wrong answers per run are wrong in the same way both times.

## What is deliberately absent from these rows

Both files predate the `run_id` / `captured_at` provenance keys added in this
increment. They were **not** back-filled. A hand-edited row is no longer the row
the harness wrote; the absence of those keys is the honest signal that these rows
were produced before the change.

The only edit applied to the copied bytes is the line terminator: the live stores
are written in Windows text mode and use CRLF, and these snapshots use LF like
the rest of the repository. Every JSON payload is verbatim, byte for byte.
