---
status: done
---

# Instruction: The sampler, the rule record, and the registry's check of the added fields

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/
│   ├── subset_sampler.py      ✅ canonical ordering, stratified seeded draw, retries, content hash, rule record + check, replay comparison
│   └── suite_registry.py      ✏️ checks `selection_rule` and item `content_hash` where declared
└── tests/
    ├── subset_fixtures.py     ✅ the constructed source and a suite drawn from it, shared by three test modules
    ├── test_subset_sampler.py ✅ draw, replay, retry, stratification, gate at publication
    └── test_suite_registry.py ✏️ a drawn definition registers; a malformed rule is refused; the placeholder seam test drops its unreplayable rule
```

## User Journey

```mermaid
flowchart TD
  A[source rows, any order] --> B[canonical order: source, stable key]
  B --> C[strata: language, then label for classification]
  C --> D[Random seed: sample k per stratum]
  D --> E{accept: gate at publication}
  E -->|yes| F[items with content_hash + selection_rule: seed, attempts, seeds_tried]
  E -->|no| G[next seed, recorded] --> D
  F --> H[registry load checks rule and hashes]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    build a constructed classification source in en fr de with four labels => source table ready: 5: system
  section Happy path
    draw 102 items with seed 7 => attempts 1, every language and label stratum filled: 5: system
    gate the drawn items at publication => level publication: 5: system
    replay the rule over the same rows => same ids same order: 5: system
  section Edge case - shuffled source
    rows shuffled => replay => same ids same order: 1: system
  section Edge case - changed seed
    seed 8 => draw => different ids: 1: system
  section Edge case - edited source item
    one row text edited => replay => that item id named: 1: system
  section Edge case - retried draw
    accept refuses the first two seeds => draw => attempts 3, seeds_tried lists all three: 1: system
  section Edge case - final seed only
    rule with attempts 3 and one seed => registry load => refused naming seeds_tried: 1: system
```

## Tasks to do

### `1)` Sampler core

> A seeded draw that is a function of the seed and the canonical source only.

1. Constants `SAMPLER_VERSION`, `CANONICAL_ORDERING`, `CONTENT_HASH_VERSION`; `SubsetSamplerError`.
2. `normalise_text`, `content_hash(row, content_fields, benchmark)`.
3. `canonical_order(rows, stable_source_key, benchmarks)`: refuse unknown source, missing/duplicate key, language outside `suite_gate.LANGUAGES`.
4. `draw(rows, spec, seed)`: allocate per stratum, refuse an under-filled stratum naming it, `random.Random(seed).sample` per stratum, build drawn items.
5. `draw_with_retries(rows, spec, *, first_seed, accept, loader, max_attempts)`: record every seed; return items and the rule record; exhausted attempts refused naming every seed.

### `2)` Rule check and replay comparison

> The rule's shape is checked; a replay names what moved.

1. `check_selection_rule(rule, task_suite)` and `check_drawn_items(items, rule)` returning problems.
2. `replay(items, rule, rows)` -> `ReplayReport` (recorded ids, redrawn ids, items whose hash moved, items absent from the source, `reproduced`).

### `3)` Registry

> The added fields are checked at load.

1. When `selection_rule` is declared, run both checks and raise `SuiteRegistryError` naming the problems; an item `content_hash` without a rule is still checked for format.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Same seed and source give identical ids and order; shuffled rows give the same; another seed differs; classification draw fills every (language, label) stratum; first seed passes the publication gate; a retried draw records every seed |
| 2 | An edited source row is named by item id on replay; an unedited replay reports reproduced |
| 3 | A drawn definition registers at `publication` and its snapshot carries `selection_rule`; a rule recording only the final seed, a classification rule without label stratification, and a malformed content hash are refused |
