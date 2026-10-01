---
objective: "Every judge call record names the provider that answered it, the reasoning effort it was issued with and its reasoning tokens apart from its output tokens; the writer refuses a record whose answering provider differs from its bound one, `judge_cost` prices reasoning tokens once per provider under a stated billing basis, and the judge prompt keeps a tested stable prefix."
status: implemented
---

# Plan: Every judge call names who answered, its reasoning effort, and its reasoning tokens

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Extend `JudgeResponse`/`JudgeCallRecord` with six additive fields, fill them honestly from the two still-bound backends, carry reasoning tokens and their billing basis into `judge_cost`, gate the new fields at the writer under schema "13", and lock the judge prompt's stable prefix with a test |
| **Source** | `aidd_docs/backlog/stories/every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens.md` |

## Phases

| #   | Phase                                                                 | File                          |
| --- | --------------------------------------------------------------------- | ----------------------------- |
| 1   | The six record fields, the two backends, and the writer gate (schema "13") | [`phase-1.md`](./phase-1.md) |
| 2   | Reasoning tokens and their billing basis in `judge_cost`               | [`phase-2.md`](./phase-2.md)  |
| 3   | Stable judge-prompt prefix, resume read-back, stubbed evidence         | [`phase-3.md`](./phase-3.md)  |

## Decisions

| Decision | Why |
| -------- | --- |
| Six new record fields: `answering_provider`, `answering_provider_source` (`response` or `direct_endpoint`), `reasoning_effort` (the literal value sent, or `not_sent`), `reasoning_tokens` (non-negative int or null), `reasoning_tokens_source` (`reported` or `derived_from_totals`, null with a null count) and `reasoning_tokens_null_reason`. | The acceptance asks for the answering provider "where the response identifies who served it ... otherwise the direct endpoint": recording which of the two the value came from keeps that claim checkable on the row. A `not_sent` sentinel states explicitly that no effort control was sent, so the record can never be read as `disabled` or `minimal`. |
| Neither Mistral's nor Google's response body names a provider, so both backends record their bound provider with source `direct_endpoint`; neither sends an effort control, so both record `not_sent`. | Mistral's response carries `choices`/`usage` only, and Google's carries `modelVersion`/`responseId` (`aidd_docs/memory/external/google-ai-studio-api.md`). Neither names a serving provider. Neither client's request body carries `reasoning_effort` or `thinkingConfig` (Google deliberately omits it). |
| Mistral records `reasoning_tokens` null with `provider_reports_no_reasoning_count`. Google records `thoughtsTokenCount` as `reported` when present; when it is absent but `totalTokenCount`, `promptTokenCount` and `candidatesTokenCount` are all present, it records `total - prompt - candidates` as `derived_from_totals` (a negative result is refused as a self-contradicting response); only with a total missing too is it null with `reasoning_count_absent_from_response`. | Mistral's usage block carries prompt/completion/total only. The pinned Google model never emits `thoughtsTokenCount`, but its `totalTokenCount` states every billed token (memory file: total always equalled prompt + candidates), so the hidden count is the response's own arithmetic, not an assumed zero. Recording it as a tagged derivation keeps the Google judge cost reportable instead of nulling it on every real call (review round 1, critical finding). |
| Billing basis per provider, declared beside the price tables: Mistral `inside_output` (an assumption, unconfirmed live), Google `beside_output`. Under `beside_output`, a null reasoning count makes that provider's judge cost null rather than smaller. The writer checks each `judge_cost.per_provider` entry's keys and its billing basis. | Mistral reports one completion counter, so any reasoning it bills can only be inside `completion_tokens`; no live reasoning call or billing doc confirms it. Google bills thoughts on top of `candidatesTokenCount` (memory file: "the cost input becomes `candidatesTokenCount + thoughtsTokenCount`"). A null count billed beside output follows `total_or_none`'s existing rule: unknown, not smaller; with the derived count it is reached only when the response's totals are missing. |
| The answering-provider check lives in `row_contract` (writer), not in `run_judge_call`. | The acceptance places the refusal "when the row is written, naming both". The record stays a faithful copy of what the backend observed. |
| The stable-prefix rule is enforced by tests over the shipped shells and over two rendered items, not by an import-time guard. | The acceptance says a misordered shell "fails a test rather than shipping"; the three shells already place the rubric before both item slots, so no shell text changes. |
