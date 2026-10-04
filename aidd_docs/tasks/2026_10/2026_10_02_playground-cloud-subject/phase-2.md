---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: The selector and the per-send statement

## Architecture projection

```txt
.
├── frontend/src/views/playground/types.ts                  ✏️ cloud subject option and loaded shape
├── frontend/src/views/playground/PlaygroundPanel.tsx       ✏️ cloud subject in the selector; send control names the provider
├── frontend/src/views/playground/PlaygroundPanel.test.tsx  ✏️ statement on every send, absent for a local subject
├── frontend/src/views/console/types.ts                     ✏️ CloudPlaygroundHolder
└── frontend/src/views/console/holder.ts                    ✏️ describes a cloud playground holder
```

## Validation

- `npm run typecheck` and `npx vitest run` in `frontend/`
