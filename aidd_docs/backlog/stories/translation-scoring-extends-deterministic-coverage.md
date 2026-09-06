---
type: story
status: done
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on: aidd_docs/backlog/stories/deterministic-classification-scoring-proves-quality-table-split.md
order: 3
---

# Story: Translation scoring extends deterministic coverage to a second use case

**As** a consultant
**I want** the translation task suite scored deterministically against the same models
**So that** I can show a second use case works on the proven scoring machinery, without yet widening the model roster

## Acceptance

- Running the translation task suite against the same local SLM and cloud model used in the classification Story produces a deterministic quality score for each.
- The result appears in the quality table alongside classification and rewriting results, attributable to the translation use case.

## Divergences from what was built

This story was written on 2026-08-21, before the benchmark-methodology epic
landed. Where it conflicted with the PRD's Benchmark Methodology or with the
shipped code, the implementation followed those and recorded the conflict.
Delivered by
`aidd_docs/tasks/2026_09/2026_09_06_translation-suite-scored-by-chrf/`.

| # | The story says | What was built | Why |
| - | -------------- | -------------- | --- |
| D1 | "the same local SLM and **cloud model**" — one cloud subject | Every provider in `QUALITY_PROVIDERS` (today `local`, `mistral`, `google`) | The Google subject landed after this story was written. Restricting translation to one cloud subject would build a narrower comparison than the classification suite already publishes. |
| D2 | The result appears "alongside classification **and rewriting** results" | Alongside classification only | The rewriting suite is a later story in the same epic and does not exist. The criterion is met for the two suites that do; nothing fabricates a rewriting row. |
| D3 | Silent on suite size, language mix, provenance, prompt-set hash, generation caps | The suite passes `suite_gate.gate_suite` and every row carries `suite_id` / `suite_version` / `prompt_set_hash` / `max_output_tokens` / `stop_sequences` / `context_length` | Methodology 2-5 and `suite_gate.py` post-date the story. Scope the story does not mention and the PRD requires. |
| D4 | "produces a deterministic quality score" — assumed to fit the existing row | `SCHEMA_VERSION` `"9"` → `"10"`, adding a conditional graded block; `correct`, `suite_accuracy` and `language_breakdown` are null on a translation row | `correct` is a boolean and `suite_accuracy` is an exact-match rate. A chrF mean is neither, and writing one into the other would publish a graded score under an exact-match name. |
| D5 | Assumes the verdict machinery works unchanged | `verdict.quality_verdict` decides on `item_score` when `predicted_label` is null on both sides | It compared `predicted_label` only, so two translation runs would have returned `reproduced` off two sets of nulls. Methodology 8 already allows it: "identical per-item predicted labels **or scores**". |
| D6 | Silent on `--resume` | `results.resume_skip_reason` gains a `task_suite` filter | It keyed on `(run_id, provider)` alone, so `--resume <classification-run-id> --suite translation` would have skipped a batch that never ran. |

One limitation is published rather than designed away: at seven items per
direction, all three per-language cells are marked `indicative` (the
threshold is 10). Clearing the mark needs nine more hand-authored reference
translations whose quality nobody in-project can natively verify for German.
A later story adds them if a native reviewer is available.

## Cancellation

n/a — not cancelled.
