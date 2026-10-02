---
objective: "Every quality row carries its item's own input and output token counts and engine-reported first-token time (null with a reason when unreported, labelled a single per-item generation, the batch's first generation marked), and the comparison command runs a paired Wilcoxon on those per-item quantities while publishing a per-batch energy difference as an observation that says why it has no test."
status: implemented
---

# Plan: Each quality item records the tokens and the first-token time its generation took

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Per-item engine-reported tokens and TTFT on quality rows (schema "18"), and per-item continuous quantities as compared fields in `comparison.py` |
| **Source** | `aidd_docs/backlog/stories/each-quality-item-records-the-tokens-and-the-first-token-time-its-generation-took.md` on branch `docs/slice-remaining-epics` (read-only); parent epic `the-engine-and-the-prompt-variant-are-measured-not-assumed`; owner answer Q24 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` on that branch |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | The per-item measurement and its row fields (schema "18") | [`phase-1.md`](./phase-1.md) |
| 2   | Both quality writers populate the fields | [`phase-2.md`](./phase-2.md) |
| 3   | Per-item quantities as compared fields; energy as an observation | [`phase-3.md`](./phase-3.md) |
| 4   | Docs and the local-run evidence | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified          |
| ------ | ----------------- |
| Live `/v1/chat/completions` response of llama-server `b10537-bf0040e15` on `qwen3-0.6b-q8` (probe run 2026-10-02, no row written) | The chat response carries `usage.prompt_tokens`, `usage.completion_tokens` and a `timings` block with `prompt_ms`, `prompt_n` and `cache_n`. A second item reused 6 cached prompt tokens (`cache_n: 6`, `prompt_n: 19` of 25), so a per-item `prompt_ms` covers only the uncached part of the prompt. |

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| Eleven quality-row fields, all required from schema "18": `item_tokens_in`, `item_tokens_out`, `item_ttft_ms`, `item_prompt_tokens_cached`, each with its own `*_null_reason`; `item_ttft_source`; `item_measurement_kind`; `item_first_in_batch`. | One scalar null reason per value is the repo's existing idiom (`reasoning_tokens_null_reason`) and flattens into the bundle without a wildcard column. Distinct `item_` names keep the per-item figures from ever being read as the batch totals or the runtime protocol's `ttft_ms`. |
| `item_ttft_ms` is `timings.prompt_ms` from the chat response, labelled `item_ttft_source: server_reported`. | The same quantity and label the runtime row's `ttft_ms` uses (`timings.parse_timings`), so the `ttft_source` discipline holds; no client-side clock is added. |
| `item_prompt_tokens_cached` records `timings.cache_n`. | Live evidence: llama-server reuses a shared prompt prefix between consecutive items, so a per-item TTFT covers only the uncached tokens. A variant that prepends a fixed instruction would have it cached after the first item; without this count a reader cannot see why its TTFT dropped. Recorded, not prevented: turning prompt caching off would change the request every published quality row was produced with. |
| `item_measurement_kind` is the constant `single_generation`, documented as one per-item generation with no warm-up exclusion and no repetitions (not a Methodology 6 aggregate). | The acceptance's label; a constant value on every row, checked by the gate, so a later measurement kind is a new value rather than a reinterpretation. |
| `item_first_in_batch` is true on the row of the first generation the invocation's batch made. | The first item runs on a freshly launched server (cold kernels, empty cache); a reader excludes it with the comparison's existing selector (`--reference-where item_first_in_batch=false`). On a resume the first resumed item is the first generation of that server launch, so it is marked. |
| Cloud rows carry the fields too: tokens from the provider's own per-call usage, TTFT and cache count null with reason `not_reported_by_provider`; an item Google refused before calling (context pre-flight) is null with `no_generation_call`. | The fields are required on every quality row, so a cloud row needs a value or a reason. Publishing null where the provider reported a count would drop data; the acceptance's engine-reported TTFT is a local-path property. |
| `comparison.py` gains a compared quantity: `score` (default, unchanged), `item_tokens_in`, `item_tokens_out`, `item_ttft_ms` (scoring kind `continuous_measurement`, Wilcoxon signed-rank), and `energy_kwh` (always an observation with its no-test reason, the two batch values and their difference). | Q24 (a). The quantity joins the family identity (a token family is not a score family, Holm never mixes them); `score` families keep their exact record shape, so every committed record still recomputes byte for byte. |
| A measurement comparison is refused when a side's rows do not carry the quantity (rows below "18"), or when the two sides' non-null `item_ttft_source` / `item_measurement_kind` labels differ. | Two TTFTs read from different sources are not one quantity; an absent field is "predates schema", never an empty pairing. |
| The story's evidence names order 4's cell pair (`baseline` vs `output_compressed`), which does not exist: order 4 is not implemented (its dependency, the campaign-as-data story, was skipped). The evidence is a real local run of two `baseline` batches on `qwen3-0.6b-q8` in the task `evidence/` folder, and the paired output-token record over them. | The run rule keeps local-run output out of the committed stores and `aidd_docs/results/README.md` figures; the README documents the fields, and the order 4 pair stays for order 4. |
