---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
order: 21
---

# Story: A cloud subject re-run is decided per item under its suite's declared tolerance

**As** a client-side engineer re-running a published cloud-subject quality batch
**I want** every quality suite to declare a per-item divergence tolerance, and a cloud subject's re-run to be decided per item under it, naming the items that diverged, or marked single-run indicative when it cannot be re-run deterministically at all
**So that** a provider's own non-determinism is read as a property of the subject rather than as a failed reproduction, and a local subject is still held to identical per-item output

Maps to: PRD Methodology 8 ("a cloud subject is judged under a stated tolerance instead ... a re-run within the suite's declared per-item divergence tolerance is reproduced and names the items that diverged, and a cloud row that cannot be re-run deterministically at all is marked single-run indicative rather than not reproduced"); PRD AC "Given a cloud subject re-run, its quality reproduction verdict is decided per item under the declared divergence tolerance and names the items that diverged; given a cloud subject that cannot be re-run deterministically, its row is marked single-run indicative rather than not reproduced"; epic criterion ledger row 8 ("the reproduction verdict for both quality and runtime"); owner decision Q71 (2026-10-01): one verdict rule for every quality batch, owned here, which the judged re-run story's subject component reuses.

Needs: a cloud subject key already configured (Mistral or Google AI Studio) for the evidence re-run. The verdict logic itself is proven on constructed rows.

Current state: `verdict.quality_verdict` decides every batch, local or cloud, on identical per-item `predicted_label` or `item_score`, so one diverging cloud item is `not_reproduced`. No suite declares a tolerance, and no row can be marked single-run indicative. The classification and translation suites both run Mistral and Google as cloud subjects today.

## Acceptance

- Every quality suite declares its per-item divergence tolerance, with its unit and the reason for its value, beside its caps and in whatever form its definition takes; the suite gate refuses a suite that declares none. The classification and translation suites each declare one. The PRD states no value: each is set during delivery against an observed cloud re-run and recorded with its reason, the way the runtime 10% was calibrated against bench runs.
- A local subject batch's verdict is unchanged: identical per-item output under the same model, prompt version and seed, or not reproduced.
- A cloud subject batch is assessed per item: it is `reproduced` when the re-run stays within the suite's declared tolerance, and the verdict block names every item that diverged even then; beyond the tolerance it is `not_reproduced`, naming the items.
- A cloud subject batch that cannot be re-run deterministically at all (its dated model id is no longer served, or its provider accepts no seed for it) is marked single-run indicative, naming which, and is never `not_reproduced`.
- The verdict block names the tolerance it was decided under and the suite version that declared it, so a reader can dispute the value rather than the arithmetic.
- `not_comparable` keeps its existing triggers (no matching reference, items on one side only, no comparable per-item value); a cloud batch is never decided off null values.
- The new verdict fields extend the quality row additively under a `SCHEMA_VERSION` bump, with its reason in the version comment block.
- This story owns the subject-side rule only. A judged batch's judged component stays with `a-judged-re-run-receives-a-reproduction-verdict-that-separates-the-subject-from-its-judges.md`, which reuses this rule for its cloud subject component.

## Code it changes

- `src/wave_local_ai_v2/verdict.py`: the per-item cloud-subject decision under a declared tolerance, the diverging-item list, and the single-run-indicative mark.
- `src/wave_local_ai_v2/classification_suite.py`, `src/wave_local_ai_v2/translation_suite.py` (or their data form, if the suite seam has landed): the declared tolerance with its unit and reason.
- `src/wave_local_ai_v2/suite_gate.py`: refuse a suite with no declared tolerance.
- `src/wave_local_ai_v2/quality_cli.py`: pass the suite's tolerance and the subject's provider to the verdict.
- `src/wave_local_ai_v2/row_contract.py`: the verdict fields and the `SCHEMA_VERSION` bump.

## Tests it needs

- `tests/test_verdict.py`: a cloud batch with diverging items inside the tolerance is `reproduced` and names them; one beyond it is `not_reproduced` naming them; a cloud batch whose model id is no longer served is single-run indicative, not `not_reproduced`; a local batch with one diverging item is still `not_reproduced`; an all-null cloud batch is `not_comparable`.
- `tests/test_suite_gate.py`: a suite declaring no tolerance is refused.
- `tests/test_row_contract.py`: a quality row missing the new verdict fields is refused; a deterministic local row validates.

## Evidence it publishes

- One cloud-subject batch of the classification or translation suite re-run against its published reference, with the verdict read back and recorded in `aidd_docs/results/README.md` beside the declared tolerance and the observed divergence, so the value is shown against what a real provider did rather than assumed to fit it.

## Cancellation

n/a: not cancelled.
