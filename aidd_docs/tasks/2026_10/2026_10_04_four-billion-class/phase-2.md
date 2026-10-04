---
status: done
---

# Instruction: Roster entry, class declaration, docs, tests (stage A)

## Architecture projection

```txt
.
├── aidd_docs/roster/models.json            ✏️ one entry from the pass record, roster_version 9, ~4B declaration names its MoE
├── aidd_docs/results/README.md             ✏️ composition block regenerated + the class's section
├── docs/setup.md                           ✏️ 1.2 requirements rows, 3.5 download section
├── aidd_docs/memory/cli.md                 ✏️ roster table
├── tests/test_roster.py                    ✏️ new entry, version 9, ~4B declaration
├── tests/test_composition_check.py         ✏️ ~4B passes, one failure left
└── tests/test_playground.py                ✏️ options list the new entry
```

## Tasks to do

1. Copy the pass record's `entry` into `models.json` with `requirements` (lower bounds, the weights' size); bump to 9; declare `~4B` (`moe_sought: true`, `moe_entry`).
2. Regenerate the README block; add the class section (candidates, quant, licence basis, MoE, spike lines).
3. `docs/setup.md` 1.2 rows and 3.5; `cli.md` table; tests.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | The roster loads; the composition check prints no `size class ~4B` failure |
| 2 | The README block equals the check's output |
| 3 | `uv run pytest` passes at the coverage floor |
