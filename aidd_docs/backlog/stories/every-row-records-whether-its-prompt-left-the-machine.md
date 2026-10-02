---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
order: 22
---

# Story: Every row records whether its prompt left the machine

**As** a client-side engineer checking what a benchmark run sent off the machine
**I want** every runtime and quality row to state where its subject prompt went, none or the cloud provider that received it, and the writer to refuse a row that does not say
**So that** "nothing left the machine" is a property every row carries and the writer gate enforces, not an inference from which client happened to produce the row

Maps to: PRD AC "Given no client-provided document or prompt in a suite, no request leaving the machine ever contains one, and every row records whether its prompt left the machine"; epic Success Evidence first check ("a row missing any required field of the row contract cannot be written"); owner decision Q72 (2026-10-01): the row contract, which is where "every row" is enforced, owns the field.

Needs: none. Code-only, proven on constructed rows and stubbed HTTP.

Current state: egress is recorded per surface only. A judged quality row carries `judge_egress` (`row_contract.JUDGE_EGRESS_FIELDS`); local subject rows, cloud-subject quality rows and runtime rows carry no egress field. A quality row's `provider` names the subject's provider (`local` for llama-server), but nothing on the contract says what that implies for egress, and a runtime row carries no `provider` at all.

## Acceptance

- Every runtime and quality row carries a subject egress field: `none` when the subject prompt was served on the machine, or the provider id that received it for a cloud subject. A writer always knows where it sent a prompt, so the field is never null.
- The writer gate refuses a row of either kind whose subject egress field is absent or null, naming the field, and appends nothing.
- On a quality row, the gate refuses a subject egress that contradicts `provider`: a `local` row recording a provider, or a cloud row recording `none`.
- A runtime row records `none`: the runtime benchmark serves its prompt from the local llama-server only.
- The judge egress block, and any search egress block a later suite adds, are kept as they are; the subject egress field describes the subject call alone and is not merged with them.
- The field extends both row kinds additively under a `SCHEMA_VERSION` bump, with its reason in the version comment block. Rows already written keep their schema version and are not rewritten (the store rule of `rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md`); the published reference rows carry the field from their next regeneration, which this story does not schedule.

## Code it changes

- `src/wave_local_ai_v2/row_contract.py`: the field on both row kinds, the null refusal, the quality-row consistency check against `provider`, and the `SCHEMA_VERSION` bump.
- `src/wave_local_ai_v2/__init__.py`: the runtime writer stamps `none`.
- `src/wave_local_ai_v2/quality_cli.py`: the quality writer stamps `none` for a local subject and the provider id for a cloud one.

## Tests it needs

- `tests/test_row_contract.py`: a row of each kind missing the field is refused naming it; a null value is refused; a `local` quality row recording a provider, and a cloud quality row recording `none`, are each refused; a judged row keeps validating its judge egress block unchanged.
- `tests/test_cli.py`, `tests/test_quality_cli.py`: with HTTP stubbed, a runtime row and a local quality row record `none`, and a Mistral and a Google subject row each record their provider.

## Evidence it publishes

- `tests/test_row_contract.py` as the refusal evidence, extending the epic's first success check to this field.

## Cancellation

n/a: not cancelled.
