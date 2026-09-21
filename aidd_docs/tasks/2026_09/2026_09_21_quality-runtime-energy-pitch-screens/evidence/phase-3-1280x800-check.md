# Phase 3: the 1280x800 no-horizontal-scroll check

## Automated guard

`frontend/src/views/widthGuard.test.tsx` renders `QualityView`, `RuntimeView`
and `EnergyView` against their fixtures and asserts no element declares an
inline `width`/`minWidth` exceeding 1280px. Passing: `npx vitest run
src/views/widthGuard.test.tsx` (3 tests).

## Manual screenshot walk

Deferred to phase 4, per plan.md's Decision and this phase's task 8: the
screens fetch live from `apiFetch`, not from the fixtures, so a real
1280x800 walk needs the service running over the reference bundle (or the
live store) -- which is phase 4's own evidence pass
(`aidd_docs/results` served by `wave-local-ai-v2 service`). Cross-referenced
from `aidd_docs/tasks/2026_09/2026_09_21_quality-runtime-energy-pitch-screens/phase-4.md`.
