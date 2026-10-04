---
status: done
---

# Instruction: Roster entry, class declaration, docs, tests (stage A)

## Architecture projection

```txt
.
├── aidd_docs/roster/models.json            ✏️ one entry from the pass record, roster_version 10
├── aidd_docs/results/README.md             ✏️ composition block regenerated + the class's section
├── docs/setup.md                           ✏️ 1.2 requirements rows, 3.6 download section
├── aidd_docs/memory/cli.md                 ✏️ roster table, composition check passes
├── .secrets.baseline                       ✏️ the public pins
├── tests/test_roster.py                    ✏️ new entry, version 10, top class
├── tests/test_composition_check.py         ✏️ every class passes
└── tests/test_playground.py                ✏️ options list the new entry
```

## Tasks to do

1. Copy the pass record's `entry` into `models.json` with `requirements` (lower bounds, the weights' size); bump to 10; the `~8B-and-up` declaration stays as it is (the flagship is its MoE).
2. Regenerate the README block; add the class section (candidates, quant difference, licence, dense and MoE, launch, spike line, untested tower dependency, language claim).
3. `docs/setup.md` 1.2 rows and 3.6; `cli.md`; tests; secrets baseline.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | The roster loads; the composition check exits 0 |
| 2 | The README block equals the check's output |
| 3 | `uv run pytest` passes at the coverage floor |
