---
status: done
---

# Instruction: The loader, the drawn suite, its snapshot and the export columns

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── scripts/hub_source.py                       ✅ shared loader helpers
├── scripts/minds14_suite.py                    ✏️ uses hub_source
├── scripts/wmt24pp_suite.py                    ✅ fetch / count-tokens / draw / verify
├── scripts/assemble_release_archive.py         ✏️ the loader named by the snapshot is not shipped
├── src/wave_local_ai_v2/suite_data/translation-mixed-domain-wmt24pp.json  ✅ 300 drawn items
├── src/wave_local_ai_v2/bundle_export.py       ✏️ max_output_tokens_basis columns
├── src/wave_local_ai_v2/translation_suite.py   ✏️ the publication suite's rationale
├── aidd_docs/results/suite-definitions/translation-mixed-domain-wmt24pp@1.json  ✅ snapshot
└── tests/
    ├── test_wmt24pp_suite.py           ✅ join, filter, directions, table hash, draw + replay over a constructed table, the committed suite
    ├── test_suite_registry.py          ✏️ shipped prompt_set_hash
    ├── test_suite_snapshot.py          ✏️ the drawn translation snapshot's keys
    ├── test_quality_cli.py             ✏️ the covering slice keeps each direction
    └── test_recompute_from_export.py   ✏️ export + recompute over a translation@4 batch and a publication batch
```

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | The suite certifies at publication with 300 items, 100 per direction, its rule, the table's SHA-256 and its cap basis recorded; a constructed table replays to its recorded ids; no segment in two directions; each reference is its direction's target side; the cap is at least twice the longest recorded count; the export and recompute run clean over a bundle holding both batches |
