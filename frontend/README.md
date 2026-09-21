# wave-local-ai-v2 dashboard

The read-only dashboard served by `service.py` from its own origin. Vite +
React + TypeScript.

## Setup

```sh
nvm use    # reads .nvmrc
npm ci
```

## Commands

| Command                  | What it does                                      |
| ------------------------ | ------------------------------------------------- |
| `npm run dev`            | Dev server, proxying `/api/*` to `127.0.0.1:8000` |
| `npm run build`          | Type-checks (`tsc -b`) and builds `dist/`         |
| `npm run lint`           | ESLint                                            |
| `npm run format`         | `prettier --check .`                              |
| `npm run typecheck`      | `tsc -b --noEmit`, over every referenced project  |
| `npm test -- --coverage` | vitest, failing under 80% line coverage           |

`dist/` is never committed: `npm ci && npm run build` from a fresh clone
reproduces it, matching `uv sync`'s posture for the Python half (see the
repo's `docs/setup.md`).
