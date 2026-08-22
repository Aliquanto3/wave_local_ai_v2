---
status: done
---

# Instruction: Three refused commits, kept as evidence

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
└── aidd_docs/tasks/2026_08/2026_08_22_fast-gate-pre-commit-hook/
    └── evidence.md            ✅ the three refusals and the three passes, transcribed
```

Everything the falsification touches outside this file is throwaway: three scratch
files and one scratch branch, all deleted before the phase closes. Nothing is pushed.

## User Journey

```mermaid
flowchart TD
    A[Cut a scratch branch] --> B[Stage a file carrying a planted fake AWS key]
    B --> C[Commit refused by the secret hook]
    C --> D[Remove the key, commit succeeds]
    D --> E[Stage a file with an unused import]
    E --> F[Commit refused by ruff check]
    F --> G[Remove the import, commit succeeds]
    G --> H[Stage an unformatted file]
    H --> I[Commit refused by ruff format --check]
    I --> J[Format the file, commit succeeds]
    J --> K[Transcribe the six outcomes into evidence.md]
    K --> L[Delete the scratch files and the scratch branch]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    Cut a scratch branch from the working branch => an isolated branch that is never pushed: 5: cli
  section Happy path
    Fix each scratch file and re-commit => each commit is written and the hook stays silent: 5: cli
    Transcribe the six hook outputs => evidence.md names each check and the reason it gave: 5: cli
  section Edge case - planted credential
    A staged file carries a fake AWS access key => run git commit => the commit is refused and the secret hook names AWS Access Key: 1: cli
  section Edge case - lint violation
    A staged file carries an unused import => run git commit => the commit is refused and ruff check names F401: 1: cli
  section Edge case - unformatted file
    A staged file passes lint but not formatting => run git commit => the commit is refused and ruff format names the file: 1: cli
  section Teardown
    Delete the scratch files and the scratch branch => the working branch carries only evidence.md: 5: cli
```

## Tasks to do

### `1)` Set up the falsification, isolated

> Nothing this task creates survives it, apart from the transcript.

1. From the working branch, cut a scratch branch (for example `chore/fast-gate-falsification`). Every commit below lands there and none is pushed.
2. Confirm the hooks are live first: `git config core.hooksPath` and the presence of `.git/hooks/pre-commit`. A green result from a hook that never ran is not evidence.

### `2)` Refuse three commits, then let each through

> One file per check, so each refusal is attributable to its own reason.

1. Planted credential: a scratch Python file assigning the canonical fake key `AKIAIOSFODNN7EXAMPLE`. Stage, commit, capture the refusal — verified to trip `AWSKeyDetector`. Remove the assignment, commit again, capture the pass. <!-- pragma: allowlist secret -->
2. Lint violation: a scratch Python file with an unused import. It is correctly formatted, so only `ruff check` can refuse it. Stage, commit, capture the refusal naming `F401`. Delete the import, commit again, capture the pass.
3. Formatting only: a scratch Python file whose sole defect is layout ruff would rewrite (for example `x = [1,2,3]`). It must pass `ruff check` — confirm that before committing, otherwise the refusal is attributed to the wrong hook. Stage, commit, capture the refusal from `ruff format --check`. Run `uv run ruff format` on it, commit again, capture the pass.
4. Stage each scratch file on its own. Two defects in one commit means the first failing hook masks the second.

### `3)` Write the transcript and clean up

> The evidence is the six outputs, not the claim that they happened.

1. Write `evidence.md` in this phase's folder: one section per check, holding the exact command, the shortest decisive line of the hook output, and the same command passing after the fix.
2. Record which hook refused each commit by name, so the transcript proves attribution rather than mere failure.
3. Delete the three scratch files, return to the working branch, delete the scratch branch. Confirm `git status` is clean apart from `evidence.md`.

## Test acceptance criteria

| Task | Acceptance criteria                                                                                                       |
| ---- | ------------------------------------------------------------------------------------------------------------------------- |
| 1    | The falsification runs on a branch that is never pushed, and the hook files are shown to be installed before the first commit attempt. |
| 2    | Three commits are refused, each by a different named hook, and each of the three succeeds once its single defect is removed. |
| 3    | `evidence.md` carries six transcripts naming the refusing hook, and the tree afterwards holds no scratch file and no scratch branch. |
