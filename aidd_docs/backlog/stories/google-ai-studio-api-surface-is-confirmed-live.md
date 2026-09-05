---
type: spike
status: done
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
order: 1
---

# Spike: Google AI Studio's API surface is confirmed against the live API

**As** the engineer about to write the second provider's client
**I want** Google AI Studio's catalog, pinning, sampling, response and free-tier behaviour answered from live calls rather than from its documentation
**So that** the second provider is built against what the API does, and the epic's largest unknown is settled before any code depends on it

## Uncertainty

`mistral_client.py` records the precedent this spike exists for: the model id Mistral's own models-overview page published (`mistral-small-4-0-26-03`) did not exist on the API, and the id that does (`mistral-small-2603`) was only found by reading a live `GET /v1/models`. Every answer below is therefore worth only what a captured live request and response make it worth.

Nothing in this repo has ever called Google AI Studio. `.env.example` carries `GOOGLE_API_KEY=replace-me`; `settings.py` does not read it; there is no client module. Whether free-tier access on terms comparable to Mistral's exists at all is unverified here.

## Questions

1. **Live catalog.** Does a live model-list endpoint exist? Its URL, its auth mechanism, and the shape of one entry — id, version, and any deprecation or retirement field.
2. **Dated ids.** Does the live listing expose dated, non-floating model ids, or only aliases? Which dated id is the pin candidate today, and which alias did it resolve from?
3. **Sampling controls.** The parameter names and accepted ranges for temperature, top-p and top-k; whether each is settable per request; and what the provider applies when the field is omitted.
4. **Seed.** Is a per-request seed exposed at all?
5. **Response shape.** Where the generated text lives; the finish-reason field and its full enum, with which values mean the caller's output cap, the model's context limit, and a safety or other block; and the usage fields for prompt, output and total tokens.
6. **Free tier.** The documented and the observed request/token limits, the HTTP status returned when one is hit, the body shape of that response, and whether a retry-after or equivalent hint is returned.
7. **API version.** The version string Methodology 12 requires on a row, and where it is read from — path segment, header, or response field.
8. **List price.** The published input and output per-million rates for the pinned id, with the source URL and the retrieval date.

## Acceptance

- Every answer cites a live request and the response it returned. No answer is sourced from a documentation page alone; where documentation and API disagree, both are recorded and the API is the answer.
- One dated, non-floating model id present on the live listing is named as the pin candidate. An id read from documentation but absent from the live listing is recorded as that failure, not silently dropped.
- If no live model-list endpoint exists, that absence is recorded as the finding and Methodology 12's pre-flight is declared unimplementable on this provider — which blocks order 2 rather than being worked around with a documentation-sourced id.
- If no per-request seed exists, the file states that judge determinism on this provider degrades to temperature 0, and that a row records what was actually pinned rather than claiming a seed that could not be sent.
- The finish-reason enum is recorded in full, with each value mapped to one of: completed, caller's cap reached, model's context limit reached, blocked, other. Methodology 9 requires the first two truncation causes to be distinguishable, so a mapping that cannot separate them is itself the finding.
- The free-tier limit answer is specific enough to drive a backoff: the status code, whether a retry-after is present, and what it contains.
- The file states whether free-tier access on terms comparable to Mistral's is confirmed, unconfirmed, or refused — the epic's open dependency, closed either way.
- The file ends with a decision: the pinned model id, the sampling set that will be pinned, seed availability, and go or no-go for order 2.

## Evidence it publishes

- `aidd_docs/memory/external/google-ai-studio-api.md` (new) — the decision file, loaded on demand per `aidd_docs/memory/README.md`. It is the document `google_client.py`'s module docstring cites, the pattern `mistral_client.py` set by carrying its own confirmation dates inline.
- The captured request/response excerpts backing each answer, quoted in that file rather than described.

## Outcome

Resolved on 2026-08-27, from live calls with `requests` and no SDK. The durable facts are `aidd_docs/memory/external/google-ai-studio-api.md`; the captured requests and responses behind them are `aidd_docs/tasks/2026_08/2026_08_26_google-ai-studio-spike/decision.md`.

- **Free tier confirmed.** The 429 bodies name the quotas literally: `generate_content_free_tier_requests` (15/minute) and `generate_content_free_tier_input_token_count` (250 000/minute), per model per project. The epic's open dependency on a second free-tier provider is closed as available.
- **Live catalog exists** at `GET /v1/models` and `GET /v1beta/models`, authenticated by an `x-goog-api-key` header, 403 without one.
- **No dated model id is addressable.** Every `-001`, `-002` and `-MM-YYYY` form 404s. The catalog publishes a release id plus a read-only `version` field (`gemini-3.5-flash-lite` → `3.5-flash-lite-07-2026`). The pin is therefore weaker than `mistral-small-2603`: it pins a release, and the pre-flight reads `version` so a rotation shows on the row instead of hiding.
- **Listing is not availability.** `gemini-2.5-flash` returns a full entry on `GET /models` and 404s on `generateContent` with *"no longer available to new users"*. A catalog-presence pre-flight copied from `mistral_client.check_model_available` would pass and then fail on every generation.
- **Pin candidate: `gemini-3.5-flash-lite`**, on `v1`. It answers, it is what the `gemini-flash-lite-latest` alias resolved to (`"modelVersion": "gemini-3.5-flash-lite"`), and it emits no thinking tokens, so `candidatesTokenCount` is the whole billable output.
- **A per-request seed exists and is honoured.** `generationConfig.seed`. Five calls at temperature 0 without it gave five distinct answers; five with `seed: 42` were byte-identical; a second seed gave a different byte-identical answer. Temperature 0 alone is *not* deterministic here, so the epic's degrade-to-temperature-0 fallback would not have worked had the seed been absent.
- **`finishReason` enum recorded in full** (21 values, from the live discovery document). `MAX_TOKENS` is the caller's cap. **No value denotes the model's context limit** — and it cannot be reached on the free tier either, because a prompt over the 1 048 576-token window necessarily exceeds the 250 000-token minute quota and returns 429 first (proved with a 1 500 002-token prompt sent alone). `truncated_context` is a `:countTokens` pre-flight refusal on this provider, not a response classification, so Methodology 9's two causes stay distinguishable.
- **Two mapping traps recorded.** `MAX_TOKENS` came back with `candidatesTokenCount: 4` against a cap of 8, so `score_item`'s `generated_tokens >= max_output_tokens` test would misclassify it as `truncated_context`; and `candidatesTokenCount` is absent rather than zero on an empty completion, which the Mistral-style `usage[...]` read would raise on.
- **The taxonomy has no value for a blocked generation.** Fifteen of the 21 enum values are neither the caller's cap nor a parse failure. Scoring them `empty` would publish "the model said nothing" for "the provider refused". Recommendation carried to the client story: raise a typed error naming the `finishReason` verbatim rather than coercing it.
- **List price** for the pinned id, Standard tier, retrieved 2026-08-27: $0.30 / 1M input, $2.50 / 1M output. Free tier is $0.00.
- **Free-tier data use, stated.** Google's API terms: unpaid-tier prompts and responses are used *"to provide, improve, and develop Google products and services"* and *"human reviewers may read, annotate, and process your API input and output"*. The PRD's egress non-goal already scopes what is sent to repo-owned suite items, but the row's egress field should record that the free tier's terms applied.

**Go for order 2.**

## Follow-up

- The client story writes `google_client.py` against `aidd_docs/memory/external/google-ai-studio-api.md`, and cites it from the module docstring the way `mistral_client.py` cites Mistral's. The evidence behind every fact in it is `aidd_docs/tasks/2026_08/2026_08_26_google-ai-studio-spike/decision.md`.
- The pre-flight cannot be catalog-presence alone; it needs a real `generateContent` probe or an explicit statement that presence is necessary and not sufficient.
- `cost.py`'s import-time guard is keyed to `mistral_client.MODEL` and needs a second arm, or a table keyed by provider.
- Whether the four-value failure taxonomy gains a `blocked` reason is a row-schema question for `every-published-row-explains-and-reproduces-itself`, not for the client story.
- Judge quality on `gemini-3.5-flash-lite` is unproven; the judge-protocol story decides it, with `gemini-3.6-flash` as the fallback at $0.75 / $3.75 plus billed thinking tokens.

## Cancellation

n/a — not cancelled.
