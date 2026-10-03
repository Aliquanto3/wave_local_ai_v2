---
type: story
status: proposed
source: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
parent: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
depends_on:
  - aidd_docs/backlog/stories/each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back.md
  - aidd_docs/backlog/stories/a-challenge-no-named-evidence-resolved-is-sustained-and-points-at-its-follow-up-item.md
order: 3
---

# Story: Each release reads its credibility verdict from its records, in its changelog entry

**As** a consultant asked whether this release has held up in front of clients
**I want** each release's verdict computed from the logged sessions and printed in that release's changelog entry, with the count and the distinct clients behind it
**So that** "credible" is a count anyone can recompute from the records, never a claim that grows true because time has passed

Maps to: PRD AC "After at least 3 such logged sessions with no sustained challenge to fiche disclosure, table separation, or judge agreement, the artifact is considered validated as credible for that release; elapsed time alone never validates it"; PRD Open Question on a product-wide check-in cadence, answered for this epic by Q68; epic Boundaries "the validation verdict per release", "backfill of earlier showings" (the counting half) and "the release-cut review"; owner answers Q63, Q64, Q66, Q67 and Q68; epic success checks 1, 3, 4, 5, 6 and 7.

Needs: code only. No model run, API key, hardware or operator.

Blocked: by Q100 (whether a dismissed session counts toward the three) in `aidd_docs/tasks/2026_10/2026_10_02_backlog-refinement/owner-questions.md`. The acceptance below is written to its recommended default, the PRD's literal text; another answer changes the dismissal bullet and its test.

Current state (verified on `main` at `c68b23e`, 2026-10-03): `CHANGELOG.md` has `## [Unreleased]`, `## [0.2.0] - 2026-09-22` and `## [0.1.0] - 2026-08-22`, none carrying a verdict line; no code or test reads `CHANGELOG.md`. `CONTRIBUTING.md`'s "Cutting a release" section has four numbered steps (confirm the version, move `[Unreleased]` into a dated section, land it by pull request, cut the annotated tag) and no count step. No verdict check exists.

## Acceptance

- A check reads the record and states, for every dated release in `CHANGELOG.md`, one verdict: `validated`, `not yet validated`, or `blocked`, each with the number of qualifying sessions out of 3, the number of distinct pseudonymous clients behind them, how many of them are backfilled and how many are dismissals (Q63, Q67). Records naming `unreleased` belong to no release's verdict. A record replaced through `corrects` is read as its latest correction.
- A session qualifies when it is complete (order 1's incomplete records never count), its audience was outside the consultant's own firm (Q63), and none of its challenges is sustained with a claims list that includes `fiche_disclosure`, `table_separation` or `judge_agreement`. A session whose only sustained challenges bear on `other` alone still qualifies (epic assumption, from the PRD's literal text). Repeat sessions with one client count separately.
- A release with at least three qualifying sessions and no blocking challenge reads `validated`. Fewer reads `not yet validated (n of 3)` however long ago the sessions were logged: the verdict reads no clock and no date difference.
- A sustained challenge whose claims include one of the three, in any session of a release whose audience was outside the firm, reads `blocked`, naming the session and the claim, permanently for that release: further clean sessions do not restore it. A session's incompleteness or backfilled mark never shields it from blocking; an internal session neither counts nor blocks. Revocation follows the order records were appended, not their session dates: when the records before the blocking one in the file already read `validated`, the verdict says that validation was revoked (Q64).
- A dismissed session, which carries no challenge, qualifies as the PRD's text has it, and the verdict states how many of the counted sessions were dismissals (Q100's default).
- Each dated release section of `CHANGELOG.md` carries one verdict line in a fixed form, documented in the check's module and in the procedure, for example `Credibility: not yet validated (1 of 3 qualifying sessions, 1 distinct client, 0 backfilled, 0 dismissals)`. A test on every push fails when any section's line differs from the check's verdict for that release, or when a dated section has none (Q66). The check prints the exact expected line for each release. The `0.1.0` and `0.2.0` sections gain their line with this story.
- The procedure from order 1 gains one step: the record's commit also updates the named release's verdict line to the line the check prints.
- `CONTRIBUTING.md`'s "Cutting a release" changes in two places: the step that dates the new section also writes its line as `not yet validated (0 of 3 ...)`; and a new step states, in the release pull request, the verdict line of the outgoing release, the one the new release supersedes, read from the check. No step validates a release by elapsed time (Q68).

## Code it changes

- The record check's module and its tests (the verdict computation and the printed line), a test reading `CHANGELOG.md`, `CHANGELOG.md` (a verdict line in each dated section), `CONTRIBUTING.md` (two edits), the procedure document (one step).

## Tests it needs

- Planted records, each changing one thing and re-running the check: two qualifying sessions read `not yet validated (2 of 3 ...)`, a third added reads `validated`; an incomplete record does not count; an internal-audience session does not count and its sustained `fiche_disclosure` challenge does not block; an `unreleased` record affects no release; three sessions from one client read three with one distinct client; a backfilled complete record counts and is reported as backfilled, a backfilled incomplete one does not count; a sustained `fiche_disclosure` challenge among three clean sessions reads `blocked`; the same challenge appended after the third clean session reads `blocked` with the revocation stated, including when its session date is earlier than theirs; two more clean sessions appended afterwards leave it `blocked`; a sustained challenge bearing on `other` alone leaves the session qualifying, one bearing on `other` and `judge_agreement` blocks; a dismissed session counts and is reported as a dismissal; a corrected record is read as its correction.
- The same planted records with every date shifted years earlier yield the identical verdict.
- A planted changelog section whose verdict line disagrees with the check fails naming the release; a dated section without a line fails.

## Evidence it publishes

- The check's output over the committed record, pasted into the delivery: every dated release with its verdict line.

## Plan shape

At most two phases: (1) the verdict computation and its planted-record tests; (2) the changelog lines, their agreement test, the procedure step and the release-cut edits.

## Cancellation

n/a: not cancelled.
