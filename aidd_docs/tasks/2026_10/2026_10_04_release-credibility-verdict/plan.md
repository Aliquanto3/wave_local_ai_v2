---
objective: "Every dated release in `CHANGELOG.md` carries one `Credibility:` line that the client-session check computes from the committed record alone (validated, not yet validated (n of 3) or blocked, with qualifying count, distinct clients, backfilled and dismissals), a test on every push fails when a line disagrees, is missing or is doubled, and the record procedure and the release cut both write that line."
status: implemented
---

# Plan: Each release reads its credibility verdict from its records, in its changelog entry

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | The verdict computation in `client_sessions.py`, its planted-record tests, the verdict line in each dated `CHANGELOG.md` section with its agreement test, one procedure step, two release-cut edits |
| **Source** | `aidd_docs/backlog/stories/each-release-reads-its-credibility-verdict-from-its-records-in-its-changelog-entry.md` (credible epic order 3, owner decision D5; builds on order 1 `e1e768f` and order 2 `76caf9f`) |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | The verdict computation and its planted-record tests | [`phase-1.md`](./phase-1.md) |
| 2   | The changelog lines, their agreement test, the procedure step and the release-cut edits | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The verdict is computed over the check's accepted records (`CheckReport.records`), never a second reader; `SessionRecord` gains `client_id`, `complete` and `blocking_claims`. | One record, one check (order 1). A refused line already fails the check, so it is never silently counted. |
| Records are replayed in append (line) order; a correction replaces its chain's current record at its own position; a release's block is sticky once any replay state reached it. | Acceptance: corrections take their own position; Q123 (a) and Q64 permanence. |
| `blocked` names the first blocking session in append order and its blocking claims; later blocks do not change the line. | "Permanently for that release": the line anchors on the event that blocked it. |
| Revocation: stated when the replay state just before the first blocking record read `validated` for that release. | Q64: append order, not session dates. |
| Fixed forms: `Credibility: validated (N of 3 qualifying sessions, D distinct client[s], B backfilled, M dismissal[s])`, `Credibility: not yet validated (...same counts...)`, `Credibility: blocked by session-<id> on <claim>[ and <claim>][, validation revoked] (...same counts...)`. More than three qualifying sessions print as `N of 3`. | The story's example form; every verdict carries the four counts the acceptance names. |
| Counts are over the final replay state's qualifying sessions of the release; `blocked` still prints them. | Acceptance "each with the number of qualifying sessions out of 3 ...". |
| The verdict line sits on its own line directly under its dated heading; the agreement test reads every line starting `Credibility:` between that heading and the next `## ` heading. | Fixed, greppable place; two lines in a section are detectable. |
| The CLI prints a `Verdicts` block with the expected line per dated release; its exit code is unchanged. The agreement is enforced by `tests/test_client_sessions.py`, which runs in CI's `pytest` on every push. | Keeps order 1's exit contract; no CI workflow change needed, so `release-build`/`release-publish` gates, permissions and determinism are untouched. |
| No gate on the release archive or tag jobs. | The acceptance asks for a push test and a release-PR step, not a tag gate; adding one would widen scope. |
| Skills `aidd-dev:01-plan` / `02-implement` / `03-assert` applied as their layout and gates rather than invoked interactively. | Orchestrator instruction: code only, small pieces, fast. |
| Review round 1: the three forms are stated in the procedure as in `Verdict`'s docstring, both checked against `VERDICT_FORMS` by a test; one `[Unreleased]` entry covers credible orders 1 to 3; the docstring states that a correction's block names the correction's id and that revocation reads the state just before the blocking record; the no-clock test also freezes the `datetime` module. | `review.md` round 1 findings. |
