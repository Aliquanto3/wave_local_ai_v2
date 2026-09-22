---
objective: "Every in-scope finding of the 2026-09-22 audit is fixed and proven by a test or a CI guard, and the backlog records the rest without a parallel row."
status: in-progress
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Audit hardening increment

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | Close audit findings C1, C2 (null rule), W5, the comparison column-key seam, W10, W11, the W7 parity test and W21; close tech-debt rows 9, 20, 38; log the two story-sized items as backlog notes, merged into existing rows where the report says one exists. |
| **Source** | `aidd_docs/tasks/2026_09/2026_09_22_audit/report.md` plus the user's scoping text (C3 and the two story-sized items, frontend-type binding W2 and shared writer extraction W3/W7/W8/W9/W13/W14/M6/M7, are out of scope). |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Reproduction verdict: the named run is the compared run, and unknowns never match | [`phase-1.md`](./phase-1.md) |
| 2   | Read side: runtime label on its own metric, comparison key built from the dimension list | [`phase-2.md`](./phase-2.md) |
| 3   | CI integrity guards: committed evidence re-verified, sampling parity, branch coverage | [`phase-3.md`](./phase-3.md) |
| 4   | Backlog: close fixed rows, log story-sized items without duplicates | [`phase-4.md`](./phase-4.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| C1: with several reference runs matching one batch, the quality verdict compares against the **first run in file order** and names that run; it does not return `not_comparable` on the ambiguity. | The two-quality-runs protocol (tech-debt row 94) puts two runs per batch in every regenerated bundle, so refusing on ambiguity would make every verdict `not_comparable`. File order is already the runtime verdict's only tie-break (`verdict.py:57`), so both verdicts share one rule. |
| C2: a verdict-blocking fiche field (`llama_cpp_build`, `quant`, `gpu_name`, `flags`) that is null on either side makes the pair not comparable, naming the field; null never equals null. Recorded as one sentence in PRD Methodology 8. | User decision. Consequence accepted and stated: a host whose fiche records `gpu_name: null` (no NVIDIA GPU, `hardware.py:60`) never receives `reproduced`, it receives `not_comparable` naming `gpu_name`. Aligning the blocking set with Methodology 8's "compute mode" and the fiche-hash wording is left out of this increment. |
| Out-of-scope audit findings are not transcribed row by row into `tech-debt.md`; the audit report stays their record. Only the two story-sized items get backlog notes, and each merges into an existing row when the report names one. | The severity gate routes 🟢 *review* findings to `tech-debt.md` (`GUIDELINES.md:19`); an audit is not a review, and copying ~50 rows would create the parallel records the dedupe instruction forbids. |
