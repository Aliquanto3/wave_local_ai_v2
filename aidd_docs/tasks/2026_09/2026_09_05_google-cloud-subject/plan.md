---
objective: "The quality CLI runs local, Mistral and Google as three subjects against the classification suite, each batch persisted before the next, with Google's rows carrying its dated id, its API version, its read-only version snapshot and a list-price cost, under the same contract Mistral's rows already satisfy."
status: in-progress
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A second cloud provider answers suite items as a subject

## Overview

| Field      | Value                                                                 |
| ---------- | ---------------------------------------------------------------------- |
| **Goal**   | Add `google_client.py` (`gemini-3.5-flash-lite`, pinned) as a third quality-suite subject, contract-valid and independently costed |
| **Source** | `aidd_docs/backlog/stories/a-second-cloud-provider-answers-suite-items-as-a-subject.md` |

## Phases

| #   | Phase                                            | File                          |
| --- | ------------------------------------------------- | ----------------------------- |
| 1   | `google_client.py`, settings, and its own tests    | [`phase-1.md`](./phase-1.md)  |
| 2   | Quality CLI wires Google in as a third batch        | [`phase-2.md`](./phase-2.md)  |
| 3   | One live three-provider run, docs, memory          | [`phase-3.md`](./phase-3.md)  |

## Resources

| Source | Verified |
| ------ | -------- |
| `aidd_docs/tasks/2026_08/2026_08_26_google-ai-studio-spike/decision.md` | Live-HTTP evidence for every fact this plan pins: the id, `version` vs no dated snapshot, the availability-probe requirement, the `seed`/`topP`/`topK` sampling block, the two response shapes that break a client copied from `mistral_client` (`candidatesTokenCount` absent not zero, `content` can be `{}`), the `finishReason` enum and its taxonomy mapping, the free-tier rate limits and `RetryInfo` shape, and the Standard-tier list price |
| `aidd_docs/memory/external/google-ai-studio-api.md` | The distilled, load-on-demand version of the same facts — what `google_client.py` cites in its module docstring |
| `src/wave_local_ai_v2/mistral_client.py` | The structural pattern this client mirrors: `requests` only, a `MistralCompletion`-shaped TypedDict, a typed error with an unavailable-model subclass, required (never defaulted) sampling kwargs |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| The per-item completion, the cloud-batch runner, the call-path fields and the batch cost/energy fields become one small per-provider dispatch table inside `quality_cli.py` (keyed by `provider` id: `"mistral"`, `"google"`), rather than a second copy-pasted `_run_google_suite`/`_google_call_path`/`_google_batch_fields` triplet | This is what "the cloud subject is selectable by provider rather than hard-wired to Mistral" (the story's own words) means at the code level, and it is what lets a fourth provider slot in later without duplicating `_run_cloud_suite`'s shape again |
| `google_client.check_model_available` returns a `GoogleModelInfo` (the catalog's `version` and `inputTokenLimit`), never a deprecation-notice string | The spike found no deprecation field in Google's catalog at all — the Mistral shape (`str \| None` notice) has nothing to return for Google, and forcing one would fabricate a field that doesn't exist upstream |
| Google's per-item truncation cause is decided from `finishReason` directly (`MAX_TOKENS` → the cap), never from `generated_tokens >= max_output_tokens` | The spike observed `candidatesTokenCount: 4` against a cap of `8` — the comparison `score_item` uses for Mistral would misclassify that as `truncated_context`. `score_item` gains an optional `truncation_reason` override that, when given, is used as-is; Mistral's call site passes nothing and keeps today's behavior byte-for-byte |
| Context-window overflow is refused pre-flight (`:countTokens` vs. the catalog's `inputTokenLimit`), and that refusal is scored as `truncated_context` without ever calling `generateContent` for that item | The spike proved this provider's free tier can never surface a context-limit `finishReason` — the 429 on the input-token quota always fires first — so `truncated_context` can only originate from the pre-flight, never from a response, or a row carrying it from Google is a bug per the spike's own words |
| A blocked or otherwise-unmapped `finishReason` (`SAFETY`, `RECITATION`, `BLOCKLIST`, `OTHER`, …) raises a typed `GoogleBlockedError` naming the reason verbatim, aborting the run rather than scoring `empty` | The taxonomy has no honest value for "the provider refused" — publishing `empty` would claim the model said nothing when it did not. `quality_cli.main`'s except tuple grows this one subclass, mirroring how it already widens for `MistralRequestError` |
| A missing `GOOGLE_API_KEY` skips the Google batch (a stderr line, zero Google rows) rather than aborting the run, while a missing `MISTRAL_API_KEY` still aborts it as it does today | The story's own acceptance criterion for this provider; Mistral's existing hard-fail behavior is unchanged because no acceptance criterion asks for it to change |
| `cost.py`'s `MISTRAL_PRICE_TABLE` stays exactly as-is (same name, same values, same import-time guard against `mistral_client.MODEL`); a sibling `GOOGLE_PRICE_TABLE` is added with its own import-time guard against `google_client.MODEL`, and a `PRICE_TABLES: dict[str, dict[str, Price]]` keyed by provider id lets `quality_cli` look either one up generically | Satisfies the decision file's "generalised to a per-provider lookup without changing Mistral's recorded values or their retrieval date" literally — `test_cost.py`'s existing literal-source assertions about `MISTRAL_PRICE_TABLE` keep passing unmodified |
| Google's `version` (the read-only catalog snapshot) and its API version (`"v1"`, the path segment) ride on the row as two additional, non-required keys, never as new entries in `row_contract.REQUIRED_FIELDS` | Acceptance criterion 6 requires "no change to the quality kind's required-field list"; `append_row`/`validate_row` only checks for the presence of required keys, so extra keys are written through untouched — this is the only way to publish both dated-identity facts without touching the shared contract every other provider's rows must also satisfy |
