# Review: candidate model verification gate

- **Verdict**: approve
- **Diff**: `HEAD...working tree (uncommitted + untracked)`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_02
- **Findings**: 0 critical, 1 warning, 4 minor

## Phases

### Phase 1 — The gate, its steps and its record

- [x] Story: one candidate through seven steps cheapest first, first failure stops — `src/wave_local_ai_v2/candidate_gate.py:646-659`; tests `test_a_branch_revision_is_refused_before_the_hub_is_asked`, `test_a_licence_forbidding_published_benchmarks_refuses_before_any_download`, `test_too_little_disk_refuses_before_the_download_starts`, `test_a_missing_download_is_refused_and_nothing_is_loaded`, `test_a_control_the_template_ignores_is_refused_and_no_claim_is_recorded` (call counts asserted)
- [x] Step 1 commit sha, never a branch; file exists at it — `candidate_gate.py:387-409`; `test_a_revision_or_file_the_hub_does_not_hold_is_refused`
- [x] Step 2 licence recorded as order 1's block; benchmark-publication ban refuses with clause — `candidate_gate.py:412-444`; `test_a_licence_forbidding_published_benchmarks_refuses_before_any_download`, `test_forbidding_clause_needs_benchmark_publication_and_a_prohibition`
- [x] Step 3 disk vs file size before download — `candidate_gate.py:447-462`; `test_too_little_disk_refuses_before_the_download_starts`
- [x] Step 4 sha256 lowercase hex off bytes, byte size, total params from GGUF — `candidate_gate.py:346-352,465-492,802-836`; pass test asserts sha256, bytes, total_params
- [x] Step 5 one load under `build_probe` build; failure names architecture + build — `candidate_gate.py:495-540`; `test_any_other_load_failure_is_refused_naming_architecture_and_build`
- [x] Step 6 template from `/props`, order 2's comparison reused (`local_client.verify_thinking_control`, `candidate_gate.py:562`), `allowed` exempt, `none` checked by one generation — `local_client.py:185-214`; `test_a_none_declaration_that_reasons_is_refused`, `test_an_allowed_declaration_enters_with_no_thinking_control`
- [x] Step 7 EN/FR/DE claim and source recorded — `candidate_gate.py:575-605`; `test_a_language_claim_without_a_source_or_outside_en_fr_de_is_refused`
- [x] Pass carries every roster value, parsed by the roster's own parser — `candidate_gate.py:660-670`, `roster.py:256-263`; `test_a_passing_candidate_carries_every_field_a_roster_entry_requires`
- [x] Refusal names step, evidence, date; append-only — `candidate_gate.py:655-659,674-678`; `test_a_second_run_on_the_same_candidate_appends`
- [x] Gate never writes `models.json` — `test_the_gate_never_writes_the_roster_file`
- [x] Unloadable architecture recorded `deferred` naming architecture and build; no other build offered — `candidate_gate.py:529-535`; `test_an_architecture_the_build_does_not_implement_is_deferred`
- [x] Malformed declaration exits 2, nothing written — `candidate_gate.py:882-890`; `test_a_bad_declaration_exits_2_and_records_nothing`, `test_a_host_failure_mid_run_exits_2`

### Phase 2 — The real hub, download and GGUF seams

- [x] Listing yields sizes and licence id; 404 is not-found — `candidate_gate.py:699-727`; `test_the_hub_listing_reads_sizes_commit_and_licence`, `test_the_hub_answers_404_as_not_found_and_other_failures_as_aborted`
- [x] Download leaves the file and no `.part`; all HTTP stubbed — `candidate_gate.py:730-751`; `test_a_download_lands_whole_with_no_part_file`, `test_a_refused_or_broken_download_leaves_nothing`
- [x] Synthetic GGUF reports architecture, expert count, dim-sum params — `test_a_moe_file_is_classed_from_its_own_metadata`, `test_an_unreadable_gguf_header_is_named`

### Phase 3 — Docs, memory and the live pass record

- [x] Live pass record for `qwen3-0.6b-q8`: sha256 matches `models.json`, 639446688 bytes, template hash `57f1fd00...` — `evidence/candidate-record-pass.jsonl` (download seam was a no-op, `evidence/live-gate-run.md`); committed-store placement left to owner (orchestrator decision)
- [x] setup.md names the command, the declaration and the record file — `docs/setup.md` 3.2

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 warning | code | 2 | `candidate_gate.py:743-744`, `:470-471` | A gated repo fetched without `HF_TOKEN` answers 401/403 => recorded as a permanent `refused` at `download`, a host fault filed against the candidate (contradicts the plan's own exit-2 rule) | Raise `GateAborted` for 401/403, keep `DownloadError` for other statuses |
| 🟢 minor | fit | 1 | `candidate_gate.py:440` | Pass entry carries hub id `apache-2.0`, shipped entry `Apache-2.0`; entry still loads (`roster.parse_entry` verified on the live record, `licence.id` is free text with no consumer) | Owner normalizes at the reviewed copy, or map hub ids to SPDX spelling later |
| 🟢 minor | code | 1 | `candidate_gate.py:529`, `server.py:_read_stderr_tail` | `deferred` relies on "unknown model architecture" being inside the last 2000 stderr bytes; otherwise classed `refused` | Acceptable; note if a deferral is ever misfiled |
| 🟢 minor | fit | 1 | `candidate_gate.py:447-469` | Step 4 re-downloads (and step 3 demands full free space) even when the file is already on disk at the listed size | Optional skip-when-present, still hashing the bytes |
| 🟢 minor | rot | 3 | `evidence/live-gate-run.md:28` | Says the pass record is the first line of `aidd_docs/roster/candidate-records.jsonl`; it now lives in `evidence/candidate-record-pass.jsonl` | Update the sentence |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (18/18)                                      |
| Files checked | candidate_gate.py, local_client.py, roster.py, server.py (read), pyproject.toml, tests/test_candidate_gate.py, tests/test_local_client.py, docs/setup.md, aidd_docs/memory/cli.md, aidd_docs/memory/codebase-map.md, evidence/* |
| Unchecked     | none (story "Evidence it publishes" committed line: owner decision, not-applicable here) |
| Unplanned     | none (`roster.parse_entry` public wrapper serves the pass-record check) |

Gates run: `uv run pytest -q` => `1524 passed, 2 warnings in 45.40s`, coverage 97.57%; `ruff check` => All checks passed; `ruff format --check` => 553 files already formatted; `mypy src/ scripts/` => Success: no issues found in 54 source files.

## Round 2

- **Verdict**: approve (scope: post-review fix)
- 401/403 => `GateAborted` naming status + `HF_TOKEN`: listing and licence text via `_hub_get` (`candidate_gate.py:695`), download (`candidate_gate.py:756`), helper `candidate_gate.py:702-710`; tests `test_a_gated_repo_without_a_token_records_nothing[401|403]`, `test_a_gated_download_mid_run_exits_2_and_records_nothing` (exit 2, no records file, no launch). Round 1 warning closed.
- Other non-200 download still a recorded `download` refusal: `DownloadError` at `candidate_gate.py:757-758`; tests `test_a_download_that_is_not_the_listed_gguf_is_refused` (500), `test_a_refused_or_broken_download_leaves_nothing` (500).
- Wording: `plan.md:40`, `phase-3.md:16,25`, `evidence/live-gate-run.md:24-25` place the pass record at `evidence/candidate-record-pass.jsonl`. Round 1 minor closed.
- Acceptance unchanged: a 401/403 says nothing about the candidate, so exit 2 with nothing written matches "a refusal names the failed step, the evidence"; every refusal kind is still recorded.
- Gates: `uv run pytest -q` => `1527 passed, 2 warnings in 46.82s` (coverage 97.57%); ruff check clean; ruff format 554 files formatted; mypy no issues in 54 files.
- Remaining non-blocking, unchanged from Round 1: licence id casing, 2000-byte stderr tail for deferral, re-download when already on disk.
