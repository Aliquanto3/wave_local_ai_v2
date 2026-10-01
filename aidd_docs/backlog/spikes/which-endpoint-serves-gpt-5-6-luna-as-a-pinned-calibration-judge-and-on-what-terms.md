---
type: spike
status: open
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parents:
  - aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md
---

# Spike: Which endpoint serves GPT-5.6 Luna as a pinned calibration judge, and on what terms

## Question

Through which endpoint can GPT-5.6 Luna be called as a calibration judge pinned to a dated id from a live catalog, with reasoning disabled or minimal under caller-pinned sampling, at what rate limits and list price, and under what data-use and retention terms for the repo's suite items and a local model's output?

## Decision

The calibration client's build inputs (order 11): the serving endpoint the owner's answer to Q7 selects, its pinned dated id, the sampling set and seed availability, the reasoning control and the effort value it sends, the finish-reason mapping, the rate-limit status and retry-hint shape, the list-price entry, the family the model is declared under, and the data-use sentence the README's egress statement carries. It also returns the projected cost of calibrating 10% of a full judged campaign at the found rate, which the owner weighs against the budget question Q9.

## Bounds

- Evidence needed: captured live requests and responses, never a documentation page alone, against the vendor's direct API, and against a router only if Q7 is answered that way (then also: whether the provider order can be fixed, fallbacks disabled, and the answering provider read off the response): live catalog endpoint and auth; whether a dated non-floating id for GPT-5.6 Luna is listed and addressable; sampling parameter names, ranges and defaults, and whether temperature is accepted at all at the chosen reasoning setting; whether a per-request seed exists and is honoured; where the content, finish reason and usage counts live, the full finish-reason enum with its block or safety values, and whether reasoning tokens are reported apart from output tokens; the lowest reasoning effort the model accepts and what is billed at it; the paid tier's rate limits, the status and body of a limit response and any retry-after hint; the API version a row records; catalogue input, output and reasoning rates with source URL and retrieval date; the endpoint's data-use and retention terms for API traffic at a named revision.
- Stop when: one dated id on one endpoint is named as pin candidate with every build input above answered from a captured call and the terms stated from their text, or no endpoint is shown able to meet Methodology 12's pre-flight or the egress non-goal, which is recorded as a no-go for the calibration judge as specified.
