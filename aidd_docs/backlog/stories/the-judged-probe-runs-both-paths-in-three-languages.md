---
type: story
status: proposed
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on:
  - aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md
  - aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md
order: 6
---

# Story: The judged probe runs both paths in three languages

**As** a consultant about to point the judged machinery at a real task suite
**I want** about ten open-ended items in EN, FR and DE judged end to end by the GLM and DeepSeek pair, a calibrated subsample among them, and published as their own reference file
**So that** the two-judge path and the calibration figure are proven by rows a reader can inspect rather than described by tests, and the single-judge path is proven by a forced collision rather than claimed by a row the current roster cannot produce

Maps to: PRD AC "Given an open-ended task result from a subject independent of both judge families, it is never presented without both judges' scores and their agreement level"; PRD AC "given the calibration subsample, its agreement with the judge pair is published as its own figure and no suite score moves because of it"; Methodology 10, 11; epic Boundaries "a judged probe of about 10 open-ended items spanning EN, FR and DE"; epic Success Evidence (all five checks, the single-judge one through order 10's forced collision); owner answers Q6 (a), Q8 (a) and Q9 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

Needs: a real local model run of one roster entry on the development laptop, and paid API keys for Z.ai, DeepSeek and the calibration judge's provider (OpenAI, per Q7 (a)), plus the Google key for the probe's one cloud-subject item.

Blocked: through `depends_on` on order 10, which waits on orders 8 and 9 and their open spikes (`aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`), and on order 11, which waits on the open spike `aidd_docs/backlog/spikes/which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms.md`.

Current state: `judge_probe.py`, its ten items, `settings.DEFAULT_JUDGE_PROBE_REFERENCE_PATH` and `tests/test_judge_probe.py` exist; the runner binds the retired Mistral and Google judges and judges its one Google-generated item with Mistral alone. `aidd_docs/results/` holds no `judge-probe-reference.jsonl`. Order 10 rebinds the runner to the pair; this story runs it and publishes.

## Acceptance

- About ten open-ended items spanning EN, FR and DE, each tagged with its language and its provenance, run end to end and written to `aidd_docs/results/judge-probe-reference.jsonl`, never into `quality.jsonl`.
- Every probe row, the local SLM rows and the one cloud-subject row alike, is judged by both GLM and DeepSeek and carries a real agreement figure. No probe row is single-judge and no probe row is produced by a Mistral or Google judge. The single-judge path is proven by order 10's forced collision, not by a probe row, and the results README says so.
- A calibration subsample of the probe's judged items, drawn under order 11's rule (per batch, seeded, stratified by language, rounded up, at least one item per language present: three items of ten on this probe), is also scored by the calibration judge. Its agreement with the pair is published as its own figure, for EN and for FR/DE separately, each with its n, and an undefined statistic is published as a null with its reason. The pair's per-item scores, the agreement figure and the contested set are the same as they would be without calibration.
- Every probe row is contract-valid under the judged quality contract and carries the judge model ids, the provider that actually answered each judge call, the judge prompt id and hash, the rubric version, both judges' scores, each judge's raw returned text and the named agreement statistic, plus the contested marking where the threshold applies; a subsampled row also carries its calibration record. The judge calls' cost sits in `judge_cost`, never in `cost_total`.
- An FR item's row shows the judge prompt each side received in French, and a DE item's in German, read off the row rather than off the template source.
- The probe publishes no benchmark score and is not a task suite. It sits below Methodology 4's 20-item gate deliberately, says so in the results README, and its file is never read as a suite reference.
- The probe's items and rubric do not pre-empt the rewriting suite's: that suite owns its own items and its own rubric text, and this file is not a draft of them.
- `aidd_docs/results/README.md` records the epic's closing answers: what the first real two-judge agreement figure was; whether the more-than-1-point contested threshold survived contact with genuine disagreement; whether paid-tier rate limits made a full-roster judged run impractical rather than merely slow; what the calibration judge's agreement with the pair was and whether it differed between EN and the FR/DE items; and what the probe campaign actually cost in judge calls, compared against the ten-dollar estimate, with no spend cap applied.

## Code it changes

- `src/wave_local_ai_v2/judge_probe.py`: the cloud-subject item judged by the pair like every other item, the calibration subsample drawn and scored through order 11's backend, and the module docstring restated to the pair, the calibration subsample and the forced-collision proof. The pair binding itself is order 10's change.
- `aidd_docs/results/README.md`: the probe's own section, its non-suite status stated, and the epic's closing answers.

## Tests it needs

- `tests/test_judge_probe.py` (HTTP stubbed): the item set covers EN, FR and DE and every item is open-ended rather than label-scored; a stubbed end-to-end run writes contract-valid judged rows to the probe path and writes nothing to `quality.jsonl`; every row, the cloud-subject row included, carries both pair scores and an agreement figure and none carries the single-judge flag; the calibration subsample holds at least one item per language present and replays to the same item ids under the same seed; the pair's scores, agreement and contested set are identical with and without calibration.

## Evidence it publishes

- `aidd_docs/results/judge-probe-reference.jsonl` committed, with its README section: the epic's Success Evidence, whose checks are readable off these rows and off order 10's forced collision.

## Cancellation

n/a: not cancelled.
