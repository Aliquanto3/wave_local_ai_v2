---
objective: "Running the classification task suite against one local SLM (llama-server) and one cloud model (Mistral) produces a deterministic quality score for each, using the same prompts, written into a quality table that is structurally separate from the runtime table -- readable without any hardware fiche or runtime metric, and vice versa."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Deterministic classification scoring proves the quality-table split

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | First quality-scoring vertical slice: one fixed classification task suite, run against one local SLM and one cloud model, scored deterministically (exact label match), written to a new `quality.jsonl` store that shares no schema with `runtime.jsonl`. Proves the quality/runtime split works end-to-end before adding translation, rewriting, judge-scoring, or more models. |
| **Source** | `aidd_docs/backlog/stories/deterministic-classification-scoring-proves-quality-table-split.md` (story, status `ready`, parent epic `aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md`) |

## Phases

| #   | Phase                                        | File                          |
| --- | --------------------------------------------- | ------------------------------ |
| 1   | Classification task suite and deterministic scorer | [`phase-1.md`](./phase-1.md)  |
| 2   | Cloud model client (Mistral)                  | [`phase-2.md`](./phase-2.md)  |
| 3   | Quality results store and settings            | [`phase-3.md`](./phase-3.md)  |
| 4   | CLI wiring (end to end, both models)          | [`phase-4.md`](./phase-4.md)  |

## Resources

| Source | Verified |
| ------ | -------- |
| `aidd_docs/memory/architecture.md` | States the quality/runtime split as a standing decision: "The two are never merged into a single table." Confirms this story is implementing an existing architectural commitment, not proposing a new one. |
| `src/wave_local_ai_v2/results.py` | Existing `append_row`/`read_rows` JSONL helpers operate on plain `dict[str, Any]` with no runtime-specific shape baked in -- reusable as-is for the quality store by pointing at a different path, which is what makes the two tables structurally separate (disjoint files, disjoint schemas) without new store code. |
| `src/wave_local_ai_v2/server.py`, `settings.py`, `__init__.py` | The runtime harness's llama-server lifecycle (`running_server`), settings loader, and CLI pattern (no argparse, one hardcoded run, `main()` catches a fixed exception tuple) are the precedent this story's CLI follows for the local-model side. |
| `.env.example` | `MISTRAL_API_KEY` already present (currently a placeholder) -- the cloud-model credential this story needs is already anticipated in project config, just unused until now. |
| `aidd_docs/memory/ecosystem.md` | Mistral is already documented as "benchmark subject · judge" -- using it as the cloud model under test (not as a judge) for this story is consistent with its documented role, not a new integration surface. |
| `pyproject.toml` | `requests` is already a runtime dependency; no new HTTP client library needed for the Mistral REST call. No Mistral/Google SDK is installed -- this story calls the REST API directly via `requests`, matching the project's existing pattern of no heavy cloud SDKs. |

## Decisions

| Decision | Why |
| -------- | --- |
| Reuse `results.py`'s existing generic `append_row`/`read_rows` for the quality store, pointed at a new `quality.jsonl` path, rather than writing a parallel `quality_results.py` module. | The helpers are already schema-agnostic (`dict[str, Any]`); a second, near-identical module would duplicate logic for no behavioral gain. Structural separation comes from the two tables living in separate files with disjoint field sets (quality rows carry no fiche/timings/energy fields, and vice versa), which a shared low-level file helper does not undermine. |
| Deterministic scoring is exact-label-match (predicted label == expected label after normalization), not a similarity metric. | The story requires "deterministic" and classification is the use case the epic picked specifically because it has "the most direct deterministic-scoring path (classification: label match)". No judge, no fuzzy metric, keeps this slice minimal and provably reproducible. |
| The classification task suite (prompts + expected labels) is authored as a small fixed in-repo Python module, not fetched from `context_input/` or an external dataset. | `context_input/` was checked and holds no classification benchmark data (only hardware/model-candidate notes) -- there is nothing to reuse. A small, fixed, in-repo suite keeps this proof-of-concept reproducible without a new data-loading dependency; the epic's later increments can widen or externalize it. |
| The local SLM reuses the already-validated Qwen3.6-35B-A3B model and llama-server flag set from the runtime harness, not a new model download. | The epic defers exact model-roster selection to later; this story only needs "one local SLM" to prove the scoring machinery, and reusing the already-working model/flags removes a variable (new model validation) that isn't this story's job. |
| Cloud model is Mistral (not Google AI). | Only one cloud model is required by the story; Mistral's REST API is the simpler of the two already-anticipated providers (chat-completions shape, no OAuth flow), and `MISTRAL_API_KEY` is already wired into `.env.example`. |
| The quality CLI is a new, separate entry point (`quality_cli.py` / new `pyproject.toml` script), not a subcommand grafted onto the existing runtime `main()`. | The existing CLI has no subcommand parsing (`argparse`) at all -- it is a single hardcoded run. Adding a second hardcoded-run entry point mirrors that existing pattern exactly; introducing subcommand parsing now would be a bigger, unrelated change this story doesn't need. |
