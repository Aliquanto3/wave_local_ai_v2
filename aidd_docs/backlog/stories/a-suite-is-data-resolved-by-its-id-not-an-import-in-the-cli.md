---
type: story
status: done
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
order: 1
---

# Story: A suite is data resolved by its id, not an import in the CLI

**As** a client-side engineer auditing which suite produced a published row
**I want** every task suite to be one declared definition, its items and caps held as data and its scoring rule named, resolved by the suite id the row carries
**So that** the suite a row names is readable without importing code, and the six suites still to come are each a registration rather than another import and another branch in the CLI

Maps to: PRD AC "Given a supported task suite, running it against a local model and a cloud model produces one quality score and one runtime record per model, from the same suite items rendered per provider under Methodology 2 and 3"; Methodology 2, 3, 4, 5; epic Boundaries "the suite seam"; owner question Q1 (`aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`), whose recommended default makes this the one seam story the interval epic's publication-suite stories depend on.

Needs: none.

## Acceptance

- A suite definition shape exists and holds, per suite: the suite id, the suite version, the four Methodology 3 generation constraints (maximum output tokens, stop sequences, context length, thinking policy), the name of its scoring rule, and its items, each item carrying its language tag, its provenance and its contamination-risk marking. The items live as data, not as Python literals.
- A registry resolves a suite id to its definition. `wave-local-ai-v2-quality --suite` takes a registered suite id; an unregistered id is refused naming the registered ones, and a definition naming a scoring rule the registry does not know is refused naming that rule.
- Every definition passes through the shipped size, language and provenance gate (`suite_gate.gate_suite`) when it is loaded; the gate is consumed, not reimplemented, and a definition the gate refuses is never run.
- The two shipped suites, `classification-support-routing` and `translation-business-short-form`, are migrated onto the shape with no item, prompt or cap changed: their suite version and `PROMPT_SET_HASH` are unchanged, and regenerating their committed snapshots in `aidd_docs/results/suite-definitions/` reproduces the existing files byte for byte. No published row is rewritten.
- Registering a further suite is a new definition and, where its scoring differs, a new named scoring rule; it needs no edit to `quality_cli.py`. Shown by a test that registers a fixture suite and runs it end to end with the HTTP clients stubbed.
- The shape accepts the per-suite and per-item fields the interval epic's stories add (the declared level, source, licence, source revision, content hash, selection rule) as additions, without a second shape. Those fields are not built here.

## Code it changes

- `src/wave_local_ai_v2/quality_cli.py`: `_SUITES` and `SuiteSpec` give way to the registry; the per-suite scoring functions become the named scoring rules.
- `src/wave_local_ai_v2/classification_suite.py`, `translation_suite.py`: items and caps move to data; what stays in code is the scoring and anything the scoring needs.
- `src/wave_local_ai_v2/suite_snapshot.py`: exports from the registered definitions instead of from the two modules.
- A new registry module and the suites' data files, at a location the implementation chooses and the README names.

## Tests it needs

- The two migrated suites' prompt-set hashes and snapshot bytes equal today's.
- An unregistered suite id and an unknown scoring rule are each refused by name; a definition with an item missing its language or provenance is refused by the gate at load.
- A fixture suite registered in the test runs through the CLI path with no change to `quality_cli.py`.

## Evidence it publishes

- Nothing new in the reference bundle: the unchanged snapshot bytes are the evidence that the migration moved no published number.

## Cancellation

n/a: not cancelled.
