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
| 3 | `uv run mypy src/` | type checking |
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

## Behavior

If a fix is needed, spawn 1 agent per assertion category to fix in parallel (e.g. lint violations / type errors / failing tests = 3 agents).
