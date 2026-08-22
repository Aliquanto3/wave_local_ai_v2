---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/rows-carry-a-schema-version-and-a-writer-gate-refuses-incomplete-rows.md
order: 3
---

# Story: Rows name the code and the tree that produced them

**As** a client-side engineer reproducing a published number
**I want** every row to carry the release version, the commit sha and whether that sha was stamped from a modified working tree
**So that** I can check out the exact code behind a row, and a row produced from code that never existed says so instead of failing silently

## Acceptance

- Methodology 19: every runtime and quality row carries `run_id`, `captured_at`, `release_version` and `commit_sha`.
- Methodology 19: every row carries `tree_dirty`, true when the working tree held uncommitted changes to tracked files at capture time.
- `release_version` falls back to the packaged version when no release tag identifies the checkout; the fallback is visible in the value rather than silent.
- Capture never aborts a run: an unavailable git context writes explicit nulls for `commit_sha` and `tree_dirty` and the row is still written, under the writer gate of order 2.
- The values are captured once per run and are identical across every row that run writes.

## Code it changes

- `src/wave_local_ai_v2/provenance.py` (new) — resolves version, sha and dirty state; degrades to nulls rather than raising.
- `src/wave_local_ai_v2/row_contract.py` — the four provenance fields become required for both row kinds.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — capture once per run, stamp on every row.

## Tests it needs

- `tests/test_provenance.py` (new) — with the git invocation stubbed: a clean tree yields `tree_dirty` false, a modified tree true, a failed invocation yields nulls, and an absent release tag yields the packaged version.
- `tests/test_cli.py`, `tests/test_quality_cli.py` — every row of one stubbed run carries the same provenance quadruple.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` and `quality-reference.jsonl` rows (order 19 and 20) carry the sha and the clean-tree flag the two current tracked files cannot carry at all.

## Cancellation

n/a — not cancelled.
