---
type: spike
status: open
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parents:
  - aidd_docs/backlog/stories/the-half-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md
  - aidd_docs/backlog/stories/the-two-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md
  - aidd_docs/backlog/stories/the-four-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md
  - aidd_docs/backlog/stories/the-top-class-spans-two-families-with-dense-and-moe-or-says-why-not.md
---

# Spike: Which candidate GGUFs exist per size class, and does the pinned build load them

## Question

For each of the epic's candidate families (Gemma 4 including the 26B-A4B MoE, Granite at 350M and 1B, Ministral, LFM2, Phi), which models exist as GGUF at a pinnable commit sha in each of the four size classes, under which licence, does the pinned llama.cpp build `b10537` load each one's architecture, and does any MoE candidate exist below the top class?

## Decision

The per-class candidate shortlist the owner answers Q12 from, and the order the class stories (orders 5 to 8) take candidates through the gate. It also tells the owner, once and before any class story starts, whether any candidate needs a newer build: the epic allows an upgrade only once for the whole roster, before the campaign, because `llama_cpp_build` is verdict-blocking and an upgrade turns every published runtime row `not_comparable`. A spike that finds every wanted architecture loads under `b10537` removes that decision; one that finds a family refused frames it with evidence instead of mid-campaign.

## Bounds

- Evidence needed: per candidate, the hub repository, the file, a commit sha and the file size at that sha, recorded from the hub rather than a blog post or leaderboard; the vendor's or packager's GGUF quants available, so a quant comparable to the Qwen entry in the same class can be named; the licence id and whether it restricts publishing benchmark results, quoted from the licence text with the URL and read date; the GGUF's declared architecture string; one `llama-server` load under `b10537` on the dev machine, recording success or the server's refusal line verbatim, for at least the smallest file of each family (one load settles an architecture); the chat template from `/props` for each loaded candidate, noting whether it declares a thinking switch; the vendor's EN/FR/DE claim with its source. For MoE below the top class: the search made (hub queries, vendor model lists) and what it returned, so a negative is a recorded search.
- Stop when: every candidate family has at least one loaded-or-refused result per class it publishes in, each class has a named shortlist or a recorded empty search, and any architecture `b10537` refuses is named with its build line. Running suites, authoring roster entries and choosing which candidates enter are out of bounds: those belong to the class stories and to Q12.
