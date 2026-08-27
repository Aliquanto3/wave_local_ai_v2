---
type: story
status: ready
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/google-ai-studio-api-surface-is-confirmed-live.md
order: 2
---

# Story: A second cloud provider answers suite items as a subject

**As** a consultant comparing local models against the cloud
**I want** a second cloud provider that answers the same suite items under the same pinning discipline Mistral already runs under
**So that** the comparison carries two cloud subjects rather than one, and a second model family exists for a judge to be independent of

## Acceptance

- Methodology 12: a row from this provider records the provider's dated model id — never a floating alias — and the API version it was called under.
- Methodology 12: a run refuses to start when that dated id is absent from the provider's live model list, and the refusal names the id and the endpoint that was checked. Absence and deprecation stay different outcomes: an absent id raises, a deprecated one returns a notice the caller surfaces and decides on.
- Methodology 1 and 3: temperature, the top-p/top-k controls the spike found, and the maximum output tokens are required arguments of the call rather than inherited from a provider default, and the row records what was actually pinned. Where the spike found no per-request seed, the row carries an explicit null seed with the reason, and never a seed value that was not sent.
- Methodology 9: the response's finish reason is mapped to the reasons the project already distinguishes — the suite's output cap reached, the model's context limit reached — plus this provider's block and other reasons. A blocked generation is recorded as blocked, never published as unparseable output.
- Methodology 16: prompt and output token counts are read off the response, and a cost is derived from a dated list-price entry keyed by the literal dated model id. A model id with no entry fails at import time rather than costing at zero, the guard `cost.py` already applies to Mistral.
- Running the existing classification suite against this provider writes contract-valid quality rows under its own `provider` value, distinguishable from `mistral`, reaching `append_row` with no change to the quality kind's required-field list.
- The API key is read from the environment, is absent from the repo, from logs and from any `Settings` repr; a run with no key configured for this provider reports its rows skipped, not failed, per the PRD's credential-free reproduction criterion.

## Code it changes

- `src/wave_local_ai_v2/google_client.py` (new) — `requests` only, no SDK, no streaming: `complete_prompt` returning content, endpoint, finish reason and the token counts, `check_model_available` against the live catalog, one typed error with an unavailable-model subclass. Mirrors `mistral_client.py` structurally so the two are reviewable side by side.
- `src/wave_local_ai_v2/settings.py` — a `google_api_key` field with `repr=False`, read from `GOOGLE_API_KEY`, not required at load time (the same rule `mistral_api_key` follows, so the runtime-only harness still starts with no cloud credential).
- `src/wave_local_ai_v2/cost.py` — a dated price entry for the pinned Google id and the same import-time guard, with the single `MISTRAL_PRICE_TABLE` generalised to a per-provider lookup without changing Mistral's recorded values or their retrieval date.
- `src/wave_local_ai_v2/prompt_provenance.py` — the template id and content hash for this provider's chat wrapper, and its endpoint carried into `is_consistent` so a row naming it cannot claim `none`.
- `src/wave_local_ai_v2/quality_cli.py` — the cloud subject is selectable by provider rather than hard-wired to Mistral.

## Tests it needs

- `tests/test_google_client.py` (new, HTTP stubbed) — a well-shaped response yields content, finish reason and both token counts; a non-200, an unparseable body, a non-string content, a non-string finish reason and a non-int token count each raise the typed error at the provider boundary; an id absent from a stubbed catalog raises the unavailable-model subclass naming the id; a deprecated entry returns a notice rather than raising.
- `tests/test_cost.py` — the new entry is keyed by the literal dated id, not by the module's `MODEL` variable; a table with no entry for the pinned id fails at import.
- `tests/test_quality_cli.py` (HTTP stubbed) — a suite run against this provider writes contract-valid rows carrying its `provider`, its dated id and its API version; a run with no key for it reports skipped rather than failed.
- `tests/test_settings.py` — `GOOGLE_API_KEY` is read, defaults to empty, and never appears in a `Settings` repr.

## Evidence it publishes

- Quality rows for a second cloud subject in `aidd_docs/results/quality.jsonl`, carrying the pinned dated id, the API version and the list price they were costed at.
- The spike's decision file cited from `google_client.py`'s module docstring, so the id's provenance is readable from the code that depends on it.

## Cancellation

n/a — not cancelled.
