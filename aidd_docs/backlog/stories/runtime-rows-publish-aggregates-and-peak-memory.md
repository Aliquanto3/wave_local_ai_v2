---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/a-runtime-row-is-a-warmed-and-cooled-repetition-set.md
order: 8
---

# Story: Runtime rows publish aggregates and peak memory

**As** a client-side engineer sizing a deployment from a published row
**I want** each headline metric published as a median with N, mean and standard deviation beside it, and memory published as a peak
**So that** I can judge the spread behind a number, and the sizing question I ask first is answered by the row rather than by one arbitrary sample

## Acceptance

- Methodology 6: `ttft_ms`, `prompt_tok_per_s` and `gen_tok_per_s` are each published at the row's top level as the median over the counted repetitions, with N, the mean and the sample standard deviation recorded beside each.
- Methodology 6: memory is published as the peak observed across the counted repetitions — `vram_used_mib` and `process_rss_bytes` both — never as a point sample.
- Methodology 6: every non-timing measurement on the row declares its aggregation: which statistic it carries, or which repetition index it was taken from.
- The named metric set is explicit in code, so a metric added later either declares an aggregation or fails the writer gate.
- The sample standard deviation is the N-1 form and is defined for N≥2; a row with N<2 cannot be written.

## Code it changes

- `src/wave_local_ai_v2/aggregation.py` (new) — median, mean, sample standard deviation, peak, and the aggregation-label attached to each published field.
- `src/wave_local_ai_v2/gpu.py`, `src/wave_local_ai_v2/timings.py` — read per repetition rather than once per run, so a peak has samples to take.
- `src/wave_local_ai_v2/__init__.py` — the row's top-level fields become aggregates over the repetition list.
- `src/wave_local_ai_v2/row_contract.py` — median, N, mean, sd per named metric, the two peaks, and the aggregation labels become required.

## Tests it needs

- `tests/test_aggregation.py` (new) — known repetition sets produce known median, mean and sd; an even N takes the mean of the two middles; peak is the maximum, not the last; N<2 raises.
- `tests/test_cli.py` — with stubbed responses returning five different timing blocks, the row's medians and peaks match hand-computed values and every non-timing field carries an aggregation label.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` (order 19): each row carries N, mean and sd where the current tracked rows carry a bare `gen_tok_per_s` of 26.046, and a VRAM peak where they carry one sample of 4548.7 MiB against a 15.2 GB RSS.

## Cancellation

n/a — not cancelled.
