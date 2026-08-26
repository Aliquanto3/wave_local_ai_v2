---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/the-fiche-carries-a-normalised-hash-every-row-cites.md
order: 15
---

# Story: Editing a fiche invalidates the rows that cite it

**As** a client-side engineer handed a published bundle
**I want** one command that tells me whether any published row cites a fiche that no longer hashes to what it claims
**So that** invalidation is something I can observe and run, not a property the documentation asserts

## Acceptance

- Methodology 14: a named validator command checks every row of a results file against the fiche registry and exits non-zero when any row cites a fiche whose stored content no longer hashes to its filename identity.
- Methodology 14: the failure output names the offending rows by run id and row position, and the fiche fields that changed.
- The validator also fails a row citing a fiche hash absent from the registry, and reports the two cases distinctly — an edited fiche and a missing one are different problems.
- A clean bundle exits zero and prints the counts it checked, so a passing run is evidence rather than silence.
- The validator reads published artifacts only; it recomputes nothing about the run and reconstructs no fiche from a row.

## Code it changes

- `src/wave_local_ai_v2/fiche_validator.py` (new) — the check, the two failure classes and the exit code.
- `pyproject.toml` — the console entry point that names the command.
- `src/wave_local_ai_v2/fiche_registry.py` — verification helper reused by the validator.

## Tests it needs

- `tests/test_fiche_validator.py` (new) — a constructed bundle of rows plus fiches exits zero; editing one stored fiche's GPU field exits non-zero and names the citing rows and the changed field; a row citing an unknown hash exits non-zero under the other failure class; an empty results file exits zero with a zero count.

## Evidence it publishes

- The command's non-zero exit against a deliberately edited fiche is the epic's third success check, run over the published bundle in `aidd_docs/results/` and recorded in its `README.md` (order 19).

## Cancellation

n/a — not cancelled.
