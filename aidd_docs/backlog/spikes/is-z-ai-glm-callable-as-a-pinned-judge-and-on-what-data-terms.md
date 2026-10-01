---
type: spike
status: open
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parents:
  - aidd_docs/backlog/stories/a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md
---

# Spike: Is Z.ai's GLM callable as a pinned judge, and on what data terms

## Question

Does Z.ai's direct API expose a GLM model that can be pinned to a dated id from a live catalog, called with reasoning disabled or minimal under caller-pinned sampling, survived on its paid tier's rate limits, and costed from a published list price, and do Z.ai's data-use and retention terms let the repo's suite items and a local model's output be sent to it?

## Decision

Go or no-go for the GLM judge client (order 8), and its build inputs: the pinned dated id, the sampling set and seed availability, the reasoning control and the effort value it sends, the finish-reason mapping, the rate-limit status and retry-hint shape, the list-price entry, and the data-use sentence the README's egress statement carries. Terms incompatible with the PRD's egress non-goal are a finding that reopens the judge pair, not a detail.

## Bounds

- Evidence needed: captured live requests and responses, never a documentation page alone, for each of the questions the completed Google spike answered (`aidd_docs/backlog/stories/google-ai-studio-api-surface-is-confirmed-live.md`): live catalog endpoint and auth, and the shape of one entry; whether dated non-floating ids are listed and addressable, and which alias each resolves from; sampling parameter names, ranges and the values applied when omitted; whether a per-request seed exists and is honoured (repeated calls with and without it); where the content, finish reason and usage counts live, the full finish-reason enum with its block or safety values, and whether reasoning tokens are reported apart from output tokens; the reasoning or thinking control, whether it can be disabled, and what is billed when it is; the paid tier's rate limits, the status and body of a limit response and any retry-after hint; the API version a row records and where it is read; catalogue input, output and reasoning rates for the pin candidate, with source URL and retrieval date; Z.ai's data-use and retention terms for API traffic at a named revision, including whether submitted text is used for training. The precedent `mistral_client.py` records stands: a documented id that is absent from the live listing is recorded as that failure.
- Stop when: one dated id is named as pin candidate with every build input above answered from a captured call and the terms stated from their text, or the API is shown unable to meet Methodology 12's pre-flight or the egress non-goal, which is recorded as a no-go.
