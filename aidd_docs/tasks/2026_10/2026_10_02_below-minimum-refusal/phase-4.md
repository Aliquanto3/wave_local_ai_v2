---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Docs, CHANGELOG, the raised-then-lowered live proof on the laptop

## Architecture projection

```txt
.
├── docs/setup.md                            ✅ section 1.2, the requirement table and its limits
├── README.md                                ✅ hardware section points to it
├── CHANGELOG.md, .env.example               ✅
├── aidd_docs/memory/cli.md, codebase-map.md ✅
└── evidence/                                ✅ raised refuses, restored runs (evidence.md)
```

## Tasks

- The table replaces the README's hardware prose; the "declared, not verified" limit is stated.
- Live proof on the laptop, all paths in `evidence/`.

## Validation

`evidence/evidence.md`; `uv run wave-local-ai-v2-validate evidence/runtime.jsonl` exit 0.
