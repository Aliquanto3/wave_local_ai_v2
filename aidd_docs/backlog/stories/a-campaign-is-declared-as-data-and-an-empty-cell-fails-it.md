---
type: story
status: ready
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/every-row-names-the-engine-that-produced-it-and-the-fiche-hashes-it.md
  - aidd_docs/backlog/stories/every-row-names-its-prompt-variant-and-a-baseline-row-carries-the-authored-prompt.md
  - aidd_docs/backlog/stories/a-gpu-run-and-a-cpu-only-run-never-share-a-fiche.md
order: 3
---

# Story: A campaign is declared as data, and an empty cell fails it

**As** the consultant planning an engine and variant campaign
**I want** the campaign declared as a tracked file naming its engines, variants, roster entries, suites and machine, checked at declaration against the caps, and a completeness check that fails on any declared cell nobody ran
**So that** "at most 2 engines and at most 4 variants" is enforced before a run rather than noticed after one, and a gap in the matrix is a failure rather than a missing row nobody sees

Maps to: PRD AC "Given a campaign, ... the campaign declares at most two engines and at most four variants"; Methodology 22 ("each a declared dimension of the campaign rather than an option taken at the call site", "every declared cell is actually run rather than left empty"); epic Boundaries "the campaign declaration as data"; epic decision "Campaign shape" (one declared machine).

Needs: none. Constructed declarations and rows exercise every case; no model run, API key, hardware or operator is required.

## Acceptance

- A campaign declaration is a tracked file with a stable campaign id naming its engines (registry ids), prompt variants (registry ids and versions), roster entries, suites and one declared machine id with its compute mode. Loading refuses, naming the offending value: more than 2 engines; more than 4 variants; an engine, variant, roster entry, suite or machine id absent from its registry; an engine entry incomplete under order 1's registry rule.
- A run started under a campaign records `campaign_id` on every row, and refuses before any server starts when its engine, variant, roster entry, suite or machine is outside that campaign's declaration. A run started with no campaign stays possible and records that it belongs to none, so day-to-day runs are not forced into a campaign.
- A completeness command lists every declared cell (engine x variant x roster entry x suite) with the run ids that fill it, and exits non-zero naming each empty cell. A cell refused under the machine epic's refusal discipline, or dropped with a recorded reason (order 8's "no mechanism" outcome), is listed as refused or dropped with that reason and is not a failure; a cell with neither rows nor a recorded reason is.
- Re-running the completeness command over the same rows returns the same listing.
- The declaration is the one campaign file: a further dimension added by its owning epic (the agentic harness list of `no-use-case-is-silently-absent`, capped at three under Methodology 23) extends this declaration and its cell product rather than introducing a second file. This story adds no harness field.

## Code it changes

- New campaign declaration loader and completeness command (a CLI entry point in `pyproject.toml`); campaign files under a tracked directory beside the results.
- The runtime and quality entry points: the campaign check before launch; `row_contract.py`: `campaign_id` (or the declared absence), `SCHEMA_VERSION` bumped.

## Tests it needs

- Declaration refusals: three engines, five variants, each unregistered id.
- Run refusal outside the declaration; a run with no campaign records none.
- Completeness: a full matrix passes; one empty cell fails naming it; a dropped cell with its reason passes and is listed as dropped.

## Evidence it publishes

- None of its own; the campaign (order 12) publishes its declaration and the completeness listing.

## Cancellation

n/a: not cancelled.
