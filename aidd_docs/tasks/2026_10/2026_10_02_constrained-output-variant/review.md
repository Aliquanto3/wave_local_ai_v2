# Review: The constrained-output variant runs under a llama.cpp grammar and names its mechanism

- **Verdict**: approve
- **Diff**: `HEAD...working tree` (uncommitted, schema "28"; `aidd_docs/tasks/2026_10/2026_10_02_night-run/run-log.md` excluded)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 3 minor

## Phases

### Phase 1 — Registry entry, engine mechanisms, campaign refusal

- [x] AC1 `constrained_output` v1: per-family format, instruction (null), GBNF grammar, hashed; translation no-op with reason — `src/wave_local_ai_v2/prompt_variants.py:156-189`, `_check_output_formats`; tests `test_constrained_output_declares_a_gbnf_grammar_for_classification_only`, `test_constrained_output_is_a_noop_without_a_grammar_outside_its_families`, `test_a_malformed_output_format_is_refused_at_load`
- [x] AC5 llama.cpp entry declares `constraint_mechanisms` (`gbnf` -> `grammar`); campaign on an engine declaring none refused at declaration — `aidd_docs/roster/engines.json:80-85`, `src/wave_local_ai_v2/campaigns.py:332-358`; tests `test_the_shipped_llama_cpp_entry_carries_gbnf_in_the_grammar_field`, `test_the_constrained_variant_on_an_engine_declaring_none_is_refused`; b10537 `--help` re-run by reviewer: `--grammar GRAMMAR  BNF-like grammar to constrain generations`

### Phase 2 — Request path, row fields (schema "28"), gate, comparison

- [x] AC2 grammar sent per request in `grammar`, only on answers, only for declared families; row names `constraint_mechanism` + `constraint_grammar_hash`; gate checks both against the registry — `local_client.py:378-393`, `quality_cli.py:364-374,863-894,1425-1428`, `row_contract.py:1618-1628`; tests `test_the_grammar_is_sent_with_every_classification_answer_and_hashed`, `test_no_grammar_is_sent_outside_the_constrained_variant_and_its_families`, `test_a_constraint_disagreeing_with_the_registry_is_refused`
- [x] AC2 added instruction visible in published prompt (none added; mechanism tested with a declared one) — `test_a_format_instruction_when_declared_is_appended_and_visible`; row `prompt_before_template` == authored prompt asserted
- [x] AC3 scorer/parser/caps/expected/items invariant; grammar-admitted unscorable output scores 0 with reason — `test_a_constrained_run_changes_nothing_but_the_variant_on_every_suite`, `test_a_grammar_admitted_but_truncated_answer_scores_0_with_its_reason`
- [x] Refusal before launch: engine without mechanism, enabled cloud provider — `test_the_constrained_variant_on_an_engine_without_gbnf_is_refused`, `test_the_constrained_variant_beside_a_cloud_provider_exits_1_before_any_process` (no `running_server` call)
- [x] AC4 both fields on `prompt_variant` axis; committed records unchanged — `comparison.py:342-354`; reviewer re-derived the committed terse record `58b1ecc07d7f` with the new code: byte-identical JSON

### Phase 3 — Docs and the laptop evidence

- [x] AC4 live pair compared by the existing command: differing `constraint_grammar_hash`, `constraint_mechanism`, `prompt_variant_id`, no confound, 0.45 vs 0.45, 0 discordant — `evidence/comparisons/...44b9986b4ebf.json` (reviewer re-derived: identical); `validate`: checked 40 row(s)
- [x] Evidence: share of baseline outputs outside the format 0/20 recorded in `aidd_docs/results/README.md` — replay (`baseline-format-replay.json`) under temperature 0, fixed seed, same build/model; 20/20 replay labels equal row `predicted_label`, and rows independently show `item_tokens_out` = 2 on every baseline item, same as the grammar-forced arm

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | rot | 3 | `evidence/evidence.md` | `grammar-probe.json` and `baseline-format-replay.json` were produced by ad hoc requests with no recorded command or script | Add the exact request/replay command (or a one-off script path) to `evidence.md` so the replay is reproducible |
| 🟢 minor | fit | 2 | `quality_cli.py:1425-1428`, `row_contract.py:1618-1628` | Row constraint fields are derived from the registry, not from the body actually sent; safe today only because `_constraint_body` refuses every path that would not send it | Keep the invariant; a future engine/provider path must route through `_constraint_body` (comment already says so) |
| 🟢 minor | fit | 2 | `quality_cli.py:1038-1041` | A GBNF grammar also constrains reasoning tokens; a future suite with `thinking_policy` enabled would silently suppress thinking while rows claim it on (both suites are `disabled` today) | When a thinking-enabled suite appears, refuse or document the combination |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (8/8) |
| Files checked | prompt_variants.py, engines.py, campaigns.py, local_client.py, quality_cli.py, row_contract.py, comparison.py, read_model.py, bundle_export.py, judge_probe.py, engines.json, results/README.md, cli.md, codebase-map.md, CHANGELOG.md, tests (7 files), evidence/* |
| Unchecked     | none |
| Unplanned     | none (`read_model.py`, `bundle_export.py`, `judge_probe.py` edits are required by the new required row fields) |

Gates (reviewer-run): `uv run pytest -q` => `2519 passed, 2 warnings in 178.18s`, coverage 98.36%; ruff check/format, mypy, detect-secrets on changed files, `merge-bundle --check`: all exit 0.
