# Review: The data is CC-BY 4.0, the code stays MIT, and each says so where it lives

## Round 1

VERDICT: PASS

### Gates

- `uv run pytest -q`: `1541 passed, 2 warnings in 50.93s`, coverage 97.57% (floor 95%).
- `uv run ruff check .`: all checks passed. `uv run ruff format --check .`: 564 files already formatted. `uv run mypy src/ scripts/`: no issues in 54 files. detect-secrets on the changed files: exit 0.

### Acceptance, one by one

1. `LICENSE` unchanged, MIT, names the code: not in `git status`; `test_license_still_names_mit_and_the_code`. Met.
2. `LICENSE-DATA` with CC-BY 4.0 in full plus scope: legal text after the marker (`LICENSE-DATA:121`) is byte-identical to a fresh `curl` of `https://creativecommons.org/licenses/by/4.0/legalcode.txt` (`cmp` identical, sha256 `9ba9550a...9411`, 18657 bytes); pinned by `test_the_legal_code_is_the_official_text_verbatim`. Scope 1.1 (`LICENSE-DATA:30-42`) names suite-definitions, row item fields, current and superseded reference files, fiches, roster `models.json`; 1.2 (`:49-52`) names untracked `runtime.jsonl`/`quality.jsonl` as not published and not covered. `test_the_scope_names_what_the_story_requires`. Met.
3. Not-granted parts: weights (`:53`), roster-recorded licences (`:55-58`), model-output fields as a separate part with `predicted_label` and the spike path, unverified (`:61-74`); the override clause at `:12-15` states nothing grants CC-BY over them. `predicted_label` is the only model-output field on all four reference files (checked: `verdict` is the reproduction verdict, not model output). NOTICE files and README repeat the exclusions; none implies CC-BY over a non-granted part. `test_the_parts_not_granted_are_named_and_the_output_part_cites_its_spike`. Met (see non-blocking 2).
4. Drawn-items section (`:77-87`): none drawn today, a drawn item carries its source's licence per item. Every published and source item checked: `provenance` `hand_written`, no `source`. Met.
5. Two assumptions disclosed in their own section 3 (`:90-102`), employment/client agreement wording present. Met.
6. Notice in each covered directory: `aidd_docs/results/`, `fiches/`, `suite-definitions/`, `roster/` (plus `comparisons/`, `suite_data/`); each names CC-BY 4.0, LICENSE-DATA and MIT; `test_every_covered_path_exists_and_says_so_where_it_lives`. Met.
7. README licence section: split in plain words, exclusions, links `](LICENSE)` and `](LICENSE-DATA)`, says where the attribution string will land; `test_the_readme_states_the_split_and_links_both_files`. Met.
8. Item-literal modules (Q43 (a)): faithful reading, not an acceptance conflict. The bullet's quantifier is "each module ... that holds hand-written item literals"; the parenthetical "(today `classification_suite.py` and `translation_suite.py`)" is stale since `d66f760`: both now hold only `LABELS`/shape/rationale, items moved to `suite_data/*.json`. A grep of every `src/wave_local_ai_v2/*.py` for item constructors, `*ITEMS` literals and item-shaped dict literals finds only `judge_probe.py` (`JUDGE_PROBE_ITEMS`, ten `_item(...)` calls); it carries the header (`judge_probe.py:1-3`) and is named in scope (`LICENSE-DATA:42`). `suite_data/` covered with a `NOTICE.md` honours Q43's intent (JSON takes no header), and its items already declare `licence: "CC-BY-4.0"`. Met.

### Test quality

Not tautological: the covered list is parsed from `LICENSE-DATA` itself and checked against the real tree. Fixture tests prove the failures: missing notice (`test_a_covered_directory_without_its_notice_fails`), notice not pointing to terms, renamed path (`test_a_renamed_covered_path_fails` reports both the missing entry and the unscoped new file), dir-vs-file, unscoped new data directory, item-literal module without header or scope entry. A new covered entry whose directory lacks a notice hits the same branch.

### Packaging

`suite_registry.py:288-290` lists only `*.json` in `suite_data/`; `test_suite_registry_ignores_the_notice_in_suite_data` proves no `NOTICE` suite id. `uv_build` ships the `.md` as package data, harmless.

### Blocking findings

None.

### Non-blocking findings

1. Story text: the last acceptance bullet's "(today `classification_suite.py` and `translation_suite.py`)" is stale since `d66f760`; update it to `judge_probe.py` and `suite_data/` when the story closes.
2. `LICENSE-DATA:32,34`: the quality row-file entries do not carve out `predicted_label` inline, while the roster entry (`:39`) does carve out its non-granted part; add "(model-output fields excepted, see 1.3)" for symmetry with "Each path in this list is covered" (`:22`).
3. `src/wave_local_ai_v2/__init__.py:66` `FIXED_PROMPT` is a hand-written string published as the runtime rows' `prompt` (CC-BY) while its source is MIT, the same dual-terms gap Q43 closed for items; not an "item literal", so outside this story; owner call.
4. Scope goes beyond the story's enumerated list (`comparisons/`, `use_case_coverage.json`, and `LICENSE-DATA:30` pre-granting "any record a project command publishes into it"); defensible, but 1.3's exclusion covers row fields only, not a future non-row file holding model outputs.
5. `LICENSE-DATA:79-81` says every published item declares `provenance` `hand_written`; the superseded schema-1 quality rows carry no `provenance` field. The test's item-module detector only catches list literals bound to `*ITEMS` names.

## Round 2

VERDICT: PASS

Scope: the three `LICENSE-DATA` edits from round 1's non-blocking 2, 4 and 5.

- Row-file entries (`LICENSE-DATA:32,34`) now carve out the model-output fields inline ("see 1.3"); the `aidd_docs/results/` entry (`:30`) excludes model-generated content. Nothing grants what 1.2/1.3 name as not granted.
- 1.3 now governs model-generated content anywhere in a covered path, "even where the file or directory holding it is covered", and 1.2 points to it. It still names `predicted_label` as a separate part, states the declaration as unverified and cites the spike, so acceptance bullet 3 holds. No acceptance line is contradicted.
- Section 2's new statement is true: every current quality row is `hand_written` with no `source`. All 40 schema-1 rows' `item_id` and `prompt` match a published suite-definition item (0 missing, 0 differing).
- The legal text after the marker still hashes to `9ba9550ad48438d0836ddab3da480b3b69ffa0aac7b7878b5a0039e7ab429411`.
- `uv run pytest -q`: `1541 passed, 2 warnings in 48.75s`; `ruff check`: all checks passed.

Blocking findings: none.

Non-blocking: 1.3's second paragraph has one unwrapped long line ("author's declaration ... against each model's"), cosmetic. Round 1 non-blocking 1 (stale story parenthetical) and 3 (`FIXED_PROMPT`) stay open, as owner calls.
