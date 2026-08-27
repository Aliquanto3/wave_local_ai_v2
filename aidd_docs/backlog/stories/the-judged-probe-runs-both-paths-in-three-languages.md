---
type: story
status: ready
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/a-rate-limited-run-persists-resumes-and-never-re-pays.md
order: 6
---

# Story: The judged probe runs both paths in three languages

**As** a consultant about to point the judged machinery at a real task suite
**I want** about ten open-ended items in EN, FR and DE judged end to end and published as their own reference file
**So that** the two-judge path and the single-judge path are proven by rows a reader can inspect rather than described by tests

## Acceptance

- About ten open-ended items spanning EN, FR and DE, each tagged with its language and its provenance, run end to end and written to `aidd_docs/results/judge-probe-reference.jsonl` — never into `quality.jsonl`.
- Local SLM outputs are judged by both providers and carry a real agreement figure; at least one cloud-subject output is judged by the other-family judge only and is flagged single-judge. Both paths are exercised by rows, not by stubs.
- Every probe row is contract-valid under the judged quality contract and carries the judge model ids, the judge prompt id and hash, the rubric version, both judges' scores, each judge's raw returned text, and either the named statistic or the single-judge flag — plus the contested marking where the threshold applies.
- An FR item's row shows the judge prompt each side received in French, and a DE item's in German, read off the row rather than off the template source.
- The probe publishes no benchmark score and is not a task suite. It sits below Methodology 4's 20-item gate deliberately, says so in the results README, and its file is never read as a suite reference.
- The probe's items and rubric do not pre-empt the rewriting suite's: that suite owns its own items and its own rubric text, and this file is not a draft of them.
- `aidd_docs/results/README.md` records what the first real two-judge agreement figure was, whether the more-than-1-point contested threshold survived contact with genuine disagreement, and whether free-tier limits made a full-roster judged run impractical rather than merely slow — the three questions the epic asks to be answered once it is done.

## Code it changes

- `src/wave_local_ai_v2/judge_probe.py` (new) — the roughly ten open-ended items with their language and provenance tags, and the runner that produces the local two-judge rows and the cloud single-judge row into the probe's own path.
- `src/wave_local_ai_v2/settings.py` — the probe reference path, defaulted, mirroring the existing `*_reference_path` settings.
- `aidd_docs/results/README.md` — the probe's own section, its non-suite status stated, and the epic's three closing answers.

## Tests it needs

- `tests/test_judge_probe.py` (new, HTTP stubbed) — the item set covers EN, FR and DE and every item is open-ended rather than label-scored; a stubbed end-to-end run writes contract-valid judged rows to the probe path and writes nothing to `quality.jsonl`; the run produces both a two-judge row carrying an agreement figure and a single-judge row carrying the flag.

## Evidence it publishes

- `aidd_docs/results/judge-probe-reference.jsonl` committed, with its README section — the epic's Success Evidence, whose five checks are all readable off these rows.

## Cancellation

n/a — not cancelled.
