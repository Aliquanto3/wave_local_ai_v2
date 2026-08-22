---
objective: "The four before-commit checks and the before-push test run refuse a bad commit at the machine that makes it, against a baseline scoped to what git tracks."
status: implemented
---

# Plan: The fast gate refuses a bad commit before it is written

## Overview

| Field      | Value                                                                             |
| ---------- | --------------------------------------------------------------------------------- |
| **Goal**   | Turn the manually-run fast gate into an installed hook, and rescope the secret baseline to the repository. |
| **Source** | `aidd_docs/backlog/stories/the-fast-gate-refuses-a-bad-commit-before-it-is-written.md` |

## Phases

| #   | Phase                             | File                         |
| --- | --------------------------------- | ---------------------------- |
| 1   | The gate exists and the tree passes it | [`phase-1.md`](./phase-1.md) |
| 2   | Three refused commits, kept as evidence | [`phase-2.md`](./phase-2.md) |
| 3   | The docs and the memory stop saying manual | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision                                                                                                     | Why                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| One `repo: local` block, every hook `language: system` invoking `uv run`                                     | Versions come from `uv.lock` alone. A `rev:`-pinned hook repo would install a second copy of ruff, mypy and detect-secrets that drifts from the ones the project actually runs. |
| The three tree-wide hooks use `pass_filenames: false` + `always_run: true`                                    | The hook entry stays byte-identical to the command in `coding-assertions.md`, so the gate and its documentation cannot diverge. Measured cost of the whole gate on this tree: 4.8s. |
| `default_install_hook_types: [pre-commit, pre-push]`                                                          | A single `uv run pre-commit install` wires both stages, so the documented install step is one line and a fresh clone cannot install half the gate.                              |
| `.secrets.baseline` regenerated with `detect-secrets scan --baseline`, not `--all-files`                       | `--all-files` is what put 35 `.venv/` entries and the untracked `.env` in the current file: without it the scan covers git-tracked files only, and `--baseline` registers the filter that keeps the baseline out of its own inventory. |
| pytest stays at `pre-push`                                                                                    | The commit-stage gate must remain a few seconds. Tests take ~4s today and will grow; paying that per commit is what makes people bypass a hook.                                 |
