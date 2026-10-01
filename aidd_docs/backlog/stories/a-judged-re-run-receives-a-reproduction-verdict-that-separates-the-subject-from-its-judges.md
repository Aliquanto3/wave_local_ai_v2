---
type: story
status: proposed
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on: aidd_docs/backlog/stories/judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md
order: 6
---

# Story: A judged re-run receives a reproduction verdict that separates the subject from its judges

**As** a client-side engineer re-running the rewriting suite on my own machine
**I want** an explicit verdict on whether my re-run reproduced the published judged score, stating separately whether the subject produced the same outputs and whether the judges scored them the same
**So that** a judged score is reproducible evidence in the same sense as a classification score, and a judge's run-to-run drift is never read as the local model failing to reproduce, nor the reverse

Maps to: PRD Goal "an explicit verdict of reproduced or not reproduced rather than an eyeball comparison"; PRD AC "Given a published run, a re-run of it returns an explicit verdict of reproduced, not reproduced, or not comparable per Methodology 8"; PRD AC "Given a cloud subject re-run, its quality reproduction verdict is decided per item under the declared divergence tolerance and names the items that diverged"; Methodology 8, 10, 11, 12; epic Success Evidence ("get the same quality scores back ... record here whether reproduction actually held"); owner answer Q59 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`: a two-part verdict, owned by this epic.

Needs: none for the verdict itself, which is proven on stubbed judge records. Its evidence re-run needs a real local model run of one roster entry on the development laptop and paid API keys for Z.ai and DeepSeek.

Blocked: through `depends_on` on `judge-scoring-with-inter-judge-agreement-proves-judged-machinery.md`, which waits on the judge pair, the judged probe and their open spikes.

Current state: `verdict.quality_verdict` decides a batch on `predicted_label`, or on `item_score` when no label is carried. A judged row's `item_score` comes from two cloud judges, so a re-run of a byte-identical local output can move it. `judge_probe.py` deliberately does not call the verdict and writes `not_comparable` by hand. No code path issues a verdict on a judged suite batch.

## Acceptance

- A judged batch's verdict block carries two components, each with its own state and the item ids that diverged: the subject component, comparing the subject's per-item outputs, and the judged component, comparing the per-item judged scores. The batch is `reproduced` only when both are; a block never reports `reproduced` off one component.
- Subject component: a local subject reproduces when each item's output is identical to the reference run's under the same model, prompt version and seed. A cloud subject is assessed under Methodology 8's per-item divergence tolerance, and one that cannot be re-run deterministically is single-run indicative, never not reproduced.
- Judged component, offline: recomputing each item's judged score, the agreement figure, the contested set and the headline score from a published row's recorded judge records (their raw returned text) reproduces the published values exactly, with no judge call issued. A mismatch here is not reproduced and names the field.
- Judged component, live: a re-judged item reproduces when each judge's score lies within the suite's declared judge tolerance of the reference, defaulting to the suite's contested threshold (1 point on a 1-5 rubric). A diverging item is named with the judge that diverged.
- A pair whose judge dated model id, judge prompt hash or rubric version differs, or is null on either side, is `not_comparable` naming that field; two unknown values never count as a match.
- No judged verdict is ever decided off null labels: a batch carrying neither a label nor a score on either side is `not_comparable` with its reason, the precedent `judge_probe.py` already writes by hand.
- The verdict block's new fields extend the quality row additively under a `SCHEMA_VERSION` bump, and a deterministic quality batch's verdict is unchanged.

## Code it changes

- `src/wave_local_ai_v2/verdict.py`: the judged verdict with its subject and judged components, and the offline recompute from recorded judge records.
- `src/wave_local_ai_v2/agreement.py`: reused for the recompute, not re-implemented.
- `src/wave_local_ai_v2/quality_cli.py`: a judged batch requests the judged verdict.
- `src/wave_local_ai_v2/row_contract.py`: the verdict block's fields and the `SCHEMA_VERSION` bump, with its reason in the version comment block.

## Tests it needs

- `tests/test_verdict.py`: identical local outputs with judge scores inside the tolerance reproduce; identical outputs with one judge outside it are not reproduced naming the item and the judge; differing outputs with identical judge scores are not reproduced on the subject component; a changed judge model id or rubric version is not comparable naming the field; the offline recompute of a tampered recorded score is refused naming the field; an all-null batch is not comparable.
- `tests/test_row_contract.py`: a judged row missing a verdict component is refused naming it; a deterministic row still validates.

## Evidence it publishes

- One second run of the rewriting suite on one local roster entry, re-judged live, with its verdict read back and recorded in `aidd_docs/results/README.md`: the epic's closing question of whether reproduction actually held for a judged suite.

## Cancellation

n/a: not cancelled.
