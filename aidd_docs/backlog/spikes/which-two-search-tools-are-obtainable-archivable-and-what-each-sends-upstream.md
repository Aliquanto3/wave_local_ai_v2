---
type: spike
status: open
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parents:
  - aidd_docs/backlog/stories/a-web-research-score-recomputes-offline-from-its-archived-search-responses.md
  - aidd_docs/backlog/stories/two-search-tools-answer-the-same-queries-and-each-row-names-its-tool.md
---

# Spike: Which two search tools are obtainable, archivable, and what does each send upstream?

## Question

Which two web-search tools, one self-hosted and one hosted API, can this project use on free or low-cost terms; does each return a response that can be archived with its row in a form from which the score recomputes offline (Methodology 17); and what does each actually forward to third parties when queried, so the self-hosted option's egress is checked rather than assumed?

## Decision

Which two tools the web-research suite's adapters implement, or whether the tool comparison is published `out-of-scope-this-release` because fewer than two are obtainable (the epic's second conditional trigger); what each row records as its egress destination; and whether either tool's terms forbid archiving or republishing its responses in the CC-BY 4.0 reference bundle.

## Bounds

- Evidence needed: for each candidate (a self-hosted metasearch instance first, then hosted APIs with a free or low-cost tier), its current pricing and quota page at a dated retrieval, its terms on storing and redistributing responses, one live response captured and saved to show what an archived response contains (result URLs, snippets, and whether page content must be fetched separately to judge against), its rate-limit and error responses as documented, and, for the self-hosted option, which upstream engines it queries by default and what it sends them.
- Stop when: two tools are shown to meet the cost, archivability and terms constraints with their egress stated, or every candidate examined is shown to fail one of them and the shortfall is stated.
