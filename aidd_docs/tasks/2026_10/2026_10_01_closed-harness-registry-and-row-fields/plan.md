---
objective: "Every quality row written from schema 20 names its agentic harness from a closed registry of Methodology 23's five candidates, that harness's version read from the installed package at run time, and its per-call prompt overhead measured under the owner's rule (Q33 (a)) or recorded unmeasurable, never a hard-coded zero; the writer gate refuses any other shape."
status: implemented
---

# Plan: Register the closed harness candidate set and its three row fields

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A `harness` registry closed at `direct`, `smolagents`, `langgraph`, `pydantic-ai`, `llamaindex`; three required quality-row fields (`harness_id`, `harness_version`, `harness_prompt_overhead`) at schema "20"; `direct` implemented as the reference on both quality writers, its overhead read from what the engine received |
| **Source** | `aidd_docs/backlog/tasks/register-the-closed-harness-candidate-set-and-its-three-row-fields.md` (PR-branch `docs/slice-remaining-epics` text), parent epic `no-use-case-is-silently-absent.md`, owner answer Q33 (a), PRD Methodology 23 |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Registry, overhead rule and the schema "20" writer gate | [`phase-1.md`](./phase-1.md) |
| 2   | `direct` on both quality writers: the item's own prompt counted under the model's tokenizer | [`phase-2.md`](./phase-2.md) |
| 3   | Readers, export dictionary, docs and live evidence | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| llama-server b10537, live (`Qwen3-0.6B-Q8_0`, port 8093) | `/tokenize` with `add_special: true` on the `/apply-template` string returns exactly `usage.prompt_tokens` of the matching `/v1/chat/completions` call (27 = 27; with one tool definition 158 = 158); `usage.prompt_tokens` stays the full count when the cache serves part of it (`cache_n` 26, `prompt_tokens` 27); `/apply-template` honours `tools`. Saved under `evidence/`. |

## Decisions

| Decision | Why |
| -------- | --- |
| `harness_prompt_overhead` is one object `{"tokens", "null_reason"}`, not an integer plus a sibling reason column | The task fixes three fields. The project's rule is "a value, or null with its reason, never a zero"; nesting keeps both inside the one field and the export flattens it to two described columns. |
| Null reasons: `unmeasurable` (the harness rewrites the item's prompt, or the engine received fewer tokens than the item's own prompt, which no wrapper can produce), `item_prompt_not_counted` (no tokenizer count of the item's own prompt exists: a cloud subject, counted only by a provider call this project does not make), and the engine count's own reason (`not_reported_by_engine`, `not_reported_by_provider`, `no_generation_call`) | Each says why no number exists, so a cloud row's absence is never read as a framework finding and a framework finding is never read as a missing measurement. |
| `direct`'s version is the installed `requests` distribution's, read through `importlib.metadata` per row | `direct` is "plain client calls with no framework"; the installed client those calls go through is `requests`. The project's own version is already `release_version` (bookkeeping, excluded from comparison), so naming it again would make every cross-release comparison confounded on a field that only restates the release. |
| The item's own prompt under `direct` is the `/apply-template` rendering of its messages and tool definitions, counted by `/tokenize` (`add_special: true`) | It is the string `direct` sends, under the tokenizer the row already names through `roster_entry_id`; tool definitions passed as `tools` render into it and so count as the item's, never as overhead (Q33 (a)). |
| Quality rows only; the runtime row is untouched | The runtime row times a fixed raw prompt with no harness, as every prior bump left it. |
| `harness_id` and `harness_version` enter the comparison's differing-field set; `harness_prompt_overhead` is excluded as a measurement | Two sides under different harnesses are a confound until the harness-comparison story adds a harness dimension; the overhead is an outcome, like the per-item tokens. |
| Framework distributions are named in the registry (`smolagents`, `langgraph`, `pydantic-ai`, `llama-index-core`) but none is a dependency | The adapters are out of scope; a row naming a framework whose package is not installed is refused at version read rather than written with a guessed version. |
