---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 4
---

# Story: Rows name the endpoint and prompt template that produced them

**As** a client-side engineer reading a stored prompt
**I want** every row to state the call path and template that produced its prompt string
**So that** I know whether the stored string is the bytes the model received, and rows written on either side of a future chat-endpoint migration stay distinguishable

## Acceptance

- Methodology 2: every row records the endpoint it called (`/completion` today, the provider's chat endpoint for a cloud row), the prompt-template id, and the template's content hash.
- Methodology 2: `none` is a legitimate template id, and is what the raw `/completion` path records today, with a null template hash — the stored prompt is then the bytes sent, byte for byte.
- Methodology 2: the stored prompt is the final string as rendered for that provider; a row states whether that string was captured as sent or reconstructed, and today's value is `captured`.
- A row whose endpoint applies a template and whose template id is `none` is refused by the writer gate: the two cannot be true together.

## Code it changes

- `src/wave_local_ai_v2/prompt_provenance.py` (new) — endpoint and template-id constants, the template content hash, and the capture-or-reconstruction label.
- `src/wave_local_ai_v2/row_contract.py` — the four call-path fields become required for both row kinds, with the consistency rule above.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — both writers stamp them at the call site that actually posts the request.
- `src/wave_local_ai_v2/mistral_client.py` — reports the endpoint it called, so a cloud row is not labelled by the local path's constants.

## Tests it needs

- `tests/test_prompt_provenance.py` (new) — the raw path yields `none` and a null hash; a templated path yields an id and a stable hash; the inconsistent pair is rejected.
- `tests/test_cli.py`, `tests/test_quality_cli.py` — with HTTP stubbed, local rows record `/completion` and cloud rows record the Mistral chat endpoint.

## Evidence it publishes

- Every row of the regenerated reference bundle (order 19 and 20) carries the endpoint, which is what lets a later reader date a row against the chat-endpoint migration owned by `no-use-case-is-silently-absent`.

## Cancellation

n/a — not cancelled.
