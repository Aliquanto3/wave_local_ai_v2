---
type: story
status: proposed
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on: aidd_docs/backlog/stories/judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md
order: 5
---

# Story: The rewriting suite scores dense and MoE side by side under the judge pair

**As** a consultant recommending a model class for a client's rewriting need
**I want** every local roster entry, MoE and dense, scored on the rewriting suite over the same items and by the same judge pair as the cloud subjects
**So that** the third use case gets the side-by-side comparison the first two already publish, and which architecture wins rewriting is measured rather than carried over from classification and translation

Maps to: PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side, and each of them cites its entry in the versioned roster file"; PRD AC "Given an open-ended task result from a subject independent of both judge families, it is never presented without both judges' scores and their agreement level"; PRD AC "Given a judged item whose two judges disagree beyond the suite's stated threshold, the item is published as contested and excluded from that suite's headline score"; PRD Goal "For each use case, the benchmark surfaces whichever model family performs best, MoE or dense"; Methodology 3, 4, 10, 11, 13, 24; epic Success Evidence ("rerun ... against the shipped model roster"); epic Progress ("the rewriting use case has no suite and no rows"); `tiny-dense-models-compared-alongside-moe` D1 (rewriting left out because the suite did not exist).

Needs: a real local model run of every local roster entry on the development laptop, and paid API keys for Z.ai and DeepSeek (the judge pair). The cloud columns reuse order 2's Mistral and Google rows where they match, and otherwise need those subjects' keys.

Blocked: only through `depends_on` on `aidd_docs/backlog/stories/judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md` (order 2, `proposed`), which waits on the judge pair's retirement story (judge epic order 10) and the judged probe, both `proposed`, and through them on the GLM and DeepSeek spikes' outstanding live calls (`aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`, both `blocked`) and on owner question Q102. It does not wait on the calibration judge.

Current state (verified on `main` at `c68b23e`, 2026-10-03):

- The roster (`aidd_docs/roster/models.json`, `roster_version` 4) holds one MoE entry (`qwen3.6-35b-a3b-ud-iq4xs`, `UD-IQ4_XS`) and a dense ladder (`qwen3-0.6b-q8`, `qwen3-1.7b-q8`, `qwen3-4b-q4km`). `tiny-dense-models-compared-alongside-moe` is `done` for classification and translation only.
- `read_model.comparison_view` (from `dense-and-moe-stand-side-by-side-on-the-same-items`, `done`) builds one entry per `suite_id` in the quality store and one column per model (`COMPARISON_COLUMN_KEY`: roster entry, provider, model id, fiche hash; plus the `architecture` dimension), so a rewriting batch reaches it without a change to its grouping. Its cells keep only `read_model.COMPARISON_CELL_FIELDS`, which holds no judge field: the judge block `_quality_entry` resolves (`agreement`, `single_judge`, `contested`, `judged_headline_score`, `judged_headline_excluded_n`) is dropped from a comparison cell today.
- `comparison.scoring_kind` recognises only a graded row (`metric_id`) and a binary row (`correct`), so a judged row carrying neither gets no paired test.
- Order 2 scores the rewriting suite against one local subject and one cloud subject; `rewriting-business-email` is not registered yet.

## Acceptance

- Every local entry of the roster at run time, today the MoE flagship and the three dense rungs, is run over the rewriting suite at one suite version: the same items, the same `prompt_set_hash`, and the same maximum output tokens, stop sequences, context length and `thinking_policy` (Methodology 3). Each row cites its `roster_entry_id` and roster version (Methodology 13).
- An entry that cannot run is present as its refusal or its failure reason, never absent: a model below its declared minimum appears as that refusal, and a failed generation scores 0 and names its reason (Methodology 9).
- Each local row is judged by the same judge pair, under the same rubric version and the same judge prompt ids, as order 2's cloud-subject rows. Each carries both judges' scores and their agreement figure, or the single-judge flag where a family collides; on the current roster every row is a two-judge row.
- Contested items stay visible with both judges' scores, are excluded from each column's headline score, and the excluded count is stated beside that headline.
- At least one MoE column and at least one dense column stand over the same rewriting items on the comparison surface, each naming its architecture and quant, with no change to that surface's column grouping; its cells carry each item's judge block, so no judged score stands there without its agreement figure or single-judge flag.
- A cloud subject's rewriting rows from order 2 are cited rather than re-run when they share the suite version and `prompt_set_hash`; otherwise the cloud subject is re-run on this batch, and the comparison never shows two suite versions as one.
- `aidd_docs/results/README.md` gains a rewriting side-by-side table: per column the headline judged score, the agreement figure, the contested count and the per-language breakdown with its n and indicative marks (Methodology 4), plus whether the dense ladder ranks by size on rewriting, the question the classification ladder answered "no".
- No difference between two columns is stated as a result unless a paired test backs it (Methodology 24); until that machinery covers judged scores, the README states the ordering as an observation.
- The batch's judge cost is recorded per judge provider in `judge_cost`, never in `cost_total`, and the README states the batch's total judge spend.

## Code it changes

- `src/wave_local_ai_v2/read_model.py`: `COMPARISON_CELL_FIELDS` gains the judge block, which a comparison cell drops today. Nothing else is expected: the rewriting suite and its rubric come from order 2, the judge pair from the judge epic, and the comparison surface from the pitch epic; this story runs them over the full roster. A change the run proves necessary is recorded as a divergence on this story.
- `aidd_docs/results/README.md`: the rewriting side-by-side section.

## Tests it needs

- `tests/test_read_model.py`: a judged suite's column set over four roster entries carries, per column, its agreement figure or single-judge flag and its contested count, so a side-by-side judged score is never rendered bare.

## Evidence it publishes

- The rewriting rows for every local roster entry in the live quality store, with the fiches they cite committed, and the README section above, so the screen and the README tables can be checked against each other.

## Cancellation

n/a: not cancelled.
