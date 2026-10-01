---
type: story
status: ready
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
order: 2
---

# Story: Every PRD use case carries a coverage state, or the record refuses to publish

**As** a client decision-maker holding the published results and the PRD's use-case list
**I want** one coverage record that gives each of the ten entries a declared state: exercised by named suites, covered as a dimension of named suites, or out of scope for this release with a reason
**So that** a missing use case is a refusal I can read rather than a silence I have to notice, and the multilingual entry is visibly a dimension rather than a forgotten suite

Maps to: PRD AC "Given the full use-case list, each of the nine task use cases (classification, translation, document comparison, text rewriting, code generation, agentic planning, agentic tool calling, web research, RAG answer generation) has at least one task suite exercising it, or is marked out of scope for this release as a labelled empty row in the published results table; multilingual EN/FR/DE coverage is satisfied as a language dimension of the classification, translation and rewriting suites per Methodology 4"; PRD Goals "Coverage spans the full set of use cases"; epic Boundaries "the coverage record as data", "the multilingual entry marked covered-by-dimension"; epic Sequence step 1; epic success check 1.

Needs: none.

## Acceptance

- The coverage record is data: one entry for each of the nine task use cases and one for multilingual EN/FR/DE coverage. Each entry declares exactly one of `exercised` (with one or more suite ids), `covered-by-dimension` (with the suite ids carrying it) or `out-of-scope-this-release` (with a non-empty reason). `exercised` takes a list, so the interval epic's publication suites add a second suite id to an existing entry rather than a second entry.
- The multilingual entry is `covered-by-dimension` and names the classification, translation and rewriting suites. Nothing is built for it.
- The command that writes the published coverage record into `aidd_docs/results/` refuses, and writes nothing, when an entry is missing, when an entry has no state, when an `exercised` or `covered-by-dimension` entry names a suite id the registry (order 1) does not resolve, or when an `out-of-scope-this-release` entry has no reason. The refusal names every failing entry, not only the first.
- An entry's state is declared, never inferred: registering a suite does not by itself make a use case `exercised`; the record is edited, and the gate checks the edit.
- Run today, the command refuses and names the entries still without a resolvable state (the six use cases this epic has yet to build, rewriting until its suite registers, and multilingual while it names the unregistered rewriting suite). That refusal is the current, honest coverage reading and is the evidence for this story; the complete record is published by the command once the last entry resolves.
- Removing any one entry from a complete fixture record makes the command refuse naming that use case (epic success check 1, verified by removal, not by reading the writer).

## Code it changes

- The coverage record's data file, beside the suite registry.
- A coverage gate and the command that publishes the record, reusing the registry from order 1.
- `aidd_docs/results/README.md`: what the published coverage record is and when it appears.

## Tests it needs

- A complete fixture record passes; removing an entry, blanking a state, naming an unregistered suite and omitting an out-of-scope reason each refuse, naming the entry.
- A record with three failing entries names all three.

## Evidence it publishes

- The refusal output against the record as committed, naming what is not yet covered. The published record itself follows once every entry resolves; until then the pitch epic's overview states the record's absence, as its own stories already require.

## Cancellation

n/a: not cancelled.
