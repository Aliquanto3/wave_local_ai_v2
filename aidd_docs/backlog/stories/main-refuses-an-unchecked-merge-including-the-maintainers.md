---
type: story
status: done
source: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
parent: aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
depends_on: aidd_docs/backlog/stories/every-push-and-pull-request-runs-a-check-suite-that-can-refuse-it.md
order: 4
---

# Story: main refuses an unchecked merge, including the maintainer's

**As** a client-side developer auditing how the numbers reached `main`
**I want** the platform to refuse any merge or push that the check suite has not passed, with no bypass for the repository's owner
**So that** "every commit was checked" is a property of the repository rather than a claim about the discipline of the person who owns it

## Acceptance

- `main` accepts changes only through a pull request, and the summary check of order 3 must be green before the merge is available.
- Bypass is off for everyone, the maintainer and the repository owner included. A gate its owner can wave through is not evidence to a client engineer.
- Force-push to `main` and deletion of `main` are refused.
- A branch must be up to date with `main` before merging, so a check that passed against stale code does not carry a merge.
- A direct push to `main` from the maintainer's own machine is refused, and the refusal transcript is kept as evidence.
- A pull request whose check is red offers no merge: the platform blocks it, rather than a convention discouraging it.
- The protection is not an invisible platform setting: the ruleset is exported to a tracked file alongside the command that applies or re-applies it, so a reader can diff the stated intent against what the repository actually enforces, and a re-created repository can restore it.
- `README.md` and `CONTRIBUTING.md` state in one line that `main` takes changes only through a checked pull request.
- The maintainer being the only committer today does not soften any of the above.

## Files it creates or changes

- `.github/rulesets/main.json` (new) — the exported ruleset, tracked so the platform setting is auditable.
- `docs/setup.md` or `CONTRIBUTING.md` — the command that applies the exported ruleset to a fresh fork or a restored repository.
- `README.md`, `CONTRIBUTING.md` — the one-line statement.

## How it is verified without a GPU

- Entirely platform configuration: nothing executes, nothing is inferred, no GPU or model is involved.
- Two transcripts are the evidence this story publishes: a rejected direct push to `main`, and a pull request with a failing check whose merge the platform refuses.
- The tracked ruleset is verified against the live setting by re-exporting it and finding no diff.

## Cancellation

n/a — not cancelled.
