---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on:
  - aidd_docs/backlog/stories/a-runtime-row-is-a-warmed-and-cooled-repetition-set.md
  - aidd_docs/backlog/stories/a-failed-generation-scores-zero-and-names-its-reason.md
order: 9
---

# Story: A failed repetition fails its row with an index and a reason

**As** a client-side engineer comparing two published runtime rows
**I want** a repetition that fails to fail the whole row, naming which one failed and why
**So that** no published aggregate is computed over a silently repaired or silently zeroed sample

## Acceptance

- Methodology 6 with 9: a repetition whose generation is empty, truncated or unparseable fails the whole row. It is not dropped and re-run, which biases toward success, and not kept as zero, which destroys the median.
- Methodology 6: the failure names the failing repetition's index and its reason, and the harness exits non-zero having written no aggregate row.
- Methodology 9: the reason comes from the same taxonomy the quality path uses — `empty`, `unparseable`, `truncated_max_tokens`, `truncated_context` — so a cap the suite chose and a limit the model imposes are never reported as one thing.
- The failure is reported on stderr as one line naming index and reason, in the harness's existing single-line error style.
- A warm-up failure fails the row under the same rule; a warm-up is not a licence to retry.

## Code it changes

- `src/wave_local_ai_v2/repetitions.py` — classifies each repetition's outcome and raises on the first failure with index and reason.
- `src/wave_local_ai_v2/timings.py` — surfaces the stop reason and generated-token count needed to separate the two truncations.
- `src/wave_local_ai_v2/__init__.py` — the new failure joins the caught error set so it prints one line rather than a traceback.

## Tests it needs

- `tests/test_repetitions.py` — a stubbed run where repetition 3 of 5 returns an empty completion writes nothing and raises naming index 3; a cap-truncated and a context-truncated stub produce the two distinct reasons; a failed warm-up fails the row.
- `tests/test_cli.py` — the failure exits non-zero, prints one line, and leaves the results file byte-identical.

## Evidence it publishes

- `tests/test_repetitions.py` is the falsification: it proves an aggregate row cannot exist over a failed repetition. No published row demonstrates this — the absence of a row is the evidence, and `aidd_docs/results/README.md` records the rule alongside the regenerated file (order 19).

## Cancellation

n/a — not cancelled.
