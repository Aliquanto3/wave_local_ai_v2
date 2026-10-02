---
status: done
---

# Instruction: Run over the committed bundle, README and memory

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── aidd_docs/results/README.md          ✏️ five tables; the fifth table's rules; leader-set section points at it
├── aidd_docs/memory/cli.md              ✏️ export command names the fifth table and its flags
├── aidd_docs/memory/codebase-map.md     ✏️ export entry names the records
└── aidd_docs/tasks/2026_10/2026_10_01_comparison-and-leader-records-fifth-table/
    └── evidence/fifth-table-run.md      ✅ command output, manifest parts, the 14 rows summarised
```

## User Journey

```mermaid
flowchart TD
  A[Export the committed bundle twice into temp dirs] --> B[cmp every file: identical]
  B --> C[Summarise comparison_records.csv with shortened ids]
  C --> D[Name the table in the results README]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Happy path
    Export the committed bundle => seven files, comparison_records 14 rows: 5: cli
    Second run => byte identical: 5: cli
```

## Tasks to do

- [x] Run the export twice; record output in `evidence/fifth-table-run.md`
- [x] README: five tables, the fifth table's rules, the leader-set section's stale "not built yet" line replaced
- [x] Memory: `cli.md`, `codebase-map.md`
