---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-web-research-score-recomputes-offline-from-its-archived-search-responses.md
order: 10
---

# Story: Two search tools answer the same queries, and each row names its tool

**As** a consultant asked which search tool to pair with a local model
**I want** the web-research queries answered through a second search tool beside the first, one self-hosted and one hosted, with tool failures kept visible in the tool comparison
**So that** I can recommend a tool per model from evidence instead of committing to one by assumption

Maps to: PRD Goals "multiple web-search tools (e.g. a self-hosted option and at least one hosted API) are implemented and compared"; PRD AC "Given the web-research use case, at least two distinct web-search tools are benchmarked against the same query set, with results attributable to which tool was used and every search response archived with its row"; PRD AC "Given a web-search call that returns no results, an error, or a rate limit, ... the item is excluded from the model's score while remaining visible in the tool comparison"; PRD Non-Goals (selecting one winning web-search tool up front); Methodology 17, 18; epic Sequence step 7; epic success checks 5 and 6.

Needs: a real local model run; access to the second search tool the spike names (an API key for a hosted tool, or an operator hosting the self-hosted one); paid API keys for Z.ai (GLM judge) and DeepSeek (DeepSeek judge).

Blocked: the open spike `aidd_docs/backlog/spikes/which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream.md`; if it finds fewer than two tools obtainable on free or low-cost terms, this story is not built and the coverage record marks the web-research tool comparison `out-of-scope-this-release` with that reason, rather than presenting one tool as the comparison.

## Acceptance

- A second implementation of order 9's adapter interface exists for the other tool the spike names, so the two are one self-hosted and one hosted.
- The same queries, under the same model and caps, are run through both tools; two rows for the same query differ only by the tool that produced them, and each names its tool (epic success check 5).
- Both tools' responses are archived and recompute offline exactly as order 9 requires.
- The published tool comparison shows, per tool, the items each tool failed (no results, error, rate limit) with their outcome, while those items stay out of the model's score (epic success check 6).
- Each row records its own egress destination, per the spike's finding for that tool.
- No winning tool is named; the comparison is the output.
- At least one batch per tool is published over the same queries, and the coverage record's web-research entry moves to `exercised` naming the suite.

## Code it changes

- The second adapter; the tool-comparison output over the two tools' rows; the coverage record entry.

## Tests it needs

- With both tools stubbed, the two rows for one query differ only in tool fields and scores.
- A stubbed failure on one tool appears in the comparison with its outcome and is absent from the model's score.

## Evidence it publishes

- The per-tool batches, their archives, and the tool comparison; once done, the epic records which two tools were obtainable and on what terms.

## Cancellation

n/a: not cancelled.
