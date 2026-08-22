# Contributing

## Branch naming

`type/short-description`, where `type` is one of: `feat`, `fix`, `chore`,
`docs`, `test`, `refactor`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): description`, imperative mood, lowercase, English only.

## Fast gate — enforced on every commit

Installed with `uv run pre-commit install` (run once per clone; see
`docs/setup.md`). A `pre-commit` stage hook runs these, in order, and refuses
the commit if any fails:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src/
uv run detect-secrets-hook --baseline .secrets.baseline
```

If the hook refuses, fix the tree, not the hook — the entry above is the
contract with `aidd_docs/memory/coding-assertions.md`.

To run the gate by hand, use `uv run pre-commit run --all-files`. The last
command scans only the filenames the hook hands it, so running it on its own
exits 0 without checking anything.

## Before push

Runs at the `pre-push` stage, installed by the same command above:

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
