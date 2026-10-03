---
type: story
status: proposed
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md
  - aidd_docs/backlog/tasks/register-the-closed-harness-candidate-set-and-its-three-row-fields.md
  - aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md
order: 9
---

# Story: A web-research score recomputes offline from its archived search responses

**As** a client-side engineer challenging a web-research score weeks after it was published
**I want** every search response archived with its row, the answer judged against those archived sources, and a live re-run labelled non-reproducible and refused against the published number
**So that** I can recompute the published score with the network off, and a score is never quietly compared against a search engine that has since changed its answers

Maps to: PRD AC "Given the web-research use case, at least two distinct web-search tools are benchmarked against the same query set, with results attributable to which tool was used and every search response archived with its row" (archival half); PRD AC "Given a web-search call that returns no results, an error, or a rate limit, the row records that tool outcome, and the item is excluded from the model's score while remaining visible in the tool comparison" (recording and exclusion half); PRD AC "every row records whether its prompt left the machine"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side"; Methodology 9, 10, 11, 17, 18; epic Boundaries "a search-tool adapter interface", "the tool-outcome rule", "egress recorded"; epic Sequence step 7; epic success checks 4 and 6.

Needs: a real local model run; an operator hosting SearXNG pinned at commit `783a094` with JSON output enabled and `google cse` removed from its default engines (no account); paid API keys for Z.ai (GLM judge) and DeepSeek (DeepSeek judge).

Blocked: by the spike `aidd_docs/backlog/spikes/which-two-search-tools-are-obtainable-archivable-and-what-each-sends-upstream.md` (`blocked`): its live SearXNG capture (Follow-up steps 1 and 2: a pinned instance queried in EN, FR and DE, each JSON body saved with the upstream URLs from the debug log) is not yet run. And through `depends_on` on `aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (`proposed`), which waits on its orders 8 and 9, each blocked by its judge-provider spike (`blocked` on live calls with a paid key) and by Q102.

Current state (verified on `main` at `c68b23e`, 2026-10-03): no search adapter, archive format, offline recompute path or web-research suite exists; `use_case_coverage.json` has `web-research` at `null`. A quality row records where its subject prompt went in `subject_egress` (`row_contract.subject_egress_for`: `none` or the provider id) and where judging sent content in `judge_egress`; no field records a search tool or its upstream engines. Rows carry `harness_id` `direct` through `quality_rows.direct_harness_fields`. Judged scoring runs only in `judge_probe.py`, and `judge_backends.py` binds only Mistral and Google.

## Acceptance

- Web research is a retrieve-then-answer pipeline: the harness issues each query's search, archives the response, and the model answers over the archived results, so every archived response is a function of the query alone. The model never decides when or what to search; an agentic web-research variant is out of this story and deferred until the tool-calling spike reports, and this suite sits outside the harness comparison this release.
- A search-tool adapter interface exists with one implementation, SearXNG (self-hosted, pinned at commit `783a094`, JSON output enabled, its default engine set minus `google cse` per owner answer Q113 (b), 2026-10-03), the one of the spike's two tools that needs no account; every row names the tool that produced its search results.
- The web-research suite is registered through the seam (order 1) with at least 20 queries, each with a dated reference answer, EN, FR and DE each at 25% or more, every query tagged and provenanced.
- Every search response is archived with its row in the run archive as the raw JSON body as returned, plus the request URL without any key, its parameters, the tool version, the engine list and a timestamp (the spike's archive form). Recomputing the suite's scores from the archive with the network disabled reproduces the published scores (epic success check 4, verified with the network off).
- The full responses stay in the run archive that the offline recompute reads. The bundle publishes per row only the result URLs, a content hash of the archived response, the tool, the egress destinations and the scores, never a result title or snippet (owner answer Q114 (a), 2026-10-03), so a bundle reader without the archive cannot recompute a web-research score.
- A live re-run of a published query is labelled non-reproducible on its row, and any comparison of it against a published number is refused naming that label.
- The answer is judged by the GLM and DeepSeek pair against the archived result snippets (no separate page fetch, which would add per-host egress), with this suite's own rubric text and contested threshold (the shipped default unless recorded otherwise).
- A search call returning no results, an error or a rate limit records that tool outcome on the row and excludes the item from the model's score; a forced 429 produces such a row and leaves the model's score computed over the remaining items (epic success check 6, verified by forcing the 429).
- Every row records that its query left the machine, to SearXNG and to each upstream engine of the pinned engine set (owner answer Q113 (b), 2026-10-03): DuckDuckGo and the Brave website, which SearXNG reaches by scraping from the instance's public IP (the spike's egress finding), and Wikipedia and Wikidata; the row's egress field names each. It carries the harness task's fields with harness `direct`.
- At least one local and one cloud batch are published. The coverage record's web-research entry stays unresolved until order 10 lands, because one tool does not satisfy the acceptance criterion.

## Code it changes

- The search adapter interface and its first implementation; the archive format; the suite's data file and scoring rule; the offline recompute path.
- `src/wave_local_ai_v2/bundle_export.py`: the web-research row's published fields, without titles or snippets.

## Tests it needs

- Offline recompute from a fixture archive equals the recorded score with network access patched to fail.
- A stubbed 429, an empty result and an error each record their outcome and are excluded from the model's score.
- A live-labelled row compared against a published row is refused.
- A web-research row's bundle export carries its result URLs, the archived response's content hash, the tool, the egress destinations and the scores, and no title or snippet.

## Evidence it publishes

- The batches, published under the Q114 (a) rule above, the suite snapshot, and the offline-recompute run; the archived responses stay in the run archive.
- One MoE and one tiny dense roster entry run over the same queries at one suite version and published side by side, each citing its roster entry; or, for an entry that cannot run this suite, a recorded refusal naming the entry and why.

## Cancellation

n/a: not cancelled.
