---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on:
  - aidd_docs/backlog/stories/runtime-rows-publish-aggregates-and-peak-memory.md
  - aidd_docs/backlog/stories/the-fiche-carries-a-normalised-hash-every-row-cites.md
order: 16
---

# Story: A re-run receives a three-state reproduction verdict

**As** a client-side engineer re-running a published row on my own machine
**I want** the harness to hand me a verdict against a named reference row
**So that** I get an answer rather than two numbers to compare by eye, and a machine that simply differs from the reference is not reported as a failed reproduction

## Acceptance

- Methodology 8: a runtime re-run carries a verdict decided on one metric, the median `gen_tok_per_s`. It is `reproduced` when a reference row shares the re-run's normalised fiche hash and the two medians differ by no more than 10% of the reference median (configurable), and `not_reproduced` otherwise.
- Methodology 8: it is `not_comparable` when no reference row shares that hash, and the verdict names the fiche fields that differ.
- Methodology 8: the verdict-blocking fiche fields are the llama.cpp build, the quant, the server flag set and the GPU. CPU, RAM, driver and OS are recorded and reported with the verdict and never block a comparison.
- Methodology 8: the row records the run id of the reference it was compared against, both runs' median `ttft_ms` and `prompt_tok_per_s` as reported deltas, and both runs' machine state — all reported, none deciding the verdict.
- Methodology 8 (quality): a quality re-run is `reproduced` when two runs of the same model, prompt version and seed produce identical per-item predicted labels; the reference run id is recorded the same way.
- The verdict is produced and stored by the harness against a named reference file, never computed at read time by a reader.

## Code it changes

- `src/wave_local_ai_v2/verdict.py` (new) — reference selection by fiche hash, the tolerance comparison, the three states, the differing-field report and the reported deltas.
- `src/wave_local_ai_v2/settings.py` — the reference file path and the tolerance as configured values.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — attach the verdict block when a reference is configured; a run with no reference records `not_comparable` with the reason, not a failure.

## Tests it needs

- `tests/test_verdict.py` (new) — over constructed reference and re-run rows: equal medians give `reproduced`; a 9.9% and a 10.1% delta fall either side; a differing GPU gives `not_comparable` naming `gpu_name`; a differing driver alone still compares and reports the difference; an empty reference file gives `not_comparable`, not `not_reproduced`; identical per-item labels give a reproduced quality verdict and one differing label does not.

## Evidence it publishes

- The verdict block on the regenerated `aidd_docs/results/runtime-reference.jsonl` rows (order 19), plus `tests/test_verdict.py` as the epic's fourth success check — the logic is falsified on constructed rows, while the 10% tolerance is calibrated from the two real bench runs of order 19.

## Cancellation

n/a — not cancelled.
