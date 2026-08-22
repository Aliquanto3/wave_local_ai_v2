# Committed results evidence

The two `*-reference.jsonl` files in this directory are the acceptance evidence
behind the branch's headline claims. They are curated snapshots: no CLI ever
writes to them, and nothing appends to them on a benchmark run.

The two files the CLIs actually append to, `runtime.jsonl` and `quality.jsonl`,
are per-machine output and stay untracked (`.gitignore`). Tracking them instead
would dirty the working tree on every run and would ship rows that do not belong
to any acceptance criterion.

## `runtime-reference.jsonl`

Three rows. Rows 1 and 2 are the throughput evidence, copied from lines 4 and
5 of this machine's `runtime.jsonl`. Row 3 is field-shape evidence for the
machine-state/TTFT-provenance increment and is **not** a throughput claim —
see its own block below.

| Claim rows 1-2 support | Value |
| ---------------------- | ----- |
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

**Row 3 of this file** (added by the machine-state/TTFT-provenance
increment): one full row from `uv run wave-local-ai-v2` at default settings
(`RUNTIME_REPETITIONS=5`, `RUNTIME_COOLDOWN_S=10.0`,
`RUNTIME_SPREAD_THRESHOLD=0.10`), produced on 2026-08-22 (`captured_at`
21:21:58 UTC) on branch `feat/machine-state-and-ttft-provenance` at tip
`ab9280d` (`tree_dirty: true` -- the branch's own uncommitted work). Carries
every field this increment added: per-repetition `machine_state`, the three
`*_spread` fields, `unreliable`, `thermal_posture`, `ttft_source`.

Its `gen_tok_per_s` is **15.256**, far below rows 1-2 (26.0 / 25.5), and it is
kept here as field-shape evidence only. Every one of its repetitions reports
`sw_thermal_slowdown` and `sw_power_cap` in `gpu_throttle_reasons`: this row
was measured on a thermally suppressed GPU, the same condition that excludes
the streaming rows above. Unlike those rows, it says so on its own face --
which is the point of the fields this increment adds -- so it is kept and
labelled rather than dropped. Read the throughput claim from rows 1-2.

| Field | Observed value |
| ----- | --------------- |
| `gen_tok_per_s` | 15.256 -- thermally suppressed, not a throughput claim |
| `gen_tok_per_s_spread` | 0.0518 (5.2%), against the 0.10 threshold -- did not flag |
| `ttft_ms_spread` | 0.0125 |
| `prompt_tok_per_s_spread` | 0.0127 |
| `unreliable` | `false` |
| `thermal_posture` | `"fixed_cooldown"` |
| `ttft_source` | `"server_reported"` |
| `gpu_temp_c` (repetition range) | 66.0-68.0 |
| `gpu_throttle_reasons` (union across repetitions) | `sw_power_cap`, `sw_thermal_slowdown` -- this machine's GPU was throttling during the run; the spread stayed under threshold anyway |
| `cpu_temp_c` / `cpu_temp_source` | `null` / `"unavailable"` -- confirms phase 1's spike conclusion on this Windows build |

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

The same applies to the four local-model rows in `quality-reference.jsonl` that
carry `"predicted_label": null, "correct": false` with no reason —
`technical-01`, `technical-02`, `billing-03` and `technical-03`, plus their
run-2 duplicates (8 rows total). The harness as it stands today always writes a
`failure_reason` naming why a generation failed (`empty`, `unparseable`,
`truncated_max_tokens` or `truncated_context`); a row with a bare null and no
reason could not be produced by this code path. These rows are **not
back-filled** either: same discipline as above, a hand-edited row is no longer
the row the harness wrote, so the honest signal is left in place rather than
reconstructed.

The only edit applied to the copied bytes is the line terminator: the live stores
are written in Windows text mode and use CRLF, and these snapshots use LF like
the rest of the repository. Every JSON payload is verbatim, byte for byte.
