---
objective: "A cpu_only runtime row carries an explicit not-applicable VRAM marker and no VRAM number anywhere, a gpu row is unchanged, the runtime view names the machine, the mode and the declared machine facts, and the comparison view keys and labels columns by machine and mode."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Every view names the machine and the mode, and a cpu_only row's VRAM reads not applicable

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `vram_used_mib` is the string `not_applicable` on every repetition, warm-up and the peak of a `cpu_only` row (schema "25", writer gate enforces it both ways); the read model reports it as a fourth absence reason `not_applicable`, resolves `machine_id` against the machine registry beside the roster pointer, and appends `machine` and `compute_mode` to `COMPARISON_DIMENSIONS`; the runtime and comparison views render all of it |
| **Source** | `aidd_docs/backlog/stories/every-view-names-the-machine-and-mode-and-cpu-only-vram-reads-not-applicable.md`; parent epic `the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md`; PRD Methodology 21 and its two machine ACs; night-run owner decision D1 |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Row-level VRAM not-applicable across repetitions, aggregate and contract | [`phase-1.md`](./phase-1.md) |
| 2   | Read model: machine pointer, comparison dimensions, absence reason | [`phase-2.md`](./phase-2.md) |
| 3   | Front end: runtime and comparison views | [`phase-3.md`](./phase-3.md) |
| 4   | Live cpu_only row viewed in the dashboard; CHANGELOG and memory | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The marker is the string `"not_applicable"` (`gpu.VRAM_NOT_APPLICABLE`) written in `vram_used_mib` itself, on the row, every counted repetition and every warm-up; `null` keeps meaning "the read failed". | Same stated-non-applicability precedent as `engine_id` / `machine_id` `not_applicable`; a value in the field itself is what a `grep` over the row sees, and it can never be read as a number or confused with `null`. The constant lives in `gpu.py` because `row_contract` -> `aggregation` -> `repetitions` already import downward and `row_contract` cannot be imported by `repetitions`. |
| Under `cpu_only` VRAM is not read at all (`run_repetition_set(vram_applies=False)`); `gpu_draw_w` is still read and the GPU energy channel is untouched. | NVML `memory_info.used` is device-wide: it would publish the desktop's or the CUDA context's occupancy as the run's figure. Power and energy keep their own measurement and labels (epic Boundaries). |
| `aggregation.aggregate_peaks` replaces the inline peak loop: a metric whose every sample is the marker peaks to the marker; a mix of marker and value raises `AggregationError`. The `aggregation["vram_used_mib"]` label is unchanged. | A mixed set is a broken row, not a peak. The label names the statistic the field would carry and the contract compares only the label keys. |
| `row_contract.VRAM_NOT_APPLICABLE_SCHEMA_VERSION = "25"`, `SCHEMA_VERSION = "25"`: from "25" a `cpu_only` runtime row must carry the marker in all three places, and a `gpu` row must never carry it. Rows below "25" are not re-checked. | Acceptance: the two absences stay distinct, enforced at the writer gate rather than by convention. |
| Read model: fourth absence reason `not_applicable`, produced only for `vram_used_mib` holding the marker (detail names `compute_mode`). `engine_id`/`machine_id` `not_applicable` strings stay values. | Converting every `not_applicable` string would silently change the quality and comparison views' existing fields beyond this story. |
| `machine_id` resolves through `resolve_machine_entry` to the registry entry (`machine_id`, `description`, every fact with its `source`/`read_from`, `registry_version`), or `pointer_unresolved` naming `machine_id`. The service reads `ServiceSettings.machine_registry_path` (default the tracked `aidd_docs/roster/machines.json`). | Mirrors `resolve_roster_entry`; facts are returned with their source so the view marks each declared or not yet declared. |
| `machine_id`/`compute_mode` move to `RUNTIME_VIEW_FIELDS`; on quality rows they stay in `QUALITY_FIELDS_NOT_RENDERED` (the quality view does not render them) and are read by the comparison view as dimensions `machine` and `compute_mode`. | Acceptance names the runtime and comparison views only; the quality and energy views are out of this story's acceptance. |
| Live evidence goes into this task's `evidence/` folder, not the live stores. | Night-run rule. |
