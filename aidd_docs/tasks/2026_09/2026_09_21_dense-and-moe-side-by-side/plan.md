---
objective: "The quality store's roster models are readable as columns over the same suite items -- one column per model naming its roster_entry_id, architecture, quant and thinking_policy, each column carrying its own suite_version, items outside a column's suite_version shown as not compared rather than blank, and the comparison reachable and quality-only, over a new store-wide route and a new frontend screen."
status: done
---

# Plan: Dense and MoE stand side by side on the same items

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A store-wide comparison read (`read_model.comparison_view`) exposed under the quality route family, and a new `views/comparison/` screen that renders one column per roster model over the same suite items, reusing `labels/` unchanged and holding the quality/runtime boundary |
| **Source** | `aidd_docs/backlog/stories/dense-and-moe-stand-side-by-side-on-the-same-items.md` |

## Phases

| #   | Phase                                                          | File                          |
| --- | --------------------------------------------------------------- | ------------------------------ |
| 1   | `read_model.comparison_view`, the `/api/comparisons` route, column/cell semantics, tests | [`phase-1.md`](./phase-1.md) |
| 2   | The `views/comparison/` screen over fixtures, App.tsx entry point, boundary test extended | [`phase-2.md`](./phase-2.md) |
| 3   | Evidence over the live store, `aidd_docs/results/README.md`, CHANGELOG               | [`phase-3.md`](./phase-3.md) |

## Resources

<!-- External sources only (URLs, docs), not code files. Omit if none consulted. -->

## Decisions

| Decision | Why |
| -------- | --- |
| A column is keyed by `(suite_id, roster_entry_id)`, not by `run_id`. Its rows are the quality rows of the **most recent** `captured_at` among rows sharing that key; `suite_version` is whatever that latest run carries, never assumed or unified across columns. | The story's own worked example needs exactly this: the cloud comparator's only rows sit at an older `suite_version` (never re-run) while the dense ladder's rows sit at a newer one, and both must appear as columns of the same suite side by side. Keying on `run_id` would force the caller to pick one run per model by hand; keying on `(suite_id, roster_entry_id)` and picking the latest data is the same "cite the current state of each model" rule `runs_view` already applies per run, moved to per-model. `captured_at` is used over `suite_version` string ordering because suite versions are not guaranteed to sort numerically forever. |
| The column identity carries a `dimensions` dict built by iterating a fixed, ordered list of dimension field names, `COMPARISON_DIMENSIONS = ("architecture",)` today. Each entry resolves from the roster entry now; a future dimension (`machine`, `engine`, `prompt_variant`) resolves from the row itself via `resolve_field`, added to the tuple. | The user's explicit design note: adding a dimension must extend a list, never reshape the view. Coding the column header as a dict keyed by this tuple -- rather than named fields (`architecture`, later `architecture_and_machine`, ...) -- means `views/comparison/` iterates `Object.entries(column.dimensions)` once and renders a new dimension without a new branch, and `read_model.py` grows the tuple without touching the column-assembly loop. |
| Items are joined by `item_id` across the union of every column's suite in the comparison, per `suite_id`. A column missing an `item_id` its suite union carries renders that cell `{"status": "not_compared"}` — a third cell shape beside a scored cell, never a `null` or a zero. | The acceptance's own words: "shown as not compared, never as equal and never as a blank that reads like a zero." A missing key would let a naive renderer coerce to `0`; an explicit status string cannot. |
| `comparison_view` is exposed at `GET /api/comparisons` (plural, no `{run_id}` segment), the one route in the quality family that is not scoped to a single run. | The comparison is store-wide by construction -- "for each suite present in the store" -- and no single `run_id` names all the rows a column needs (see decision 1). Forcing a `run_id` into the path would either pick one arbitrary run's rows (wrong per decision 1) or be ignored (a dead path parameter), both worse than a route that says what it reads. |
| The screen is reachable from a new top-level nav item beside "Runs", not from a run's tab strip. `App.tsx`'s `Selection` union gains a `{ status: 'comparison' }` member; no router library is added, matching the sibling pitch-screens plan's own decision. | A run-scoped tab strip cannot host a screen that reads no single run -- `TabStrip` in `App.tsx` is typed on one `runId`. The comparison needs its own entry point at the same level as "pick a run," which is exactly where `RunsList` already sits. |
| `views/comparison/` reuses `frontend/src/labels/` unchanged and its own `types.ts`, matching `views/quality/`'s and `views/runtime/`'s own convention; `views/boundary.test.ts` is extended with a third pairwise check so no file under `views/comparison/` imports `views/runtime/`. | The acceptance is explicit that this is "the same boundary order 3 establishes, held where the temptation to breach it is strongest" -- a comparison screen is the one place a reviewer might reach for a runtime figure to explain a score, so the structural guard needs to cover this directory too, not just the original pair. |

