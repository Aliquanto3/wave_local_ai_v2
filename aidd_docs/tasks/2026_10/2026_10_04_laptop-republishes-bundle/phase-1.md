---
status: done
---

# Instruction: Fresh-clone setup walk

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── docs/setup.md  ✏️ every step the walk needed that it did not name
└── aidd_docs/tasks/2026_10/2026_10_04_laptop-republishes-bundle/evidence/
    └── setup-walk.md  ✅ the walk's log and the gaps found
```

## User Journey

```mermaid
flowchart TD
  A[git clone the branch into a temp dir] --> B[follow docs/setup.md 1 to 4]
  B --> C{step setup.md did not name?}
  C -- yes --> D[record the gap, fix setup.md in the worktree]
  C -- no --> E[next step]
  D --> E
  E --> F[clone ready to run, no API key in its .env]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    clone the branch into a new temp dir => clean tree on feat/night-run-2026-10-02: 5: cli
  section Happy path
    uv sync, .env from .env.example, MACHINE_ID and COMPUTE_MODE set => the CLIs resolve the laptop profile: 5: cli
  section Teardown
    delete the clone after phase 2 => no throwaway tree left: 5: system
```

## Tasks to do

### `1)` Walk

> Reach a runnable clone with setup.md alone.

1. Clone, check out the branch, `uv sync`, `.env` from `.env.example` with `SLM_MODELS_DIR`, `LLAMA_SERVER_PATH`, `MACHINE_ID`, `COMPUTE_MODE`; no key.
2. Log each step and every gap in `evidence/setup-walk.md`.

### `2)` Fix setup.md

> One fix per gap, in the worktree.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1    | The clone's CLIs start a run under `laptop-mobile-gpu` and the mode's declared profile |
| 2    | Every gap logged has a matching sentence in `docs/setup.md` |
