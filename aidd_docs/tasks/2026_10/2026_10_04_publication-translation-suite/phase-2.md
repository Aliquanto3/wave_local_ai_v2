---
status: done
---

# Instruction: Licence texts, NOTICEs, coverage record and the README statement of the rung

## Architecture projection

```txt
.
├── LICENSE-DATA                                           ✏️ section 2.2 WMT24++, section 3 the WMT24 research-use declaration
├── src/wave_local_ai_v2/suite_data/{NOTICE.md,LICENSE-APACHE-2.0.txt}        ✏️ ✅
├── aidd_docs/results/suite-definitions/{NOTICE.md,LICENSE-APACHE-2.0.txt}    ✏️ ✅
├── aidd_docs/results/{NOTICE.md,LICENSE-APACHE-2.0.txt}                      ✏️ ✅
├── src/wave_local_ai_v2/use_case_coverage.json            ✏️ translation gains the suite id
├── aidd_docs/results/README.md                            ✏️ rung, pool sizes, per-domain counts, translated sources
└── tests/test_data_licence.py, tests/test_wmt24pp_suite.py ✏️ Apache text verbatim, section 2.2 and 3, README counts recomputed
```

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Section 2 names WMT24++ and Apache-2.0; section 3 holds the third declaration; each directory holding drawn WMT24++ items carries the Apache-2.0 text verbatim and its NOTICE states the change; the README's per-domain counts equal the definition's |
