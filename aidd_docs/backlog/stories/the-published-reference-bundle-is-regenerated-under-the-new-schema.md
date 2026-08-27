---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on:
  - aidd_docs/backlog/stories/a-re-run-receives-a-three-state-reproduction-verdict.md
  - aidd_docs/backlog/stories/editing-a-fiche-invalidates-the-rows-that-cite-it.md
  - aidd_docs/backlog/stories/rows-carry-a-cost-and-what-it-was-derived-from.md
order: 19
---

# Story: The published reference bundle is regenerated under the new schema

**As** a client-side engineer handed the project's published evidence
**I want** the runtime reference republished together with the artifacts its rows point at
**So that** the bundle I am handed actually verifies — a row citing a fiche hash, a roster entry and a suite id proves nothing if those files are not published beside it

## Acceptance

- The published bundle is `aidd_docs/results/runtime-reference.jsonl` plus the fiche registry, the roster file, the suite definition snapshot and the prompt templates its rows cite; every pointer on every published row resolves inside the bundle.
- Two real runs on the bench machine, in a quiet thermal window, produce runtime rows with a verdict and both runs' machine state attached.
- The 10% tolerance is recorded in `aidd_docs/results/README.md` against the observed spread of those runs, rather than assumed to fit it; if the observed spread contradicts the threshold, that is recorded as a finding for the PRD, not tuned away.
- The fiche validator command is run over the published bundle and its zero exit and counts are recorded; the deliberate-edit case is run once and its non-zero exit recorded.
- The current `runtime-reference.jsonl` and `quality-reference.jsonl` are retained as superseded — renamed, marked with the schema version that produced them, and explained in the README — never deleted and never back-filled, so the repo is not empty of published numbers for the epic's duration.
- The README states what a reader can and cannot do with a row alone, and that the bundle rather than the line is the unit being handed over.
- The suite definition published here is a snapshot export of the suite as the code holds it, not a registry: the suite definition shape and its registry belong to `no-use-case-is-silently-absent`.

## Code it changes

- No production module by necessity. A small export path may be added under `src/wave_local_ai_v2/` for the suite definition snapshot; everything else is produced by running the CLIs the previous stories built.
- `aidd_docs/results/README.md` — the bundle inventory, the superseded files, the observed spread against the threshold, and the validator runs.

## Tests it needs

- `tests/test_reference_bundle.py` (new) — over the committed bundle: every published row's `fiche_hash`, roster entry id and suite id resolve to a published artifact; every row carries the current `schema_version`; the superseded files carry their own older version and are excluded from the bundle check.

## Evidence it publishes

- The bundle itself: `aidd_docs/results/runtime-reference.jsonl`, `aidd_docs/results/fiches/`, `aidd_docs/roster/models.json`, the suite definition snapshot, and the README recording both bench runs and both validator invocations. This is the artifact the epic's Success Evidence hands to someone who did not produce it.

## Cancellation

n/a — not cancelled.
