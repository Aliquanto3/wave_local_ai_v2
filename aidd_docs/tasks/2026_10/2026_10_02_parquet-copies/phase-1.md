---
status: done
---

# Instruction: the pinned release group, the Parquet script and the archive's `--parquet`

## Architecture projection

```txt
.
├── pyproject.toml                         ✅ `release` group (pyarrow==25.0.1), mypy override
├── uv.lock                                ✅ pyarrow 25.0.1 locked
├── scripts/
│   ├── audit_dependencies.py              ✅ exports --all-groups
│   ├── release_parquet.py                 ✅ types, write, cell-by-cell check
│   └── assemble_release_archive.py        ✅ build/verify --parquet, README section
└── tests/
    ├── test_release_parquet.py            ✅ typing everywhere; Parquet where pyarrow is
    └── test_assemble_release_archive.py   ✅ build() returns (path, lines)
```

## Steps

1. `uv add --group release --no-sync pyarrow==25.0.1`; the audit exports every group so the release group is audited.
2. `release_parquet.py`: unit-to-kind table over every dictionary unit; `parse_cell` per kind (empty = None, timestamps as UTC microseconds); `write_parquet` typed from the dictionary; `check_parquet` reads back and compares columns, types, row count, then each cell; `build_copies`/`compare_copies` over the five tables.
3. `assemble_release_archive.py --parquet`: the copies join the expected files (byte-compared), `verify` also runs `compare_copies` on the archive's own files and returns one line per table, the README gains "Parquet copies" (CSV is right; pyarrow version), the clone-only scan skips `.parquet`.
4. Tests: every dictionary unit typed (runs in the matrix); parse/refusal cases; with pyarrow, equal copies, determinism, one altered cell fails, a value where the CSV is empty fails, wrong type / missing row / other columns / unreadable / missing copy fail, an altered copy in the archive fails `verify`, the command prints every table.
