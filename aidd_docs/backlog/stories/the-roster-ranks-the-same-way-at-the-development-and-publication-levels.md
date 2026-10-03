---
type: story
status: proposed
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
depends_on:
  - aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md
  - aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md
order: 11
---

# Story: The roster ranks the same way at the development and publication levels, or says where it does not

**As** an academic or technical reviewer weighing whether a finding on the small hand-written suites survives on a public benchmark
**I want** at least two roster subjects published at both levels on both suites, and a written statement of whether the publication and development levels rank them the same way
**So that** a ranking that flips between the uncontaminated hand-written suite and the public subset reads as the contamination signal it may be, and a ranking that holds reads as a finding that survives at scale, within what the intervals resolve

Maps to: epic Success Evidence, the "Once `done`" paragraph ("whether the publication and development levels ranked the roster the same way", a disagreement between them being "a contamination signal" and "worth more than either score alone"); epic decision "The two levels coexist"; Methodology 4, 5; owner answer Q130 (a), 2026-10-03, which narrowed orders 7 and 8 to one subject each and filed this comparison here.

Needs: a real local model run: for each of the two use cases, batches at both levels on enough roster subjects that at least two are published at both. Orders 7 and 8 publish one subject each, so at least one more subject per use case, four batches, on the bench machine.

Blocked: through `depends_on` on `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` and `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md`, both `ready`, not yet built, which create the two publication suites and publish their first subject at both levels. Created 2026-10-03 under owner answer Q130 (a) and not yet through a three-amigos review, so it stays `proposed` until one.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- No publication suite exists. The committed `quality-reference.jsonl` holds 80 `classification-support-routing@2` rows over two subjects (Qwen3.6-35B-A3B local, mistral-small-2603 cloud) at schema `"7"`, and no translation row.
- The comparison record refuses two sides whose `suite_id` or `suite_version` differ (`comparison._ABSENCE_REFUSAL_FIELDS`), so the two levels, being different suite ids over different items, are never compared by a record; the epic puts any rank-agreement statistic out of scope.
- A leader set is computed per suite (id and version) and machine class, over local subjects only, by `wave-local-ai-v2-compare --leader-sets` (`leader_set.py`), so each level gets its own leader set and the two are read side by side, never merged.

## Acceptance

- For each of the two use cases, at least two roster subjects have a published batch at both levels: the publication suite of order 7 or 8, and its hand-written counterpart at its current version. Each subject's two batches share `roster_entry_id`, `fiche_hash` and `engine_build`, the pair orders 7 and 8 define. The subjects those orders publish count toward the two. New rows are appended under the supersede-don't-backfill discipline.
- `aidd_docs/results/README.md` sets, per use case, each subject's development-level score and publication-level score side by side, each with its interval, and never averages the two levels. [Methodology 4]
- It states, per use case, whether the two levels order the subjects the same way, read off the two published tables by hand. Where a level's leader set or a comparison record between two subjects at that level says they are not distinguishable, their order at that level is reported as not resolved rather than as a rank. No rank-agreement statistic is computed and no cross-level comparison record is written.
- A disagreement is reported as the contamination signal the epic names, naming the subjects and the direction of the flip; an agreement is reported with both levels' minimum detectable effects, so it is not read as stronger than they allow.
- The observation is recorded in the epic's Done note, as the "Once `done`" paragraph asks.

## Code it changes

- None by necessity. The batches run through `wave-local-ai-v2-quality`, and the leader sets and any comparison record through `wave-local-ai-v2-compare`.

## Tests it needs

- A recorded recomputation over the bundle: every score and interval in the side-by-side table matches the published rows, each subject's two batches share `roster_entry_id`, `fiche_hash` and `engine_build`, and the leader sets recomputed by `wave-local-ai-v2-compare --leader-sets` match the published records.

## Evidence it publishes

- The added batches, the leader-set records of both levels, the README's side-by-side table with its per-use-case statement, and the epic's Done note.

## Cancellation

n/a: not cancelled.
