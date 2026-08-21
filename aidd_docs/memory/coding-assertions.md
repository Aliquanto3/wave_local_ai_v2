# Coding Assertions

The checks that must pass for code to count as done.

## Before commit

The fast gate (wired via pre-commit).

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `uv run ruff check .` | lint |
| 2 | `uv run ruff format --check .` | formatting |
| 3 | `uv run mypy src/` | type checking |
| 4 | `uv run detect-secrets-hook --baseline .secrets.baseline` | secret scanning |

## Before push

| Order | Command | Checks |
| ----- | ------- | ------ |
| 1 | `uv run pytest` | tests |

## Behavior

If a fix is needed, spawn 1 agent per assertion category to fix in parallel (e.g. lint violations / type errors / failing tests = 3 agents).
