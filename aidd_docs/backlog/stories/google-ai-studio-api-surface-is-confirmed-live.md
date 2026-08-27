---
type: spike
status: ready
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

## Cancellation

n/a — not cancelled.
