# Phase 4: evidence over the reference bundle and the live store

Same built bundle (`frontend/dist/`, `npm run build`) and the same
`wave-local-ai-v2-serve` process family for both walks -- only
`RUNTIME_RESULTS_PATH`/`QUALITY_RESULTS_PATH` (and, for the reference
walk, `SERVICE_SCHEMA_FLOOR=7`) changed between them. No code change
between the two.

## Screenshots (all at 1280x800)

Filed as `.jpg` (the browser tool's own capture format), not `.png` as
the phase's architecture projection first named them -- the content is
what matters, not the container format.

- `phase-4-quality-reference-bundle.jpg` -- the "7" reference bundle,
  quality run `d20afbda710c40378e6ad5ca8d9b6558`. Honest absences: the
  coverage record's `DeclaredAbsenceLabel`, `thinking_policy` on every
  row's caps cell as `not reported (predates this field)` naming
  `row_schema_version: "7"`, and every row's judge column as
  `judged-score-withheld` (no store holds a judged row). Real values
  elsewhere: per-language `indicative` marks, `failure_counts`'s four
  reasons, `verdict`.
- `phase-4-runtime-reference-bundle.jpg` -- the same bundle, runtime run
  `f5f78c795eaa4175ac506440e597ee3e`. `TtftCell` (`ttft_ms` beside
  `ttft_source`), `RSS` in MB and `VRAM` in MiB with distinct suffixes,
  the fiche rendered unconditionally.
- `phase-4-energy-reference-bundle.jpg` (+ the `-quality-store` and
  `-runtime-store` variants, both filed) -- the composite headline and
  all three per-channel `EnergyMethodLabel`s, over either store for the
  same reference bundle.
- `phase-4-quality-live-store.jpg` -- the live `quality.jsonl` (schema
  up to `"11"`), a translation run's graded (chrF) score shape rendered
  populated -- real per-language scores and indicative marks, not an
  absence.
- `phase-4-runtime-live-store.jpg` -- the live `runtime.jsonl` (schema
  up to `"10"`), populated TTFT/throughput/memory/fiche.
- `phase-4-energy-live-store.jpg` -- the live runtime store's energy
  detail, populated headline and per-channel methods.

## A bug the walk caught, fixed before this evidence was taken

The first pass through this walk (clicking a quality run, then the
`Runtime` tab) hit a real `404`: `read_model.runs_view`'s own docstring
states quality and runtime run ids are minted independently by two
separate CLIs over two separate stores -- there is no run whose id
resolves against both. `App.tsx`'s tab strip previously assumed one
shared `run_id` navigable across all three screens (per `plan.md`'s own
Decision), which does not hold against the real data. Fixed by scoping
the tab strip to the selected run's own kind (`Quality` XOR `Runtime`,
plus `Energy` always, defaulting its store toggle to the matching kind)
-- `frontend/src/App.tsx`, `frontend/src/views/RunsList.tsx`. All
screenshots above are from the rebuilt bundle with the fix in place.
