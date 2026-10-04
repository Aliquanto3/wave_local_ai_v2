---
status: done
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Instruction: Refusal tests and the evidence

## Architecture projection

```txt
.
├── tests/test_playground.py   ✏️ unset => absent and refused, client never called even with the benchmark key; local exchange never reaches a cloud client; refused under a run; 429 => named refusal; no body carries the key
├── aidd_docs/memory/cli.md    ✏️ the setting and the cloud subject
└── evidence/                  ✅ key search over a stubbed cloud exchange's service output
```

## Validation

- `uv run pytest`: 2692 passed, total coverage 98.45%
- `evidence/key-search.txt`: the real settings loader and app under uvicorn on loopback, `mistral_client`'s endpoint pointed at a fake provider (one answer, then 429s echoing the key in their body); 0 hits for the key across every response and 32 captured log lines. Reproduce with `evidence/key-search.py.txt` (`uv run python -X utf8 key-search.py <out>`).
- Pending: browser QA video (no browser session in the unattended run); a real-provider exchange (owner decision D2: no paid call)
