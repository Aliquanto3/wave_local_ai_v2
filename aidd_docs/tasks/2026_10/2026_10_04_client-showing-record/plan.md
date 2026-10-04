---
objective: "One tracked, append-only `aidd_docs/results/client-sessions.jsonl` holds one record per client showing, a check refuses every malformed record naming its line and field and reports incomplete ones, a test proves the committed versions only ever append, and a written same-day procedure takes the consultant from the end of a session to a committed record, the record published under CC-BY 4.0 like the rest of the results."
status: implemented
---

# Plan: Each client showing is logged as a record someone who was not there can read back

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | The reception record (`client-sessions.jsonl`, shipped empty), its format and check (`client_sessions.py`, command `wave-local-ai-v2-client-sessions`), the append-only history test, the procedure under `docs/`, and the licence scope |
| **Source** | `aidd_docs/backlog/stories/each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back.md` (owner decision D5 of the night run: implement; no fabricated session record committed) |

## Phases

| #   | Phase                                                         | File                         |
| --- | ------------------------------------------------------------- | ---------------------------- |
| 1   | The record file, its tracking and the append-only history test | [`phase-1.md`](./phase-1.md) |
| 2   | The record format, its check, its refusals and its command     | [`phase-2.md`](./phase-2.md) |
| 3   | The procedure, the walk scenario and the licence scope          | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Keys, in the documented order: `record_format` (`"1"`), `session_id` (`session-` + 12 hex), `client_id` (`client-` + 12 hex), `session_date`, `logged_date`, `release`, `release_commit`, `audience` (`external`/`internal`), `shown`, `outcome`, `backfilled`, `corrects`, `challenges`; per challenge `role`, `criterion`, `claims`, `evidence_offered`, `resolving_evidence`, `follow_up`. | `session_id` leads every line, so the secrets scanner's id heuristic (a `_id` key before the value on the line) covers the 12-hex ids and the 40-hex commit after them; the order is also the reading order a reader who was not there needs. |
| `challenges` (the list itself) is a required identity/attribution field: absent is refused, `[]` is stated empty. | The acceptance puts exactly the three PRD content fields in the incomplete class and requires every format field to sit in exactly one class; the list is what a `challenged` outcome is checked against. |
| `release` names a version exactly as a dated `## [x.y.z] - YYYY-MM-DD` heading of `CHANGELOG.md` carries it, or `unreleased`. `release_commit` is required (40 lowercase hex, `git cat-file -e <sha>^{commit}` in the changelog's repository) with `unreleased` and refused with a dated release. | One meaning per field: a dated release is identified by its heading; a commit beside it would be a second identity that could disagree. |
| The "session before its release" refusal applies to dated releases only. | An `unreleased` record has no release date; its commit date is not what the acceptance names. |
| A content field (`role`, `criterion`, `evidence_offered`) absent and one stated as an empty string are both reported incomplete, with different reasons (`absent` / `stated empty`). | Both leave the PRD's question unanswered, and the report still keeps them apart. |
| `resolving_evidence` is a string; `""` states that none resolved the challenge. `null` is refused. | One representation for "none", distinguishable from the key being left out. |
| Unknown keys are refused at record and challenge level. | "The record has no field for" a client name or deal outcome is then enforced, not only documented. |
| Exit codes: `0` no refusal (incomplete records reported), `1` any refusal, `2` the record or changelog file cannot be read. | Matches the project's other checks (`composition_check`). |
| The append-only walk is a module function (`append_only_violations`) used by the repo test; shallow history raises a skip outside CI and is a violation with `CI` set. | Keeps the logic under coverage and tests it on throwaway repositories, including a shallow clone. |
| The secrets-scan test uses `detect_secrets`' Python API with the baseline's own plugin and filter settings, plus a positive control that a bare 40-hex value under a non-id key is flagged. | Running the pre-commit hook module can rewrite `.secrets.baseline`; the control stops the test passing vacuously. |
| The walk by someone other than the author is prepared as a written scenario in `evidence/walk-scenario.md`; the walk itself is the orchestrator's (D5). | The author cannot produce that evidence. |
| `scripts/assemble_release_archive.py` gains one `PATHS_NOT_SHIPPED` entry for the record (not in the story's change list). | The release archive ships `LICENSE-DATA` and refuses any path it names that the archive does not hold; once LICENSE-DATA names the record (acceptance), the archive tests fail without it. The record is appended after a release ships, so the repository, not a frozen archive, holds its current version. |

### Walk corrections

The independent walk (`evidence/independent-walk/walk-report.md`) passed the check (`PASS: 1 record(s), 1 incomplete field(s)`) and kept the deal remark out. Each unclear step it found, and its fix in `docs/client-session-record.md`:

| # | Walker point | Fix |
| - | ------------ | --- |
| 1 | Step 4's command takes no path; `--sessions` undocumented | Step 4 names the default file and documents `--sessions <scratch file>` for a draft, adding that a draft alone misses the cross-record checks, so the real file is checked again after appending. |
| 2 | "It prints every record it read back" overstates the output | Step 4 says it prints one summary line per accepted record (and lists what that line holds), never the free text; step 5 re-reads every free-text field of the line itself. |
| 3 | Who checks the criterion against the claims | Step 3 says the check cannot and prints nothing about it; a person does (the first real session's read-back and the commit's reviewer), and a mismatch is corrected by an appended correction. |
| 4 | What `claims` holds when the criterion is left out | Step 3: still required and non-empty; name the claims the challenger's words bore on, `other` only when they bore on none of the three. |
| 5 | `evidence_offered` when none was given | A known negative fact is written (`"none offered"`, complete); only an unknown fact is left out (incomplete); `""` is reported as stated empty (incomplete). |
| 6 | `backfilled` readable two ways for a session logged later | `true` only for a showing held before the record file was first committed (with the `git log --diff-filter=A` command that prints that date); `false` for every later session, however late. |
| 7 | No rule for logging after the same day | New "Logging late" section: log as soon as possible, same steps, `backfilled: false`, the date gap is in the record, unknown facts left out. |
| 8 | Whether `shown` names the release again | The `shown` row says it is optional; `release` is the field that counts. |

Review fixes, round 1: `append_only_violations` now fails when `git log` exits non-zero (test `test_a_history_git_cannot_read_fails_rather_than_passing`); step 2 says `release_commit` must exist in the clone the check runs in, CI included; the archive's `PATHS_NOT_SHIPPED` reason sends readers to `main` for the current record; the `NOTICE.md` wrap is fixed.
