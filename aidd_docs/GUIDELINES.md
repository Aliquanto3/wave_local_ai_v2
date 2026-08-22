# AI Operating Guidelines

How this team drives AI coding assistants on this project. Keep it short and specific to this repo. Fill the placeholders, drop what does not apply.

## House rules

- English only in every committed file (code, identifiers, docstrings, comments, commit messages, docs); French is for `context_input/` source material only, never for committed output.
- Tests stub HTTP and never start `llama-server` or call a live API.
- The quality table and the runtime table are never merged; every runtime row carries its hardware fiche.
- Secrets live only in `.env` (gitignored), never in code or docs.
- Commits stay atomic, follow Conventional Commits, imperative lowercase subject.

## Validation depth

- Before commit: run the fast gate — `ruff check`, `ruff format --check`, `mypy src`, `detect-secrets-hook`.
- Before push: run `pytest`.
- Every implementation gets exactly one `aidd-dev:05-review` after its last phase, then merges.
- Severity gate: 🔴 and 🟡 findings block the merge and are fixed in the same branch; 🟢 findings are appended to `aidd_docs/backlog/tech-debt.md`, never block, and never trigger another review round.

## When the AI drifts

- `/clear`, restate the objective in one sentence, point at the plan file on disk.
- If a review loop produces findings about tests asserting constants against themselves, stop reviewing and merge.

For the general AIDD playbook (planning, review loops, prompting and context hygiene, anti-patterns), see the framework docs: <https://github.com/ai-driven-dev/framework>.
