---
objective: "The quality table, the runtime table with its fiche, and the per-run energy detail each render as their own screen over the four read-model routes, every methodology mark on screen through a shared, screen-boundary-enforced label component, and no screen ever composes a quality figure with a runtime one."
status: in-progress
---

# Plan: Quality, runtime and energy read at pitch distance, every caveat on screen

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship the three screens (`views/quality`, `views/runtime`, `views/energy`) plus their shared `labels/` mark components, over the read-model's existing four routes, with the quality/runtime component boundary asserted structurally |
| **Source** | `aidd_docs/backlog/stories/quality-runtime-and-energy-read-at-pitch-distance.md` |

## Phases

| #   | Phase                                                    | File                          |
| --- | --------------------------------------------------------- | ------------------------------ |
| 1   | Read-model verification, the one real gap, route tests    | [`phase-1.md`](./phase-1.md)  |
| 2   | The nine mark label components, unit-tested per state     | [`phase-2.md`](./phase-2.md)  |
| 3   | The three screens over fixtures, boundary test, no-scroll | [`phase-3.md`](./phase-3.md)  |
| 4   | Evidence over the reference bundle and the live store, CHANGELOG, docs | [`phase-4.md`](./phase-4.md) |

## Resources

<!-- External sources only (URLs, docs), not code files. Omit if none consulted. -->

## Decisions

| Decision | Why |
| -------- | --- |
| `read_model.py` and the four routes ship **no new fields**. Reading `QUALITY_VIEW_FIELDS`, `RUNTIME_VIEW_FIELDS` and `resolve_suite_definition` against the committed `"7"` reference bundle shows every field the story names already resolves — `contamination_risk`, `indicative_reasons`, `failure_counts`, `ttft_source`, and the three `*_spread` fields all carry real values on the reference bundle's rows; only `thinking_policy` (added at schema `"11"`) is genuinely absent on those `"7"` rows. | The story's "Code it changes" section describes the target shape, not a diff — `read_model.py` was already built complete against `row_contract.REQUIRED_FIELDS` by the four-views story (`3b20028`), and its own partition test (`test_every_contract_field_is_rendered_or_declared_unrendered`) already fails the build if a contract field is ever left unrendered. Phase 1 is a verification-and-close-the-one-gap pass, not a field-by-field build. |
| The nine `frontend/src/labels/` components are exactly: `IndicativeLabel`, `ContaminationRiskLabel`, `ContestedLabel`, `SingleJudgeLabel`, `UnreliableLabel`, `VerdictLabel`, `EnergyMethodLabel`, `ScopeComparabilityLabel`, `DeclaredAbsenceLabel` — matching the story's "Code it changes" list exactly. `ttft_source`, the four caps, and the failure-count breakdown render as small screen-local pieces inside `views/runtime/` and `views/quality/`, not as `labels/` components. | Those three appear on exactly one screen each, so nothing forces "the same mark rendered two ways on two screens" — the failure mode `labels/` exists to prevent. Widening the shared set beyond the story's own nine risks scope creep the story didn't ask for; each screen-local piece still gets its own unit test, so per-refusal coverage is unaffected. |
| `DeclaredAbsenceLabel` is a second, generic absence marker, distinct from the existing `components/Absent.tsx`. | `components/Absent.tsx` renders one API-carried field's three-reason absence (`predates_schema` / `null_in_row` / `pointer_unresolved`). The judged-score-withheld case, the coverage-record-not-built-yet case, and the energy-headline-withheld case are not single-field absences the API names — they are a whole construct the view itself declares absent, carrying a free-text reason. Reusing `Absent`'s three-reason shape for those would either invent a fourth reason (contradicting `read_model`'s "finite three reasons" contract) or misreport a design-time absence as a data-time one. |
| The coverage record renders as a static `DeclaredAbsenceLabel` naming `no-use-case-is-silently-absent` on the quality screen, wired to no API field. | No store, route, or `read_model` field carries a coverage record today — it is owned and built by that sibling epic, per its own Boundaries ("This epic excludes: showing any of this to a human. The pitch epic renders the coverage record... This epic makes those exist and be correct"). The story's own line is explicit: "this story builds the surface and fabricates no entry." Adding a stub field to `read_model.py` for a record that cannot exist yet would be exactly the fabrication the story rules out; a static, honestly-labelled absence in the view is not. |
| Screen navigation is a run-scoped tab strip (`Quality \| Runtime \| Energy`) added to `App.tsx`'s own state, no routing library. | No router is installed (`frontend/package.json`), and the app is a single internal tool with three screens sharing one `run_id`. Adding `react-router-dom` for three tabs over one piece of state is a dependency the task does not need; `App.tsx` already holds the `KeyGate`-wrapped root and can hold a `{ run_id, screen }` selection the same way. |
| Quality/runtime component-boundary enforcement is a Vitest structural test (`views/boundary.test.ts`) reading each view directory's source text for the other view's type-module import path, not an ESLint rule. | The story allows either ("make that a lint rule or a test"). No import-boundary ESLint plugin is installed, and adding one for a single rule is heavier than a source-scanning test in the same style the Python side already uses for its own structural guarantee (`test_a_field_added_to_the_contract_fails_the_partition`). A failing-by-construction test (temporarily add a cross-import, confirm the test fails, remove it) is the same proof either mechanism would give. |
| `QualityView`, `RuntimeView` and `EnergyView` TypeScript types each live inside their own screen's directory (`views/quality/types.ts`, etc.), not in the shared `api/types.ts`. | `api/types.ts` today holds only `RunsView` and the identity/absence primitives every view shares (`Absent`, `Maybe`, `RosterEntry`) — none of it is a "quality" or "runtime" view model. Putting the three new view-model types there would make `api/types.ts` itself a module every screen imports, silently defeating the boundary the structural test is built to catch. |
| The 1280×800 no-horizontal-scroll check ships as a documented manual screenshot walk (phase 3's evidence), not a Vitest/jsdom assertion, backed by one cheap automated guard (no rendered element's inline/computed `width` exceeds 1280px). | jsdom performs no real layout: `scrollWidth`/`clientWidth`/`getBoundingClientRect` are all `0` in it regardless of content, so an `overflow`-based assertion would pass unconditionally and prove nothing — exactly the flakiness the story's own fallback clause anticipates ("if that proves flaky, a documented manual check with a screenshot in the phase file"). |
