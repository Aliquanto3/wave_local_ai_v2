---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Reproduction verdict: the named run is the compared run, and unknowns never match

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/
│   └── verdict.py        ✏️ C1: quality reference narrowed to one run; C2: null blocking field => not_comparable
├── tests/
│   └── test_verdict.py   ✏️ two-reference-run test; null-on-either-side tests
└── aidd_docs/tasks/2026_08/
    └── 2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md  ✏️ one sentence in Methodology 8 recording the null rule
```

## User Journey

```mermaid
flowchart TD
  A[Writer computes a verdict before append_row] --> B{Runtime or quality}
  B -->|runtime| C{Any blocking field null on candidate fiche}
  C -->|yes| D[not_comparable, differing_fields names the null field]
  C -->|no| E[Match references, skipping any whose blocking field is null]
  E -->|no match| F[not_comparable, closest reference's differing fields, null counted as differing]
  E -->|match| G[reproduced or not_reproduced on gen_tok_per_s]
  B -->|quality| H[Matching reference rows grouped by run_id]
  H --> I[First run in file order is the reference]
  I --> J[Items compared against that run only; reference_run_id names it]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    Register fiches and build reference rows in tmp_path => registry and rows ready: 5: system
  section Happy path
    Two reference runs cover the same items, first run's labels match, second's differ => verdict reproduced, reference_run_id is the first run's: 5: system
    Candidate and reference fiches share every non-null blocking field and medians agree => verdict reproduced: 5: system
  section Edge case - two reference runs, first differs
    First run's labels differ on one item, second run's match => quality verdict => not_reproduced naming that item and the first run's id: 1: system
  section Edge case - null on both sides
    Both fiches carry llama_cpp_build null, everything else equal => runtime verdict => not_comparable, differing_fields names llama_cpp_build: 1: system
  section Edge case - null on the reference only
    Reference fiche carries gpu_name null, candidate's is set => runtime verdict => not_comparable, differing_fields names gpu_name: 1: system
  section Edge case - null on the candidate only
    Candidate fiche carries flags null => runtime verdict => not_comparable naming flags, no reference scanned as a match: 1: system
```

## Tasks to do

### `1)` Quality verdict names the run it compared against (C1)

> `reference_by_item` and `reference_run_id` come from the same single run.

1. In `quality_verdict` (`verdict.py:273-324`), after `select_quality_references`, keep only the rows whose `run_id` equals the first matching row's `run_id` (file order); build `reference_by_item` from those rows only.
2. Every returned block (`unmatched_items`, no-comparable-field, final) takes `reference_run_id` from that chosen run.
3. Document the rule in the `quality_verdict` docstring: several reference runs => the first in file order, same tie-break as `select_runtime_reference`.
4. Add `test_quality_two_reference_runs_compare_against_the_named_run` and its mirror (first run differs, second matches => `not_reproduced`) in `tests/test_verdict.py`.

### `2)` A null blocking field never matches (C2)

> null on either side of `_RUNTIME_BLOCKING_FIELDS` => `not_comparable` naming the field.

1. Add a helper returning the blocking fields that are `None` in a fiche.
2. In `runtime_verdict`, before `select_runtime_reference`: when the candidate fiche has any null blocking field, return `not_comparable` with `differing_fields` naming each such field and a reason stating a null blocking field cannot be compared.
3. In `select_runtime_reference`, skip a reference whose fiche has a null blocking field.
4. In `_closest_reference_differing_fields`, count a field null on either side as differing even when both are null.
5. Update the module docstring (`verdict.py:1-11`) with the null rule.
6. Add three tests: null on both sides, reference only, candidate only; each asserts `not_comparable` and the named field.

### `3)` Record the rule in the PRD (C2)

> One sentence, Methodology 8.

1. In PRD Methodology 8 (`2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md:50`), after the sentence listing the verdict-blocking fiche fields, add: a verdict-blocking field that is null on either side makes the pair not comparable, naming that field; two unknown values never count as a match.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | With two reference runs of one batch, `reference_run_id` names the run whose items decided the verdict, and a disagreement confined to that run changes the verdict |
| 1 | Existing quality verdict tests pass unchanged |
| 2 | A runtime pair where `llama_cpp_build` is null on both fiches is `not_comparable` with `llama_cpp_build` in `differing_fields`, never `reproduced` |
| 2 | A null blocking field on only one side yields `not_comparable` naming that field |
| 2 | A pair with every blocking field non-null behaves exactly as before (existing runtime verdict tests pass unchanged) |
| 3 | PRD Methodology 8 states the null rule in one sentence and no other PRD line changes |
