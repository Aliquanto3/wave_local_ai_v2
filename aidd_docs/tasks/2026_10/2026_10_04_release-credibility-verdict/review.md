# Review: Each release reads its credibility verdict from its records

## Round 1

VERDICT: CHANGES-REQUIRED

Evidence: `timeout 900 uv run pytest -q` => `3043 passed, 20 skipped, 2 warnings in 209.42s`, coverage 98.54% (`client_sessions.py` not listed under skip-covered, so 100%). `ruff check`, `ruff format --check`, `mypy src/ scripts/` clean; detect-secrets on the six changed files exit 0.

Acceptance, one by one:
- Verdict per dated release with the four counts; `unreleased` excluded; correction at its own append position; block kept once reached: `release_verdicts` (`client_sessions.py` ~672-705). Proved by `test_an_unreleased_record_belongs_to_no_release`, `test_a_corrected_record_is_read_as_its_correction`, `test_a_correction_moving_a_session_to_another_release_moves_its_count`, `test_a_correction_never_removes_a_block[*]`.
- Qualification (complete, external, no sustained blocking claim; `other` alone qualifies; repeats count): `_qualifies`. Proved by the incomplete, internal, one-client-three-times, backfilled and `other` tests.
- `validated` / `not yet validated (n of 3)`, no clock: `test_two_qualifying_sessions_...`, `test_the_verdict_reads_no_clock[2026-10-04|2031-01-01]`, `test_shifting_every_date_by_the_same_years_...`. Code reads no `date.today`.
- `blocked` naming session and claim, permanent, incomplete/backfilled never shield, internal neither counts nor blocks, revocation by append order (earlier session date included): `test_a_block_appended_after_validation_revokes_it_whatever_its_date`, `test_an_incomplete_or_backfilled_session_still_blocks`, `test_a_block_names_every_blocking_claim_of_its_session`, `test_a_correction_adding_a_block_after_validation_revokes_it`.
- Dismissals counted and reported: `test_a_dismissed_session_counts_and_is_reported_as_a_dismissal`.
- One verdict line per dated section, push test fails on disagree/missing/doubled naming the release, check prints the line, module documents the three forms, 0.1.0 and 0.2.0 gain lines: `changelog_verdict_mismatches`, `Verdict` docstring, `test_the_committed_changelog_carries_the_checks_verdict_for_every_release`, `test_a_planted_changelog_line_that_is_wrong_fails_naming_the_release[*]`, `test_the_command_prints_the_expected_line_for_each_release`. Zero records => both lines read `not yet validated (0 of 3 ...)` (evidence file and `test_no_record_reads_not_yet_validated_zero_of_three_for_every_release`). `test_citation.py` date checks and the archive tests pass (headings untouched; `CHANGELOG.md` is only a clone-only name in `assemble_release_archive.py`).
- Procedure step and two release-cut edits: `docs/client-session-record.md` step 6 added, step 7 renumbered with the step-5 back-reference updated to "step 7"; `CONTRIBUTING.md` steps 2 and 3 added, 4-5 renumbered. No elapsed-time step.

Blocking findings:
1. `docs/client-session-record.md:199-209`: the acceptance requires the fixed line form "documented in the check's module and in the procedure"; the procedure only says to copy the printed line. Fix: state the three forms there (as in the `Verdict` docstring), including `blocked by session-<id> on <claim>[ and <claim>][, validation revoked]` and the count suffix.

Non-blocking findings:
1. `CHANGELOG.md [Unreleased]` carries no entry for credible orders 1, 2 or 3, although `phase-2.md` lists "Unreleased entry"; CONTRIBUTING step 2 builds release notes from `[Unreleased]`, so the client-session record and verdict would ship unannounced. Add one entry covering the three orders.
2. A correction that blocks is named by the correction's own `session_id`, not the chain's first session; acceptable under "naming the session", but a reader may expect the original id.
3. Revocation reads only the state just before the blocking record: validated, then a correction dropping to 2 of 3, then a block, reads `blocked` with no "validation revoked". Matches the literal Q64 text; worth one line in the docstring.
4. `test_the_verdict_reads_no_clock` patches `client_sessions.date` only; a `datetime.now()` call would escape it. The years-shift test covers the date-difference half.
5. `aidd-dev:05-review` applied as its three axes (code, behavior vs plan, relevancy) rather than invoked, to keep `review.md` the only file created.

## Round 2

VERDICT: PASS

Evidence: `timeout 900 uv run pytest -q` => `3047 passed, 20 skipped, 2 warnings in 209.14s`, coverage 98.54%; `ruff check`, `ruff format --check`, `mypy src/ scripts/` clean; detect-secrets on the changed files exit 0.

Round 1 findings, verified:
- Blocking 1 fixed: `docs/client-session-record.md` step 6 states the three forms and the `<counts>` suffix. `test_the_module_and_the_procedure_state_the_same_verdict_forms` asserts every `VERDICT_FORMS` entry appears in both the `Verdict` docstring and the procedure, and `test_every_printed_line_has_one_of_the_documented_forms[not-yet|validated|blocked]` matches printed lines against them.
- Non-blocking 1 fixed: `CHANGELOG.md [Unreleased]` has one entry covering credible orders 1-3. It accurately describes the record, the check, sustained challenges and the verdict line.
- Non-blocking 2 and 3 fixed: the docstring and the procedure both say a block added by a correction names the correction's `session_id`, and they state Q64's literal revocation reading.
- Non-blocking 4 fixed: `test_the_verdict_reads_no_clock` also freezes `datetime.date` and `datetime.datetime` (restored by monkeypatch).

Non-blocking findings:
1. `VERDICT_FORMS` is read only by tests, and the printed-line regex in `test_every_printed_line_has_one_of_the_documented_forms` is hand-written, not derived from it. The "revoked" variant is not among that test's parameters, though other tests cover it.
