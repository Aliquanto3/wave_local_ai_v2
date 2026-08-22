# Review: CI check suite

- **Verdict**: approve (all five warnings resolved; counts below are what the review found)
- **Diff**: `main...working tree (feat/ci-check-suite)`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 5 warning, 10 minor

## Phases

### Phase 1 — Coverage plumbing

- [x] `uv sync --locked` succeeds and installs `pytest-cov`; `uv.lock` carries the new entry — `pyproject.toml:43`, `uv.lock` gains `pytest-cov` + `coverage`; run: `Resolved 84 packages / Checked 84 packages`, exit 0
- [x] `uv run pytest` prints a coverage summary and writes `coverage.xml`; total close to 98% (443 statements, 11 missed) — run: `TOTAL 443 11 98%`, `Coverage XML written to file coverage.xml`
- [x] Dropping coverage below 80% makes `uv run pytest` exit non-zero with the missing lines named — `pyproject.toml:23` (`--cov-fail-under=80 --cov-report=term-missing`); falsified with `--cov-fail-under=99`: `FAIL Required test coverage of 99% not reached. Total coverage: 97.52%`
- [x] After `uv run pytest`, `git status` shows no untracked `.coverage`, `coverage.xml`, `htmlcov/` — `.gitignore:28-30`; `git status --porcelain` after the run lists none

### Phase 2 — Dependency audit tool

- [x] `uv sync --locked` installs `pip-audit`; `uv run pip-audit --version` succeeds — `pyproject.toml:40`; `uv run pip-audit --format json --locked -s osv <pylock dir>` ran and emitted JSON for 84 packages
- [x] `docs/dependency-waivers.yml` exists, parses as valid YAML, states blocking severities and the 90-day rule in its header, zero entries — `docs/dependency-waivers.yml:1-17`
- [x] `uv run python scripts/audit_dependencies.py` exits 0 against the current lock — run: `no findings` / `no blocking findings`, `EXIT=0`
- [x] `uv run pytest tests/test_audit_dependencies.py` passes and the two waiver cases are non-vacuous — 4 passed; mutation check (both assertions flipped to `is True`) gave `2 failed, 2 passed`, restored to `4 passed`

### Phase 3 — CI workflow

- [x] Workflow triggers on push and pull request with two `test` legs plus one `required` job — `.github/workflows/ci.yml:3-15`, `:46-49`
- [x] Both legs complete `uv sync --locked` without a lockfile diff — `.github/workflows/ci.yml:24`; local `uv sync --locked` exit 0, lock not stale
- [x] Both legs run the fast gate, `pytest`, a per-OS coverage artifact, a job summary, and the audit — `.github/workflows/ci.yml:26-44`; local `uv run pre-commit run --all-files` passes all four hooks, planted tracked secret falsifies it (`detect-secrets ... Failed`, exit 1); no step touches `llama-server`, weights, a GPU, or a credential
- [x] The `required` job is green only when both legs are, under a fixed name — `.github/workflows/ci.yml:46-58` (`name: required`, `needs: [test]`, `if: always()`, non-`success` exits 1); `fail-fast: false` at `:13` keeps both legs reported

### Phase 4 — Docs and enforcement evidence

- [x] README shows the CI badge and a working link to `docs/dependency-waivers.yml` with a plain-language blocking line — `README.md:3`, `README.md:26-29`; badge slug matches `origin` (`Aliquanto3/wave_local_ai_v2`)
- [x] CONTRIBUTING names the required check and the matrix without duplicating the command list — `CONTRIBUTING.md:44-52`
- [x] `grep -r "local, client-side enforcement only" aidd_docs/memory/` returns nothing; both files state CI enforcement — grep exit 1 (no match); `aidd_docs/memory/architecture.md:14-16`, `aidd_docs/memory/coding-assertions.md:32-46`
- [x] A deliberately failing PR is red, the same branch turns green once fixed, both states observed — green PR #10 [runs/32574496872](https://github.com/Aliquanto3/wave_local_ai_v2/actions/runs/32574496872) (both legs + `required` success); red PR #11 [runs/32574709902](https://github.com/Aliquanto3/wave_local_ai_v2/actions/runs/32574709902) (both legs failed the `Fast gate` on `F401`, `required` failed); recorded in `phase-4.md`, now `status: done`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | code | 2 | `scripts/audit_dependencies.py:21` | Imports `yaml`, but `pyyaml` is not declared anywhere in `pyproject.toml` — only `types-pyyaml` was added. It resolves solely through `detect-secrets`/`pre-commit` pulling it transitively (`uv.lock:612,1171`), so dropping or bumping either dev tool silently breaks the merge gate. | **Applied**: `uv add --group dev pyyaml`. |
| 🟡 | fit | 2 | `scripts/audit_dependencies.py:116-126` | `_finding_waiver` returns `None` for an expired or over-90-day entry, indistinguishable from no entry at all, so `main()` prints only `BLOCKING`. The story's "the run names which entry expired" and phase-2's own journey ("exit 1 naming the expired entry") are unmet. | **Applied**: added `waiver_rejection()` returning the reason, `evaluate_waiver()` now delegates to it, and `main()` prints `BLOCKING (waiver expired 2026-02-01)` / `BLOCKING (no waiver)`; two tests cover the reason strings. |
| 🟡 | conform | 2 | `pyproject.toml:46` and `.pre-commit-config.yaml:19-24` | The gate runs `mypy src/` only, so `scripts/audit_dependencies.py` — the file that decides a merge — is never type-checked, and the `types-pyyaml` stub this diff adds is dead weight. | **Applied**: hook widened to `uv run mypy src/ scripts/` (passes), and the command updated in `CONTRIBUTING.md:22`, `aidd_docs/memory/coding-assertions.md:15`, `aidd_docs/GUIDELINES.md:15`. |
| 🟡 | code | 3 | `.github/workflows/ci.yml:1-7` | No `permissions:` block, so both jobs receive the repository-default `GITHUB_TOKEN` scope on a workflow that runs on every pull request, including from forks. | **Applied**: `permissions: contents: read` at workflow level (`ci.yml:8-9`). |
| 🟡 | functional | 4 | `aidd_docs/tasks/2026_08/2026_08_22_ci-check-suite/phase-4.md` | Criterion 4 unmet: the falsification the story publishes as its evidence does not exist — no red-then-green run observed. | **Closed**: green PR #10 `runs/32574496872` (both legs + `required` success), red PR #11 `runs/32574709902` (both legs failed the `Fast gate` on `F401 os imported but unused`, `required` failed at `Check matrix result`). Both recorded in `phase-4.md`, now `status: done`. |
| 🟢 | fit | 2 | `scripts/audit_dependencies.py:87` | Only `database_specific.severity` is read, so a PYSEC-id finding always resolves `UNKNOWN` and blocks regardless of its real severity (verified: `PYSEC-2023-228` → `UNKNOWN`, `GHSA-h4gh-qq45-vh27` → `MODERATE`). Fail-closed as designed, but it trains waivers onto low findings. | Follow the OSV `aliases` list to a GHSA id before falling back to `UNKNOWN`. |
| 🟢 | rot | 3 | `.github/workflows/ci.yml:43-44` | The audit runs on both legs, but `uv export --format pylock.toml` emits the universal set (84/84 packages) and pip-audit's `PyLockSource._collect_from_packages` ignores `marker` entirely, so both legs audit an identical set. The plan's Decision justifying per-leg no longer holds; the duplicate run only doubles the network-failure surface of a merge-blocking step. | Gate the step on `matrix.os == 'ubuntu-latest'` and correct the plan's Decision row. |
| 🟢 | code | 3 | `.github/workflows/ci.yml:32-41` | `Coverage summary` carries `if: always()` but `Upload coverage report` does not, so a failing `pytest` produces a summary and no artifact — the case where the artifact matters most. | Add `if: always()` to the upload step. |
| 🟢 | code | 2 | `scripts/audit_dependencies.py:168` | `finding not in blocking` labels a below-threshold finding `waived` though no waiver touched it, and compares dicts by value across the whole list. | **Applied** (same loop as the `fit` warning above): keyed set lookup, statuses now `below-threshold` / `waived` / `BLOCKING (...)`. |
| 🟢 | code | 2 | `scripts/audit_dependencies.py:83` | A transient OSV network error escapes as a traceback; the gate still fails closed, but the run reads as a script bug rather than an audit result. | Catch `requests.RequestException`, return `"UNKNOWN"`, print the reason. |
| 🟢 | code | 2 | `scripts/audit_dependencies.py:104` | `_as_date` calls `.replace(tzinfo=UTC)` on a naive `datetime` immediately before `.date()`, which discards it — the call is a no-op. | Drop `.replace(tzinfo=UTC)`. |
| 🟢 | code | 2 | `tests/test_audit_dependencies.py:5-7` | A module-level `sys.path.insert` mutates global state to reach `scripts/`, forcing the import below the statement. | Set `pythonpath = ["scripts"]` in `[tool.pytest.ini_options]` and import normally. |
| 🟢 | rot | 1 | `pyproject.toml:22-26` | `[tool.coverage.run] source` duplicates `--cov=src/wave_local_ai_v2`; phase-1 made it conditional on `--cov` under-scoping, which it does not (443 statements measured either way). | Drop the `[tool.coverage.run]` block. |
| 🟢 | code | 3 | `.github/workflows/ci.yml:9,46` | Neither job sets `timeout-minutes`, so a hung step burns the default 360 minutes on a workflow that blocks every merge. | Add `timeout-minutes: 15` to both jobs. |
| 🟢 | code | 3 | `.github/workflows/ci.yml:17,19,33` | Actions are referenced by mutable major tags (`@v4`, `@v10`), not commit SHAs, on a workflow that gates merges. | Pin to commit SHAs with the version as a trailing comment. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (16/16)                                      |
| Files checked | `.github/workflows/ci.yml`, `scripts/audit_dependencies.py`, `tests/test_audit_dependencies.py`, `docs/dependency-waivers.yml`, `pyproject.toml`, `uv.lock`, `.gitignore`, `README.md`, `CONTRIBUTING.md`, `aidd_docs/memory/architecture.md`, `aidd_docs/memory/coding-assertions.md` |
| Unchecked     | none                                              |
| Unplanned     | `types-pyyaml` added to the dev group (`pyproject.toml:46`), tracing to no criterion; `run_pip_audit` exports `uv.lock` to a scratch `pylock.toml` first (`scripts/audit_dependencies.py:39-54`), a step phase-2 task 3.1 does not describe |
