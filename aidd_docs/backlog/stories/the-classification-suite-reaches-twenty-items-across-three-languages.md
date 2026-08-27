---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-declares-its-caps-tags-and-language-mix.md
  - aidd_docs/backlog/stories/a-failed-generation-scores-zero-and-names-its-reason.md
order: 20
---

# Story: The classification suite reaches twenty items across three languages

**As** a consultant publishing a classification score
**I want** the only suite that exists to satisfy the size and language-mix rules its own gate enforces
**So that** the project's one published quality score stops being marked indicative by its own methodology

## Acceptance

- Methodology 4: the classification suite holds at least 20 items, and EN, FR and DE each cover at least 25% of them.
- Methodology 4: the ten added items are natively authored in their language, not machine-translated from the existing ten, and the four routing labels stay semantically disjoint in each language.
- Methodology 5: every added item declares its provenance and, where public, is marked contamination-risk — the ten added items are hand-written, so the declaration is `hand_written`.
- The suite gate of order 1 passes the suite at suite level: it is no longer marked indicative for size or mix.
- Methodology 4: every per-language cell is still reported with its n and marked indicative, because 20 items at a 25% share leaves at most 5 per language and the criterion marks any cell computed over fewer than 10 items indicative. This is recorded as an observed consequence of the initial thresholds, for the first-full-roster-run review, not resolved by changing a threshold here.
- The suite version bumps and the prompt-set hash changes, which retires the existing reproduced-twice evidence; two consecutive runs under the new suite version regenerate `aidd_docs/results/quality-reference.jsonl` and the reproduction is checkable from the file itself through the run ids the rows now carry.
- The regenerated quality rows carry every field the earlier stories added, and each row's verdict states whether the second run reproduced the first.

## Code it changes

- `src/wave_local_ai_v2/classification_suite.py` — ten added items with their tags, the bumped suite version and the changed prompt-set hash.
- `src/wave_local_ai_v2/scoring.py` — per-language accuracy and n beside the suite accuracy, with the per-cell indicative mark.
- `src/wave_local_ai_v2/quality_cli.py` — writes the per-language breakdown onto every row.

## Tests it needs

- `tests/test_classification_suite.py` — 20 items; each of EN, FR and DE at or above 25%; every item tagged and provenance-declared; no two items sharing a prompt; the label set unchanged.
- `tests/test_suite_gate.py` — the real suite now passes the suite-level gate while its per-language cells remain indicative.
- `tests/test_scoring.py` — per-language accuracy over a constructed mixed-language scored set, with n per language and the indicative mark on cells below 10 items.

## Evidence it publishes

- The regenerated `aidd_docs/results/quality-reference.jsonl` — two consecutive runs per model under the bumped suite version, with run ids, per-language cells and failure reasons, replacing the 40 rows whose reproduction claim cannot be read from the file.

## Cancellation

n/a — not cancelled.
