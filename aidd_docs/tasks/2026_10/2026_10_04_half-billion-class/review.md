# Review: the ~0.5B class spans two families (round 1, 2026-10-04)

VERDICT: CHANGES-REQUIRED

Blocking findings:
1. `aidd_docs/results/quality-reference.jsonl:81-121` (and `machines/laptop-mobile-gpu/quality.jsonl:81-121`): the 41 rows carry `tree_dirty: true` beside `commit_sha` `4cf22a1`, whose `models.json` is `roster_version` 6 with no `granite-4.0-h-350m-q8` entry (`git show HEAD:aidd_docs/roster/models.json | grep -c granite` = 0), so a re-run from the row's own provenance fails at `ROSTER_ENTRY_ID` resolution. Methodology 19's epic calls a sha stamped from a modified tree "the exact artifact this epic exists to remove", and story 18 (`de62f0e`) just made every bundle row `tree_dirty: false`. Fix: commit roster, candidate record, docs, tests and `release_parquet.py` first (without the 41 rows), re-run both suites from that clean tree (model already on disk, no download), promote, merge, `--check`, and update the README's run_ids, scores, findings and its "tree_dirty: true" sentence (README lines 839-860) to the clean runs.

Acceptance:
- Shortlist, gate order, Q8_0 quant, stop rule: proven (`candidate-records.jsonl` pass record; `evidence/candidates/*.json` at the story's pins; `gate-...log` exit 0; README table).
- Entry from pass record: proven field by field (revision sha `a864f82...`, sha256 `c7d98736...c942`, 366,195,616 bytes, 340,332,224 params, dense/0 experts, family `ibm`, `~0.5B`, apache-2.0 card at the pinned sha, language claim from the base card at `3b17b71...` (checked on the hub: the GGUF card names no languages), `thinking_control: none`); `roster_version` 6 -> 7; `docs/setup.md` 3.3 pinned `hf download --revision` + `Get-FileHash ... .ToLower()`; `test_each_second_family_entry_matches_docs_setup_and_launches_as_dense`.
- LFM `client_commercial_use: false`: proven as declared (`candidates/lfm2.5-350m-q8.json`), basis stated in README; entry not reached.
- Suites to completion, rows carry entry id / `ibm` / `~0.5B` / `disabled`: proven (41 rows, 0 failures), but see blocking 1. Append-only: proven (`git diff -U0` => one hunk `@@ -80,0 +81,41 @@` per file, 0 removed lines); `merge-bundle --check` exit 0 (6 runtime, 121 quality); validate exit 0 (248 rows).
- Declaration two families + MoE search recorded: proven (`test_the_half_billion_class_records_its_moe_search_and_spans_two_families`).
- Composition check passes for `~0.5B`, README block regenerated: proven (live output == README block; `test_the_readme_quotes_the_check_output_on_the_shipped_roster` passes).
- Q126 deferred/refused handling: n/a (no refusal); spike lines: proven (granitehybrid closed by the pass record; granite, lfm2 "not reached").
- FR/DE contradiction named, claim kept: proven (verified against `subject_output`: en-fr-01/02/03/07 English, fr-de-06 "Not").

Tests: `uv run pytest -q` => `3054 passed, 20 skipped, 2 warnings in 219.86s`, coverage 98.51%; release group `29 passed`; ruff, format, mypy clean.

Non-blocking:
- `models.json` granite `server_flags.sampler` is Qwen's recommended sampler (0.6/20/1.5), not sourced from IBM's card; suites override it (rows: temperature 0), but the playground path would use it.
- `requirements.*.ram_gb` 0.37 is the weights only (labelled lower bound, honest); the Qwen 0.6B peak was 1.7x its weights, so a fit check on it is optimistic.
- No `Qwen3-0.6B` row at these suite versions exists, so the class has no same-version side-by-side yet (README states it); a follow-up re-run of `qwen3-0.6b-q8` would close the story's "So that".
- `scripts/release_parquet.py:95-97` new unit `as the metric defines` => STRING: justified (first translation rows bring `metric_params_*` into `quality_items`, `bundle_export.py:869-871`), typed honestly; `.secrets.baseline` additions are the public revision shas and the GGUF sha256 only.
- Narrowed tests (`test_roster.py` base-card language-claim exception, qwen-only thinking-control test, `test_bundle_export.py` bare `none` cell) match documented behaviour (`bundle_export.py:1207-1213`).

Reviewer note: the `aidd-dev:05-review` skill was not invoked; the three axes were reviewed directly. One accidental `git add -N .` was reverted at once with `git reset -- <paths>` (index only; working tree untouched; index now empty).

## Round 2 (2026-10-04)

VERDICT: PASS

Blocking finding 1 of round 1 is resolved:
- All 41 appended rows (`quality-reference.jsonl:81-121`, identical to `machines/laptop-mobile-gpu/quality.jsonl:81-121` and to `evidence/clean-rerun/quality.jsonl`) carry `tree_dirty: false` and `commit_sha` `8852bf0252cd90ca08a6e0473d998c282b60dc34`, run_ids `cb8cb4ff...` (20) and `be0dda5e...` (21), `roster_version` 7, fiche `5ce2bf21...`; `8852bf0`'s roster holds the entry.
- Additions only: `git diff -U0` => one hunk `@@ -80,0 +81,41 @@` per file, 0 removed lines.
- `merge-bundle --check` exit 0 (6 runtime, 121 quality); `wave-local-ai-v2-validate` with `FICHE_REGISTRY_DIR` unset, on both reference files and the machine store: `checked 248 row(s)`, exit 0.
- Reproduction claim verified: the clean rows equal the superseded dirty rows on every item's `subject_output`, `item_score`, `correct`, `predicted_label`, suite scores, intervals, language breakdowns, fiche and template hash (0 differences over 41 items).
- README lines 842-849 match the rows (accuracy 0.50 [0.30, 0.70], en 0.50 n=10, fr 0.40*, de 0.60*; chrF 0.484 [0.358, 0.614], 0.328 / 0.326 / 0.799); no stale run_id left in the README; findings unchanged and still true.
- Superseded logs labelled (`suite-classification.log`, `suite-translation.log`, `promote.log`, `merge.log` first line "SUPERSEDED: dirty-tree run ..."); `run-summary.md` and `plan.md` name the superseded pair.

Tests: `timeout 900 uv run pytest -q` => `3054 passed, 20 skipped, 2 warnings in 213.65s`, coverage 98.51%.

Non-blocking:
- `run-summary.md` says `git status --porcelain` was "empty" at the top of each log; the clean-rerun logs show two untracked (`??`) paths, no tracked change. `tree_dirty: false` is still correct (it counts tracked files only); reword to "no tracked change".
- The untracked `aidd_docs/results/fiches/5ce2bf21...json` must be committed with the rows, or the validator fails with `missing` on a clean clone.
