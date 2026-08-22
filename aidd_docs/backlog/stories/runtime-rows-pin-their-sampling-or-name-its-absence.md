---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 6
---

# Story: Runtime rows pin their sampling or name its absence

**As** a client-side engineer reproducing a throughput figure
**I want** a runtime row to either pin the seed it ran under or declare that it had none
**So that** I know whether a re-run can produce the same generation at all, and an unpinned seed is a disclosed source of spread rather than a hidden one

## Acceptance

- Methodology 1 (runtime half): every runtime row records the seed, temperature, top_p, top_k, presence penalty and the exact model id it ran under, in the same `sampling` block shape the quality rows already use.
- Methodology 1: the row records `seed_pinned` — true when a seed determined the output, false when the run used the server's per-request random seed. Recording sampling values that did not determine the output does not satisfy this criterion.
- When `seed_pinned` is false, the row names the unpinned seed as a spread source, which the Methodology 7 flag of order 10 reports alongside its own statistic.
- Whichever of the two the delivery takes, the choice is stated on the row and not in a comment: pinning a seed departs from the validated baseline command in `context_input/baseline_qwen36.md` and re-validates it against the two curated rows before the roster's first entry is frozen (order 12).
- The quality path's per-request sampler override is untouched and remains the single source of quality sampling.

## Code it changes

- `src/wave_local_ai_v2/server.py` — the sampler flag constants, and a seed flag if the delivery pins one; the flag list stays a byte-for-byte reproduction of whatever is re-validated.
- `src/wave_local_ai_v2/__init__.py` — assembles the `sampling` block and `seed_pinned` onto the runtime row.
- `src/wave_local_ai_v2/row_contract.py` — the sampling block and `seed_pinned` become required runtime-row fields.

## Tests it needs

- `tests/test_server.py` — the built flag list matches the validated baseline exactly, seed flag included or absent as decided.
- `tests/test_cli.py` — with HTTP stubbed, the written row's sampling block matches the flags the server was launched with, and `seed_pinned` reflects the seed's presence.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` rows (order 19) carry a sampling block the two current tracked rows lack entirely, plus the re-validation note in `aidd_docs/results/README.md` if the baseline command moved.

## Cancellation

n/a — not cancelled.
