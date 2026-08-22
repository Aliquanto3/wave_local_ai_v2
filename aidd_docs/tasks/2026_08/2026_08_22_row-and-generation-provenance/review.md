# Review: Rows name their code, call path and failure reason

- **Verdict**: changes-requested
- **Diff**: `main...feat/row-and-generation-provenance`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 1 critical, 3 warning, 3 minor

## Phases

### Phase 1 — Rows name the code and the tree that produced them

- [x] `build_info.commit_sha()` / `version()` behave as before; `tests/test_build_info.py` passes unmodified — `src/wave_local_ai_v2/build_info.py:61`, file untouched in the diff, 158 tests pass
- [x] `capture_provenance()` never raises regardless of git presence or exit state; total git failure yields `commit_sha=None`, `tree_dirty=None`, non-null `release_version` — `tests/test_provenance.py:88`
- [x] `validate_row` refuses a row missing any of the three and accepts them present with `None` — `src/wave_local_ai_v2/row_contract.py:26`, `:65`; the check is key-presence only, `:113`
- [x] One stubbed runtime run carries the triple; one stubbed quality run writes 20 rows all carrying the identical triple — `tests/test_cli.py:143`, `tests/test_quality_cli.py:470`
- [x] All five test files pass; `provenance.py` reaches 100% line coverage, so each new branch is exercised — pytest run, `src/wave_local_ai_v2/provenance.py 17 0 100%`
- [x] Story: every runtime and quality row carries `run_id`, `captured_at`, `release_version`, `commit_sha` — `src/wave_local_ai_v2/row_contract.py:26`, `:65`
- [x] Story: every row carries `tree_dirty`, true on uncommitted changes to tracked files — `src/wave_local_ai_v2/provenance.py:44`, `tests/test_provenance.py:14`, `:25`
- [x] Story: `release_version` falls back to the packaged version, the fallback visible in the value — `src/wave_local_ai_v2/provenance.py:66` (`+untagged`), `tests/test_provenance.py:73`
- [x] Story: capture never aborts a run; an unavailable git context writes explicit nulls and the row is still written under the writer gate — `src/wave_local_ai_v2/provenance.py:36`, `tests/test_provenance.py:44`
- [x] Story: captured once per run, identical across every row that run writes — `src/wave_local_ai_v2/quality_cli.py:109` (one call threaded to both batches), `tests/test_quality_cli.py:479`

### Phase 2 — Rows name the endpoint and prompt template

- [x] `is_consistent` returns `False` for exactly the one forbidden combination, `True` otherwise; `template_hash` is deterministic — `src/wave_local_ai_v2/prompt_provenance.py:41`, `tests/test_prompt_provenance.py:60`
- [x] `validate_row` raises on a non-`/completion` endpoint paired with `"none"`, accepts every combination the writers produce — `src/wave_local_ai_v2/row_contract.py:124`, `tests/test_prompt_provenance.py:76`
- [x] `complete_prompt`'s caller receives `content` and `endpoint`; the 401, malformed-body and null-content paths are unchanged — `src/wave_local_ai_v2/mistral_client.py:122`, `tests/test_mistral_client.py:41`
- [x] The runtime row and the local/mistral quality rows carry the correct, distinct quadruple — `src/wave_local_ai_v2/__init__.py:229`, `tests/test_cli.py:146`, `tests/test_quality_cli.py:484`
- [x] All four test files pass; the consistency test fails if the `is_consistent` call were removed — it is the only assertion path to `RowContractError` for a complete row
- [x] Story: every row records the endpoint called, the prompt-template id and the template's content hash — `src/wave_local_ai_v2/quality_cli.py:281`
- [x] Story: `none` with a null hash is what the raw `/completion` path records — `src/wave_local_ai_v2/__init__.py:230`, `src/wave_local_ai_v2/quality_cli.py:249`
- [x] Story: the row states capture-or-reconstruction and today's value is `captured` — `src/wave_local_ai_v2/prompt_provenance.py:24`, `src/wave_local_ai_v2/quality_cli.py:284`
- [x] Story: a row whose endpoint applies a template and whose template id is `none` is refused by the writer gate — `src/wave_local_ai_v2/row_contract.py:124`

### Phase 3 — A failed generation scores zero and names its reason

- [x] `score_item` maps empty / whitespace / unparseable / valid / both truncation kinds to five distinct outcomes; `failure_counts` always carries all four keys — `src/wave_local_ai_v2/scoring.py:85`, `:126`, `tests/test_scoring.py:57`
- [x] `complete_prompt` surfaces `finish_reason` and `generated_tokens`; a response missing either raises `MistralRequestError` — `src/wave_local_ai_v2/mistral_client.py:113`, `tests/test_mistral_client.py:98`
- [x] `validate_row` refuses a quality row missing `failure_reason` or `failure_counts`; the runtime set is untouched — `src/wave_local_ai_v2/row_contract.py:97`, runtime frozenset unchanged at `:23`
- [ ] A stubbed cap-truncated local completion and a stubbed context-truncated cloud completion each produce their distinct reason — the local half holds (`tests/test_quality_cli.py:526`), the cloud half is proved against a response Mistral does not emit: `tests/test_quality_cli.py:551` stubs `finish_reason="length"` with `generated_tokens < MAX_OUTPUT_TOKENS`, while `length` means the `max_tokens` cap was reached. The real context-limit value, `model_length`, is not mapped at `src/wave_local_ai_v2/quality_cli.py:229`
- [x] All three test files pass; the four reasonless `predicted_label: null` rows could not be produced by this path — every `predicted_label=None` branch in `scoring.py` sets a reason (`:85`, `:99`, `:112`), and `failure_reason` is a required quality field
- [x] Story: an empty, truncated or unparseable generation scores 0, stays in the denominator and records a reason; no item is dropped — `src/wave_local_ai_v2/scoring.py:85`, `tests/test_scoring.py:129`
- [ ] Story: the taxonomy separates `truncated_max_tokens` (the suite's cap) from `truncated_context` (the model's own limit) — the split is correct inside `score_item` (`src/wave_local_ai_v2/scoring.py:93`), but on the cloud path `truncated_context` is unreachable: `model_length` maps to `truncated=False`. Same defect as the box above; one finding covers both
- [x] Story: a scored item that succeeded records a null failure reason, never an absent key — `src/wave_local_ai_v2/scoring.py:118` sets `failure_reason=None` on the success branch
- [x] Story: the denominator is the item count, and a row states how many items failed and under which reasons — `src/wave_local_ai_v2/scoring.py:139`, `src/wave_local_ai_v2/quality_cli.py:308`
- [x] Story: the four current reasonless rows cannot be produced by the new code path — verified against `aidd_docs/results/quality-reference.jsonl`: 8 rows with `predicted_label: null`, none carrying a `failure_reason` key, at `technical-01`, `technical-02`, `billing-03`, `technical-03` across two runs

### Phase 4 — Changelog, codebase map and reference evidence note

- [x] `CHANGELOG.md`'s `## [Unreleased]` names all three stories' row-schema additions and the `complete_prompt` return-shape change in the existing bullet style — `CHANGELOG.md:20-34`
- [x] `codebase-map.md` names `provenance.py` and `prompt_provenance.py` among the modules shared by both entry points — `aidd_docs/memory/codebase-map.md:22`
- [x] `results/README.md` names the four `predicted_label: null`-with-no-reason rows and states plainly they are not back-filled — `aidd_docs/results/README.md:61-71`; the "8 rows total" count matches the file

## Findings

<!-- Severity gate per aidd_docs/GUIDELINES.md:19 — 🔴/🟡 fixed on this branch, 🟢 filed to aidd_docs/backlog/tech-debt.md. Each Fix cell ends with what was done. -->

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🔴 | functional | 3 | `src/wave_local_ai_v2/quality_cli.py:229` | `truncated = response["finish_reason"] == "length"` misses `model_length`, Mistral's documented value for the model's own context limit (enum: `stop`, `length`, `model_length`, `error`, `tool_calls`). A context-truncated cloud generation reads as not truncated, falls through to `normalize_label`, and is published as `unparseable` — or as a scored prediction if the partial text still holds a label token. `truncated_context` is unreachable on the cloud path, which is the one distinction story 5 exists to make; `tests/test_quality_cli.py:551` hides this by stubbing `finish_reason="length"` with `generated_tokens < MAX_OUTPUT_TOKENS`, a pair Mistral never emits. | Map both values to truncated (`finish_reason in {"length", "model_length"}`, as a named constant in `mistral_client.py`), keeping the `generated_tokens >= max_output_tokens` split to name which kind. Restub the cloud-truncation test with `finish_reason="model_length"` and add a `length` case asserting `truncated_max_tokens`. **Applied**: `mistral_client.TRUNCATING_FINISH_REASONS`, used at `quality_cli.py:255`; both cloud truncation kinds now covered at `tests/test_quality_cli.py:551`, `:576`. |
| 🟡 | code | 3 | `src/wave_local_ai_v2/mistral_client.py:113-115` | `finish_reason` and `generated_tokens` are extracted as `Any` and returned into a `TypedDict` declaring `str` / `int`, with no type guard — while `content` twelve lines above carries an explicit `isinstance` check whose own comment states the rule ("Same rule and same wording as the local path's guard"). A `finish_reason: null` silently reads as not-truncated; a non-numeric `completion_tokens` raises an uncaught `TypeError` inside `score_item`'s comparison, past the `MistralRequestError` boundary `main()` catches. | Guard both with the same `isinstance` pattern already used for `content` and raise `MistralRequestError` naming the offending value. **Applied**: `mistral_client.py:126-136`, covered by `tests/test_mistral_client.py:116`. |
| 🟡 | conform | 3 | `tests/test_cli.py:25` | `QUALITY_ONLY_FIELDS` was not widened with `failure_reason` and `failure_counts`, the two fields story 5 deliberately added to the quality kind only. The set's own comment names its job — "stops a quality field reaching a runtime row" — for `architecture.md`'s "the two are never merged"; the guard now covers 19 of the 21 quality-only fields. | Add `"failure_reason"` and `"failure_counts"` to the set. **Applied**: `tests/test_cli.py:44-45`. |
| 🟡 | rot | 2 | `src/wave_local_ai_v2/quality_cli.py:249-256` | `_score_and_write` derives `prompt_template_id` and `prompt_template_hash` from `provider == "local"` with an `else` meaning "any non-local provider is the Mistral chat wrapper", while `endpoint` — the same call path's other half — is threaded in as a parameter. Two sources for one truth: a third provider silently stamps Mistral's template id and hash, and the row-contract consistency rule cannot catch it (a non-raw endpoint with a named template id is legal). | Pass the four call-path fields as one `call_path_fields` dict from each call site, mirroring `provenance_fields`, and drop the `provider` branch. Removes two parameters and one branch. **Applied**: `_local_call_path()` / `_mistral_call_path()` at `quality_cli.py:167-192`, spread at `:300`. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/quality_cli.py:225` | `endpoint = responses[0]["endpoint"]` raises `IndexError` on an empty suite; `suite_gate` marks an under-sized suite indicative rather than refusing it, so nothing upstream forbids the case. Unreachable today (the suite is a 10-item module constant). | Refuse an empty suite in the gate, or return early from `_run_cloud_suite` before indexing. **Filed** to `tech-debt.md`. |
| 🟢 | rot | 1 | `src/wave_local_ai_v2/provenance.py:32-33` | `provenance.py` reaches into `build_info._run_git` and `build_info._PACKAGE_DIR`, two underscore-private names, from another module; the underscore now claims a scope the code does not honour. `provenance.commit_sha()` is a bare one-line delegation to `build_info.commit_sha()` on top. The plan mandated the reuse, not the naming. | Rename to `run_git` / `PACKAGE_DIR` (package-public), and let callers of the sha go to `build_info` directly. **Filed** to `tech-debt.md`. |
| 🟢 | conform | 4 | `CHANGELOG.md:32-34` | The `complete_prompt` return-shape entry sits under `### Added` though it changes an existing public surface from a bare string to a structured result; `phase-4.md:46` names `### Changed` as the default and Keep a Changelog puts it there. | Move the bullet to the `### Changed` section at `CHANGELOG.md:36`. **Filed** to `tech-debt.md`. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 94% (30/32)                                       |
| Files checked | `src/wave_local_ai_v2/build_info.py`, `provenance.py`, `prompt_provenance.py`, `row_contract.py`, `scoring.py`, `mistral_client.py`, `quality_cli.py`, `__init__.py`, `tests/test_provenance.py`, `test_prompt_provenance.py`, `test_scoring.py`, `test_mistral_client.py`, `test_cli.py`, `test_quality_cli.py`, `test_row_contract.py`, `test_results.py`, `CHANGELOG.md`, `aidd_docs/memory/codebase-map.md`, `aidd_docs/results/README.md` |
| Unchecked     | Phase 3, "cap-truncated and context-truncated completions each produce their distinct reason" — fix; Phase 3 story line, "the taxonomy separates `truncated_max_tokens` from `truncated_context`" — fix (same defect, one finding row) |
| Unplanned     | none — every changed file appears in a phase's architecture projection |
