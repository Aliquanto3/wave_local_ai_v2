# Review: A challenge no named evidence resolved is sustained and points at its follow-up item

- **Verdict**: approve
- **Diff**: `e1e768f...working tree` (uncommitted: `client_sessions.py`, `test_client_sessions.py`, `docs/client-session-record.md`, `aidd_docs/memory/cli.md`)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_04
- **Findings**: 0 critical, 0 warning, 5 minor

## Phases

### Phase 1 — The derivation, the follow-up refusals and the procedure step

- [x] Sustained derived, never typed: `is_sustained` is the only decider (null, `""`, whitespace) — `src/wave_local_ai_v2/client_sessions.py:188`; no sustained/resolved key in `CHALLENGE_KEYS` (unknown keys refused); read-back count `client_sessions.py:490`; `test_no_named_resolving_evidence_reads_as_sustained`, `test_named_resolving_evidence_reads_as_resolved`
- [x] "Within that session" and post-session evidence goes to the item — `docs/client-session-record.md:116-121`
- [x] `null` now sustained, key still required; order 1's acceptance ("must be present and may be stated empty") still holds: absent refused (`REQUIRED_CHALLENGE_FIELDS`, order-1 planted test kept), changed test now uses `resolving_evidence=3` — `tests/test_client_sessions.py:250`
- [x] Refusals naming session and challenge: missing / empty / null follow-up, outside the folders, bare folder, missing file, type mismatch both ways, no frontmatter, `..`, POSIX and drive absolute, backslash — `client_sessions.py:209,367,389`; `test_a_sustained_challenge_without_a_valid_follow_up_is_refused` (16 cases); defect and spike pass — `test_a_sustained_challenge_pointing_at_a_matching_item_passes`
- [x] Frontmatter read with the stdlib — `client_sessions.py:195`; `test_the_frontmatter_type_is_read_with_the_standard_library`
- [x] Item carries client id and a chain session id, checked after the whole file is read — `client_sessions.py:417,545`; no-session / no-client cases, `test_an_item_naming_only_the_replaced_record_serves_its_correction`, `test_an_item_naming_an_unrelated_session_is_refused`, `test_a_correction_loop_through_a_duplicate_id_terminates`
- [x] Item never names the client organisation nor carries client material — `docs/client-session-record.md:133-135`
- [x] Committed-record test runs the refusals on every push — `check_file` wires `repo_item_reader` (`client_sessions.py:559`), run by `test_the_committed_record_file_passes_the_check`, CI `ci.yml` pytest on push to main and PRs; rename fails — `test_a_cited_item_renamed_after_commit_fails_the_committed_record_check`; procedure commits record and item together — `docs/client-session-record.md` step 6
- [x] One item serves several challenges; resolved challenge may link an item and stays resolved — `test_two_challenges_may_share_one_item`, `test_a_resolved_challenge_may_link_an_item_and_stays_resolved`
- [x] Path frozen; cancelled / done item leaves the challenge sustained; path change via correction — `docs/client-session-record.md:147-154`; `test_a_closed_item_leaves_its_challenge_sustained`
- [x] Kind recorded by folder (defect = shown wrong, spike = unresolved), procedure step added — `docs/client-session-record.md:123-130`; folder/type check `FOLLOW_UP_FOLDERS`
- [x] Fix not built — no fix code in the diff

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 minor | code | 1 | `client_sessions.py:195-206` | Unclosed `---` block reads a body line `type: defect` as frontmatter (test codifies `"---\ntype: spike\n"` -> `spike`) | Return None when no closing `---` is found; flip that test case |
| 🟢 minor | code | 1 | `client_sessions.py:197` | A UTF-8 BOM item reads as "frontmatter type None": fail-safe but misleading | Strip a leading `﻿` before splitting |
| 🟢 minor | fit | 1 | `client_sessions.py:417` | Chain check also accepts an earlier record whose item names only its later correction's id: broader than "a record of the chain that cites it"; fail-open only within one chain | Accept as is, or restrict to ids of chain records citing the same path |
| 🟢 minor | fit | 1 | `client_sessions.py:171` | Items read from the working tree: right (CI checkout = commit; local check precedes commit per steps 5-6), but on Windows a mis-cased path passes locally; ubuntu CI leg catches it | None needed; note only |
| 🟢 minor | fit | 1 | `client_sessions.py:367` | `follow_up` on a resolved challenge held to the full rules: stricter than the literal "accepts", consistent with Q65 linking, plan decision recorded | Keep; reasonable, not scope creep |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 100% (11/11) |
| Files checked | src/wave_local_ai_v2/client_sessions.py, tests/test_client_sessions.py, docs/client-session-record.md, aidd_docs/memory/cli.md |
| Unchecked     | none |
| Unplanned     | none |

Gates: `uv run pytest -q` => `3011 passed, 20 skipped, 2 warnings in 207.47s`, total coverage 98.53% (client_sessions.py 99.7% lines); `ruff check` => All checks passed; `ruff format --check` => 801 files already formatted; `mypy src/ scripts/` => no issues in 75 source files.
