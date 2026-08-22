---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
order: 1
---

# Story: A suite declares its caps, tags and language mix, and a short suite publishes indicative

**As** a client-side engineer auditing a published score
**I want** every task suite to declare the generation caps it ran under, the language and provenance of each item, and its own compliance with the size and mix thresholds
**So that** I can tell a defensible score from an indicative one from the row alone, and the suites written after this one are born compliant instead of re-implementing the check

## Acceptance

- Methodology 3: the classification suite declares its maximum output tokens, stop sequences and context length; every row it produces records those three values, and two models compared on one item record identical values.
- Methodology 2 (suite half): the suite declares a suite id, a suite version and a SHA-256 hash over its prompt set; every row records all three, and editing any item's prompt changes the hash.
- Methodology 4: every item carries a language tag among `en`, `fr`, `de`; the gate computes item count and each language's share of the suite.
- Methodology 4: a suite below 20 items, or whose EN, FR or DE share falls below 25%, is marked indicative with the reason named, and every row it produces carries that mark. The suite as it stands today (10 items, EN only) is marked indicative rather than passing.
- Methodology 4: the gate reports n per language and marks any per-language cell computed over fewer than 10 items indicative under the same rule.
- Methodology 5: every item declares provenance among `hand_written`, `licensed`, `public`; a `public` item is marked contamination-risk on every row it produces; the gate refuses a suite with a missing or self-inconsistent declaration, and verifies nothing about the declaration's truth.
- The gate validates fields, not a suite shape: it accepts any object exposing those fields, so the suites the sibling epic authors are checked by it without change.

## Code it changes

- `src/wave_local_ai_v2/classification_suite.py` — per-item `language`, `provenance`, `contamination_risk`; module-level suite id, suite version, caps and prompt-set hash, in the form the module already takes (the suite definition *shape* and its registry stay with `no-use-case-is-silently-absent`).
- `src/wave_local_ai_v2/suite_gate.py` (new) — the gate: counts, per-language shares, provenance consistency, the indicative verdict and its reason.
- `src/wave_local_ai_v2/quality_cli.py` — writes caps, suite id, suite version, prompt-set hash, item tags and the indicative mark onto every quality row.

## Tests it needs

- `tests/test_suite_gate.py` (new) — constructed suites: 19 items marked indicative, a 20-item suite at 20% DE marked indicative, a missing provenance declaration refused, a per-language cell of 5 items marked indicative, a compliant suite passing.
- `tests/test_classification_suite.py` — every item carries all three tags; the prompt-set hash is stable across calls and changes when one prompt changes.
- `tests/test_quality_cli.py` — with the HTTP client stubbed (no llama-server, no Mistral call), a written row carries the caps, the suite triple and the indicative mark.

## Evidence it publishes

- The deliberately shrunk suite in `tests/test_suite_gate.py` is the epic's third success check, provable without twenty items existing.
- The fields become publicly readable on the regenerated `aidd_docs/results/quality-reference.jsonl` (order 20).

## Cancellation

n/a — not cancelled.
