# Night run, 2026-10-02

Branch `feat/night-run-2026-10-02` (worktree `wave_local_ai_v2-night`), cut from `main` at `c68b23e` (equal to `origin/main` after a fetch). Nothing pushed, no PR, no paid API call.

## Owner decisions (2026-10-02)

- D1 Professional PC gate waived: a-gpu-run-and-a-cpu-only-run-never-share-a-fiche and the stories after it are implemented although the-professional-pc-is-confirmed-able-to-take-part-before-code-depends-on-it stays open. A waived story marked done is noted "depends_on waived by owner 2026-10-02 (D1)" here. `depends_on` and acceptance are never edited.
- D2 No paid API call of any kind (cloud subjects, judges, calibration). Cloud logic is proven on constructed rows or stubbed HTTP; cloud evidence is logged as pending.
- D3 Citation: the mechanics ship with a clearly marked placeholder identity; the story stays `ready`, waiting for the owner's identity.

## Setup

- `git worktree add ../wave_local_ai_v2-night -b feat/night-run-2026-10-02 main`; `uv sync`. `pre-commit install` NOT run (hooks run with `uv run pre-commit run`). No `.env` in the worktree.
- Previous run (`2026_10_01_unattended-implementation/run-log.md`): it has no "Run rules learned" heading; the rules sit in its "Paused" section and "Housekeeping": resume a stalled subagent with SendMessage and smaller reads/writes; scan staged files with detect-secrets (`--all-files` scans nothing for that hook); a classifier-refused cherry-pick is replaced by `git show` reads; stop llama-server by PID, never `taskkill /IM`.
- Briefs: `implementer-brief.md`, `reviewer-brief.md` in this folder.
- Environment: GPU RTX 3060 Laptop 6 GB, 0 MiB used, no llama-server running at start. Docker daemon not running at start (`failed to connect to the docker API`).

Baseline gates:
- `uv run pytest` => "2097 passed, 2 warnings in 169.69s", total coverage 98.10% (floor 95%).
- `uv run pre-commit run --all-files` => ruff check, ruff format, mypy, detect-secrets Passed.
- `uv run python scripts/audit_dependencies.py` => "no findings / no blocking findings", exit 0.
- `uv run wave-local-ai-v2-validate` => quality-reference "checked 80 row(s)", runtime-reference "checked 2 row(s)", both exit 0.

## Stories

| # | Story | Outcome | Commits | Evidence |
| - | ----- | ------- | ------- | -------- |
