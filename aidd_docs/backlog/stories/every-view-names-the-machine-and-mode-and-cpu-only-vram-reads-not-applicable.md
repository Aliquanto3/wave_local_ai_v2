---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/a-gpu-run-and-a-cpu-only-run-never-share-a-fiche.md
order: 2
---

# Story: Every view names the machine and the mode, and a cpu_only row's VRAM reads not applicable

**As** a reader of the published tables
**I want** a `cpu_only` row to carry no VRAM number, and every row to show which machine, which mode and which memory generation produced it
**So that** a zero or a desktop's idle VRAM is never read as a measurement, and two machines' rows are never told apart only by an opaque fiche hash

Maps to: PRD AC "Given a GPU-bearing machine, running a declared `cpu_only` profile produces ordinary published rows carrying no VRAM figure but an explicit not-applicable"; PRD AC "Given the no-GPU professional-PC configuration... distinguished by machine"; Methodology 21; epic success checks 3 and 7.

Current state: `gpu.py:24` reads `memory_info.used`, the **device-wide** VRAM in use, so a `cpu_only` run on the laptop today would publish the desktop's own VRAM occupancy as the run's figure. The comparison view keys columns on `fiche_hash` (`read_model.py:365-370`), so machines already open separate columns once order 1 lands, but nothing in any view says which machine a column is: `COMPARISON_DIMENSIONS` reserves `machine` and does not carry it (`read_model.py:349-353`), and the runtime view's fiche block renders a fixed key list (`RuntimeView.tsx:72-82`).

## Acceptance

- A `cpu_only` runtime row carries no VRAM number at the row level, in its peak aggregate, or in any counted repetition, and each of those places carries an explicit not-applicable marker a reader can tell apart from an unmeasured value. `grep` over a `cpu_only` row finds no `vram_used_mib` holding a number, zero included. [PRD AC cpu_only rows; epic success check 3]
- A `gpu` row's VRAM figure is unchanged, and a `gpu` row whose VRAM read failed still says unavailable, not not-applicable: the two absences stay distinct.
- The GPU fields stay on a `cpu_only` fiche of a GPU-bearing machine; the GPU energy channel keeps its own measurement and label. Erasing either would hide that the machine had a GPU and chose not to use it. [epic Boundaries]
- The runtime view's fiche block shows the machine id and the compute mode, and resolves the machine id to its declared entry to show memory type and speed and whether a GPU is present, each marked declared. A machine id that does not resolve renders as a named unresolved pointer, never as a blank.
- The comparison view carries `machine` and `compute_mode` as comparison dimensions, appended to `COMPARISON_DIMENSIONS` and resolved from the row, so a column names its machine and mode rather than differing only by fiche hash.
- The not-applicable VRAM renders as "not applicable" in the runtime view, distinct from the existing "not reported" absence.

## Code it changes

- `repetitions.py`, `aggregation.py` (the `PEAK_METRICS` path), `__init__.py`: VRAM under `cpu_only`.
- `row_contract.py`: the not-applicable marker, `SCHEMA_VERSION` bumped.
- `read_model.py`: machine pointer resolution beside the roster pointer; `COMPARISON_DIMENSIONS`; the not-applicable absence reason.
- `frontend/src/views/runtime/RuntimeView.tsx`, `frontend/src/views/comparison/ComparisonView.tsx`, their `types.ts` and fixtures; `frontend/src/components/Absent.tsx` if a reason label is added.
- `CHANGELOG.md` Unreleased.

## Tests it needs

- `tests/test_cli.py` / `tests/test_aggregation.py`: a stubbed `cpu_only` run publishes no VRAM number anywhere on the row; a stubbed `gpu` run is unchanged; a failed read on `gpu` stays unavailable.
- `tests/test_read_model.py`: machine pointer resolved and unresolved; the partition tests still hold with the new fields; two rows differing only in machine open two columns naming their machines.
- `RuntimeView.test.tsx` and the comparison view tests: machine, mode and declared memory type rendered; "not applicable" rendered distinct from "not reported".

## Evidence it publishes

- The laptop `cpu_only` row from order 1's proof, re-run under this schema, shown in the runtime view with its VRAM reading "not applicable" and its machine and memory generation named: one screenshot per view, filed with the plan's evidence.

## Plan shape

1. Row-level VRAM not-applicable across repetitions, aggregate and contract.
2. Read model: machine pointer, comparison dimensions, absence reason.
3. Front end: runtime and comparison views.
4. Live `cpu_only` row on the laptop viewed in the dashboard; CHANGELOG.

## Cancellation

n/a — not cancelled.
