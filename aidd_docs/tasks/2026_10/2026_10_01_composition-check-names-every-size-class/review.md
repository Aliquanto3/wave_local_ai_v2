# Review: the composition check names every size class and refuses an unlabelled single-family one

## Round 1

VERDICT: PASS

Reviewed against the PR-head story text on `docs/slice-remaining-epics` (owner answers Q10 (a), Q11 (a), Q12 (a)), the uncommitted working tree on `feat/ready-stories-unattended`.

### Gates

- `uv run pytest -q`: `1776 passed, 2 warnings in 89.86s`; `Required test coverage of 95% reached. Total coverage: 97.88%`. `composition_check.py` and `quality_rows.py` at 100% lines and branches.
- `uv run ruff check .`: `All checks passed!`. `uv run ruff format --check .`: `590 files already formatted`. `uv run mypy src/ scripts/`: `Success: no issues found in 55 source files`.

### Acceptance, one by one

1. Four-value vocabulary, banded on total parameters at 1B/3B/6B, edges held as configuration and stated as revisable: met. `roster.SIZE_CLASS_BANDS` / `SIZE_CLASSES` / `size_class_for` (`src/wave_local_ai_v2/roster.py:101-124`). The check reads the table, never literal numbers. Tests: `test_size_class_for_bands_total_parameters_at_the_q10_edges`, `test_the_vocabulary_is_the_bands_names_in_order`.
2. Bytes on disk recorded, published beside the class, never banded and never read by the class-agreement check: met. `composition_check._entry_report` bands on `total_params` only (`composition_check.py:105-114`). Test: `test_bytes_on_disk_alone_suggesting_another_class_is_not_named`.
3. Every entry declares `size_class`, total parameters and bytes on disk, and the four shipped entries carry all three: met. The fields are optional at load (same seam as `family`/`licence`), and the check names any entry that omits one. Shipped values: the dense byte counts match `docs/setup.md:251-253`, and the totals are summed off the GGUF tensors (`evidence/gguf-figures.txt`). Test: `test_each_shipped_entry_carries_its_class_and_the_figures_read_off_its_file`.
4. One declaration per class, as data: met. The top-level `size_classes` block in `aidd_docs/roster/models.json` is shape-checked by `roster._parse_size_classes`. A class that holds entries but has no declaration is named. Tests: `test_a_size_class_declaration_loads`, `test_load_roster_refuses_a_malformed_declaration_naming_its_class`, `test_a_class_with_entries_and_no_declaration_fails`.
5. The per-class report and every listed failure: met. Each failure has its own test in `tests/test_composition_check.py`: two families pass; a labelled ladder passes; an unlabelled single-family class fails naming the class; no MoE and no reason fails, and recording the reason passes; an entry with no family, no class, no total, no bytes or no licence is named. Class/total disagreement is tested on both sides of each of the 1B, 3B and 6B edges (`test_a_class_disagreeing_with_total_params_is_named_at_each_edge`, `test_a_class_agreeing_with_total_params_is_not_named`).
6. Calibration: met. On the shipped roster the check reports four classes, each `families: qwen`, and exits 1 naming all four as unlabelled (`test_the_shipped_roster_reports_four_single_family_classes_and_fails`). It also names the three dense classes for "no MoE represented and no reason recorded". That is a legitimate failure under condition 5: the shipped roster records `moe_sought: false` and no reason. No class is labelled.
7. The flagship resolves its family through the fallback, with no exception: met. The flagship entry still has no `family` field, and the roster's `REQUIRED_FIELDS` is untouched. The calibration test asserts `flagship.family == "qwen"` and that no entry-level failure is raised.
8. `family` and `size_class` on quality rows, additive, with the schema bumped and no back-fill: met with a wording deviation (see non-blocking 1). `row_contract.SCHEMA_VERSION = "19"`, and a row below "19" is excused by `_predates_subject_composition`. Both quality writers stamp the fields (`quality_cli.py:1199`, `judge_probe.py:886`). Tests: `test_a_quality_row_without_family_or_size_class_is_refused_at_19`, `test_an_earlier_version_row_without_either_field_still_validates`, `test_every_row_names_its_subjects_family_and_size_class`.
9. README composition section produced from the check's output: met. It is held to the output byte for byte by `test_the_readme_quotes_the_check_output_on_the_shipped_roster`, and it states four unlabelled single-family classes.
10. A documented pre-publication step that is not in the merge gate: met. See the README section "When to run it" and `aidd_docs/memory/cli.md`. `.pre-commit-config.yaml` and `ci.yml` are untouched.

### Points judged specifically

- **Candidate-gate regression (efd5f47): none.** Parsing `candidate-record-pass.jsonl`'s `entry` with the new `roster.parse_entry` (scratch script outside the repo) loads `qwen3-0.6b-q8` with `size_class None bytes None total None`. The new fields are optional at load, so a pass record still loads.
- **roster_version 4, bundle and fiche: unaffected.** The fiche projection reads entry id, sha256 and quant only, not the new fields. The bundle export documents the three new roster columns in `ROSTER_ENTRY_FIELDS` and the two new quality columns in `_QUALITY_FIELDS`. `tests/test_reference_bundle.py` and every committed-store validation test pass. The rows of the committed stores are below "19" and are excused, never back-filled.
- **Cloud rows: subject family, `size_class` null.** Taken literally, "of the entry it cites" would stamp `qwen` on a Mistral or Google row, because a cloud row cites the local entry it ran beside. That reading contradicts Q11 (one meaning of `family`, which the judge-independence guard reads) and the epic's exclusion of cloud subjects. The implementation follows the intent; the acceptance wording needs correcting (non-blocking 1).
- **Extra failures.**
  - "Class with entries and no declaration": required by condition 4.
  - "MoE entry omitted from, or wrongly named in, the declaration": follows from "which entry represents it if one was found".
  - "Ladder label on a multi-family class": a mild addition beyond the story. It contradicts the literal "a class spanning two families passes" only when the label is itself false. It cannot fire on any passing case the story lists, or on the shipped roster.
- **Calibration:** matches the story. See condition 6.

### Non-blocking findings

1. `aidd_docs/backlog/stories/the-composition-check-...md` (PR-head), acceptance bullet 8: the words "of the entry it cites" should read "of the row's subject (the local entry for a local row; the cloud model's own family and a null class for a cloud row)". This is a backlog wording fix, not a code change.
2. `src/wave_local_ai_v2/candidate_gate.py:~324` `_roster_entry`: the pass entry does not carry `size_class`, `bytes_on_disk` or `architecture.total_params`, although the gate already observes `bytes` and `total_params`. A gate-passed entry pasted into the roster would therefore be named by the composition check. Fix this before orders 5 to 8 add entries.
3. `src/wave_local_ai_v2/composition_check.py:144-151`: the "labelled ladder spans two or more families" failure goes beyond the listed failures. Keep it, but state it in the story so the acceptance and the code agree.
4. `tests/test_service.py`: `test_no_response_body_carries_both_a_quality_and_a_runtime_field` now subtracts every roster-entry identity key, where only `family` collides. That is slightly broader than needed, but harmless.
5. `aidd_docs/roster/models.json` declares `~8B-and-up` with `moe_sought: true`, and the check never reads `moe_sought`. The value is reported only; whether "sought" is accurate for the flagship is order 8's to confirm.

## Round 2

VERDICT: PASS

Scope: the post-review fix to the candidate gate (round 1, non-blocking finding 2). After this fix the pass entry carries `size_class`, `bytes_on_disk` and `architecture.total_params`.

- Correct. `candidate_gate._entry_block` (`src/wave_local_ai_v2/candidate_gate.py:297-331`) writes the class as `roster.size_class_for(total_params)`, so it agrees with the composition check's band by construction. Its key order matches `models.json` (`size_class`, `bytes_on_disk`, `family`). `run_gate` passes `facts.total_params` (summed off the GGUF tensors) and `size`, the hub size that `_step_download` has already checked equals the file's `st_size` (`:489-494`).
- Unreadable figures cannot crash the gate. A size missing from the hub listing is refused at `STEP_DISK` (`:463`). A truncated or non-GGUF header raises `GgufError`, which is refused at `STEP_DOWNLOAD` (`:499-501`). Both refusals happen before the entry is built.
- One theoretical edge remains. A GGUF with zero tensors gives `total_params == 0`, which `roster.parse_entry` refuses at `:684`, and that `RosterError` is not caught. In practice the load step refuses such a file first. A one-line guard in the download step would close it (non-blocking).
- The pass entry still loads. The committed `candidate-record-pass.jsonl` entry parses with the new `roster.parse_entry` (`size_class None bytes None total None`, all optional). `test_a_passing_candidate_carries_every_field_a_roster_entry_requires` asserts the three new fields on both the raw entry and the parsed entry.
- Gates. `uv run pytest -q`: `1776 passed, 2 warnings in 82.74s`, total coverage 97.88%. ruff check, ruff format and mypy are clean.
