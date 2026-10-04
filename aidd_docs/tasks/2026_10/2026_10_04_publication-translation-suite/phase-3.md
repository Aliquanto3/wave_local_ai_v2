---
status: done
---

# Instruction: Stage B: the two published batches, promotion, merge and evidence

```txt
.
├── aidd_docs/results/machines/laptop-mobile-gpu/quality.jsonl  ✏️ two batches appended
├── aidd_docs/results/quality-reference.jsonl                  ✏️ merged
├── aidd_docs/results/README.md                                ✏️ the run section
└── tests/test_reference_bundle.py                             ✏️ the translation publication batch has its development pair
```

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Both batches in the bundle with `score_interval`, the same `roster_entry_id`, `fiche_hash`, `engine_build` and commit, `tree_dirty: false`; `truncated_max_tokens` count stated; export and recompute clean |
