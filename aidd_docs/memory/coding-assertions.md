# Coding Assertions

The checks that must pass for code to count as done.

## Before commit

The fast gate. Enforced by a `pre-commit` stage hook, defined in
`.pre-commit-config.yaml`; installed with `uv run pre-commit install`. This
table and the hook entries must change together — the table is the contract.

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `uv run ruff check .` | lint |
| 2 | `uv run ruff format --check .` | formatting |
| 3 | `uv run mypy src/ scripts/` | type checking |
| 4 | `uv run detect-secrets-hook --baseline .secrets.baseline` | secret scanning |

Row 4 is handed the staged filenames by the hook; run by hand with no filenames
it scans nothing and exits 0. The manual equivalent of the whole gate is
`uv run pre-commit run --all-files`.

## Before push

Runs at the `pre-push` stage, deliberately not a commit-stage hook — tests are
slower than the fast gate and paying that cost per commit is what makes
people bypass a hook.

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `uv run pytest` | tests |

## CI (server-side)

`.github/workflows/ci.yml` runs on every push to `main` and every pull
request, on a `ubuntu-latest` + `windows-latest` matrix (Python 3.12), behind
one stable `required` check. Each leg runs:

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `uv run pre-commit run --all-files` | the four before-commit hooks above (lint, format, types, secrets) |
| 2 | `uv run pytest` | tests, coverage-gated at 80% (`pyproject.toml`'s `--cov-fail-under`) |
| 3 | `uv run python scripts/audit_dependencies.py` | dependency vulnerabilities, severity-resolved via OSV, waivable via `docs/dependency-waivers.yml` |

`coverage.xml` is uploaded per OS and the coverage percentage is printed to
the job summary. This is the same command set as local enforcement — CI is
not a different gate, it is the local one, run server-side.

## Behavior

If a fix is needed, spawn 1 agent per assertion category to fix in parallel (e.g. lint violations / type errors / failing tests = 3 agents).
