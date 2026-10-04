---
objective: "The committed bundle is regenerated from the laptop's own tracked location under the current schema, from a fresh-clone setup walk, with the flagship and Qwen3-0.6B pairs in both modes, the schema-7 snapshot superseded and unpinned."
status: implemented
---

# Plan: The laptop proves both modes and republishes the bundle once

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | One bench session on the laptop regenerates the bundle under schema "30", proves `gpu` and `cpu_only` for Qwen3-0.6B, and supersedes the schema-7 snapshot |
| **Source** | `aidd_docs/backlog/stories/the-laptop-proves-both-modes-and-republishes-the-bundle-once.md` |

## Phases

| #   | Phase                                   | File                         |
| --- | --------------------------------------- | ---------------------------- |
| 1   | Fresh-clone setup walk                  | [`phase-1.md`](./phase-1.md) |
| 2   | Bench session                           | [`phase-2.md`](./phase-2.md) |
| 3   | Promote, merge, supersede, validator    | [`phase-3.md`](./phase-3.md) |
| 4   | README, docs, tech debt, tests          | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| Bench runs execute from the fresh clone (clean tree at the branch head), live stores and fiche registry pointed into this task's `evidence/`; promotion and merge run in the worktree from those stores | The rows then carry `tree_dirty: false` and the walk under test is the one that produced them; the tracked location lives in the worktree where the orchestrator commits |
| Each run 1 is decided against an empty reference file, each run 2 against a file holding only its own run 1 | "Second against the first" without the schema-7 bundle or another mode's run being a candidate reference |
| Quality pairs run `QUALITY_PROVIDERS=local,mistral` in one invocation per run, on `classification-support-routing@5` | Mirrors the bundle being regenerated (one `run_id` per run, both subjects); exactly 2 x 20 paid Mistral items (owner decision D6) |
| The German routing item (`account-de-01`) is re-deferred by name, not reworded | Rewording moves `prompt_set_hash` and forces suite version 6, outside D6's paid scope (`classification-support-routing@5`) and every record citing @5; the fresh Mistral pair is recorded as new evidence on it |
| Superseded files named `*-reference.schema-7.jsonl` (the schema version), unlike `schema-1` (a generation count) | The story, the merge's own refusal message and the pin's comment name `schema-7`; the README states both conventions |
| No `.env` key in the clone; `MISTRAL_API_KEY` injected only into the two quality commands' environment | Owner decision D6 |
| The quiet thermal window is asserted from a captured machine state, not confirmed by an operator | Orchestrator decision D8 (no operator present) |
| The schema-7 comparison and leader-set records are `git mv`-renamed into `comparisons.schema-7/` and `leader-sets.schema-7/` | They cite run ids that only the superseded rows hold, and the export refuses a record citing a run the bundle does not hold; kept unedited beside the rows they were computed over, like the rows themselves |
| The Parquet copy types `vram_used_mib` as a string, its dictionary unit naming the `not_applicable` identifier beside MiB | A float column must turn `not_applicable` into null, the value a failed read on a `gpu` row also takes; a string keeps the three cases apart, at the cost of a cast for a numeric reader (the CSV is unchanged) |
| Tests whose subject is a fixed set of real rows read the superseded schema-7 files; the current bundle is asserted in `test_reference_bundle.py`, the current export in `test_bundle_export.py::test_the_current_bundle_exports` and `test_recompute_from_export.py` | The schema-7 bytes never change again; the republished bundle will |
