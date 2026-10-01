---
type: story
status: done
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/a-rate-limited-run-persists-resumes-and-never-re-pays.md
order: 7
---

# Story: Every judge call names who answered, its reasoning effort, and its reasoning tokens

**As** a client-side engineer auditing a judged score
**I want** each judge call on a row to name the provider that actually answered it, the reasoning effort it was issued with, and the tokens it spent reasoning, apart from the tokens it spent answering
**So that** a judged score cannot have been produced by a silently substituted provider, and a judge that thinks before it scores is visible on the row rather than averaged into its output

Maps to: PRD AC "Given a judged item, its row names the judge provider that actually answered, the reasoning effort the call was issued with, and its reasoning-token count separately from its output tokens"; Methodology 11 ("Every judge call pins the provider that actually answers ... records the reasoning effort it was issued with (disabled or minimal), and counts reasoning tokens separately from output tokens"); epic Boundaries "per-judge-call row constraints"; epic decision "`judge_cost` is its own block ... Reasoning tokens are counted separately again within it".

Needs: none. Stubbed backends prove the contract; no model run, API key, hardware or operator is required.

Current state: `judge.JudgeCallRecord` carries `model_id`, `provider`, `family`, `score`, `raw_text`, `failure_reason`, `tokens_in`, `tokens_out` and `retries`; `provider` is the constant the backend was bound with, not a value read from the answer. No record carries a reasoning effort or a reasoning-token count. `judge_protocol`'s three language shells already place the rubric before the item prompt and the subject output.

## Acceptance

- Each judge call record names the provider that answered it. Where the provider's response identifies who served it, that is the value recorded; otherwise it is the direct endpoint the call was sent to.
- No fallback routing: a judge call that fails on its bound provider is never re-issued to another provider or another model. The run goes partial and names that provider and item, the contract order 5 already ships. A judge record whose answering provider differs from the provider the judge was bound to is refused when the row is written, naming both.
- Each judge call record carries the reasoning effort it was issued with, as it was sent in the request. A backend that sends no effort control records that none was sent; a record never claims `disabled` or `minimal` for a control that was not sent.
- Each judge call record carries its reasoning-token count apart from its output-token count. A provider that does not report reasoning tokens yields an explicit null with the reason, never a zero.
- The row's `judge_cost` block carries reasoning tokens per provider beside output tokens and states whether that provider bills them inside its output count or beside it. No token is counted twice in the cost, and `cost_total` stays the subject generation's.
- The new record fields extend the judged contract additively under a `SCHEMA_VERSION` bump: a judged row missing any one of them is refused naming it, and a deterministic quality row validates unchanged.
- The judge prompt keeps a stable prefix: for one suite, language and rubric version, every rendered judge prompt shares a byte-identical prefix covering the shell's instructions and the rubric, and every item-specific substitution comes after it. A shell that places an item slot before the rubric fails a test rather than shipping.
- A resumed run reads the new fields back unchanged and re-issues no judge call already recorded.

## Code it changes

- `src/wave_local_ai_v2/judge.py`: `JudgeResponse` and `JudgeCallRecord` gain the answering provider, the issued reasoning effort and the reasoning-token count; `JUDGE_CALL_RECORD_FIELDS` follows from the TypedDict as today.
- `src/wave_local_ai_v2/judge_backends.py`: the backends still bound fill the new fields with what they actually send and receive.
- `src/wave_local_ai_v2/cost.py`: `judge_cost_fields` carries reasoning tokens per provider and the billing basis.
- `src/wave_local_ai_v2/row_contract.py`: the answering-provider check and the `SCHEMA_VERSION` bump with its reason in the version comment block.

## Tests it needs

- `tests/test_judge.py` (HTTP stubbed): a stubbed response naming a different answering provider is refused; a backend sending no effort control records that none was sent; an absent reasoning count is null with a reason, not zero.
- `tests/test_cost.py`: reasoning tokens billed inside the output count are not added twice; billed beside it, they are priced once.
- `tests/test_row_contract.py`: a judged row missing each new field is refused naming it; a deterministic row still validates.
- `tests/test_judge_protocol.py`: two items of one suite and language render prompts with a shared prefix ending after the rubric.

## Evidence it publishes

- A stubbed judged row read back showing the answering provider, the issued effort, and reasoning tokens apart from output tokens, cited in the story's task evidence.

## Cancellation

n/a: not cancelled.
