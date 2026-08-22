# Contributing

## Branch naming

`type/short-description`, where `type` is one of: `feat`, `fix`, `chore`,
`docs`, `test`, `refactor`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): description`, imperative mood, lowercase, English only.

## Fast gate — run before every commit

In order:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run detect-secrets-hook --baseline .secrets.baseline
```

## Before push

```sh
uv run pytest
```

Tests stub HTTP and never start `llama-server` or call a live API — `pytest`
needs no GPU and no API key either.

## Severity gate

- 🔴 and 🟡 findings block merge and are fixed on the same branch.
- 🟢 findings are appended to `aidd_docs/backlog/tech-debt.md`, never block,
  and never trigger another review round.

See [`aidd_docs/GUIDELINES.md`](aidd_docs/GUIDELINES.md) for the full house
rules.
