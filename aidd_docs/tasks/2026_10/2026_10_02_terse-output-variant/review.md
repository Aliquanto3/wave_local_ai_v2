# Review: The terse-output variant runs every item and meets baseline in a paired test

- **Verdict**: approve (night-run brief: `VERDICT: PASS`, no blocking finding; the one 🟡 below is a CHANGELOG fix, non-blocking under the brief's definition)
- **Diff**: `HEAD...working tree` (uncommitted, schema "27")
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 1 warning, 3 minor

## Phases

### Phase 1 — Registry entry, applicability and the no-op row field

- [x] `output_compressed` v1 resolves, wording is the hashed definition, edited definition refused — `src/wave_local_ai_v2/prompt_variants.py:101-129`, `tests/test_prompt_variants.py::test_output_compressed_appends_its_declared_instruction_on_classification`
- [x] Applicability declared in the entry with its reason (`classification` only; translation reason stated), malformed or reasonless declaration refused at load — `prompt_variants.py:111-118,163-176`, `test_a_malformed_applicability_is_refused_at_load`, `test_an_applicability_without_its_reason_is_refused_at_load`
- [x] Undeclared family returns the authored text with `noop=True` — `prompt_variants.py:208-237`, `test_output_compressed_records_a_noop_outside_its_declared_families`
- [x] Schema "27" quality row: missing / disagreeing noop refused, prompt must equal the variant applied to the authored text, "26" row still validates — `row_contract.py:241,1588-1617`, `tests/test_row_contract.py` (8 new tests)

### Phase 2 — `--prompt-variant` and the story's tests

- [x] `--prompt-variant ID[@VERSION]`, unregistered id exits 1 before any process — `quality_cli.py:219-240,270`, `test_the_prompt_variant_flag_parses_an_id_and_an_optional_version`, `test_an_unregistered_prompt_variant_exits_1_before_any_process`
- [x] Invariance (caps, stop sequences, context length, thinking policy, sampling, metric triple, expected output, parser/scorer outcomes, item ids and order) on every registered suite, local and mistral — `tests/test_quality_cli.py:3240`
- [x] No-op rows keep every item, carry the authored text — `tests/test_quality_cli.py:3284`
- [x] Unparseable terse answer scores 0, `failure_reason` `unparseable`, all 20 counted (accuracy 0.0, not null) — `tests/test_quality_cli.py:3302`
- [x] Constructed pair through `compare_sides`: kind `test`, no confound, differing fields `["prompt_variant_id"]` — `tests/test_quality_cli.py:3320`

### Phase 3 — Docs and the laptop cell pair

- [x] Campaign pair run, both cells filled (20/20 each), compared with `--dimension prompt_variant`: McNemar b=3 c=0 p=0.25 `reference_higher`, `not distinguishable`, differing `prompt_variant_id` only, no confound; token comparison Wilcoxon all-zero — `evidence/comparisons/*.json`, `evidence/campaign-completeness.log`, `evidence/validate.log` (40 rows)
- [x] README names the record path, the verdict as published, the output-token difference (2.0 vs 2.0) — `aidd_docs/results/README.md:600-631`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | rot | 3 | `CHANGELOG.md:28` | New `### Fixed` heading inserted inside `[Unreleased] ### Added`: every pre-existing Added entry below it (lines 33-418) now reads as Fixed | Move the `### Fixed` block after the last Added entry (before `### Changed`, line 419) |
| 🟢 | fit | - | story acceptance line 4 | "differing-field set names exactly (`prompt_variant_id`, `prompt_variant_version`)" cannot hold literally while both arms are v1; implementation and test assert `["prompt_variant_id"]` plus subset of the two, which is the intent (nothing outside the variant fields) | Amend acceptance wording to "a non-empty subset of the variant fields and nothing else" |
| 🟢 | code | 1 | `src/wave_local_ai_v2/row_contract.py:1603` | A non-baseline schema-"27" row whose suite/item does not resolve is accepted without a prompt check (baseline is refused); tested as intended (`test_a_variant_row_whose_item_cannot_be_resolved_is_not_held_to_a_text`) | Consider refusing it like baseline once no legitimate unresolvable non-baseline row exists |
| 🟢 | conform | 2 | `src/wave_local_ai_v2/comparison.py:235-237` | `score_interval` exemption is outside the story's listed code (declared in plan Decisions and CHANGELOG Fixed); correct and narrow: the block is an outcome of the scores like `suite_accuracy`; published records recompute byte-identical (committed rows are schema "7", predate the field) | None required; keep it called out in the commit message |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (11/11) |
| Files checked | prompt_variants.py, row_contract.py, quality_cli.py, comparison.py, judge_probe.py, __init__.py, bundle_export.py, read_model.py, tests (6 files), CHANGELOG.md, cli.md, codebase-map.md, results/README.md, evidence/ |
| Unchecked     | none |
| Unplanned     | none (the `score_interval` exemption is planned in Decisions) |

Gate: `uv run pytest -q` => `2472 passed, 2 warnings in 164.20s`, coverage 98.34%; `ruff check` all passed; `ruff format --check` 704 files formatted; `mypy src/ scripts/` no issues in 67 files. `wave-local-ai-v2-compare --leader-sets` over `aidd_docs/results/quality-reference.jsonl` into a scratch copy => every comparison and leader-set record "unchanged", `diff -r` empty.
