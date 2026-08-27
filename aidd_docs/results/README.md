# Committed results evidence

The reference bundle is five parts, handed to an auditor together: `runtime-reference.jsonl`,
`quality-reference.jsonl`, `fiches/` (the hardware/run fiches those rows cite by hash),
`aidd_docs/roster/models.json` (the models those rows cite by `roster_entry_id`), and
`suite-definitions/` (the classification suite's item set, cited by `suite_id`/`suite_version`
on every quality row). No one file in this set is self-sufficient.

A row alone names its model, sampling, machine (by `fiche_hash`) and code `commit_sha` --
but resolving any of those to an actual artifact needs the rest of the bundle sitting
beside it: `fiche_hash` resolves only against `fiches/`, `roster_entry_id` only against
`aidd_docs/roster/models.json`, `suite_id`/`suite_version` (quality rows) only against
`suite-definitions/`. `tests/test_reference_bundle.py` asserts every pointer on every
row of the current-schema bundle resolves.

The two `*-reference.jsonl` files are curated snapshots: no CLI ever writes to them, and
nothing appends to them on a benchmark run. The two files the CLIs actually append to,
`runtime.jsonl` and `quality.jsonl`, are per-machine output and stay untracked
(`.gitignore`). Tracking them instead would dirty the working tree on every run and would
ship rows that do not belong to any acceptance criterion.

## This regeneration (Story 19 + Story 20, 2026-08-27)

Both files were regenerated from scratch under the current schema (`schema_version` `"7"`),
against the 20-item suite (`suite_version` `"2"`, `en`/`fr`/`de` all >=25% share) Story 20
added. Produced on 2026-08-27 by `uv run wave-local-ai-v2` and `uv run
wave-local-ai-v2-quality` against a local llama-server (build `b10537`,
`Qwen3.6-35B-A3B-UD-IQ4_XS`) and `mistral-small-2603`.

Read the code state from the rows, not from this paragraph: every one of the 82 rows
carries `commit_sha` `9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7` (the suite-snapshot
commit, branch `feat/trilingual-suite-and-reference-bundle`) with `tree_dirty: true` --
the runs were taken mid-branch, before the commit that added these files. The dirty
flag is on the rows and is not back-filled away: it says the `commit_sha` alone does not
pin the exact working tree that produced the numbers.

### `runtime-reference.jsonl`: two runs, second against the first

| Run | `run_id` | `gen_tok_per_s` (published) | `prompt_tok_per_s` (published) | `verdict` |
| --- | -------- | --------------------------- | ------------------------------ | --------- |
| 1 | `f5f78c79...` | 25.408 | 272.643 | `not_comparable` (no reference configured yet) |
| 2 | `f7faeef7...` | 24.802 | 273.302 | `reproduced` against run 1 |

The published `gen_tok_per_s` / `prompt_tok_per_s` are the medians over each run's five
counted repetitions, and they are what the tolerance is judged on: `verdict.py` compares
`RUNTIME_REPRODUCTION_TOLERANCE` (10%) against the `*_delta` fields run 2's own verdict
block carries. Observed on those rows: `gen_tok_per_s_delta` **2.39%**,
`prompt_tok_per_s_delta` **0.24%**, `ttft_ms_delta` **0.24%** -- all inside the 10%
tolerance, so no finding for the PRD on this axis. (The repetition *means* are 25.329 and
24.826, a 1.98% spread; they are not the figures the threshold judges and are given here
only so the two do not get confused.) Run 2's verdict carries `reference_run_id` naming
run 1's `run_id` and an empty `differing_fields`.

### `quality-reference.jsonl`: two runs, local + mistral each, second against the first

| Model | Provider | `run_id` | Accuracy | `verdict` |
| ----- | -------- | -------- | -------- | --------- |
| `Qwen3.6-35B-A3B` | local | `5e13166d...` | 0.80 | `not_comparable` (run 1) |
| `mistral-small-2603` | mistral | `5e13166d...` | 0.95 | `not_comparable` (run 1) |
| `Qwen3.6-35B-A3B` | local | `d20afbda...` | 0.80 | `reproduced` against run 1 |
| `mistral-small-2603` | mistral | `d20afbda...` | 0.90 | `not_reproduced` against run 1 |

The local model reproduced exactly (0.80 both runs). The Mistral cloud model did not:
0.95 -> 0.90 across two runs sent with the same pinned sampler (`temperature=0`,
`random_seed=20260821`) -- an observed cloud-side finding for the PRD (the provider does
not guarantee bit-identical output at temperature 0), not a defect in this harness's
verdict logic, which correctly flagged the divergence rather than silently reporting
`reproduced`.

The divergence is one item, and every German misroute in the bundle lands on the same
label, which is a second finding and about the suite rather than the provider:

| Item | Expected | `mistral-small-2603` predicted | Runs affected |
| ---- | -------- | ------------------------------- | -------------- |
| `account-de-01` ("Zwei-Faktor-Authentifizierung deaktivieren, finde aber die Option nicht") | `account` | `technical` | both |
| `other-de-01` ("Zeitplan für die nächste Feature-Ankündigung") | `other` | `technical` | run 2 only (`differing_fields: ["other-de-01"]`) |

`account-de-01` is the stable one: a two-factor setting is an `account` subject, but
"I cannot find the option" reads as a `technical` complaint, and the strongest model in
the roster picks `technical` deterministically both times. Story 20 requires the four
labels to stay semantically disjoint in each language; this item is recorded here as
evidence they are not yet, in German. The item text is **not** edited in place: editing
a prompt moves `PROMPT_SET_HASH`, which would invalidate every row in this bundle. The
revision belongs to the next regeneration and is filed as such.

The local model's four wrong answers per run are all `unparseable` completions on EN
items (`technical-01`, `technical-02`, `billing-03`, `technical-03`), identical across
both runs -- a generation-failure mode named by `failure_reason` on the row, not a
routing ambiguity.

Per-language breakdown (`language_breakdown`, both providers, both runs -- accuracy /
n / indicative):

| Language | n | local accuracy | mistral accuracy | indicative |
| -------- | - | --------------- | ------------------ | ---------- |
| `en` | 10 | 0.60 | 1.00 | **false** (n >= 10) |
| `fr` | 5 | 1.00 | 1.00 | **true** (n < 10) |
| `de` | 5 | 1.00 | 0.80 (run 1) / 0.60 (run 2) | **true** (n < 10) |

`fr` and `de` sit at n=5, below `MIN_PER_LANGUAGE_CELL_ITEMS` (10): an observed
consequence of the 25%-share split at 20 total items (plan.md's Decisions), not a defect.
The suite-level gate (`gate_suite`) is not indicative -- item count and every language's
25% share both pass -- but the per-language cells for `fr`/`de` are, and every row says so
via `language_breakdown[lang].indicative`.

### Superseded files: kept, not deleted

`runtime-reference.schema-1.jsonl` and `quality-reference.schema-1.jsonl` are this
regeneration's predecessors, `git mv`-renamed rather than overwritten. The `.schema-<N>`
suffix counts superseded bundle generations -- this is generation 1, the first bundle
this repo published -- and is deliberately **not** a `schema_version` value: no row in
either file carries `schema_version` `"1"`. What they actually carry is
`schema_version` `"2"` on one row of `runtime-reference.schema-1.jsonl` and no
`schema_version` key at all on its other two rows and on all 40 rows of
`quality-reference.schema-1.jsonl`, because the key postdates them. They were produced
against the 10-item, EN-only suite. They
are kept for published-evidence continuity across the epic's duration (`every-published-
row-explains-and-reproduces-itself`'s Boundaries) -- a reader following an old citation
still finds the row it pointed at. `tests/test_reference_bundle.py` names them explicitly
as the superseded set and never folds them into the current-schema bundle checks.

### Validator proof (this regeneration)

`uv run wave-local-ai-v2-validate aidd_docs/results/runtime-reference.jsonl
aidd_docs/results/quality-reference.jsonl`:

| Run | Result |
| --- | ------ |
| Clean pass over the assembled bundle | `checked 82 row(s)`, exit **0** |
| One fiche field hand-edited (`gpu_name`) | exit **1**, `edited (82)` naming every row citing that fiche and `changed_fields: ['gpu_name']` -- all 82 rows share one fiche (same machine/flag configuration across all four runs) |
| Edit reverted (`git checkout --`) | `checked 82 row(s)`, exit **0** again |

## Earlier increments' evidence (predates this regeneration)

The sections below describe rows this regeneration **replaced**. They are kept as a
record of what earlier increments validated at the time; the bytes they describe now
live only in the `*.schema-1.jsonl` files above, not in the live `*-reference.jsonl`
files this README's own head section describes.

### `runtime-reference.jsonl` (schema-1, superseded)

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

### `quality-reference.jsonl` (schema-1, superseded)

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

### What was deliberately absent from the schema-1 rows

Both files predate the `run_id` / `captured_at` provenance keys added by a later
increment. They were **not** back-filled. A hand-edited row is no longer the row
the harness wrote; the absence of those keys is the honest signal that these rows
were produced before the change.

The same applies to the four local-model rows in the schema-1 `quality-reference`
file that carry `"predicted_label": null, "correct": false` with no reason —
`technical-01`, `technical-02`, `billing-03` and `technical-03`, plus their
run-2 duplicates (8 rows total). The harness as it stands today always writes a
`failure_reason` naming why a generation failed (`empty`, `unparseable`,
`truncated_max_tokens` or `truncated_context`); a row with a bare null and no
reason could not be produced by this code path. These rows are **not
back-filled** either: same discipline as above, a hand-edited row is no longer
the row the harness wrote, so the honest signal is left in place rather than
reconstructed.

The only edit ever applied to copied bytes is the line terminator: the live stores
are written in Windows text mode and use CRLF, and these snapshots use LF like
the rest of the repository. Every JSON payload is verbatim, byte for byte.

### Fiche hash, invalidation validator, and reproduction verdict (superseded rows)

Both schema-1 files predate `fiche_hash` and `verdict` entirely -- neither key exists
on any row in either file. `row_contract.FICHE_HASH_SCHEMA_VERSION` ("3") is the
version that introduced them; every row in both files carries a `schema_version` below
it (or none at all), so `wave-local-ai-v2-validate` reports all of them under
its non-fatal `legacy` class rather than `missing`.
