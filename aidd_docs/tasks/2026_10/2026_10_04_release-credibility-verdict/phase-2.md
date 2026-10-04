---
status: done
---

# Instruction: The changelog lines, their agreement test, the procedure step and the release-cut edits

## Architecture projection

```txt
.
├── src/wave_local_ai_v2/client_sessions.py   ✏️ changelog_verdict_mismatches
├── tests/test_client_sessions.py             ✏️ committed CHANGELOG.md agrees; planted disagree / missing / doubled lines fail naming the release
├── CHANGELOG.md                              ✏️ a Credibility line under 0.2.0 and 0.1.0; Unreleased entry
├── CONTRIBUTING.md                           ✏️ dating step writes the 0-of-3 line; new step quotes the outgoing release's verdict in the release PR
├── docs/client-session-record.md             ✏️ new step: update the release's verdict line in the record's commit
└── aidd_docs/memory/cli.md                   ✏️ the command's Verdicts block
```

## Validation

Full gate from the brief: `uv run pytest`, `uv run pre-commit run --all-files`, secrets scan on changed files, dependency audit, both reference validations.
