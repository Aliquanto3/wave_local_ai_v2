---
status: pending
---

# Instruction: Stage B: the two published batches, promotion, merge and evidence

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── aidd_docs/results/machines/laptop-mobile-gpu/quality.jsonl  ✏️ two batches appended
├── aidd_docs/results/quality-reference.jsonl                  ✏️ merged
├── aidd_docs/results/fiches/                                  ✏️ a fiche if new
├── aidd_docs/results/README.md                                ✏️ the run section
└── tests/test_reference_bundle.py                             ✏️ the pair shares roster entry, fiche and engine build
```

## User Journey

```mermaid
flowchart TD
  A[committed tree] --> B[publication batch over the new suite]
  B --> C[development batch of classification-support-routing]
  C --> D[promote both run_ids]
  D --> E[merge-bundle, --check, validate, export + recompute]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Happy path
    two batches on one subject => rows tree_dirty false, same sha: 5: cli
    merge --check => exit 0: 5: cli
    recompute_from_export => every value matches: 5: cli
```

## Tasks to do

### `1)` Run and publish

> Both sizes carry `score_interval` on one subject from one committed tree.

1. Two batches, one session, one subject; promote; merge; check; README.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Both batches are in the bundle with `score_interval`, the same `roster_entry_id`, `fiche_hash` and `engine_build`, and the export and recompute run clean |
