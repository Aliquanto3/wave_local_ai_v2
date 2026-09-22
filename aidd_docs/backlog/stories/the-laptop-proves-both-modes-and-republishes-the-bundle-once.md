---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/every-view-names-the-machine-and-mode-and-cpu-only-vram-reads-not-applicable.md
  - aidd_docs/backlog/stories/each-model-machine-and-mode-runs-under-its-own-named-profile.md
  - aidd_docs/backlog/stories/a-model-below-its-declared-minimum-refuses-and-the-refusal-is-published.md
  - aidd_docs/backlog/stories/each-machine-returns-its-rows-by-pull-request-and-a-hash-collision-is-refused.md
order: 6
---

# Story: The laptop proves both modes and republishes the bundle once

**As** a client-side engineer reading the published bundle
**I want** the laptop's evidence regenerated under the epic's final schema in one bench session, with the proving model run in both modes, and returned through the laptop's own pull request
**So that** the bundle stops being five schema versions behind the code, and the first machine of the three-machine path is proven end to end before the other two depend on it

Maps to: PRD AC "Given the repo cloned fresh onto a different machine... without undocumented manual fixes"; PRD AC "Given a GPU-bearing machine, running a declared `cpu_only` profile..."; PRD AC "Given a published run, a re-run of it returns an explicit verdict..."; Methodology 6, 8, 19, 21; epic Dependencies "fold the two into one bench session".

Current state: the committed bundle carries `schema_version` `"7"` (`tests/test_reference_bundle.py:48`) while the code writes `"12"`, and a regeneration is already filed (`aidd_docs/backlog/tech-debt.md`, 2026-09-05 row on the bundle being a schema behind). Orders 1 to 4 each bump the schema again. This story pays the quiet-thermal-window cost once, for all of them.

## Acceptance

- From a fresh clone in a new directory on the laptop, following `docs/setup.md` alone (the existing models directory may be reused: the walk under test is the setup, not the download), with the laptop's declared machine id and each mode's declared profile.
- **The existing bundle is regenerated under the final schema**, on Story 19's protocol: two runtime runs of the flagship in a quiet thermal window (the second against the first), two quality runs per subject already in the bundle, the validator proof. The superseded files are `git mv`-renamed with the schema version that produced them and kept, never edited or back-filled. [PRD M19; the row epic's supersede-don't-backfill rule]
- **The proving model runs in both modes**: `Qwen3-0.6B` under the laptop's `gpu` profile and its `cpu_only` profile, two runs each, the second against the first. Each `cpu_only` row carries VRAM not applicable; the `gpu`-versus-`cpu_only` pair never receives a throughput verdict against each other; each mode's second run receives a real `reproduced` or `not_reproduced` against its own first. [PRD AC cpu_only rows; PRD M8]
- The German routing item the 2026-08-27 tech-debt row defers "to the next regeneration" is resolved or explicitly deferred again by name here, since this is that regeneration.
- The rows, fiches and any refusal records are promoted into the laptop's tracked location, merged into the bundle by order 5's merge step, and land on `main` through the laptop's own pull request with CI green; `PUBLISHED_BUNDLE_SCHEMA_VERSION` moves to the final schema.
- Every step the walk needed that `docs/setup.md` did not name is added to it, and listed.

## Code it changes

- `docs/setup.md`: whatever the walk proves missing.
- `aidd_docs/results/`: the laptop's tracked location, the merged bundle, the renamed superseded files, the fiche registry.
- `tests/test_reference_bundle.py`: `PUBLISHED_BUNDLE_SCHEMA_VERSION` and the superseded-file list.
- `aidd_docs/results/README.md`: a dated regeneration section in the form Story 19's already takes; `aidd_docs/backlog/tech-debt.md`: the regeneration row closed with evidence.

## Tests it needs

- None new beyond what the regenerated bundle makes the existing suite assert: `tests/test_reference_bundle.py` green against the new bundle, including the three bundle-level assertions order 5 added. A regression the walk uncovers gets its test; if it uncovers none, that is stated.

## Evidence it publishes

- The regenerated bundle itself, with the laptop's rows in both modes.
- The results README section: rows cited by `run_id`, the two verdicts per mode, the `cpu_only`-versus-`gpu` throughput ratio on the laptop as an observation, and the setup gaps found.

## Plan shape

1. Fresh clone and setup walk on the laptop; gaps recorded as found.
2. The quiet-window bench session: flagship runtime pair, quality pairs, `Qwen3-0.6B` pairs in both modes.
3. Promote, merge, supersede, validator proof.
4. Results README, docs fixes, tech-debt closure, the laptop's pull request.

## What the operator runs by hand

The laptop is the development machine, so every command is agent-executable there. The operator's own part is the thermal window: close other GPU and CPU load, keep the laptop on mains power in its usual performance profile, and confirm "quiet" before phase 2 starts; the agent does not decide the machine is idle.

## Cancellation

n/a — not cancelled.
