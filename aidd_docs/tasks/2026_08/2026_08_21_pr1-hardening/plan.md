---
objective: "Every open warning-level finding from the PR #1 full-branch review is closed, every results row is attributable to a run, and the acceptance evidence is committed to the repository."
status: in-progress
---

# Plan: PR #1 hardening increment

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Close the nine open 🟡 of the full-branch review plus four named 🟢, grouped by module, so PR #1 can merge on one pass. |
| **Source** | `aidd_docs/tasks/2026_08/2026_08_21_expectations-gap-audit/audit-and-plan.md` section 4.2 and 4.4 (step 0.4), backed by `aidd_docs/tasks/2026_08/2026_08_21_full-branch-review/review.md` |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Row provenance and store safety | [`phase-1.md`](./phase-1.md) |
| 2   | Server lifecycle honesty | [`phase-2.md`](./phase-2.md) |
| 3   | Metrics collection resilience | [`phase-3.md`](./phase-3.md) |
| 4   | Cloud client and quality run order | [`phase-4.md`](./phase-4.md) |
| 5   | Committed evidence and project memory | [`phase-5.md`](./phase-5.md) |

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| `run_id` and `captured_at` are produced by two helpers in `results.py`, not by each CLI. | Both stores must use the same identifier shape and the same clock, or rows from the two CLIs cannot be correlated to one session. `results.py` is the only module both CLIs already import. |
| The two provenance keys are added to both stores even though the tables stay disjoint. | `architecture.md` forbids merging the quality and runtime tables; it does not forbid a shared provenance key. Attribution is a property of a row, not of a table, and the existing disjointness guards (`QUALITY_ONLY_FIELDS`, `RUNTIME_ONLY_FIELDS`) list metric fields only, so neither is weakened. |
| `read_process_rss` swallows `psutil.Error` and returns `None`; the CLI except tuples are not widened for it. | The failure happens after the measurement succeeded. Aborting the run then throws away a good row; a null RSS field costs one column. `psutil.Error` does not subclass `OSError`, so it would otherwise need its own entry in both tuples. |
| `OSError` replaces `requests.RequestException` in both CLIs' except tuples rather than joining it. | Verified locally: `requests.RequestException.__mro__` has `OSError` as its immediate base, so listing both leaves a permanently unreachable entry. One name, one comment, same caught set plus the disk errors `append_row` can raise. |
| `aidd_docs/results/` is un-ignored, but the two live append targets (`runtime.jsonl`, `quality.jsonl`) stay ignored by exact filename; curated `*-reference.jsonl` snapshots are committed instead. | The acceptance evidence must survive outside this machine (PRD reproducibility goal). Tracking the live stores instead would dirty the working tree on every benchmark run and would ship the four rows from the reverted streaming experiment, whose thermally-throttled `gen_tok_per_s` of 17-18 sits next to the acceptance rows with nothing to distinguish them. |
| The committed reference rows are kept byte-for-byte as produced, without back-filling the new provenance keys. | They are evidence. A hand-edited row is no longer the row the harness wrote; the absence of `run_id` dates them, which is the honest signal. |
