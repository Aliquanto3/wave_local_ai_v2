# Review: The local quality path answers through the model's own chat template

- **Verdict**: changes-requested
- **Diff**: `be57dea...064b311`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_06
- **Findings**: 0 critical, 6 warning, 2 minor

## Phases

### Phase 1 — The chat call path, probed live before it is written

- [x] `evidence.md` holds verbatim `/props`, `/apply-template` and two chat responses against a named `build_info`, and states the byte-for-byte match — `evidence.md:7-14`, `:18-39`, `:30-31`, `:51-59`
- [x] The flagship answers under the switch with its `chat_template_caps`, and one translation item is recorded both ways at the 128-token cap — `evidence.md:122-145`, `:147-166`
- [x] `thinking_policy`'s two values declared once, the request argument spelled in exactly one module — `row_contract.py:84-86`, `local_client.py:75` (repo-wide `enable_thinking` grep hits `local_client` only)
- [x] The chat endpoint paired with `none` is refused, paired with the new id accepted — `tests/test_prompt_provenance.py:75-83`
- [x] Stubbed server yields content, a `finish_reason` truncation flag and both token counts; a body missing `choices` raises the named error; `disabled` sends the kwargs on both calls, `allowed` on neither — `tests/test_local_client.py:65-124`, `:171-222`, `:241`
- [x] The suite passes with no existing expectation changed by this phase — commit `8f7b823` touches only new files plus additive constants

### Phase 2 — Both local writers move onto it

- [x] Every quality row carries `thinking_policy`, both suites read `disabled`, a row without it is refused, the runtime row is unaffected — `row_contract.py:249-253`, `tests/test_quality_cli.py:1712-1727`, `tests/test_cli.py` green untouched
- [x] A stubbed local batch produces one completion per item with truncation from `finish_reason`; a malformed body surfaces `LocalRequestError` and exits 1 with one stderr line; the kwargs reach both calls — `quality_cli.py:766-790`, `tests/test_quality_cli.py:934-950`, `:702-712`, `:1730-1746`
- [x] A local row's `prompt` is the rendered string, `prompt_template_id` is not `none`, the hash equals the served template's, `prompt_capture` is `reconstructed` — `quality_cli.py:683-702`, `tests/test_quality_cli.py:895-908`, live row `e716ce86` matches `evidence.md:32-39` + `:110-113` byte for byte
- [x] The probe's local rows carry the same four call-path values and no `/completion` POST remains in `judge_probe` — `judge_probe.py:1009-1021`, `tests/test_judge_probe.py:504-511`
- [x] A local batch publishes `tokens_in_total` as the sum and a non-null rate; the cloud batch's own fields are unchanged — `quality_rows.py:44-70`, `tests/test_quality_cli.py:357-368`
- [x] Every cloud-row and runtime-row expectation still passes, and the changelog names what a local row now means — `tests/test_cli.py` untouched, `CHANGELOG.md:408-441`

### Phase 3 — Version-addressed suite snapshots, then the version bump

- [x] One file per (suite id, suite version); a re-export after a bump adds a file rather than overwriting one — `suite_snapshot.py:31-43`, `:127-136`, `tests/test_suite_snapshot.py:115-133`
- [x] Every bundle row resolves to a definition carrying its own version and prompt-set hash — `tests/test_reference_bundle.py:70-90`, both renames recorded as renames with zero byte change
- [x] Both suite modules declare the new version with a stated reason, both new snapshots carry their predecessor's prompt-set hash — `classification_suite.py:37-45`, `translation_suite.py:38-44`, `tests/test_suite_snapshot.py:126-133`
- [x] A batch at the new version yields `not_comparable`, and no published `.jsonl` byte moved — `tests/test_verdict.py:393-409`, `git diff be57dea..HEAD -- aidd_docs/results/*.jsonl` empty

### Phase 4 — The live re-run and the corrected record

- [x] The pilot batch satisfies the four Verification facts with its `tokens_out_total` behind the decision — defect `Verification` table, witness row `e716ce86`, `tokens_out_total` 40
- [x] Eight batches across four entries and two suites at the new versions; the validator exits `0`; every cited fiche is committed — re-run here: `checked 596 row(s)`, exit `0`, four cited fiches all tracked
- [x] Every published figure traces to a row, the superseded section is intact and points forward, the comparator's version mismatch is stated — all 10 scores, 8 `run_id`s and both `tokens_out_total` figures re-derived from `quality.jsonl`; `README.md:275-284`, `:531-538`
- [x] The defect reads `done` with row evidence, and exactly the two resolved tech-debt rows are closed — defect `status: done`, `tech-debt.md` two rows `closed`, the truncation row narrowed and the envelope row updated, both still `open`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | rot | 4 | `aidd_docs/results/README.md:571` | "The flagship's `fr-de-03` completion is **byte-identical** across the two runs" is contradicted by the rows it cites: the old `subject_output` is `"\n\n<think>\n\n</think>\n\nDas von Ihnen…"` and the new one `"Das von Ihnen…"`. What is byte-identical is the translated sentence, and the difference is exactly the envelope the paragraph is about — so the sentence undercuts its own evidence. | Say the translated sentence is byte-identical and that the superseded row carries the empty `<think>` envelope in front of it; the 0.4078 → 0.4205 delta is then attributable to the envelope alone, which is the claim being made. |
| 🟡 | conform | 3 | `aidd_docs/memory/cli.md:70` | Project memory still documents the export target as `aidd_docs/results/suite-definitions/<suite_id>.json`, "one file each". Both halves are now false, and this file is loaded into every session, so the next increment inherits the wrong layout. | `<suite_id>@<suite_version>.json`, one file per (suite, version), a bump adding a file beside its predecessor. |
| 🟡 | rot | 3 | `aidd_docs/results/README.md:134` | "The translation suite's first live run" cites `suite-definitions/translation-business-short-form.json`, a path this branch renamed. The record's own discipline is that a reader chasing an old citation still finds the definition; this pointer now resolves to nothing. | Repoint to `translation-business-short-form@1.json`, the file that section's `suite_version` `"1"` rows resolve to. No number changes. |
| 🟡 | code | 2 | `tests/test_judge_probe.py:126` | `_fake_render` is used only by the stub, never in an assertion: no test reads the probe row's `prompt` or its `thinking_policy`. `judge_probe._run_local_batch` could stop passing `prompt=rendered_prompt` — falling back to `_build_row`'s `item["prompt"]` default — and the whole suite would stay green, on the exact behavior this increment exists to create, in the second of the two writers. | Assert in `test_the_local_and_cloud_rows_record_their_own_call_paths` that each local row's `prompt` equals `_fake_render(item["prompt"])` and that every row carries `thinking_policy` `"disabled"`. |
| 🟡 | code | 2 | `tests/test_cli.py:94` | `QUALITY_ONLY_FIELDS` did not gain `thinking_policy`. Its own comment names the set as the guard that stops a quality field reaching a runtime row (`architecture.md`'s "the two are never merged"), and `validate_row` checks only for *missing* fields, never extra ones — so nothing else would catch the leak. | Add `"thinking_policy"` to the set. |
| 🟡 | conform | 3 | `CHANGELOG.md:405` | No entry for the two suite-version bumps (classification `"2"`→`"3"`, translation `"1"`→`"2"`) or for the `<suite_id>@<suite_version>.json` snapshot addressing. The bump is the mechanism that makes every previously published local number `not_comparable`, and the rename moves a path the changelog itself documented at `:269`; a reader of the changelog alone learns neither. | One `### Changed` bullet: both versions bumped with `prompt_set_hash` unmoved, why that supersedes rather than edits, and the version-addressed snapshot filenames with the two `git mv`s. |
| 🟢 | code | 1 | `src/wave_local_ai_v2/row_contract.py:86` | `THINKING_POLICIES` is declared as the field's vocabulary but gates nothing: `validate_row` checks `ttft_source` against its valid set yet accepts any string for `thinking_policy`. Only `local_client._thinking_kwargs` rejects an unknown value, so a cloud-only batch publishes whatever the suite declared, unvalidated. | Validate `row["thinking_policy"] in THINKING_POLICIES` in `validate_row`'s quality branch, beside the `ttft_source` check. |
| 🟢 | fit | 4 | `aidd_docs/tasks/2026_09/2026_09_06_local-chat-templated-quality-path/evidence.md:178` | Phase 4's architecture projection promised the run log appended here, and its task 2.2 asks for `run_id`, `fiche_hash`, wall clock and headline score per batch. `evidence.md` still ends at phase 1's probe; the README carries `run_id`s and scores but no per-batch wall clock and no per-batch fiche mapping, so the eight runs' cost is unrecorded. | Append a phase 4 section to `evidence.md`: one row per batch with `run_id`, `fiche_hash`, wall clock and headline score. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (20/20)                                      |
| Files checked | `local_client.py`, `quality_cli.py`, `judge_probe.py`, `quality_rows.py`, `row_contract.py`, `prompt_provenance.py`, `settings.py`, `suite_snapshot.py`, `classification_suite.py`, `translation_suite.py`, `tests/test_local_client.py`, `tests/test_quality_cli.py`, `tests/test_judge_probe.py`, `tests/test_suite_snapshot.py`, `tests/test_reference_bundle.py`, `tests/test_verdict.py`, `tests/test_row_contract.py`, `tests/test_prompt_provenance.py`, `tests/test_results.py`, `tests/test_translation_suite.py`, `.pre-commit-config.yaml`, `CHANGELOG.md`, `aidd_docs/results/README.md`, `aidd_docs/backlog/tech-debt.md`, `aidd_docs/memory/architecture.md`, `aidd_docs/results/suite-definitions/*.json` |
| Unchecked     | none                                              |
| Unplanned     | `.pre-commit-config.yaml:45` widens the `detect-secrets --exclude-files` class to `[a-z0-9@-]+` (forced by the rename, named in no criterion; probed — it adds exactly `@` to the class and skips nothing a `[a-z0-9-]+` name did not already skip, the exclusion being directory-scoped by design in both versions); `aidd_docs/memory/architecture.md:96` records the filename/pattern coupling that caused it |
