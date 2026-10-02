# The fifth table over the committed bundle (2026-10-02)

Command, from the worktree root, run twice into two directories:

```txt
uv run wave-local-ai-v2-export --output-dir <tmp>/export
wrote <tmp>/export/quality_items.csv (80 rows)
wrote <tmp>/export/runtime_aggregates.csv (2 rows)
wrote <tmp>/export/fiches.csv (5 rows)
wrote <tmp>/export/roster.csv (4 rows)
wrote <tmp>/export/comparison_records.csv (14 rows)
wrote <tmp>/export/column_dictionary.csv (439 rows)
wrote <tmp>/export/bundle_manifest.csv (7 rows)
```

Every one of the seven files of the two runs compared with `cmp`: byte identical.

`bundle_manifest.csv`, the two new parts:

```txt
comparison_families,aidd_docs/results/comparisons,4,record_version,1;2
leader_sets,aidd_docs/results/leader-sets,1,record_version,1
```

`comparison_records.csv`: 14 rows, 96 columns (95 plus `fields_not_carried`), 96
`carried=true` dictionary entries for it and no `carried=false` one (the bundle holds
all three record kinds). Ids shortened to 12 characters here, run ids to 8; the table
carries them whole.

| `record_kind` | Record | `family_supersedes` | Comparison (reference vs candidate) | `comparison_kind`, adjusted-p null reason | Subject, status, reason |
| --- | --- | --- | --- | --- | --- |
| comparison_family | 1e1658cbe073 | 2ef9fd3581d2, d4641d06a525 | | | |
| comparison | 1e1658cbe073 | 2ef9fd3581d2, d4641d06a525 | 5e13166d Qwen3.6-35B-A3B vs 5e13166d mistral-small-2603 | refusal, comparison_refused | |
| comparison | 1e1658cbe073 | 2ef9fd3581d2, d4641d06a525 | d20afbda Qwen3.6-35B-A3B vs d20afbda mistral-small-2603 | refusal, comparison_refused | |
| comparison_family | 2ef9fd3581d2 | (none) | | | |
| comparison | 2ef9fd3581d2 | (none) | d20afbda Qwen3.6-35B-A3B vs d20afbda mistral-small-2603 | refusal, (null in a record_version 1 record) | |
| comparison_family | 837e5355b954 | 1e1658cbe073 | | | |
| comparison | 837e5355b954 | 1e1658cbe073 | 5e13166d Qwen3.6-35B-A3B vs 5e13166d mistral-small-2603 | refusal, comparison_refused | |
| comparison | 837e5355b954 | 1e1658cbe073 | 5e13166d Qwen3.6-35B-A3B vs d20afbda Qwen3.6-35B-A3B | refusal, comparison_refused | |
| comparison | 837e5355b954 | 1e1658cbe073 | d20afbda Qwen3.6-35B-A3B vs d20afbda mistral-small-2603 | refusal, comparison_refused | |
| comparison_family | d4641d06a525 | (none) | | | |
| comparison | d4641d06a525 | (none) | 5e13166d Qwen3.6-35B-A3B vs 5e13166d mistral-small-2603 | refusal, (null in a record_version 1 record) | |
| leader_set | 053c65354ff8 | | | | |
| leader_set_subject | 053c65354ff8 | | | | 5e13166d, member |
| leader_set_subject | 053c65354ff8 | | | | d20afbda, not compared, refused on thinking_policy (absent) |

The current family is the one no row's `family_supersedes` names: `837e5355b954`, which
the leader set's `leader_set_family_id` cites. `tests/test_bundle_export.py`
(`test_the_fifth_table_over_the_committed_bundle`) checks over these bytes that every cell
equals the value its record holds at that path and every record value has its column.
