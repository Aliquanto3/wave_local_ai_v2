# Review: Fiche hash, invalidation validator, and reproduction verdict

- **Verdict**: changes-requested
- **Diff**: `HEAD...working-tree` (d1709f6 + untracked `fiche_registry.py`, `fiche_validator.py`, `verdict.py`, their tests, `aidd_docs/results/fiches/`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_24
- **Findings**: 0 critical, 10 warning, 7 minor

## Phases

### Phase 1 — Fiche projection, hash, registry, rows cite the hash

- [x] `normalise_fiche` output has no `flags` key and no filesystem path — `src/wave_local_ai_v2/hardware.py:44` (`_NORMALISED_KEYS`), `tests/test_hardware.py:72`
- [x] Two fiches differing only by `flags` (one carrying `D:\ia\models\...`) hash identically — `tests/test_hardware.py:81`
- [x] Two fiches differing by `gpu_name` hash differently — `tests/test_hardware.py:88`
- [x] Dict key insertion order never changes the hash — `src/wave_local_ai_v2/hardware.py:113` (`sort_keys=True` over a fixed-order projection), `tests/test_hardware.py:95`
- [x] Writing the same fiche twice leaves exactly one file — `src/wave_local_ai_v2/fiche_registry.py:42`, `tests/test_fiche_registry.py:19`
- [x] `read_fiche` on an unwritten hash returns `None` — `src/wave_local_ai_v2/fiche_registry.py:54`, `tests/test_fiche_registry.py:29`
- [x] `read_fiche` after `write_fiche` returns the fiche including its `flags` — `tests/test_fiche_registry.py:35`
- [x] `REQUIRED_FIELDS["runtime"]` drops the ten flattened fields and gains `fiche_hash` — `src/wave_local_ai_v2/row_contract.py:52`
- [x] `REQUIRED_FIELDS["quality"]` contains `fiche_hash` — `src/wave_local_ai_v2/row_contract.py:115`
- [x] A stubbed run writes a row whose `fiche_hash` resolves via `read_fiche` — `tests/test_cli.py:230`
- [x] A stubbed quality run's local-provider and mistral-provider rows cite the identical `fiche_hash` — `tests/test_quality_cli.py:198`

### Phase 2 — Invalidation validator

- [x] `verify_fiche` returns `"missing"` for an unwritten hash, `"ok"` for an untouched one — `src/wave_local_ai_v2/fiche_registry.py:72`, `tests/test_fiche_validator.py:53,62`
- [x] A file edited in place with a stale filename hash is `"edited"`, recomputed from the file's own content, no row read — `src/wave_local_ai_v2/fiche_registry.py:76`, `tests/test_fiche_validator.py:72`
- [x] Inside a committed git registry, `changed_fields` names the actual differing key — `src/wave_local_ai_v2/fiche_registry.py:134`, `tests/test_fiche_validator.py:83`
- [x] Outside git, `changed_fields` degrades to a named `"unavailable: ..."` — `src/wave_local_ai_v2/fiche_registry.py:100`, `tests/test_fiche_validator.py:86`
- [x] A clean bundle exits 0 with the correct checked count — `tests/test_fiche_validator.py:251`
- [x] An edited fiche exits non-zero naming the citing row by run id and position — `tests/test_fiche_validator.py:124`
- [x] A row citing an absent hash lands in the distinct `missing` class — `src/wave_local_ai_v2/fiche_validator.py:109`, `tests/test_fiche_validator.py:151`
- [x] A zero-row file exits 0 with a zero count — `tests/test_fiche_validator.py:241`
- [x] The validator never recomputes a run (no server launch, no roster load) — `src/wave_local_ai_v2/fiche_validator.py:64-130` reads rows and JSON files only
- [x] `pyproject.toml` registers `wave-local-ai-v2-validate` — `pyproject.toml:31`
- [x] The no-args form resolves the two settings-configured result paths without raising when those paths are absent — `src/wave_local_ai_v2/fiche_validator.py:152`, `results.read_rows` returns `[]`; verified live: `checked 5 row(s)`, exit 0

### Phase 3 — Three-state verdict, both CLIs attach it

- [x] `Settings` carries `fiche_registry_dir`, `runtime_reference_path`, `quality_reference_path`, `runtime_reproduction_tolerance` with the stated defaults — `src/wave_local_ai_v2/settings.py:67-73`
- [x] `REQUIRED_FIELDS` requires `verdict` on both kinds — `src/wave_local_ai_v2/row_contract.py:54,117`
- [x] Equal medians against a matching reference → `reproduced` — `src/wave_local_ai_v2/verdict.py:150`, `tests/test_verdict.py:42`
- [x] 9.9% delta → `reproduced`, 10.1% → `not_reproduced` — `tests/test_verdict.py:54`
- [x] A differing `gpu_name` alone → `not_comparable` naming `gpu_name` — `src/wave_local_ai_v2/verdict.py:140`, `tests/test_verdict.py:70`
- [x] A differing `cpu`/`gpu_driver_version` alone still matches and reports — `src/wave_local_ai_v2/verdict.py:24` (blocking set excludes them), `tests/test_verdict.py:83`
- [x] An empty reference list → `not_comparable`, never `not_reproduced` — `src/wave_local_ai_v2/verdict.py:114`, `tests/test_verdict.py:96`
- [x] Identical per-item `predicted_label`s → `reproduced` quality verdict — `tests/test_verdict.py:119`
- [x] One differing label → `not_reproduced` naming that `item_id` — `src/wave_local_ai_v2/verdict.py:200`, `tests/test_verdict.py:128`
- [x] No matching `model_id`/`suite_version`/seed → `not_comparable` — `src/wave_local_ai_v2/verdict.py:192`, `tests/test_verdict.py:140`
- [x] A stubbed runtime run against a temp reference produces a present, internally consistent `verdict` — `src/wave_local_ai_v2/__init__.py:396`, `tests/test_cli.py:271`
- [x] A stubbed quality run attaches one verdict per (model, provider) batch, identical across its rows — `src/wave_local_ai_v2/quality_cli.py:379-390`, `tests/test_quality_cli.py:180`

### Phase 4 — Live run, evidence, docs and memory

- [x] A real row carries `fiche_hash` and a `verdict` block valued `not_comparable` with a correct reason — verified live: `runtime.jsonl` row `89c3d14104584f4c87da7f2cff646562`, `reason: "no reference row shares this candidate's roster_entry_id"`; both reference files confirmed to carry no `roster_entry_id` on any row
- [x] `wave-local-ai-v2-validate` exits 0 against both reference files — verified live: `checked 43 row(s)`, `legacy (pre-fiche-hash, not fatal): 43`, exit 0
- [ ] The fiche file this run produced is committed under `aidd_docs/results/fiches/` — the file exists and the directory is non-ignored, but it is still untracked (`?? aidd_docs/results/fiches/`); committing is the post-review step in this project's flow
- [x] `aidd_docs/results/README.md` states the not-comparable-until-story-19 fact and records the observed verdict block — `aidd_docs/results/README.md:109-153`
- [x] `CHANGELOG.md`'s `[Unreleased]` names all three shipped capabilities — `CHANGELOG.md:72-95`
- [x] `docs/setup.md` documents the validator command and the fiches directory alongside the other two — `docs/setup.md:271-289`
- [x] `cli.md` lists three commands — `aidd_docs/memory/cli.md:19-31`
- [x] `codebase-map.md` lists the three new modules and the new entry point — `aidd_docs/memory/codebase-map.md:22,33`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | code | 3 | `src/wave_local_ai_v2/verdict.py:147-163` | A matched reference row is indexed and divided by without a guard. Confirmed: a reference row lacking `ttft_ms` raises `KeyError`, one with `ttft_ms: 0.0` raises `ZeroDivisionError`. Both fire in `__init__.py:397`, after the server has exited and **before** `append_row`, and neither type is in `main()`'s caught tuple (`__init__.py:200-212`) — so a malformed reference file discards a completed multi-minute measurement and prints a traceback instead of an `error:` line. | Treat a reference row missing any compared metric, or carrying a zero denominator, as non-matching so the flow falls through to `not_comparable` with a named reason; or return `None` deltas for the two reported-only metrics. Add a test for each. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/verdict.py:200-206` | The differing-item comprehension skips every candidate item with no reference counterpart, so an empty result cannot be told apart from a real all-match. Confirmed: candidate `item_id` `z-9` against reference `item_id` `a-1`, same `model_id`/`suite_version`/seed, returns `{"verdict": "reproduced"}` on zero compared items. A false `reproduced` is the worst failure mode of a reproduction verdict, and the module already applies the opposite discipline to an empty reference list. | Compare the two `item_id` sets first: any candidate item absent from the reference (or vice versa) makes the batch `not_comparable`, naming the unmatched ids, rather than silently narrowing the comparison. |
| 🟡 | code | 2 | `src/wave_local_ai_v2/fiche_validator.py:145-149` | The comment says "A settings load is skipped when explicit paths are given"; the next line calls `load_settings()`, which `_require_existing_path`s `SLM_MODELS_DIR` and `LLAMA_SERVER_PATH`. Confirmed: `wave-local-ai-v2-validate runtime-reference.jsonl` with a non-existent models dir exits 1 with `error: SLM_MODELS_DIR=... does not exist on disk`. A reader or CI job checking a published artifact must own a local model install — against story 15's "reads published artifacts only". | In the explicit-path branch resolve the registry dir from `FICHE_REGISTRY_DIR` / `DEFAULT_FICHE_REGISTRY_DIR` directly (or catch `SettingsError` and fall back to the default), and make the comment describe what the code does. |
| 🟡 | code | 2 | `src/wave_local_ai_v2/fiche_validator.py:144` | An explicitly named results path that does not exist is silently zero rows: `results.read_rows` returns `[]`, so a typo'd path prints `checked 0 row(s)` and exits 0. The one command whose job is proving integrity gives a clean bill of health for a file it never opened. | Refuse a non-existent path when it came from `argv` (one line on stderr, exit 1); keep the tolerant behaviour only for the two default live stores, where absence genuinely means zero rows. |
| 🟡 | rot | 2 | `src/wave_local_ai_v2/fiche_validator.py:67-73` | The docstring contradicts the code and misstates the output: positions **are** reset per file (the `enumerate` sits inside the per-path loop at `:81`), and `fiche_path` is the registry path, not the results file — so no issue entry, and no `legacy` entry at all, says which results file it came from. With the default two-path invocation, "position 3" is ambiguous between `runtime.jsonl` and `quality.jsonl`. | Add the source results path to `_RowIssue` and `_LegacyIssue`, populate it, and rewrite the docstring to state per-file 0-based positions. |
| 🟡 | rot | 3 | `src/wave_local_ai_v2/verdict.py:164-165` | `candidate_machine_state` / `reference_machine_state` are set from `row.get("repetitions")`: the names promise a machine-state summary and deliver the entire repetition array, and the candidate copy duplicates a sibling key of the very row it is written onto (a 5-repetition run's full nested block, stored twice in one JSON object, free to diverge). These are published row fields, so the shape is expensive to change once story 19 makes matches real. | Drop `candidate_machine_state` — the row already carries `repetitions` — and rename the remaining one to what it holds (`reference_repetitions`), or project both to the machine-state summary the field name claims. |
| 🟡 | conform | 3 | `.env.example:19` | The four new settings vars (`FICHE_REGISTRY_DIR`, `RUNTIME_REFERENCE_PATH`, `QUALITY_REFERENCE_PATH`, `RUNTIME_REPRODUCTION_TOLERANCE`) are absent, though the file lists every other settings var including `ROSTER_PATH`/`ROSTER_ENTRY_ID`, explicitly commented as "neither is expected to be overridden today". The three reference/tolerance vars appear in no doc at all — `docs/setup.md:271-289` and `cli.md:19-31` mention only `FICHE_REGISTRY_DIR` — so story 16's "named reference" is undiscoverable to an operator. | Add the four commented entries to `.env.example`, and name the reference paths and the tolerance where `docs/setup.md:254` already documents `RUNTIME_SPREAD_THRESHOLD`. |
| 🟡 | conform | 3 | `src/wave_local_ai_v2/settings.py:67-73` | `tests/test_settings.py` is untouched: none of the four new fields has a default or env-override test, and the `minimum=0.0` guard on `RUNTIME_REPRODUCTION_TOLERANCE` (`settings.py:146`) is never exercised. The previous increment's numeric setting got both halves of the pattern (`test_load_settings_reads_the_repetition_protocol_overrides`, `test_load_settings_refuses_invalid_repetition_protocol_values`). | Extend those two tests with the four vars and a negative-tolerance case, mirroring the existing structure. |
| 🟡 | conform | 4 | `aidd_docs/memory/architecture.md:55` | Still reads "Every result row must carry its hardware fiche (CPU, RAM, GPU, driver, llama.cpp build, quant, flags)" — precisely the ten fields this increment removed from the row. Project memory is loaded into every session by `CLAUDE.md`, so the stale line will actively steer future work back to the old shape. Phase 4 updated `cli.md` and `codebase-map.md` but not this file. | Reword to "must cite its hardware fiche by `fiche_hash`; the fiche itself is stored write-once under `aidd_docs/results/fiches/`", keeping the "a number without a fiche is meaningless" clause. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/verdict.py:128` | The `no reference row shares this candidate's roster_entry_id` branch is uncovered by any test, yet it is the single outcome the shipped evidence publishes (`aidd_docs/results/README.md:139-146`). The `_resolve_fiche` → `None` paths (`:40,56,62,83,90`) are equally uncovered and describe the exact state of both committed reference files: rows with no `fiche_hash`. | Add three cases to `tests/test_verdict.py`: a reference row with a different `roster_entry_id`, a reference row with no `fiche_hash`, and a candidate row whose `fiche_hash` is not in the registry — asserting the reason string each returns. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 97% (38/39)                                       |
| Files checked | `src/wave_local_ai_v2/hardware.py`, `fiche_registry.py`, `fiche_validator.py`, `verdict.py`, `row_contract.py`, `settings.py`, `__init__.py`, `quality_cli.py`, `pyproject.toml`, `tests/test_hardware.py`, `test_fiche_registry.py`, `test_fiche_validator.py`, `test_verdict.py`, `test_cli.py`, `test_quality_cli.py`, `test_results.py`, `test_row_contract.py`, `CHANGELOG.md`, `docs/setup.md`, `aidd_docs/results/README.md`, `aidd_docs/results/fiches/`, `aidd_docs/memory/cli.md`, `aidd_docs/memory/codebase-map.md` |
| Unchecked     | Phase 4 — the live run's fiche file is committed under `aidd_docs/results/fiches/` — not-applicable (file written and non-ignored; the commit is the post-review step per `GUIDELINES.md`'s "one review after the last phase, then merges") |
| Unplanned     | `tests/test_results.py:24-25` and `tests/test_row_contract.py:41-42` gained the two new required fields (contract follow-through, not in the phase files); `quality_cli._run_local_suite` lost its `roster_entry`/`model_path` parameters and `build_flags` moved to the caller (`quality_cli.py:135`) — a refactor the plan implied but did not name; gate re-run clean: 319 passed, 95.81% coverage, `ruff check`/`ruff format --check`/`mypy src/ scripts/` all pass |
