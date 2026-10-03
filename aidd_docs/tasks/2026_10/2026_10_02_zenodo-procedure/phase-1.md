---
status: done
---

# Instruction: The procedure, its README link and its guard test

## Architecture projection

```txt
.
├── README.md                              ✅ (link + DOI rule pointer)
├── docs/
│   └── zenodo-deposit.md                  ✅ (new)
└── tests/
    └── test_zenodo_deposit_procedure.py   ✅ (new)
```

## User Journey

```mermaid
flowchart TD
  A[A venue asks for a DOI] --> B[Owner opens docs/zenodo-deposit.md]
  B --> C[Download the release asset unchanged]
  C --> D[New upload on Zenodo: values from CITATION.cff]
  D --> E[Publish, read the version DOI]
  E --> F[Branch: identifiers entry in CITATION.cff, line in README]
  F --> G[pytest tests/test_citation.py still passes]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Happy path
    Workflows parsed => none names Zenodo or a Zenodo token: 5: system
    CITATION.cff and README.md read => no 10.5072 sandbox DOI: 5: system
    README.md read => it links docs/zenodo-deposit.md: 5: system
  section Edge case
    A workflow text naming ZENODO_TOKEN => the check reports it: 1: system
    A citation text holding a 10.5072 DOI => the check reports it: 1: system
```

## Tasks to do

### `1)` Write `docs/zenodo-deposit.md`

> What to upload, every metadata value and its `CITATION.cff` source, the licence and the mixed-terms description, recording the DOI back, why nothing is automated, the sandbox proving walk and its corrections log, the deposit log.

### `2)` Link it from `README.md`

> One line in "Download the results (no clone)" and one in "Attribution and citation" naming where a DOI goes once one exists.

### `3)` Add `tests/test_zenodo_deposit_procedure.py`

> No workflow names Zenodo; no sandbox DOI in `CITATION.cff` or `README.md`; the README links the procedure; each helper reports a constructed violation.

## Validation

- `uv run pytest`, `uv run pre-commit run --all-files`, the secrets scan on the changed files, `scripts/audit_dependencies.py`, and both `wave-local-ai-v2-validate` runs, from the worktree root.
- Pending (owner): the sandbox walk and the corrections it causes, logged in the procedure's "Proving walk" section.
