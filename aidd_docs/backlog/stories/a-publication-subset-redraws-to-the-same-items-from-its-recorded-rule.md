---
type: story
status: ready
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-certified-to-its-declared-level-and-every-item-names-its-licence-and-source.md
order: 5
---

# Story: A publication subset redraws to the same items from its recorded rule

**As** an academic or technical reviewer asking "how did you pick these hundred items"
**I want** the answer to be a recorded selection rule I can replay to get the same item ids in the same order, with each drawn item provably the item that was scored
**So that** a publication suite's subset cannot have been chosen to flatter a result, and an upstream edit to the source is visible at the item rather than only at the set

Maps to: PRD AC "Given a published suite, ... a publication-level suite names each public benchmark its subset came from, that benchmark's licence, and the selection rule that produced the subset" (the selection-rule half); Methodology 4 (canonical ordering, stable source key, loader and sampler versions, stratification, per-item content hash, seed retries), Methodology 5; epic Boundaries "licence and source on the item, selection rule on the suite"; epic success check 2.

Needs: none. The sampler is proved against a constructed source table; no model run, API key, hardware or operator is required. Drawing a real subset is orders 7 and 8.

## Acceptance

- The selection rule is recorded as data on the suite: each benchmark drawn from with its licence and revision, the seed, the sampler version, the loader library and its version, the stable source key, and the canonical ordering (source rows sorted by that key) applied before sampling.
- The sampler is stratified by construction: by language always, and by label as well where the source is a classification benchmark, so the first seed meets the publication level's 25% language share (order 4) by design.
- Where a seed is nonetheless retried, the attempt count and every seed tried are recorded; a retry loop that records only the final seed is refused.
- Each drawn item carries a content hash over its own normalised text, its licence, its source and that source's revision.
- Replaying the recorded rule over the same source returns the same item ids in the same order. Changing the seed changes them; shuffling the source rows before the replay changes nothing, because the canonical ordering is applied first; changing nothing changes nothing.
- A source item whose text no longer matches its recorded content hash is named by item id on replay, rather than surfacing only as a changed `prompt_set_hash`.
- The drawn subset passes order 4's gate at the `publication` level on the first recorded seed of the constructed source.
- The fields this adds to the suite definition are the ones the epic names (source, licence, content hash, selection rule); they are proposed to the suite definition shape owned by `no-use-case-is-silently-absent`, not forked from it.

## Code it changes

- `src/wave_local_ai_v2/` (new sampler module): canonical ordering, stratified seeded draw, retry recording, per-item content hash, the selection-rule record.
- A replay entry point, so the rule is checked by a command rather than described in prose.

## Tests it needs

- Same seed and source returns identical ids and order; a shuffled source returns the same; a changed seed differs; an edited source item is named by id; a retried draw records every seed; a classification fixture is stratified by label and language; the result certifies at `publication`.

## Evidence it publishes

- None beyond the tests: the first real draw and its record are published by orders 7 and 8.

## Cancellation

n/a: not cancelled.
