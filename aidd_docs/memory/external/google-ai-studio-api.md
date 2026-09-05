# Google AI Studio (Gemini API) — pinned facts

The reference `google_client.py` cites. Loaded on demand, per `aidd_docs/memory/README.md`.

Every fact here was confirmed against the live API on **2026-08-27** with `requests` and no SDK. The captured requests and responses that establish each one live in `aidd_docs/tasks/2026_08/2026_08_26_google-ai-studio-spike/decision.md`; this file carries the conclusions only. When something below stops being true, re-confirm it against the live API rather than against Google's documentation — the spike found the two disagreeing.

## What is pinned

| Item | Value |
| --- | --- |
| Model id | `gemini-3.5-flash-lite` |
| Snapshot marker | the catalog entry's `version` field, `3.5-flash-lite-07-2026` on 2026-08-27 |
| API version | `v1` (path segment; `v1beta` is a superset and accepts the same body) |
| Base URL | `https://generativelanguage.googleapis.com/v1` |
| Catalog | `GET /models`, `GET /models/gemini-3.5-flash-lite` |
| Generation | `POST /models/gemini-3.5-flash-lite:generateContent` |
| Token pre-flight | `POST /models/gemini-3.5-flash-lite:countTokens` |
| Auth | header `x-goog-api-key: <key>` (a `?key=` query parameter also works and is not used, so the key never reaches a URL or a log line) |

## Pinning is weaker here than on Mistral

Google exposes **no dated model id**. Every `-001`, `-002` and `-MM-YYYY` form returns 404. The catalog publishes a release id plus a separate read-only `version` string, so `gemini-3.5-flash-lite` pins a release, not a build. The pre-flight reads `version` and the row publishes it, so a silent rotation to a later build shows up as a changed field rather than disappearing the way a `-latest` alias would.

`gemini-flash-lite-latest` is the floating alias, and it resolved to this id — the same relationship `mistral-small-latest` → `mistral-small-2603` records.

**Presence on the catalog does not mean the model answers.** `gemini-2.5-flash` returns a full `GET /models/{id}` entry and 404s on `generateContent` with *"no longer available to new users"*. A pre-flight written the way `mistral_client.check_model_available` is — membership in the listing — passes on a retired model and then fails on every generation. The Google pre-flight needs a real `generateContent` probe, or the catalog check has to be understood as necessary and not sufficient.

There is also no deprecation field anywhere in the catalog: no equivalent of the `deprecation` / `deprecation_replacement_model` pair that `mistral_client._deprecation_notice` reads. Retirement surfaces only as that 404, which is to say after it has already broken the call.

## What the client sends

```
POST {base}/models/gemini-3.5-flash-lite:generateContent
  systemInstruction: {parts: [{text: ...}]}      # `system_instruction` also accepted
  contents:          [{role: "user", parts: [{text: ...}]}]
  generationConfig:  {temperature, topP, topK, seed, maxOutputTokens, candidateCount: 1}
```

Every sampling field is a required argument of the client function, never defaulted — the same rule and the same reason as `mistral_client.complete_prompt`. The provider's own defaults are published on the catalog entry (`temperature: 1`, `topP: 0.95`, `topK: 64`) and `maxOutputTokens` defaults to the entry's `outputTokenLimit` of 65 536, so a row that inherits them is neither reproducible nor running under the cap it publishes.

`temperature` accepts `[0.0, 2.0]`; outside it the API returns 400 naming the range. Unknown `generationConfig` keys are rejected with 400, which is what makes an accepted field real acceptance rather than a silent drop.

Two deliberate absences:

- **`thinkingConfig`** — `thinkingBudget: 0` is rejected on this model, and the model emits no thinking tokens without it. Sending nothing is correct.
- **`stopSequences`** — it works, but a sequence that fires immediately returns `finishReason: "STOP"` with `content: {}`, indistinguishable on the row from a model that chose to say nothing. A judge template that needs one passes it explicitly.

## Determinism

`generationConfig.seed` exists, is accepted, and is honoured.

Temperature 0 with `topP: 1` and `topK: 1` and **no seed** produced five different answers to the same prompt, diverging at the first character. The identical block **with a seed** produced five byte-identical answers, and a second seed produced a different byte-identical answer.

So temperature 0 alone is not reproducible on this provider, and the seed is what makes a judge call reproducible. Anything that drops the seed silently drops reproducibility.

## Response fields to read

Generated text is `candidates[0].content.parts[*].text` — a **list**, so concatenate; never index `parts[0]`.

Provenance worth carrying onto the row: `modelVersion` (what actually served the request) and `responseId`.

Token counts live in `usageMetadata`: `promptTokenCount`, `candidatesTokenCount`, `totalTokenCount`, and `thoughtsTokenCount` on thinking models.

Two shapes that break a client copied from `mistral_client`:

- **`candidatesTokenCount` is absent, not zero**, when nothing was generated. `mistral_client` reads `usage["completion_tokens"]` with a subscript because Mistral always sends it; here that raises on a legitimate empty completion. Read it with a default of `0`.
- **`content` can be `{}`** with no `parts` key at all. Text extraction must tolerate a missing `content` and a missing `parts` and yield `""`.

This model reports no `thoughtsTokenCount` — `totalTokenCount` always equalled prompt + candidates — which is one of the reasons it is the pin. `gemini-3.6-flash` and `gemini-3.5-flash` spent 84-88 hidden thinking tokens on a one-word answer, billed as output and invisible in the text.

## `finishReason` mapped onto the failure taxonomy

The enum has 21 values (recorded in full in the decision file). Against `scoring.FAILURE_REASON_*`:

| Google outcome | Taxonomy |
| --- | --- |
| `STOP`, text non-blank, label parses | no failure |
| `STOP`, text non-blank, label does not parse | `unparseable` (decided by `normalize_label`, not by the provider) |
| `STOP` or `MAX_TOKENS`, text blank or `parts` absent | `empty` (`score_item` checks blankness first) |
| `MAX_TOKENS` | `truncated_max_tokens` |
| model's own context limit | `truncated_context` — **unreachable**, see below |
| the 15 blocked/error values | **no taxonomy value fits**, see below |

**`truncated_max_tokens` must be read off `finishReason` directly.** `score_item` separates the two truncation causes with `generated_tokens >= max_output_tokens`. On Google that test is wrong: a generation capped at 8 reported `candidatesTokenCount: 4`, so the comparison fails and a plainly cap-truncated item scores `truncated_context`. Google reports fewer output tokens than the cap it enforced.

**`truncated_context` cannot occur on this provider's free tier**, so Methodology 9's two causes stay distinguishable. No `finishReason` value denotes the model's context window; and a prompt over the 1 048 576-token window necessarily exceeds the 250 000 input-tokens-per-minute quota, so the 429 always fires first. The condition is instead detectable before the call: `:countTokens` is free of the token quota, so compare its `totalTokens` against the catalog entry's `inputTokenLimit` and refuse the item locally. A row carrying `truncated_context` from this provider is a bug.

**The taxonomy has no value for a blocked generation.** Fifteen enum values (`SAFETY`, `RECITATION`, `BLOCKLIST`, `PROHIBITED_CONTENT`, `SPII`, `ESCALATION`, `OTHER`, `MALFORMED_RESPONSE`, the `IMAGE_*` family, the tool-call family) mean the provider stopped for a reason that is neither the caller's cap nor a parse failure. Scoring them `empty` would publish "the model said nothing" when the truth is "the provider refused". The client raises a typed error naming the `finishReason` verbatim instead. Whether the taxonomy gains a fifth `blocked` reason is a row-schema question for `every-published-row-explains-and-reproduces-itself`.

## Free tier, rate limits, and retry

Free-tier access is confirmed: the 429 bodies name the quotas literally, `generate_content_free_tier_requests` and `generate_content_free_tier_input_token_count`.

| Limit | Value |
| --- | --- |
| Requests per minute | 15, per model per project |
| Input tokens per minute | 250 000, per model per project |
| Requests per day | unobserved; Google no longer publishes a per-model table, and it would surface as a third `quotaId` on the same 429 shape |

A breach returns HTTP `429` with `error.status: "RESOURCE_EXHAUSTED"`. **There is no `Retry-After` header and no `X-RateLimit-*` family** — the wait hint is in the body, at the `error.details[]` entry whose `@type` is `type.googleapis.com/google.rpc.RetryInfo`, in its `retryDelay` duration string. The quota that was hit is named at the `google.rpc.QuotaFailure` entry, in `violations[0].quotaId` and `quotaValue`.

Retry inputs: `429` and `503` are retryable (`503` is real — two newer model ids returned *"currently experiencing high demand"*); `404` and `400` are not. Fall back to exponential backoff when `RetryInfo` is absent, since the hint is not contractually guaranteed. Pacing at 4 seconds between calls stays under 15/minute and avoids the limit entirely, which is the primary strategy; backoff exists for the daily quota and for contention.

## Price

Paid **Standard** tier, retrieved 2026-08-27 — the tier this key is served on, per the `X-Gemini-Service-Tier` response header and `usageMetadata.serviceTier`:

| | Input / 1M | Output / 1M |
| --- | --- | --- |
| Free tier | $0.00 | $0.00 |
| Paid, Standard | $0.30 | $2.50 |

For comparison, `mistral-small-2603` is $0.15 / $0.60.

The cost table keys the literal id and records the paid rate, so a row publishes what the generation would cost at list price — the only figure comparable across providers. Runs made on the free tier cost nothing, and that fact belongs on the row rather than being implied by a zero. Batch and Flex are half Standard; Priority is $0.54 / $4.50; the client sends no `serviceTier`, so Standard applies.

If the pin ever moves to `gemini-3.6-flash`, the cost input becomes `candidatesTokenCount + thoughtsTokenCount`, not `candidatesTokenCount` alone.

## Data use on the free tier

Google's API terms, unpaid services: content submitted and the responses generated are used *"to provide, improve, and develop Google products and services"*, and *"human reviewers may read, annotate, and process your API input and output"*. Paid services exclude both. The terms also say plainly: *"Do not submit sensitive, confidential, or personal information to the Unpaid Services."*

Free-tier prompts and responses are therefore used for training and may be human-reviewed, which the PRD's data-egress non-goal already covers because only repo-authored suite items are ever sent.

Two consequences for the row, owned by the client and row stories rather than settled here: the egress field should record that the free tier's terms applied, because the same call under a billing account carries materially different ones; and judging a client-provided document would be a confidentiality question, not merely an egress one, which Google's own wording forbids.
