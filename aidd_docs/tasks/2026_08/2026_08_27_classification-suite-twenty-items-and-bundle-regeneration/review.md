# Review: Classification suite reaches twenty items, reference bundle regenerated

- **Verdict**: changes-requested
- **Diff**: `main...feat/trilingual-suite-and-reference-bundle`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_27
- **Findings**: 0 critical, 5 warning, 5 minor

## Phases

### Phase 1 — Ten added items, suite version bump, per-language scoring + gate

- [x] `CLASSIFICATION_TASK_SUITE` holds 20 items — `src/wave_local_ai_v2/classification_suite.py:83-202`
- [x] EN/FR/DE each cover at least 25% (10/5/5 = 50/25/25%) — `tests/test_classification_suite.py:19-27`
- [x] The ten added items declare `provenance="hand_written"` (`_item` default) — `src/wave_local_ai_v2/classification_suite.py:71`, `tests/test_classification_suite.py:30-33`
- [x] The ten original EN items are unchanged — `tests/test_classification_suite.py:78-129`
- [x] `SUITE_VERSION` `"1"`→`"2"`, `PROMPT_SET_HASH` recomputed to `d41a2134...` — `src/wave_local_ai_v2/classification_suite.py:36,219`
- [x] `score_suite_by_language` returns one `LanguageCell` per `suite_gate.LANGUAGES`, accuracy over that language only, `n` matching, `indicative` true exactly when `n < 10` — `src/wave_local_ai_v2/scoring.py:157-184`, `tests/test_scoring.py:190-220`
- [x] A quality row carries `language_breakdown`; `validate_row("quality", …)` refuses a row missing it; `SCHEMA_VERSION` is `"7"` — `src/wave_local_ai_v2/quality_cli.py:480-482,505`, `src/wave_local_ai_v2/row_contract.py:34-37,199`
- [x] `gate_suite(CLASSIFICATION_TASK_SUITE)["indicative"] is False`, `per_language_indicative == {"en": False, "fr": True, "de": True}` — `tests/test_suite_gate.py:111-119`
- [x] `pytest` 386 passed, `mypy`/`ruff check`/`ruff format --check` clean — re-run this review

### Phase 2 — Suite definition snapshot export

- [x] `python -m wave_local_ai_v2.suite_snapshot` writes `aidd_docs/results/suite-definitions/classification-support-routing.json` matching `build_snapshot()` — byte-equal on re-export, verified this review
- [x] `build_snapshot()` carries `suite_id`/`suite_version`/`prompt_set_hash`/caps and the six per-item fields, none renamed — `src/wave_local_ai_v2/suite_snapshot.py:43-58`, `tests/test_suite_snapshot.py:6-31`
- [x] `pytest`/`mypy`/`ruff` clean — re-run this review

### Phase 3 — Live bundle regeneration on the bench machine

- [x] Both superseded files exist under `.schema-1.jsonl`, tracked, byte-identical to their pre-rename content — `git cmp` against `main:` blobs, verified this review
- [x] Two runtime rows; run 2's verdict names run 1's `run_id` and states `reproduced` with empty `differing_fields` — `aidd_docs/results/runtime-reference.jsonl`
- [x] Four quality batches (2 runs x 2 providers, 20 rows each); each run-2 batch names the matching run-1 `run_id` (`reproduced` local, `not_reproduced` mistral on `other-de-01`) — `aidd_docs/results/quality-reference.jsonl`
- [x] Validator exits 0 with `checked 82 row(s)`; the deliberate `gpu_name` edit exits 1 naming all 82 rows and `changed_fields: ['gpu_name']`; the revert returns exit 0 — all three reproduced this review

### Phase 4 — README bundle inventory, reference-bundle test, CHANGELOG, memory

- [x] `test_reference_bundle.py` resolves every row's `fiche_hash`, `roster_entry_id`, `suite_id`/`suite_version` and asserts the current `schema_version` — `tests/test_reference_bundle.py:1-75`
- [x] `README.md` names the bundle as one unit, states what a row alone can/cannot do, records both runtime runs against the 10% tolerance, records the per-language breakdown with the indicative cells named, and explains both superseded files — `aidd_docs/results/README.md:3-92`
- [x] `CHANGELOG.md` `## [Unreleased]` names the 20-item suite, `language_breakdown`, the schema bump, the snapshot export and the regeneration — `CHANGELOG.md:12-32`
- [x] `cli.md` and `architecture.md` carry no stale 10-item or EN-only reference — grep clean
- [x] `pytest` 386 passed, `pre-commit run --all-files` green (ruff, ruff format, mypy, detect-secrets) — re-run this review

### Story 20 — The classification suite reaches twenty items across three languages

- [x] Methodology 4: at least 20 items, EN/FR/DE each at least 25% — 20 items at 10/5/5
- [ ] Methodology 4: the ten added items are natively authored and the four labels stay semantically disjoint in each language — authorship holds (distinct FR/DE scenarios, no EN parallel), disjointness does not: `account-de-01` is routed `technical` by `mistral-small-2603` in both published runs, and `other-de-01` in one
- [x] Methodology 5: every added item declares its provenance (`hand_written`) and its contamination risk — `classification_suite.py:71,79`
- [x] The suite gate passes the suite at suite level — `indicative: false`, `indicative_reasons: []` on all 80 published quality rows
- [x] Methodology 4: every per-language cell reported with its n and its indicative mark, recorded as an observed consequence — `language_breakdown` on every row, `aidd_docs/results/README.md:60-70`
- [x] The suite version bumps, the prompt-set hash changes, and two consecutive runs regenerate `quality-reference.jsonl` with the reproduction checkable from the file's own run ids — `suite_version "2"`, `prompt_set_hash d41a2134…`, run ids `5e13166d…`/`d20afbda…`
- [x] The regenerated rows carry every field the earlier stories added and a verdict stating whether run 2 reproduced run 1 — 68 keys per row including `verdict`, `fiche_hash`, `cost_total`, `emissions_kg`

### Story 19 — The published reference bundle is regenerated under the new schema

- [x] Every pointer on every published row resolves inside the bundle — 82/82 rows: `fiche_hash` → `fiches/b9d1af56….json`, `roster_entry_id` → `qwen3.6-35b-a3b-ud-iq4xs`, `suite_id`/`suite_version`/`prompt_set_hash` → the snapshot, `prompt_template_id`/`prompt_template_hash` → `prompt_provenance.py`
- [x] Two real runs in a quiet thermal window with a verdict and both runs' machine state — per-repetition `machine_state`, `gpu_throttle_reasons: ["gpu_idle"]`, 66-70 °C, `thermal_posture: fixed_cooldown`
- [x] The 10% tolerance is recorded in the README against the observed spread — recorded, but against a statistic the harness never computes (see finding 2)
- [x] The validator is run over the bundle with its zero exit and counts recorded, and the deliberate-edit case with its non-zero exit — `aidd_docs/results/README.md:83-92`, all three reproduced this review
- [ ] The current files are retained as superseded — renamed, **marked with the schema version that produced them**, and explained in the README — renamed and explained, but the `.schema-1` suffix names a `schema_version` no row in either file carries (`"2"` on one row, absent on 42)
- [x] The README states what a reader can and cannot do with a row alone, and that the bundle is the unit handed over — `aidd_docs/results/README.md:3-14`
- [x] The suite definition published here is a snapshot export, not a registry — `src/wave_local_ai_v2/suite_snapshot.py:1-10`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | fit | 3 | `aidd_docs/results/README.md:26-28` | The README attributes the runs to "branch `feat/trilingual-suite-and-reference-bundle` at tip `63ececa`", but all 82 rows carry `commit_sha 9bc9da88…` (the phase-2 commit) with `tree_dirty: true`. The published narrative contradicts the rows' own provenance fields, which is exactly what the epic makes the rows carry. | State the commit the rows carry (`9bc9da8`) and that the tree was dirty, the way the schema-1 section already does for its row 3 at `:132`. |
| 🟡 | fit | 3 | `aidd_docs/results/README.md:37-39` | "Observed spread … `gen_tok_per_s` **1.98%** … well inside `RUNTIME_REPRODUCTION_TOLERANCE` (10%)" is computed from repetition means (25.329 / 24.826). The tolerance is applied by `verdict.py:168-178` to `gen_tok_per_s_delta`, which the rows carry as **2.387%** over the published medians (25.408 / 24.802). The recorded number is not the one the threshold judges. | Quote the rows' own `gen_tok_per_s_delta` (2.39%) and `prompt_tok_per_s_delta` (0.24%) as the spread the tolerance is measured against; keep the means as a labelled secondary column if useful. |
| 🟡 | functional | 3 | `CHANGELOG.md:31`, `aidd_docs/results/README.md:74-77` | Story 19 asks the superseded files to be "marked with the schema version that produced them". `.schema-1` matches nothing: `runtime-reference.schema-1.jsonl` holds `schema_version` `"2"` on one row and none on two, `quality-reference.schema-1.jsonl` none on all 40. The CHANGELOG compounds it by calling the same bundle "schema-6". | Correct the CHANGELOG to what the rows carry, and add one README sentence defining the `.schema-<N>` suffix as a superseded-generation counter, not a `schema_version` value. Renaming again is worse: no single version fits a file whose rows predate the key. |
| 🟡 | functional | 1 | `src/wave_local_ai_v2/classification_suite.py:182-188`, `aidd_docs/results/README.md:50-55` | Story 20 requires the four labels to stay semantically disjoint in each language. `account-de-01` ("Zwei-Faktor-Authentifizierung deaktivieren, finde aber die Option nicht") is routed `technical` by `mistral-small-2603` in **both** published runs, and `other-de-01` in one — the sole cause of the `not_reproduced` verdict. The README explains the 0.95→0.90 drop purely as cloud nondeterminism, naming neither item nor the pattern. | Record the two misrouted DE items and their predicted label in the README as an observed suite finding beside the nondeterminism reading. The item text itself cannot be fixed here: editing it moves `PROMPT_SET_HASH` and invalidates the bundle just published, so file the revision as backlog work for the next regeneration. |
| 🟡 | code | 4 | `tests/test_reference_bundle.py:59-70` | `test_every_quality_row_resolves_its_suite_definition` checks `suite_id` and `suite_version` but not `prompt_set_hash`, so a suite edit that moves the hash without bumping the version leaves the bundle check green — the hash is the one pointer that detects exactly that drift. | Add `assert snapshot["prompt_set_hash"] == row["prompt_set_hash"]` beside the existing two asserts. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/suite_snapshot.py:66-72` | `sys.exit(0)` after `main()` is dead — falling off `main()` already exits 0 — and `sys` is imported for nothing else. | Drop the `sys` import and the `sys.exit(0)` line. |
| 🟢 | conform | 2 | `src/wave_local_ai_v2/suite_snapshot.py:32` | `SUITE_DEFINITIONS_DIR` is a hardcoded relative `Path`, while every other artifact path is a `settings.DEFAULT_*` constant and `fiche_registry.py:4-5` states the convention outright ("never hardcoded in this module"). | Add `DEFAULT_SUITE_DEFINITIONS_DIR` to `settings.py` and read it here. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/scoring.py:170-172` | `by_language[item["language"]]` raises a bare `KeyError` for a language outside `LANGUAGES`. Unreachable today (`Literal` type plus `gate_suite` refusing first), but the sibling path in `suite_gate.py:98-101` raises a named `SuiteGateError` for the same condition. | Either `setdefault` and drop the unknown bucket with a comment, or raise the same named error. |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/classification_suite.py:30-36` | The `"2":` version-history comment sits above `SUITE_ID`, separated from the `SUITE_VERSION` line it documents, unlike `row_contract.py:34-37` where the same convention sits directly above its constant. | Move the two version-history lines below `SUITE_ID`, directly above `SUITE_VERSION`. |
| 🟢 | rot | 4 | `tests/test_reference_bundle.py:15-22` | The two reference paths are rebuilt from a local `RESULTS_DIR` while the fiche and roster pointers in the same file come from `settings.DEFAULT_FICHE_REGISTRY_DIR` / `DEFAULT_ROSTER_PATH`. `settings.DEFAULT_RUNTIME_REFERENCE_PATH` / `DEFAULT_QUALITY_REFERENCE_PATH` exist and hold the same values. | Read all four from `settings`, so a default path move breaks one place, not two. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 93% (28/30)                                       |
| Files checked | `src/wave_local_ai_v2/classification_suite.py`, `scoring.py`, `quality_cli.py`, `row_contract.py`, `suite_snapshot.py`, `suite_gate.py`, `fiche_registry.py`, `settings.py`, `verdict.py`, `tests/test_classification_suite.py`, `test_scoring.py`, `test_suite_gate.py`, `test_suite_snapshot.py`, `test_reference_bundle.py`, `test_quality_cli.py`, `test_cli.py`, `test_results.py`, `test_row_contract.py`, `test_prompt_provenance.py`, `aidd_docs/results/README.md`, `runtime-reference.jsonl`, `quality-reference.jsonl`, `runtime-reference.schema-1.jsonl`, `quality-reference.schema-1.jsonl`, `suite-definitions/classification-support-routing.json`, `fiches/b9d1af56….json`, `aidd_docs/roster/models.json`, `CHANGELOG.md`, `aidd_docs/memory/cli.md`, `architecture.md`, `.gitignore`, `.pre-commit-config.yaml` |
| Unchecked     | Story 20 "the four routing labels stay semantically disjoint in each language" — fix; Story 19 "marked with the schema version that produced them" — fix |
| Unplanned     | `.pre-commit-config.yaml:37-42` — the `detect-secrets` exclude pattern gained a `suite-definitions.[a-z0-9-]+[.]json$` branch, traced to no phase criterion; justified in place (the snapshot's `prompt_set_hash` is a SHA over public prompt text) and consistent with the existing fiche exclusion |
