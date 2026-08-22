---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 7
---

# Story: A runtime row is a warmed and cooled repetition set

**As** a client-side engineer judging a throughput figure
**I want** a runtime measurement to be a declared repetition protocol rather than one shot
**So that** I can re-run it under the same protocol instead of guessing it, and read the raw repetitions rather than trust a summary

## Acceptance

- Methodology 6: one server process produces one runtime row set; the process does not restart between repetitions and the row records that.
- Methodology 6: the process's first generation is a warm-up, recorded as such and excluded from N.
- Methodology 6: the counted repetitions are at least 5 (configurable, default 5), run back-to-back, each separated by a fixed cooldown whose duration the row records (default 10 s).
- Methodology 6: the counted repetitions are kept in full, inline in the aggregate row as an ordered list, each carrying its repetition index and its own measurements.
- The warm-up does not contaminate the counted repetitions: with `-np 1` the server shares one slot, and this repo has already measured a warm-up bleeding its context into the measured request and collapsing `gen_tok_per_s` from 26 to 11.8 (`src/wave_local_ai_v2/__init__.py:29-40`). The harness clears the slot state between generations and the acceptance run shows repetition 1 not systematically below repetitions 2..N.
- A protocol value is data, never a convention: warm-up count, restart-between-repetitions, cooldown seconds and repetition count are all row fields.

## Code it changes

- `src/wave_local_ai_v2/repetitions.py` (new) — the warm-up, the counted loop, the cooldown, the slot-state clearing, and the ordered raw-repetition list.
- `src/wave_local_ai_v2/__init__.py` — one request becomes one repetition set; the row assembles the protocol fields and the inline repetition list.
- `src/wave_local_ai_v2/settings.py` — repetition count and cooldown seconds as configured values with the PRD's defaults.
- `src/wave_local_ai_v2/row_contract.py` — the protocol fields and the repetition list become required runtime-row fields.

## Tests it needs

- `tests/test_repetitions.py` (new) — with the HTTP call and the sleep both stubbed: N requests plus one warm-up are issued, the warm-up is excluded from the counted list, indices are ordered and contiguous, the cooldown is applied N-1 times at the configured duration, and the slot-clearing call precedes each counted repetition.
- `tests/test_settings.py` — the two new settings default to 5 and 10 s and are overridable.
- `tests/test_cli.py` — the written row carries the ordered repetition list and the four protocol fields.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` (order 19) — each row an N≥5 repetition set with its raw repetitions inline, against the two single-shot rows it supersedes.

## Cancellation

n/a — not cancelled.
