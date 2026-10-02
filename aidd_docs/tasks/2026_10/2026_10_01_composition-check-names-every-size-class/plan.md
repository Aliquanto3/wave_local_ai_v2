---
objective: "A command reads the roster and reports, per size class, its families, its dense and MoE presence and its ladder label, exiting non-zero naming every class or entry the roster is silent about; on the shipped roster it names all four classes as unlabelled single-family ones, and every quality row written afterwards carries its subject's family and size class."
status: implemented
---

# Plan: The composition check names every size class and refuses an unlabelled single-family one

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Add the size-class vocabulary and bands, the three per-entry figures and the per-class declaration to the roster, the composition-check command, `family`/`size_class` on quality rows at schema "19", and the README composition section quoting the shipped roster's calibration output. |
| **Source** | `aidd_docs/backlog/stories/the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one.md` (PR-head text on `docs/slice-remaining-epics`, status `ready`); owner answers Q10 (a), Q11 (a), Q12 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Roster: size-class vocabulary, the three figures, the per-class declaration, shipped data at version 4 | [`phase-1.md`](./phase-1.md) |
| 2   | The composition-check module and command, over constructed and shipped rosters | [`phase-2.md`](./phase-2.md) |
| 3   | `family` and `size_class` on quality rows at schema "19" | [`phase-3.md`](./phase-3.md) |
| 4   | README composition section, documented pre-publication step, memory | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The vocabulary is `~0.5B`, `~2B`, `~4B`, `~8B-and-up`, banded on total parameters with lower edges 1e9, 3e9, 6e9 held in `roster.SIZE_CLASS_BANDS` beside `SIZE_CLASSES`. | Q10 (a). One table of (class, lower edge): moving an edge is a value change; the check reads the table, never literal numbers. |
| `size_class` and `bytes_on_disk` sit on the entry; `total_params` (an exact integer count) sits in `architecture` beside `active_params_b`. All three are optional at load and shape-checked when present; the check names an entry missing any of them. | The check must be able to *name* an entry with no class, so the loader cannot refuse it first (same seam as `family`, `licence`). An integer count makes "just below 1B" exact. `bytes_on_disk` is a file fact like `sha256`; total parameters a model fact like active parameters. |
| The per-class declaration lives in the roster file as a top-level `size_classes` object keyed by class: `single_family_ladder`, `moe_sought`, `moe_entry`, `moe_absent_reason`. Optional at load, shape-checked when present; a non-empty class with no declaration is named by the check. | Data, never README prose; one file to review. The bundle export reads `entries` only, so the top-level block cannot leak an undescribed column. |
| The shipped roster declares its honest state: every class `single_family_ladder: false`, the three dense classes `moe_sought: false` with no reason, the top class `moe_sought: true` with the flagship as its MoE entry. | The story forbids labelling the shipped roster here (the search is orders 5 to 8); recording "not sought" makes the calibration name the silence rather than hide it. |
| Beyond the story's listed failures, the check also names a class labelled a single-family ladder that spans two or more families, and a declared `moe_entry` that is not a MoE entry of that class (or a MoE entry the declaration omits). | A label or a MoE claim that contradicts the entries would be published beside them; the epic wants the classing falsifiable from the file. Neither fires on the shipped roster or on any story-listed passing case. |
| A class with no entries is reported as empty and not failed. | The PRD rule reads "each size class it publishes"; an empty class publishes nothing. |
| Exit codes: `0` passes, `1` names failures, `2` the roster file cannot be loaded. | Mirrors `candidate_gate` (`2` = nothing could be checked). |
| A quality row's `family` is its *subject's* family (`roster.family_of(model_id, entry)` for a local row, `family_of(model_id)` for a cloud row); `size_class` is the entry's for a local row and `null` for a cloud row. | A cloud row cites the local entry it ran beside, so "the entry it cites" would stamp `qwen` on a Mistral row. A cloud model has no size class. Noted as a backlog wording gap in the report. |
| Schema "19" fields are required only on a row whose own `schema_version` is "19" or later (`row_contract.SUBJECT_COMPOSITION_SCHEMA_VERSION`). | Story test: an earlier-version row still validates. Writers always stamp the current version, so the gate is not weakened for new rows. |
| `family`/`size_class` go in `read_model.QUALITY_FIELDS_NOT_RENDERED`. | The epic excludes rendering the composition to a reader; the partition test still forces the decision to be explicit. |
| `candidate_gate`'s pass entry carries `bytes_on_disk`, `architecture.total_params` and the `size_class` `roster.size_class_for` bands them in (review finding 2). | The gate already reads both figures off the file; the band is deterministic (Q10), so the pass entry the author copies is complete and agrees with the composition check by construction. |
| The composition check is not added to the merge gate or to CI. | Acceptance: the shipped roster is expected to fail it. |
