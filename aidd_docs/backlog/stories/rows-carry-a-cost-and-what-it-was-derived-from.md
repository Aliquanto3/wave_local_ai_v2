---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-per-channel-energy-emissions-and-their-scope-boundary.md
order: 18
---

# Story: Rows carry a cost and what it was derived from

**As** a client-side engineer recomputing a published cost a year later
**I want** every row to carry the inputs behind its cost and the unit both sides are normalized against
**So that** I can tell a wrong row from a moved price, and an on-prem cost from a cloud cost divides by the same denominator

## Acceptance

- Methodology 16: a cloud row carries tokens in and out plus an estimated cost from the provider's list price at run time.
- Methodology 16: a row carrying a derived cost also carries what it was derived from — the list price value, its currency and the timestamp it was retrieved — mirroring how Methodology 15 stores the factor beside `energy_kwh`.
- Methodology 16: a local row carries an energy cost derived from a configurable kWh price, with that price, its currency and its retrieval timestamp recorded the same way.
- Methodology 16: both sides are expressed against one normalization unit, chosen once for the project and recorded on every row.
- A row whose cost is present without its derivation inputs is refused by the writer gate.
- Cost is reported, never optimised: no threshold, ranking or recommendation is derived from these fields here.

## Code it changes

- `src/wave_local_ai_v2/cost.py` (new) — the two derivations, the normalization unit, and the derivation-input block.
- `src/wave_local_ai_v2/mistral_client.py` — surfaces token counts from the response.
- `src/wave_local_ai_v2/settings.py` — kWh price, currency, list-price source and the normalization unit as configured values.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — the cost block lands on both row kinds.
- `src/wave_local_ai_v2/row_contract.py` — cost, its inputs and the normalization unit become required.

## Tests it needs

- `tests/test_cost.py` (new) — a stubbed cloud response's token counts times a fixed list price give the expected cost, with price, currency and timestamp on the row; a local row's kWh price times `energy_kwh` gives the expected cost; a cost without its inputs is refused; both row kinds record the same normalization unit.
- `tests/test_mistral_client.py` — token counts are read from the stubbed response and a response without them yields nulls rather than raising.

## Evidence it publishes

- The regenerated `aidd_docs/results/quality-reference.jsonl` (order 20) for the cloud side and `runtime-reference.jsonl` (order 19) for the local side — neither current file carries any cost field at all.

## Cancellation

n/a — not cancelled.
