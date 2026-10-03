---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Console panel and second-machine evidence

## Architecture projection

```txt
.
├── frontend/src/api/client.ts                   ✏️ console options, start, streamed NDJSON read with the key header
├── frontend/src/App.tsx                         ✏️ console entry shown only when options report demo mode on
└── frontend/src/views/console/                  ✅ ConsolePanel (selects only: kind, suite, entry, profile), LiveOutput, types, tests
```

## Tasks

- Re-apply the old branch's panel; add the profile select fed by the options route's per-entry profiles; send `machine_id` and `compute_mode` of the chosen profile.
- Evidence: second-laptop browser-QA videos and the side-by-side row are pending (operator).

## Validation

`npm ci --offline`, `npx vitest run`, `npx tsc -b` (typecheck) in `frontend/`.
