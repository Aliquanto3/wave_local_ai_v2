---
objective: "Every runtime and quality row carries `subject_egress` (`none`, or the cloud provider id that received the subject prompt), the writer gate refuses a row where it is absent, null or contradicts the quality row's `provider`, and both writers stamp it under row schema \"16\"."
status: implemented
---

# Plan: Every row records whether its prompt left the machine

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A required `subject_egress` field on both row kinds (schema "16"), its null and consistency refusals in the writer gate, the three writers stamping it, and every registry that partitions the contract (read model, bundle dictionary, comparison dimensions) describing it |
| **Source** | `aidd_docs/backlog/stories/every-row-records-whether-its-prompt-left-the-machine.md` on branch `docs/slice-remaining-epics` (read-only); parent epic `every-published-row-explains-and-reproduces-itself`; owner answers Q72 (a) and Q75 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` on that branch |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The field on the contract, its refusals, the three writers stamping it, and the registries that partition the contract | [`phase-1.md`](./phase-1.md) |
| 2   | CHANGELOG, results README and memory describe schema "16" | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| Field name `subject_egress`, a string: `none` or the provider id (`mistral`, `google`). One helper, `row_contract.subject_egress_for(provider)`, maps a subject provider to the value; `local` maps to `none`. | The story names a "subject egress field" holding `none` or the provider id. Keeping the mapping on the contract module means the writers and the gate cannot disagree about it. |
| The gate refuses an absent key (the required set), a `null`, and a non-string or empty value on both kinds. On a quality row it refuses any value other than `subject_egress_for(provider)`: a `local` row must record `none`, a cloud row must record its own provider id. | The acceptance lists the two contradictions (`local` + a provider, cloud + `none`); requiring equality with the provider id also refuses a cloud row naming another provider, which "the provider id that received it" already implies. |
| The runtime row is held to the value `none` by the gate itself, beside presence, non-null and well-formedness. | A runtime row carries no `provider`, but the runtime benchmark serves its prompt from the local llama-server only, so any other value is a contradiction the gate can refuse (review fix). |
| `judge_probe.py` stamps the field too, though the story's "Code it changes" omits it. | It writes quality rows through the same gate; without the field every probe row would be refused. Recorded as a story/code gap. |
| `subject_egress` joins the comparison `model` dimension's fields, beside `provider`. | A difference outside the compared dimension is a confound that turns the comparison into an observation (`not_comparable`) rather than a test; a local-vs-cloud model comparison would otherwise lose its test over a field that is a function of `provider`. |
| Not rendered by the read-model views (both kinds' not-rendered sets); described in the bundle dictionary as a common field. | Same precedent as schema "14" and "15": whether the pitch renders a field is the pitch epic's call; the dictionary must describe every contract field or the export refuses. |
| `SCHEMA_VERSION` "15" -> "16", additive, with the reason in the comment block. No committed store is edited or regenerated. | The story; a row keeps the schema it was written under and is never back-filled. The read model renders the field in no view (both not-rendered sets), so no view reports it at all, absent or present. |
