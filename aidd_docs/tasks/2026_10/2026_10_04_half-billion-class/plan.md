---
objective: "The ~0.5B class holds a second family beside Qwen3-0.6B, admitted through the candidate gate and run through both suites on the laptop, or is labelled a single-family ladder citing every refusal, and the composition check passes for the class."
status: implemented
---

# Plan: The ~0.5B class spans two families, or is published as a searched single-family ladder

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Gate the class's pinned candidates in order until one non-Qwen entry passes and completes both suites; publish its entry, rows, download section and the class's composition |
| **Source** | `aidd_docs/backlog/stories/the-half-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md` |

## Phases

| #   | Phase                                        | File                         |
| --- | -------------------------------------------- | ---------------------------- |
| 1   | Candidate gate runs, in gate order           | [`phase-1.md`](./phase-1.md) |
| 2   | Roster entry, both suites, promote and merge | [`phase-2.md`](./phase-2.md) |
| 3   | Class declaration, README, setup, tests      | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `https://huggingface.co/api/models/ibm-granite/granite-4.0-h-350m-GGUF/revision/a864f823cce6e6048b5752e2816fe7a23987d790` | the pinned sha resolves; `Q8_0` is shipped; card `license: apache-2.0`; no LICENSE file (the gate reads README.md) |
| `https://huggingface.co/ibm-granite/granite-4.0-h-350m/blob/3b17b717b8f2f5d305b0a92c1491e239aeda19c8/README.md` l.23-24 | the language statement (the GGUF repo's card states none) |

## Decisions

| Decision | Why |
| -------- | --- |
| Each declaration copies the class's Qwen entry's `server_flags` verbatim (sampler included) and `load_profile` `{n_cpu_moe: null, threads: 8}` | The spike's example declaration; quality batches pin their sampler per request (`quality_cli.LOCAL_SAMPLING`), so the launch sampler does not move a score, and a shared launch block keeps the family comparison about the model |
| The Granite language claim cites the base model card at its own sha, not the GGUF repo | The GGUF repo's README carries no language statement; the gate records the declared source, and the roster test's "read at the entry's own revision" rule is narrowed to the licence for this entry |
| The new entry's `requirements` declare RAM and disk as lower bounds (the weights' size), VRAM `not_yet_declared` | No runtime peak exists for the model; the flagship's `cpu_only` RAM is the precedent for a declared lower bound |
| Suite rows are produced from the worktree with the uncommitted entry (`tree_dirty: true`) | The implementer may not commit; a clean-clone run cannot see an entry that is not committed. Stated in the evidence for the orchestrator |
| `scripts/release_parquet.py` types the unit `as the metric defines` as a string column | The bundle's first translation rows bring `metric_params_*` columns whose unit had no Parquet type, so the release build refused the bundle; a string keeps each CSV cell whatever shape a metric's parameter takes (the precedent is `as the fiche field`) |
| Candidate records are appended to the tracked default `aidd_docs/roster/candidate-records.jsonl` | The story names that file as the candidate record the refusals behind a label are read from |
