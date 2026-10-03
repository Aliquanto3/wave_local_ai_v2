---
type: story
status: proposed
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens.md
order: 9
---

# Story: A DeepSeek judge answers through DeepSeek under the pinning discipline

**As** a consultant who needs judges independent of every model on the roster
**I want** DeepSeek callable as a judge through DeepSeek's own direct API, pinned, priced and bound at the judge seam like the existing provider clients
**So that** the second member of the judge pair the PRD names exists, and a judged row can carry two independent scores and their agreement

Maps to: Methodology 11 ("The judge pair is Z.ai's GLM and DeepSeek, each called through that provider's own direct API"), Methodology 12; PRD Dependencies "Paid, low-cost direct API access to the two judge providers (... DeepSeek for DeepSeek)"; PRD AC "Given a judged item, its row names the judge provider that actually answered, the reasoning effort the call was issued with, and its reasoning-token count separately from its output tokens"; epic Boundaries "the judge pair", "the two spikes those clients need, before either is written", "egress recorded on the calls this epic introduces"; epic Dependencies "Z.ai's and DeepSeek's API surfaces", "Those providers' data-use and retention terms".

Needs: a paid API key (DeepSeek), for the spike and for this story's one live judge call. Owner act before the first paid call: the training opt-out email to privacy@deepseek.com (owner answer Q103 (c), 2026-10-03).

Blocked: by the spike `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md` (`blocked`; desk research done 2026-10-02 found the catalog documents only floating names, repointed in place), which needs its live calls with a paid DeepSeek key: the `/models` ids, a dated-id probe, the version path, a non-thinking judge call's usage, the seed, `reasoning_effort: "none"`, the caller's cap, the context-limit error, one captured 429, and the terms revision saved on the day. The epic requires the spike before the client is written.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- No DeepSeek client and no `deepseek` family: `roster.KNOWN_FAMILIES` holds `qwen`, `mistral`, `google`, `ibm`, `liquid`, `microsoft`; `roster.MODEL_FAMILIES` holds the three subject ids; `cost.PRICE_TABLES` and `cost.REASONING_TOKEN_BILLING` key only `mistral` and `google`; `settings.Settings` reads only `mistral_api_key` and `google_api_key` among cloud provider keys.
- `judge_backends.py` binds `mistral_judge_backend` and `google_judge_backend`, both recording `judge.REASONING_EFFORT_NOT_SENT`, and is the only judge-path module that imports a provider client.
- Order 7's fields are in place: `judge.JudgeCallRecord` carries `answering_provider`, `answering_provider_source`, `reasoning_effort`, and `reasoning_tokens` with `reasoning_tokens_source` or `reasoning_tokens_null_reason`; `cost.judge_cost_fields` refuses a judge provider with no `REASONING_TOKEN_BILLING` basis.
- `JudgeCallRecord` has no API-version, build-marker, sampling or seed field: subject rows carry `model_version` and `api_version` (`quality_cli.py`), judge records do not.
- Precedents to mirror: `mistral_client.check_model_available` (absent id raises `ModelUnavailableError`, a deprecated one returns a notice), `mistral_client.RetryableRequestError` with its retry hint, and `retry.Pacer`, `retry.RetryBudget`, `retry.call_with_retry`.

## Acceptance

- Methodology 12, as amended by owner answer Q102 (a), 2026-10-03: a DeepSeek judge record carries DeepSeek's release id (DeepSeek publishes no dated id and repoints its names in place; `deepseek-v4-pro` is the spike's desk candidate) read from DeepSeek's live model list, never a documentation-sourced id, the API version it was called under, and every build marker the provider returns. A run needing this judge refuses to start when that id is absent from the live list, or when a recorded build marker differs from the pinned one, naming the id, the marker where one differs, and the endpoint checked; a deprecated id returns a notice the caller surfaces rather than raising.
- Sampling is pinned by the caller: temperature, the top-p control the spike found and the maximum output tokens are required arguments of the call, never a provider default. Where the spike found no per-request seed, the record says so with the reason and never carries a seed that was not sent.
- The call is issued with reasoning disabled or minimal, through the control or the model choice the spike found, and records that effort and its reasoning tokens through order 7's fields. A DeepSeek judge cannot be bound at any other effort.
- The response's finish reason is mapped to completed, caller's cap reached, model's context limit reached, blocked, or other. A blocked or safety-stopped judge call fails that call with the provider's reason named verbatim; it is never parsed into a score.
- The client raises one typed error, with an unavailable-model subclass and a retryable rate-limit subclass carrying the retry hint the spike recorded, so `retry.py`'s backoff, pacing and resume apply unchanged to this provider.
- Methodology 16: prompt, output and reasoning token counts are read off the response, and the call is costed from a dated list-price entry keyed by the literal pinned id. An id with no entry fails at import time rather than costing at zero. Where the spike found time-of-day or cache-hit pricing, the entry records which rate the cost was computed at.
- The pinned id is declared as family `deepseek`, and `deepseek` enters `roster.KNOWN_FAMILIES` additively: no subject family is removed, and the local families the roster epic adds are untouched.
- The client is bound as a judge backend in `judge_backends.py` and imported by no other judge-path module.
- The API key is read from one named environment variable, is absent from the repo, from logs and from any `Settings` repr, and a run needing this judge with no key configured says so before any paid call is made, naming the variable.
- Egress: a judged row that used this judge names DeepSeek among the providers the item and the subject output reached, and the README's egress sentence names DeepSeek and the data-use and retention terms the spike recorded (Privacy Policy of 2026-02-10, Open Platform Terms effective 2026-04-29: API inputs may be used for training unless opted out, are processed and stored in the PRC, and are retained "as long as necessary" with no fixed period). Per owner answer Q103 (c), 2026-10-03, the owner sends the training opt-out email to privacy@deepseek.com before the first paid call (an owner act, not code), and the README states that it was sent, its date, and whether DeepSeek confirmed it.

## Code it changes

- `src/wave_local_ai_v2/` (new DeepSeek client module): `requests` only, no SDK, no streaming, mirroring `mistral_client.py` and `google_client.py`; its module docstring cites the spike's decision file.
- `src/wave_local_ai_v2/judge_backends.py`: the DeepSeek backend, paced and retried per batch like the existing two.
- `src/wave_local_ai_v2/judge.py`, `src/wave_local_ai_v2/row_contract.py`: the API version and the build markers on the judge record, with its `SCHEMA_VERSION` bump, unless order 8 lands them first.
- `src/wave_local_ai_v2/cost.py`: the DeepSeek price table in `PRICE_TABLES` with its import-time guard, and DeepSeek's basis in `REASONING_TOKEN_BILLING`.
- `src/wave_local_ai_v2/roster.py`: the `deepseek` family and the pinned id's entry in `MODEL_FAMILIES`.
- `src/wave_local_ai_v2/settings.py`, `.env.example`: the key, `repr=False`, not required at load time.
- `README.md`: the egress sentence.

## Tests it needs

- A new client test module (HTTP stubbed): a well-shaped response yields content, finish reason and all token counts; each malformed field raises the typed error at the provider boundary; an id absent from a stubbed catalog raises the unavailable-model subclass naming it; a build marker differing from the pinned one refuses the run naming the marker; a 429 raises the retryable subclass carrying the hint; a block finish reason fails the call with the reason named.
- `tests/test_cost.py`: the entry is keyed by the literal pinned id; a missing entry fails at import.
- `tests/test_judge.py` (HTTP stubbed): a judge call through the DeepSeek backend yields a contract-valid judge record with family `deepseek`, its effort and its reasoning tokens.
- `tests/test_settings.py`: the key is read, defaults to empty, never appears in a repr.

## Evidence it publishes

- One live DeepSeek judge call over one probe item, its judge record read back and contract-valid, cited in the story's task evidence. It is written to no results file.

## Cancellation

n/a: not cancelled.
