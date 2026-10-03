---
type: story
status: ready
source: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
parent: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
order: 1
---

# Story: Each client showing is logged as a record someone who was not there can read back

**As** the consultant who has just shown benchmark results to a client or their engineer
**I want** one tracked, structured record of that session, written the same day by following a short procedure, that names the release shown, who challenged what, on which criterion and with which evidence, without naming the client
**So that** how a result was received is something a reader who was not in the room can look up, instead of an anecdote held in one person's memory

Maps to: PRD AC "Given a benchmark result shown to a client or their engineer, the consultant logs in a tracked file whether it was challenged, dismissed, or accepted, with the challenger's role, the evidence offered, and the acceptance criterion disputed"; epic Boundaries "the reception record", "backfill of earlier showings" (the marking half) and "the documented procedure"; epic Excludes "deal outcomes and business KPIs" and "client-provided material"; owner answers Q60 (one append-only structured file under `aidd_docs/results/`), Q61 (pseudonymous client id, mapping outside the repository), Q62 (the resolution names its evidence), Q63 (only showings outside the consultant's own firm count, so the record says which kind it was) and Q67 (a backfilled record is marked) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`; epic success checks 1 and 6 (the record half) and 8.

Needs: code only, plus one walk of the procedure by someone other than its author for the evidence (a separate agent session counts). No model run, API key or hardware. The record holds no real session until order 4.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- No reception record exists in any form: no file under `aidd_docs/`, `docs/`, `src/` or `tests/` records a showing, a challenge or a verdict.
- `.gitignore` ignores `aidd_docs/results/*.jsonl` and re-includes only `*-reference.jsonl` and `*-reference.schema-*.jsonl`. A JSONL record placed directly in `aidd_docs/results/` without its own negation would never be tracked, and nothing would say so. `git check-ignore` without `--no-index` reports a tracked file as not ignored even when a rule matches it.
- No result-store reader globs the top level of `aidd_docs/results/`: `bundle_export.py`, `read_model.py`, `service.py` and `tests/test_reference_bundle.py` use explicit paths or subdirectory globs, so a new top-level file breaks none of them.
- `LICENSE-DATA` covers `aidd_docs/results/` as "the published results directory ... and any record a project command publishes into it"; `tests/test_data_licence.py` checks subdirectories and `*-reference*.jsonl` files against the scope list, not other top-level files.
- The secrets hook (`.pre-commit-config.yaml`) excludes only fiches and suite-definition snapshots; `.secrets.baseline` flags high-entropy hex and base64 strings, except values its id filter recognises under keys ending in `_id`.
- Every hand-run check in the project is a `[project.scripts]` entry in `pyproject.toml` backed by a module under `src/wave_local_ai_v2/` (coverage is measured there, floor 95%).
- Releases exist to be named: `CHANGELOG.md` carries `## [0.1.0] - 2026-08-22` and `## [0.2.0] - 2026-09-22`; tags `v0.1.0` and `v0.2.0` exist.

## Acceptance

- One append-only structured file, `aidd_docs/results/client-sessions.jsonl`, holds one record per session, one JSON object per line (Q60 names JSONL or YAML; JSONL is taken because it matches the result stores beside it and appends without rewriting earlier records). The file is tracked: its own `.gitignore` negation exists, and a test fails if `git check-ignore --no-index` matches the path.
- Each record carries: a record format version; `session_id` and `client_id`, each a fixed prefix followed by 12 lowercase hexadecimal characters (no word from the client's name); the session date and the date it was logged; the release the shown results came from, either a dated section of `CHANGELOG.md` or `unreleased` together with the full 40-character lowercase hexadecimal hash of the commit the shown results were produced from, whose existence the check confirms with `git cat-file -e`; whether the audience was outside the consultant's own firm or inside it; what was shown, described in words; the outcome (`challenged`, `dismissed` or `accepted`); whether the record is backfilled; an optional `corrects` naming the session id of an earlier record this one replaces; and, per challenge raised, the challenger's role, the acceptance criterion disputed, the non-empty list of claims it bears on drawn from `fiche_disclosure`, `table_separation`, `judge_agreement` and `other`, the evidence offered in the session, the evidence presented within the session that resolved it (or an empty value when none did), and an optional follow-up item path (order 2 enforces it).
- The fields fall into two classes, and every field the format requires is in exactly one. Identity and attribution fields (format version, both ids, both dates, release, audience, what was shown, outcome, backfilled flag, and each challenge's claims list and resolving-evidence field) are refused when absent; the resolving-evidence field must be present and may be stated empty. The three content fields the PRD names (the challenger's role, the evidence offered, the criterion disputed) leave the record in the file when absent, reported as incomplete by the check; order 3 decides that an incomplete record does not count. A field stated empty (an empty challenge list on an accepted session) is distinguishable from one left out.
- A test run on every push runs the check over the committed record file and fails on any refusal; incomplete records are reported, not failed, and the empty file passes. The check refuses, naming the line and the field, a file in which: a line does not parse; a required identity or attribution field is absent; an enumerated field holds a value outside its set; two records share a session id; a `corrects` names no earlier record; a release is neither a dated section of `CHANGELOG.md` nor `unreleased` with a commit; a session is dated before the date of the release it names; a record is logged before its session date; an id does not match its pattern; a `challenged` outcome carries no challenge, or an `accepted` or `dismissed` outcome carries one.
- The claims list on a challenge must follow from the criterion named in words: the procedure says so, and the read-back of order 4 checks one against the other, because the consultant's choice of claim decides whether a release is blocked.
- A backfilled record carries `backfilled: true`; the procedure says a showing that predates the record is entered only if it can still name the release, the challenger's role, the evidence offered and the criterion disputed (Q67).
- No record carries a client organisation's name, any client-provided document, prompt or dataset, or any deal outcome: the record has no field for them, and the procedure forbids them in the free-text fields. The mapping from pseudonymous client id to client is kept outside the repository by the consultant (Q61). The procedure states that this property is checked by reading the file, because no check can detect a name typed into free text.
- Records are append-only: a committed line is never edited or removed, and a mistaken record is corrected by appending a record that `corrects` it, the earlier line staying in place. A correcting record carries its own new session id, and the check refuses a second record correcting the same id, so corrections form a chain whose last link is the record read. A test walks the file's committed versions along `git log --first-parent` of HEAD, reading blobs (`git show <rev>:<path>`, never the working tree), and fails when a version is not a line-for-line prefix of the following one. It fails rather than skips when `git rev-parse --is-shallow-repository` prints `true` and `CI` is set; the `test` job's checkout in `.github/workflows/ci.yml` sets `fetch-depth: 0`.
- A written procedure, linked from `aidd_docs/results/README.md`, takes the consultant from "the session just ended" to a committed record in a few steps short enough for the same day: which fields to fill, in a documented key order, and how to read the check's output, how ids are minted and where the client mapping is kept, that the record is written in English even when the session was held in French and quotes are translated rather than transcribed, and how a correction is appended. Its worked example lives in the procedure, not in the record file.
- `LICENSE-DATA` and `aidd_docs/results/NOTICE.md` name the record and publish it under the same CC-BY 4.0 terms as the rest of `aidd_docs/results/`; the record's path is added to the set `tests/test_data_licence.py` requires the scope to name.

## Code it changes

- `aidd_docs/results/` (the record file, empty at first), `.gitignore` (one negation), a new module under `src/wave_local_ai_v2/` holding the record format and its check with its `tests/test_<module>.py`, `pyproject.toml` (a console script for the hand-run check), `.github/workflows/ci.yml` (history depth for the append-only test), the procedure document (new, under `docs/`), `aidd_docs/results/README.md` (link), `LICENSE-DATA`, `aidd_docs/results/NOTICE.md`, `tests/test_data_licence.py` (one required path), `aidd_docs/memory/cli.md` and `aidd_docs/memory/codebase-map.md` (the new command).

## Tests it needs

- The tracked-file test with `--no-index`.
- One planted file per refusal above, each failing with the line and field named; a well-formed file passing.
- A planted record leaving out each of the three content fields, reported as incomplete and not refused; one leaving out the release, and one leaving out a challenge's claims list, both refused; a record with an explicitly empty challenge list reported as complete.
- A planted record leaving out what was shown, and one leaving out a resolving-evidence field, both refused.
- A backfilled record and an `unreleased` record read back with their markings; an `unreleased` record naming a commit that does not exist refused; a correcting record accepted, a `corrects` naming no record refused, and a second correction of the same id refused.
- The committed-record test: the shipped empty file passes, and a planted malformed committed file fails it.
- The append-only test, on a throwaway repository as `tests/test_fiche_validator.py` already builds one: a history whose second version edits an earlier line fails; one that only appends passes; a merge of two branches that each append passes along the first-parent line; a shallow clone with `CI` set fails.
- The secrets scan run over a well-formed dated record and a well-formed `unreleased` record with its full commit hash, keys in the procedure's documented order, finds nothing.

## Evidence it publishes

- The procedure walked once on a written scenario by someone other than its author, who fills a record and commits nothing; the filled record and the check's output are filed with the delivery.

## Plan shape

At most three phases: (1) the record format, the file, its tracking and the append-only test; (2) the check, its refusals and its command; (3) the procedure and the licence scope.

## Cancellation

n/a: not cancelled.
