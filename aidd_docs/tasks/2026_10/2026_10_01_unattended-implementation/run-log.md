# Unattended implementation run, 2026-10-01

Branch `feat/ready-stories-unattended` (worktree `wave_local_ai_v2-impl`), cut from `docs/slice-remaining-epics` at `ef1249e`.

## Final report

_Pending: written at the end of the run._

## Setup

- Environment: `uv sync`, `uv run pre-commit install`. No `.env` in the worktree, and no cloud API key in the shell environment: no paid call is reachable.
- Baseline: `uv run pytest` => 1015 passed, coverage 95.74% (floor 95%). `uv run pre-commit run --all-files` => ruff check, ruff format, mypy, detect-secrets all passed.
- Local evidence prerequisites: pinned build `llama-b10537-bin-win-cuda-12.4-x64/llama-server.exe` present; `D:\ia\models` holds all four roster GGUFs. Local runs pass `LLAMA_SERVER_PATH`/`SLM_MODELS_DIR` explicitly, with `QUALITY_PROVIDERS=local` and results paths outside the committed stores.
- Side effect: `pre-commit install` in the worktree rewrote the shared `.git/hooks/pre-commit` and `pre-push` to point at the worktree venv. After removing the worktree, re-run `uv run pre-commit install` in the main repo.

## Stories

| # | Story | Outcome | Commits | Evidence |
| - | ----- | ------- | ------- | -------- |
| 1 | every-quality-batch-publishes-its-interval-and-what-it-could-resolve | skipped: acceptance wrong against the math | none | The acceptance requires the bootstrap to agree with Wilson 95% within 0.01 on each bound at n=20, p=0.80. Wilson(16/20) = [0.5840, 0.9193]. A bootstrap quantile over 20 binary items lies on the 0.05 grid, so the upper bound misses by at least 0.019. Checked with a stdlib percentile bootstrap (10 000 resamples, seeds 1/2/3 => [0.60, 0.95]). n=100 passes or fails depending on the seed (upper bound 0.87 or 0.88 vs 0.8666). Owner fix options: widen the tolerance at n=20, check Wilson only at n>=100, or use exact binomial quantiles as the reference. Also open: the story does not define the minimum detectable effect beyond "read off the same resample". No in-scope story depends on it. |
