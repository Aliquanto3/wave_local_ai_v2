---
status: done
---

# Instruction: Both suites from the committed tree, promote, merge (stage B)

## Architecture projection

```txt
.
├── aidd_docs/results/machines/laptop-mobile-gpu/quality.jsonl     ✏️ promoted rows appended
├── aidd_docs/results/fiches/<hash>.json                           ✅ promoted fiche
├── aidd_docs/results/quality-reference.jsonl                      ✏️ re-derived by merge-bundle
├── aidd_docs/results/README.md                                    ✏️ the class's rows and findings
└── aidd_docs/tasks/2026_10/2026_10_04_four-billion-class/evidence/ ✅ live stores, fiches, logs
```

## Tasks to do

1. With no tracked change, run `wave-local-ai-v2-quality --suite classification-support-routing` and `--suite translation-business-short-form` for the entry (`MACHINE_ID=laptop-mobile-gpu`, `COMPUTE_MODE=gpu`, `QUALITY_PROVIDERS=local`, `ROSTER_ENTRY_ID=<entry>`, live store and fiche registry in `evidence/`).
2. Check every row: `tree_dirty: false`, the stage A commit's sha.
3. `wave-local-ai-v2-promote`, `wave-local-ai-v2-merge-bundle`, `--check`, validator with `FICHE_REGISTRY_DIR` unset.
4. README rows section and findings (claim contradictions named, claims kept).

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | 20 classification and 21 translation rows carry the entry id, family `ibm`, `~4B`, `disabled` |
| 3 | `merge-bundle --check` exits 0; validate exits 0 on both reference files |
