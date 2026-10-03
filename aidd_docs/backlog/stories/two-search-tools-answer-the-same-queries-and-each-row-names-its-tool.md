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

Needs: a real local model run; an account and prepaid credits for the hosted tool Q112 settles (Mojeek Web Search API on its Business plan by default, about £2 to £3 per 1,000 queries); the SearXNG instance order 9 runs; paid API keys for Z.ai (GLM judge) and DeepSeek (DeepSeek judge).

Blocked: by Q112 (which hosted tool is the second tool) and Q113 (which SearXNG engine set is pinned); by the spike `aidd_docs/backlog/spikes/which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream.md` (`blocked`): its live Mojeek capture (Follow-up steps 3 and 4: queries in EN, FR and DE saved with the key redacted, and one forced quota or error response) is not yet run; and through `depends_on` on `a-web-research-score-recomputes-offline-from-its-archived-search-responses.md` (`proposed`), blocked by the spike's SearXNG capture, Q113, Q114 and, through the judge pair, Q102. Desk evidence found two tools obtainable (SearXNG self-hosted, Mojeek hosted); if the live capture finds fewer than two obtainable on free or low-cost terms, this story is not built and the coverage record marks the web-research tool comparison `out-of-scope-this-release` with that reason, rather than presenting one tool as the comparison.

Current state (verified on `main` at `c68b23e`, 2026-10-03): no search adapter, archive, tool-comparison output or web-research suite exists, and `use_case_coverage.json` has `web-research` at `null`. No row field names a search tool or its egress destination; `subject_egress` and `judge_egress` cover only the subject and judge calls. `bundle_export.py` has no tool-comparison table.

## Acceptance

- A second implementation of order 9's adapter interface exists for the hosted tool Q112 settles (the spike names Mojeek, with Tavily as fallback), so the two are SearXNG self-hosted and one hosted.
- The same queries, under the same model and caps and through order 9's retrieve-then-answer pipeline under harness `direct`, are run through both tools; two rows for the same query differ only by the tool that produced them, and each names its tool (epic success check 5).
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
