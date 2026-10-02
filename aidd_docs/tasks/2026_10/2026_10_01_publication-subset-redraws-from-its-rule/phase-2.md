---
status: done
---

# Instruction: The replay command and the docs naming it

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/
│   ├── subset_replay.py        ✅ `python -m` command: --suite | --definition, --source
│   └── suite_registry.py       ✏️ docstring names where the added fields are checked
├── aidd_docs/memory/
│   ├── cli.md                  ✏️ the replay command
│   └── codebase-map.md         ✏️ the two modules
└── tests/
    └── test_subset_replay.py   ✅ exit codes and named items
```

## User Journey

```mermaid
flowchart TD
  A[python -m wave_local_ai_v2.subset_replay --definition d.json --source s.jsonl] --> B[load + gate definition]
  B --> C{selection_rule?}
  C -->|no| X[exit 1: no rule]
  C -->|yes| D[read JSONL rows] --> E[replay]
  E -->|reproduced| F[exit 0: count, seed, sampler version]
  E -->|differs| G[exit 1: named items / first differing position]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    write a drawn definition and its source table to tmp => files ready: 5: cli
  section Happy path
    replay over the same source => exit 0 printing reproduced: 5: cli
  section Edge case - edited source
    one row text edited => replay => exit 1 naming the item id: 1: cli
  section Edge case - changed rule seed
    definition seed changed => replay => exit 1 naming the first differing position: 1: cli
  section Edge case - no rule
    shipped development suite => replay => exit 1 naming the missing rule: 1: cli
  section Edge case - bad source
    source line not JSON => replay => exit 1 naming the line: 1: cli
```

## Tasks to do

### `1)` Replay command

> The rule is checked by a command, not described in prose.

1. argparse: mutually exclusive `--suite`/`--definition`, required `--source`.
2. Load, read rows, call `subset_sampler.replay`, print the verdict; exit 0 or 1.

### `2)` Docs

> Memory names the command and the modules.

1. `cli.md`: the command beside `suite_snapshot`/`use_case_coverage`.
2. `codebase-map.md`: the sampler and replay modules.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Unchanged source exits 0; an edited row exits 1 naming its item id; a changed seed exits 1; a suite without a rule exits 1; a malformed source line exits 1 |
| 2 | Memory names the command, its flags and exit codes |
