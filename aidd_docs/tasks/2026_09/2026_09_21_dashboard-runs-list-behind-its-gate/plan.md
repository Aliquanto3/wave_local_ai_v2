---
objective: "The service serves a built dashboard on its own origin, opening on a runs list that names every absence and every dirty tree, and a `frontend` CI job blocks a merge exactly as the Python job does."
status: in-progress
---

# Plan: The browser opens on the list of runs, behind the front-end's own gate

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Serve a Vite+React+TS dashboard from `service.py`'s own origin, opening on a runs list built over `/api/runs`, gated by a `frontend` CI job wired into `required` |
| **Source** | `aidd_docs/backlog/stories/the-browser-opens-on-the-list-of-runs-behind-its-own-gate.md` |

## Phases

| #   | Phase                                          | File                          |
| --- | ----------------------------------------------- | ----------------------------- |
| 1   | Decisions, origin plumbing, runs-view extension | [`phase-1.md`](./phase-1.md)  |
| 2   | Frontend scaffold, API client, key gate         | [`phase-2.md`](./phase-2.md)  |
| 3   | Runs list view, absence rendering, local build  | [`phase-3.md`](./phase-3.md)  |
| 4   | CI `frontend` job, docs, setup path             | [`phase-4.md`](./phase-4.md)  |

## Resources

<!-- External sources only (URLs, docs), not code files. Omit if none consulted. -->

## Decisions

| Decision   | Why   |
| ---------- | ----- |
| Bundle is built during setup (`npm ci && npm run build`), never committed | A committed `dist/` rots against its source between commits and bloats every diff that touches the frontend; the fresh-machine command is one line, matching `uv sync`'s own posture for the Python half. Recorded jointly with `clean-machine-runs-it-and-nothing-reaches-main-unchecked`, which owns the fresh-machine walk, per the epic's open decision. |
| Package manager: npm, with `frontend/package-lock.json` committed | No concrete reason favors pnpm/yarn here (no workspace, no monorepo need); npm ships with Node and needs no extra install step on a fresh machine, matching the "no undocumented manual fixes" acceptance criterion. |
| Node version pinned via `frontend/.nvmrc` (not `engines`) | `.nvmrc` is what the CI Node-setup action reads directly (`node-version-file`), so the pin lives in exactly one file the workflow and a local `nvm use` both read — an `engines` field would be a second place to keep in sync and npm does not enforce it by default. |
| `release_version`, `commit_sha`, `tree_dirty` move from `RUNTIME_VIEW_FIELDS`/`QUALITY_VIEW_FIELDS` into `RUNS_VIEW_FIELDS` | The acceptance criteria name these three on the runs list; today's `RUNS_VIEW_FIELDS` (`run_id`, `captured_at`, `schema_version`, `roster_entry_id`) does not carry them. `_identity(row)` (built from `RUNS_VIEW_FIELDS`) is already spread into every runtime and quality per-row entry as well as every runs-list entry, so moving the three field names into that one set surfaces them on `/api/runs` with no new code path and renders unchanged on the two existing per-run routes — a relocation, not a duplication, and the partition invariant (`tests/test_read_model.py`) stays satisfied since the sets stay disjoint. |
| A new `_runs_collection` field enumerates the distinct roster entries a run's rows cite (`models`), and, quality only, the distinct `task_suite` values (`suites`) | The acceptance names "the suites and models the run covers"; today's collection reads only the first row per `run_id`. Listing values already present on other rows of the same run is an enumeration, not a score, verdict or aggregate, so it stays inside `read_model`'s "nothing is computed" rule — unlike `row_count`, which already scans every row of the run for the same reason. Runtime rows carry no suite dimension, so `runtime_runs` entries carry `models` only; `suites` is a quality-only key, not an absence, since the concept does not apply to a runtime row at all. |
| Front-end ESLint/Prettier/`tsc` stay CI-only, not in `.pre-commit-config.yaml`'s fast gate | The fast gate is a `uv run`-only pipeline; wiring `npm` invocations into it would force every contributor's local pre-commit hook to have Node installed even for a Python-only change, and would slow the commit-stage hook (already the discipline `coding-assertions.md` optimizes for speed). The `frontend` CI job runs on every push and PR already, so the gate exists — just at CI time rather than commit time. Recorded in `.pre-commit-config.yaml` as a comment, per the story's own acceptance criterion. |
| CORS is configured but restricted to the one dashboard origin, and is defence-in-depth only | Matches the epic's decided single-origin topology: the browser never needs cross-origin `/api` access in the shipped topology (same host:port), so CORS has nothing to permit in production and exists only to fail closed if that topology is ever violated. |
