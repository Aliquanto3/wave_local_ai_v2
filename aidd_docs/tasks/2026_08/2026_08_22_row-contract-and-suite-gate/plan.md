---
objective: "Every runtime and quality row is refused unless contract-complete and schema-versioned, and the classification suite declares its caps, tags, hash and gate verdict, with today's 10-item suite landing marked indicative."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Row contract and suite gate

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship the row contract + writer gate (Story: rows-carry-a-schema-version...) and the suite's caps/tags/language-mix declaration + gate (Story: a-suite-declares-its-caps-tags-and-language-mix), as one increment, row-contract first. |
| **Source** | `aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md` (order 2), `aidd_docs/backlog/stories/a-suite-declares-its-caps-tags-and-language-mix.md` (order 1), PRD `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` (Methodology 2, 3, 4, 5, 19), epic `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md` |

## Phases

| #   | Phase                                          | File                          |
| --- | ----------------------------------------------- | ---------------------------- |
| 1   | Row contract + writer gate + schema_version      | [`phase-1.md`](./phase-1.md) |
| 2   | Suite caps/tags/hash + suite_gate                | [`phase-2.md`](./phase-2.md) |
| 3   | quality_cli writes suite fields, contract extended | [`phase-3.md`](./phase-3.md) |
| 4   | Docs: README tag example, codebase map, CHANGELOG | [`phase-4.md`](./phase-4.md) |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| Phase 1's initial `REQUIRED_FIELDS` per row kind is exactly the set of keys the current two writers already always populate (every `TypedDict` field the runtime/quality row assembly spreads in today, confirmed present-even-when-None: `hardware.HardwareFiche`, `timings.Timings`, `gpu.GpuStats`, `energy.EnergyResult` all degrade to an explicit `None` value, never an absent key) plus `schema_version` itself. This makes phase 1 a pure gate on the status quo — it cannot fail the two existing CLIs — and phase 2/3 then *extend* that one contract with the suite-declared fields (caps, suite id/version/hash, item tags, indicative mark), which is the "single list every later story extends" the row-contract story requires. |
| `schema_version` is a plain string constant (e.g. `"1"`), bumped by hand when a required-field set changes; `read_rows` gains an optional `schema_version` filter rather than the store being rotated. This is Methodology 19 and the epic's row-contract decision, applied literally: rows of several versions coexist in one untracked per-machine file, selected at read time. |
| `suite_gate.py` accepts any object exposing the required attributes/keys (duck-typed, not `isinstance(suite, ClassificationSuite)`), per the story's "validates fields, not a suite shape" and the epic's boundary that the suite-shape/registry work is a sibling epic's. |
| The prompt-set hash is SHA-256 over a stable, deterministic serialization of the suite's item prompts (e.g. sorted-by-`item_id` join of `prompt` strings) — not over the whole `ClassificationItem` dicts, so adding a non-prompt field later does not silently change the hash the story requires to move only when a prompt changes. |
| The current 10-item EN-only suite is left at 10 items (no retrofit to 20 in this increment — that one-time retrofit is explicitly a separate, later piece of the epic's boundary). Phase 2's gate must therefore mark it indicative for two independent reasons at once (below 20 items, and FR/DE share at 0% < 25%), and phase 2's tests assert the *reason text* names both. |
