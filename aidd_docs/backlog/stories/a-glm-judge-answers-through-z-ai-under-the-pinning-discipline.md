---
type: story
status: proposed
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens.md
order: 8
---

# Story: A GLM judge answers through Z.ai under the pinning discipline

**As** a consultant who needs judges independent of every model on the roster
**I want** Z.ai's GLM callable as a judge through Z.ai's own direct API, pinned, priced and bound at the judge seam like the existing provider clients
**So that** the first member of the judge pair the PRD names exists in a form a judged row can cite and a reader can re-derive

Maps to: Methodology 11 ("The judge pair is Z.ai's GLM and DeepSeek, each called through that provider's own direct API"), Methodology 12; PRD Dependencies "Paid, low-cost direct API access to the two judge providers (Z.ai for GLM ...)"; PRD AC "Given a judged item, its row names the judge provider that actually answered, the reasoning effort the call was issued with, and its reasoning-token count separately from its output tokens"; epic Boundaries "the judge pair", "the two spikes those clients need, before either is written", "egress recorded on the calls this epic introduces"; epic Dependencies "Z.ai's and DeepSeek's API surfaces", "Those providers' data-use and retention terms".

Needs: a paid API key (Z.ai), for the spike and for this story's one live judge call.

Blocked: by the spike `aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`. The epic requires the spike before the client is written.

## Acceptance

- Methodology 12: a GLM judge record carries a dated, non-floating model id read from Z.ai's live catalog, and the API version it was called under. A run needing this judge refuses to start when that id is absent from the live catalog, naming the id and the endpoint checked; a deprecated id returns a notice the caller surfaces rather than raising.
- Sampling is pinned by the caller: temperature, the top-p control the spike found and the maximum output tokens are required arguments of the call, never a provider default. Where the spike found no per-request seed, the record says so with the reason and never carries a seed that was not sent.
- The call is issued with reasoning disabled or minimal, through the control the spike found, and records that effort and its reasoning tokens through order 7's fields. A GLM judge cannot be bound at any other effort.
- The response's finish reason is mapped to completed, caller's cap reached, model's context limit reached, blocked, or other. A blocked or safety-stopped judge call fails that call with the provider's reason named verbatim; it is never parsed into a score.
- The client raises one typed error, with an unavailable-model subclass and a retryable rate-limit subclass carrying the retry hint the spike recorded, so `retry.py`'s backoff, pacing and resume apply unchanged to this provider on its paid tier.
- Methodology 16: prompt, output and reasoning token counts are read off the response, and the call is costed from a dated list-price entry keyed by the literal dated id. An id with no entry fails at import time rather than costing at zero.
- The dated id is declared as family `glm`, and `glm` enters `roster.KNOWN_FAMILIES` additively: no subject family is removed, and the local families the roster epic adds are untouched.
- The client is bound as a judge backend in `judge_backends.py` and imported by no other judge-path module.
- The API key is read from one named environment variable, is absent from the repo, from logs and from any `Settings` repr, and a run needing this judge with no key configured says so before any paid call is made, naming the variable.
- Egress: a judged row that used this judge names Z.ai among the providers the item and the subject output reached, and the README's egress sentence names Z.ai and the data-use and retention terms the spike recorded.

## Code it changes

- `src/wave_local_ai_v2/` (new Z.ai client module): `requests` only, no SDK, no streaming, mirroring `mistral_client.py` and `google_client.py` so the three are reviewable side by side; its module docstring cites the spike's decision file.
- `src/wave_local_ai_v2/judge_backends.py`: the GLM backend, paced and retried per batch like the existing two.
- `src/wave_local_ai_v2/cost.py`: the Z.ai price table in `PRICE_TABLES` with its import-time guard.
- `src/wave_local_ai_v2/roster.py`: the `glm` family and the dated id's entry in `MODEL_FAMILIES`.
- `src/wave_local_ai_v2/settings.py`, `.env.example`: the key, `repr=False`, not required at load time.
- `README.md`: the egress sentence.

## Tests it needs

- A new client test module (HTTP stubbed): a well-shaped response yields content, finish reason and all token counts; each malformed field raises the typed error at the provider boundary; an id absent from a stubbed catalog raises the unavailable-model subclass naming it; a 429 raises the retryable subclass carrying the hint; a block finish reason fails the call with the reason named.
- `tests/test_cost.py`: the entry is keyed by the literal dated id; a missing entry fails at import.
- `tests/test_judge.py` (HTTP stubbed): a judge call through the GLM backend yields a contract-valid judge record with family `glm`, its effort and its reasoning tokens.
- `tests/test_settings.py`: the key is read, defaults to empty, never appears in a repr.

## Evidence it publishes

- One live GLM judge call over one probe item, its judge record read back and contract-valid, cited in the story's task evidence. It is written to no results file.

## Cancellation

n/a: not cancelled.
