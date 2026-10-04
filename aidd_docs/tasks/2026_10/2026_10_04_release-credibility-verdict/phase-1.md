---
status: done
---

# Instruction: The verdict computation and its planted-record tests

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/client_sessions.py   ✏️ SessionRecord client_id/complete/blocking_claims, Verdict, release_verdicts, verdict_line, Verdicts block in the report
└── tests/test_client_sessions.py             ✏️ planted-record verdict tests, date-shift and frozen-clock invariance
```

## Test Scope

Every planted case the story's "Tests it needs" names: 2 then 3 qualifying sessions; incomplete; internal (no count, no block); `unreleased`; one client three times; backfilled complete/incomplete; a block among clean sessions; a block appended after `validated` (revoked, even with an earlier session date); clean sessions after a block; `other` alone vs `other` + `judge_agreement`; a dismissal; a correction read as itself; a correction adding a `table_separation` block after `validated`; a correction removing a block or adding resolving evidence. Dates shifted by years and two frozen clocks yield one verdict.

## Validation

`timeout 600 uv run pytest tests/test_client_sessions.py`
