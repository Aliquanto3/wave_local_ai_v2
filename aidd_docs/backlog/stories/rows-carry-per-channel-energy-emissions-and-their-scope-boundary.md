---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 17
---

# Story: Rows carry per-channel energy, emissions and their scope boundary

**As** a client-side engineer weighing an energy figure in a sustainability report
**I want** each energy channel to state how it was obtained and carry its own value, with the emissions figure, its factor, its region and its scope boundary beside it
**So that** a composite number is never labelled by the method of its smaller measured part, and a local figure is never silently compared with a cloud one

## Acceptance

- Methodology 15: every row carries `cpu_energy_kwh`, `gpu_energy_kwh` and `ram_energy_kwh` beside `cpu_energy_method`, `gpu_energy_method` and `ram_energy_method`, plus the total `energy_kwh`.
- Methodology 15: the composite `energy_kwh` carries no single method label. The current derivation — the GPU channel's label applied to CodeCarbon's CPU+GPU+RAM total at `src/wave_local_ai_v2/energy.py:52-55` — is removed, so a row can no longer publish `measured_nvml` over a figure whose largest component is a TDP estimate.
- Methodology 15: every row carries `emissions_kg`, the emission factor and the region used to convert between it and `energy_kwh`, with the factor and region declared for CodeCarbon's offline mode rather than looked up live.
- Methodology 15: every row declares its emissions scope boundary — a local row is Scope 2 and excludes hardware amortization and facility overhead; a cloud row carries a Scope-3 estimate with the id of the formula that produced it.
- Methodology 15: any published comparison of the two states that they are not like-for-like until a local Scope-3 component exists; the statement lives with the published rows, not only in a doc.
- A channel CodeCarbon could not report is an explicit null with an `unavailable` method, never a zero.

## Code it changes

- `src/wave_local_ai_v2/energy.py` — returns per-channel values and per-channel methods; the single-label derivation is deleted.
- `src/wave_local_ai_v2/emissions.py` (new) — the offline factor and region, the local Scope-2 conversion, and the cloud Scope-3 formula with its id.
- `src/wave_local_ai_v2/settings.py` — emission factor, region and Scope-3 formula id as configured values.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — the fields land on both row kinds.
- `src/wave_local_ai_v2/row_contract.py` — the channel triples, emissions, factor, region and scope boundary become required.

## Tests it needs

- `tests/test_energy.py` — with the tracker stubbed: a GPU-measured run labels only the GPU channel `measured_nvml` and the CPU channel `estimated_tdp`; a missing channel yields null plus `unavailable`, not zero; a tracker that fails to stop yields nulls across all three channels.
- `tests/test_emissions.py` (new) — `energy_kwh` times the configured factor equals `emissions_kg`; a local row is Scope 2; a cloud row carries the formula id; a missing factor refuses the row rather than defaulting.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` (order 19), where the two rows currently published as `energy_method: measured_nvml` over 0.00037 kWh become three labelled channels with an emissions figure, a factor and a region beside them.

## Cancellation

n/a — not cancelled.
