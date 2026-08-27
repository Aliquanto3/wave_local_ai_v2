---
objective: "The classification suite holds 20 natively-authored items across EN/FR/DE at compliant shares with per-language reporting, and the published reference bundle (runtime + quality reference files, fiche registry, roster, suite snapshot) is regenerated under the current schema with two verdict-bearing runs each and a validator proof, superseding — never deleting — the old evidence."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Classification suite reaches twenty items, reference bundle regenerated

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship story 20 (suite reaches 20 items across EN/FR/DE, per-language reporting) then story 19 (bundle republished under the current schema), as one increment — story 20 first because story 19's regeneration runs against the bumped suite version and its prompt-set hash. |
| **Source** | `aidd_docs/backlog/stories/the-classification-suite-reaches-twenty-items-across-three-languages.md` (order 20), `aidd_docs/backlog/stories/the-published-reference-bundle-is-regenerated-under-the-new-schema.md` (order 19), PRD `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` (Methodology 4, 5, 8), epic `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md` |

## Phases

| #   | Phase                                                              | File                          |
| --- | ------------------------------------------------------------------- | ---------------------------- |
| 1   | Ten added items, suite version bump, per-language scoring + gate    | [`phase-1.md`](./phase-1.md) |
| 2   | Suite definition snapshot export                                    | [`phase-2.md`](./phase-2.md) |
| 3   | Live bundle regeneration on the bench machine (manual checklist)    | [`phase-3.md`](./phase-3.md) |
| 4   | README bundle inventory, reference-bundle test, CHANGELOG, memory   | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `aidd_docs/results/README.md` (current) | The two `*-reference.jsonl` files are curated snapshots no CLI writes to; `.gitignore` ignores every `aidd_docs/results/*.jsonl` except `*-reference.jsonl`, so a renamed superseded file (`runtime-reference.schema-1.jsonl`) no longer matches that negation pattern and needs its own `.gitignore` entry or it silently drops out of tracking. |
| `src/wave_local_ai_v2/prompt_provenance.py` | The "prompt templates" story 19 asks to be published beside the bundle are already the tracked source constants (`TEMPLATE_ID_NONE`, `TEMPLATE_ID_MISTRAL_CHAT_MESSAGE` + its content hash) — no new template file exists to export; the bundle satisfies this by the module already being committed source. |
| `src/wave_local_ai_v2/settings.py` | `RUNTIME_REFERENCE_PATH` / `QUALITY_REFERENCE_PATH` are read at write time by `verdict.runtime_verdict` / `verdict.quality_verdict` to decide each row's verdict — pointing the setting at a first run's copied rows before the second run is how the "second run carries a verdict against the first" requirement is met live, without new code. |
| `src/wave_local_ai_v2/row_contract.py` | `SCHEMA_VERSION` is currently `"6"`; every prior schema-shape change bumped it with a comment naming the story. Story 20's `language_breakdown` field is the next one. |
| `aidd_docs/roster/models.json`, `aidd_docs/results/fiches/*.json` | Already tracked and already resolvable by `roster_entry_id` / `fiche_hash` — no new artifact needed for these two bundle pointers, only the reference rows themselves need to cite the entries these files already hold. |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| The suite grows only in FR (+5) and DE (+5), EN stays at its existing 10 items. 20 items total gives EN 50%, FR 25%, DE 25% — both ≥25% — while every per-language cell (EN=10, FR=5, DE=5) still sits at or below `MIN_PER_LANGUAGE_CELL_ITEMS` (10), so FR/DE stay indicative per Methodology 4's own math, recorded as an observed consequence rather than re-tuned. |
| Per-language accuracy/n/indicative is computed in `scoring.py` (a new `score_suite_by_language`), reusing `suite_gate.LANGUAGES` and `suite_gate.MIN_PER_LANGUAGE_CELL_ITEMS` rather than redeclaring them — one threshold definition, not two. `suite_gate.py` does not import `scoring.py`, so this is a one-directional dependency, no cycle. |
| The per-language breakdown is a new required quality-row field (`language_breakdown`), added the same way every prior schema-shape change was: `row_contract.SCHEMA_VERSION` bumps `"6"` → `"7"`, comment names the story. It is batch-level (repeated on every item row of a suite run), the same pattern `suite_accuracy` already uses — it describes the batch, not the single item. |
| The suite definition snapshot is a small standalone module (`suite_snapshot.py`) with a `build_snapshot()` function and a `__main__` block writing to `aidd_docs/results/suite-definitions/<suite_id>.json`, not a new CLI entry point in `pyproject.toml` and not a registry — the epic explicitly excludes the suite-shape/registry work, and one suite exists today. |
| The superseded reference files are renamed in place (`git mv`) before the new regeneration writes to the now-freed `runtime-reference.jsonl` / `quality-reference.jsonl` filenames, and `.gitignore` gets an explicit negation for the new `*-reference.schema-*.jsonl` name shape so they stay tracked — the existing `!aidd_docs/results/*-reference.jsonl` pattern does not match a name ending in `.schema-1.jsonl`. |
| Phase 3's second run of each kind (runtime, quality) gets its verdict against the first by pointing `RUNTIME_REFERENCE_PATH` / `QUALITY_REFERENCE_PATH` at a temporary copy of the first run's own rows — no code change needed, the settings indirection already exists for exactly this. |

