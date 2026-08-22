---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-declares-its-caps-tags-and-language-mix.md
  - aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 5
---

# Story: A failed generation scores zero and names its reason

**As** a client-side engineer reading a suite accuracy
**I want** every failed generation to score zero, stay in the denominator and record why it failed
**So that** an accuracy figure cannot hide unparseable output behind wrong answers, and a truncation I can dispute is distinguishable from one I cannot

## Acceptance

- Methodology 9: an item whose generation is empty, truncated or unparseable scores 0, remains in the denominator, and records a failure reason; no item is ever dropped from a comparison.
- Methodology 9: the reason taxonomy separates `empty`, `unparseable`, `truncated_max_tokens` (the suite's cap under Methodology 3 was reached, a suite-level choice a challenger can dispute) and `truncated_context` (the model's context limit was reached, a property of the model).
- A scored item that succeeded records a null failure reason, never an absent key.
- The suite accuracy denominator is the item count, and a row states how many of its items failed and under which reasons.
- The four current quality rows carrying `"predicted_label": null, "correct": false` with no reason cannot be produced by the new code path: an unparseable output now names itself.

## Code it changes

- `src/wave_local_ai_v2/scoring.py` — `score_item` returns a failure reason beside `predicted_label`; `score_suite` reports the failure counts it aggregated over.
- `src/wave_local_ai_v2/quality_cli.py` — reads the stop reason and generated-token count from the provider response to tell the two truncations apart, and writes the reason on every row.
- `src/wave_local_ai_v2/mistral_client.py` — surfaces the provider's finish reason instead of returning content alone.
- `src/wave_local_ai_v2/row_contract.py` — failure reason and failure counts become required quality-row fields.

## Tests it needs

- `tests/test_scoring.py` — empty, whitespace-only, label-free and valid completions map to the four states; a failed item stays in the denominator.
- `tests/test_quality_cli.py` — with stubbed responses, a cap-truncated completion and a context-truncated completion produce the two distinct reasons; a stubbed Mistral finish reason maps to the same taxonomy.

## Evidence it publishes

- The regenerated `aidd_docs/results/quality-reference.jsonl` (order 20) replaces today's four reasonless nulls: the local model's 0.60 becomes readable as wrong answers or as failed generations rather than being indistinguishable between the two.

## Cancellation

n/a — not cancelled.
