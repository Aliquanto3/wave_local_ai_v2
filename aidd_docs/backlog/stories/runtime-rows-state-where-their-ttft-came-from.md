---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 11
---

# Story: Runtime rows state where their TTFT came from

**As** a client-side engineer comparing two time-to-first-token figures
**I want** every runtime row to say whether its TTFT was reported by the inference server or measured by the client
**So that** two differently obtained numbers are never compared as if they were the same measurement

## Acceptance

- Methodology 20: every runtime row records `ttft_source`, one of `server_reported` or `client_measured`, under the same discipline the energy method labels carry.
- Methodology 20: today's value is `server_reported`, taken from llama-server's `timings.prompt_ms`, and the row says so — the caveat currently living only in a code comment becomes a published field.
- The field is required by the writer gate, so a future client-side measurement cannot land unlabelled.
- No streaming or slot-isolation work is done here: corroborating the server's figure with an independent client measurement stays out of scope, and this story publishes the provenance of the number as it is obtained today.

## Code it changes

- `src/wave_local_ai_v2/timings.py` — `parse_timings` returns the source label beside the three metrics, so the label is produced where the number is.
- `src/wave_local_ai_v2/__init__.py` — the field lands on the row; the existing comment at `__init__.py:184-199` shrinks to what the row does not already say.
- `src/wave_local_ai_v2/row_contract.py` — `ttft_source` becomes a required runtime-row field.

## Tests it needs

- `tests/test_timings.py` — a parsed server response yields `server_reported`; an unrecognised source value is rejected rather than passed through.
- `tests/test_cli.py` — the written row carries `ttft_source`, and a row without it is refused by the writer gate.

## Evidence it publishes

- Every row of the regenerated `aidd_docs/results/runtime-reference.jsonl` (order 19) carries `ttft_source`, where the two current tracked rows publish a bare `ttft_ms` of 5821.988 and 5747.284 with nothing saying who measured it.

## Cancellation

n/a — not cancelled.
