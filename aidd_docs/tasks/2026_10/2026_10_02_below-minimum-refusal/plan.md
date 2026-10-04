---
objective: "Every roster entry declares a minimum RAM, VRAM (gpu only) and disk per compute mode with its calibration source; a pre-flight check in the three writers refuses a run below a declared minimum before the weights are looked for or llama-server starts, writes no row, and publishes one refusal record per refusal in a tracked per-machine file."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A model below its declared minimum refuses, and the refusal is published

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `requirements` per entry per mode in `models.json` (`{value, source, read_from}`), required and validated by `roster.load_roster`; `preflight.py` observes the machine (total RAM, allocatable VRAM, free disk when the weights are absent), refuses naming requirement, mode, declared and observed values, and writes one refusal record (`row_contract.validate_refusal`, `results.append_refusal`) to `REFUSALS_DIR/<machine_id>.jsonl`; called from the three writers right after the run profile resolves, before the model path |
| **Source** | `aidd_docs/backlog/stories/a-model-below-its-declared-minimum-refuses-and-the-refusal-is-published.md`; parent epic `the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md`; night-run owner decision D1 |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Declared requirements and their loader, calibrated from published peaks | [`phase-1.md`](./phase-1.md) |
| 2   | The pre-flight check and its placement in the three writers | [`phase-2.md`](./phase-2.md) |
| 3   | The refusal record, its contract and its per-machine file | [`phase-3.md`](./phase-3.md) |
| 4   | Docs, CHANGELOG, the raised-then-lowered live proof on the laptop | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Requirements live on the roster entry (`requirements.<mode>.<ram_gb|vram_gb|disk_gb>`), not in `profiles.json`. Both modes are required; `vram_gb` is required under `gpu` and refused under `cpu_only`. | A minimum is a property of the model in a mode, not of a machine; the profile registry is per machine. "Code it changes" allows either home. |
| Unit: decimal GB (10^9 bytes) for every declared and observed value; observed RAM is `psutil.virtual_memory().total`, observed disk is `shutil.disk_usage(SLM_MODELS_DIR).free`. | The published peaks the story cites ("15.2 GB RSS") are decimal; one unit avoids a GiB/GB mix in the comparison. |
| gpu RAM minimums = the published runtime peaks (`process_rss_bytes`, `aidd_docs/results/README.md` side-by-side runtime table): 15.23 / 1.08 / 2.28 / 4.28 GB. | Acceptance line 1. |
| cpu_only RAM: the 0.6B from its measured cpu_only peak (4761899008 B, committed evidence of the named-run-profiles story); the three others declare a lower bound, the larger of their gpu-mode peak and their weights' `bytes_on_disk` (a cpu_only run holds every weight in host memory and at least what the gpu run held there), labelled as a lower bound in `read_from`. | No cpu_only peak is published for them; a bound derived from two published figures is sourced, not invented, and a too-low one surfaces as a run that starts and then fails (disclosed in `docs/setup.md`). |
| gpu VRAM: `not_yet_declared` for all four. The published `vram_used_mib` is NVML's device-wide used memory (4527 MiB for the 0.6B, whose weights are 0.64 GB; 6115 MiB for the 4B, above the laptop's declared 5.1 GB allocatable it ran on), not the model's own need. A `not_yet_declared` requirement is not checked and the pre-flight says so on stderr. | "None is invented": a device-wide figure would refuse runs that are published as successful. Same honesty discipline as machines and profiles (D1). |
| disk = `bytes_on_disk` of the weights, both modes; checked only when the weights file is absent. | Acceptance line 2. |
| Observed VRAM: the machine's declared `vram_allocatable_gb` when declared, else NVML's reported total; neither available with a declared VRAM requirement is a pre-flight error (exit 1), not a refusal record. | Acceptance line 2; a record would claim a measured shortfall that was never observed. |
| The pre-flight runs right after `profiles.resolve_for_run` and before `_local_model_path` / `server.build_flags`. | The record carries the profile id; a triple with no runnable profile is already refused by the resolver. |
| First failing requirement wins, checked in the order RAM, VRAM, disk: one refusal, one record. | The story's record names "the failed requirement". |
| `RequirementRefusal` and `PreflightError` subclass `roster.RosterError`. | Every writer's `main` already maps a `RosterError` to one stderr line and exit 1; no new handler. |
| Refusal record: its own contract (`row_contract.REFUSAL_FIELDS`, `REFUSAL_CONTRACT_VERSION` "1", `record_kind` "refusal"), no `schema_version`; `REFUSALS_DIR` (default `aidd_docs/results/refusals/`, tracked: the ignore rule covers only top-level `aidd_docs/results/*.jsonl`) holds `<machine_id>.jsonl`. No row schema bump. | Acceptance line 6; a record without `schema_version` is never selectable by a runtime view's schema floor. |
| The requirement field is required by `load_roster` only; `roster.parse_entry` (the candidate gate's pass check) keeps it optional. | A candidate has no measured peak before its first run; its block is copied into `models.json`, where `load_roster` then demands the calibrated declaration. |
| `roster_version` 5 -> 6. | The roster gains a required field. |
| Live evidence goes to this task's `evidence/`, never the committed stores. | Night-run rule. |
