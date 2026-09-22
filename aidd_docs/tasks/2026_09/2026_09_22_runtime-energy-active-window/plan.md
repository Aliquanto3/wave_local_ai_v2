---
objective: "A runtime row's energy, emissions and cost-per-token figures are measured over the counted repetitions' active windows only, never the cooldowns between them, and the row names the method and the two window sizes it measured."
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Runtime energy measured per repetition, not per window

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Fix audit finding C3: `measure_energy` currently wraps the whole counted-repetition span, so idle cooldown is 43-89% of the measured window and biases every runtime energy/emissions/cost-per-token figure toward fast models looking artificially expensive. Measure each counted repetition's own energy in isolation, sum the deltas for the row's published energy figures, and record `active_window_s`, `idle_window_s` and `energy_window_method` beside them. |
| **Source** | `aidd_docs/tasks/2026_09/2026_09_22_audit/report.md` finding C3 (`src/wave_local_ai_v2/__init__.py:349-353`, `src/wave_local_ai_v2/repetitions.py:126-127`) plus the user's scoping text: per-repetition CodeCarbon start/stop, summed active windows, `active_window_s`/`idle_window_s` recorded; a fallback to whole-window-minus-idle-baseline with a new `energy_window_method` field if per-repetition proves too heavy or inaccurate at ~10 s windows, verified by one probe on this machine before committing; PRD Methodology criterion 15 gains the window rule; the results README notes pre-change rows measured the whole window (superseded, never edited); live re-run of one fast dense model and the MoE flagship with a before/after per-token energy comparison. At most four phases. W4 (the local quality energy window covering server launch/model load) is the report's own follow-up item and stays out of this story's scope — quality rows are untouched. |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Probe: verify per-repetition CodeCarbon tasks on this machine, decide the method | [`phase-1.md`](./phase-1.md) |
| 2   | Runtime harness measures energy per repetition; schema, aggregation and read-model updates | [`phase-2.md`](./phase-2.md) |
| 3   | PRD Methodology 15 gains the window rule; results README records the supersession | [`phase-3.md`](./phase-3.md) |
| 4   | Live evidence: re-run a fast dense model and the MoE flagship, publish the before/after comparison | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `.venv/Lib/site-packages/codecarbon/emissions_tracker.py` (`start_task`/`stop_task`, `BaseEmissionsTracker.start`/`stop`) | CodeCarbon ships a task API built for exactly this: `start_task()`/`stop_task(task_name)` isolate one sub-span's energy delta on the *same* tracker instance (no new hardware probe per call), returning per-channel `TaskEmissionsData` with the same `cpu_energy`/`gpu_energy`/`ram_energy`/`energy_consumed`/`gpu_count` shape `energy.EnergyResult` already reads off `final_emissions_data`. `stop_task` requires a prior `start_task`; `stop()` still needs a prior plain `start()` and releases the hardware handles once, at the end. This is materially lighter than instantiating a fresh `OfflineEmissionsTracker` per repetition, which is the mechanism the "too heavy at ~10 s windows" contingency in the source was guarding against — the probe in phase 1 confirms this holds on this machine rather than assuming it from reading the library. |

## Decisions

| Decision | Why |
| -------- | --- |
| Per-repetition measurement uses one `OfflineEmissionsTracker`'s `start_task()`/`stop_task()` around each counted repetition's `send()` call, not a fresh tracker per repetition. The tracker's own `start()`/`stop()` still frame the whole counted set, for hardware lifecycle and the final `gpu_count` check `measure_energy` already relies on. | `start_task`/`stop_task` is CodeCarbon's own mechanism for isolating a sub-span without re-probing hardware; a fresh tracker per repetition would pay full hardware detection five times and is the expensive alternative the source's fallback clause exists to avoid, not the first thing to try. Confirmed cheap enough by phase 1's probe before this is built. |
| The new logic lives entirely in `energy.py` (a `RepetitionEnergyTracker` helper) and `__init__.py`'s `_run`. `repetitions.py` is untouched: `run_repetition_set` still takes a plain zero-arg `send`, and the energy wrapping happens by wrapping that closure before it is passed in. | `repetitions.py`'s docstring already states it "never builds the HTTP body itself" and only sequences calls; making it aware of CodeCarbon would couple a pure sequencing module to a measurement concern it does not otherwise depend on, for no benefit — the wrapping composes from outside with no change to its signature. |
| If any one counted repetition's `stop_task()` fails to return data, the whole row's energy figures become `unavailable` (all four channel values `None`, `energy_window_method` `unavailable`, the same value as a tracker that never started) rather than a partial sum over fewer repetitions. | Matches `cost.total_or_none`'s existing rule elsewhere in this codebase: a total missing one sample is unknown, not smaller. A partially-summed energy figure silently under-reports without saying so. |
| `active_window_s` is the same quantity as the row's existing `wall_clock_s` (the sum of each repetition's own timed `send()` call) restated beside the energy figures; `idle_window_s` is `(repetitions_n - 1) * cooldown_s`, deterministic from settings already on the row. Neither is a new measurement stream. | The audit's own idle-share formula is exactly `(repetitions_n-1)*cooldown_s` over that plus `wall_clock_s` — reusing the two quantities that formula already names, under names that sit next to the energy block, means a reader auditing energy does not have to know `wall_clock_s` is the same span, and no new timer is introduced to drift from the one `repetitions.py` already owns. |
| The three new fields (`active_window_s`, `idle_window_s`, `energy_window_method`) become required on the **runtime** row only, rendered via `read_model.RUNTIME_VIEW_FIELDS` — not `ENERGY_VIEW_FIELDS`, the field set the runtime and quality energy routes share. `SCHEMA_VERSION` bumps to `"12"`. | `read_model.energy_view`'s own docstring states both row kinds carry "the same thirteen energy fields," and `tests/test_read_model.py`'s `test_every_contract_field_is_rendered_or_declared_unrendered` enforces that `ENERGY_VIEW_FIELDS` entries are required on both kinds via one shared `RENDERED_SETS` mapping. Adding the three fields there would force quality rows to carry them too, which is W4's fix (the quality energy window spans server launch and model load, a different span shape) and stays out of this story per the user's scope. `RUNTIME_VIEW_FIELDS` carries no such cross-kind constraint. |
| `energy_kwh`, `cpu_energy_kwh`, `gpu_energy_kwh` and `ram_energy_kwh` keep their field names and keep being consumed unchanged by `emissions.local_emissions`, `cost.local_cost` and `cost.cost_per_million_tokens` on the runtime row — only their *meaning* changes, from the whole counted-repetition window to the summed active windows. `aggregation.AGGREGATION_LABELS`' text for those four entries is updated to say so. | Redefining what the figure measures, rather than adding parallel `*_active` fields, is what actually fixes the bias the audit found: every downstream consumer (emissions, cost, cost-per-token) is already wired to these field names, and the fix has to reach cost-per-token to matter. `AGGREGATION_LABELS` is a plain key-name set for the runtime→quality contract-partition check (`row_contract.MEASUREMENT_FIELDS`), so changing its label *text* does not touch quality rows, which never carry an `aggregation` block. |
