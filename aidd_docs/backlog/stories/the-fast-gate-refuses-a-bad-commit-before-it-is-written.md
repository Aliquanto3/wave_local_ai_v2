---
type: story
status: ready
source: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
parent: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
depends_on: aidd_docs/backlog/stories/a-fresh-machine-reaches-both-benchmarks-from-the-readme-alone.md
order: 2
---

# Story: The fast gate refuses a bad commit before it is written

**As** a maintainer of the benchmark
**I want** the fast gate installed as a hook instead of run by discipline, against a baseline that describes this repository
**So that** a commit failing lint, format, types or the secret scan is refused where it is made, and the secret gate is an actual gate rather than an inventory of third-party noise

## Acceptance

- `.pre-commit-config.yaml` runs exactly the four before-commit checks of `aidd_docs/memory/coding-assertions.md`, in that order, as local hooks invoking the same `uv run` commands, so the hook and the documented gate cannot drift apart.
- `uv run pytest` runs at the `pre-push` stage, matching the before-push line of the same file. It is not a pre-commit hook: the fast gate stays fast.
- A commit staging a file that carries a planted fake credential is refused by the hook, and the same commit succeeds once the credential is removed.
- A commit staging a lint violation, and one staging an unformatted file, are each refused for their own reason.
- `.secrets.baseline` is regenerated over what git tracks. The virtualenv, the tool caches, `uv.lock` and untracked files are excluded, and the regenerated baseline holds no entry under `.venv/` — 35 of the 36 file entries in the current baseline are `.venv/` site-packages, and the 36th is the untracked `.env`.
- Every remaining baseline entry is an audited non-secret, so the file states what was reviewed rather than what was merely present when it was generated.
- `aidd_docs/memory/coding-assertions.md` and `aidd_docs/memory/architecture.md` stop describing the gate as manual with no hook installed, and describe what is now enforced and where.
- The install step (`uv run pre-commit install`, plus the `pre-push` hook type) is written into `CONTRIBUTING.md` and the setup path of order 1, so a fresh clone reaches the same enforcement.
- `uv run pre-commit run --all-files` passes on the tree as it stands, so the gate agrees with the repository it is being added to instead of being landed red.

## Files it creates or changes

- `.pre-commit-config.yaml` (new) — the four commit-stage hooks and the one push-stage hook.
- `.secrets.baseline` — regenerated, scoped to tracked files, entries audited.
- `aidd_docs/memory/coding-assertions.md`, `aidd_docs/memory/architecture.md` — the manual-gate wording replaced.
- `CONTRIBUTING.md`, `docs/setup.md` — the install step.

## How it is verified without a GPU

- All five checks are pure Python over the working tree. None starts `llama-server`, downloads a model, or needs a GPU or a cloud credential.
- Falsification, and the evidence this story publishes: three throwaway commits on a scratch branch — one carrying a planted fake secret, one a lint violation, one an unformatted file — each refused by the hook, transcripts kept; then the same commits succeeding once fixed.
- The baseline rescope is checkable by counting: the file entries of the regenerated baseline are all paths that `git ls-files` returns.

## Cancellation

n/a — not cancelled.
