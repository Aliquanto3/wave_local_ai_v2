---
type: story
status: proposed
source: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
parent: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
depends_on:
  - aidd_docs/backlog/stories/each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back.md
  - aidd_docs/backlog/stories/a-challenge-no-named-evidence-resolved-is-sustained-and-points-at-its-follow-up-item.md
  - aidd_docs/backlog/stories/each-release-reads-its-credibility-verdict-from-its-records-in-its-changelog-entry.md
order: 4
---

# Story: The first real client session is logged the same day and read back by someone who was not there

**As** the project owner
**I want** the first real showing of results to a client or their engineer logged the same day under the procedure, and read back by someone who was not in the room
**So that** the record is proven against a real session rather than planted ones, and the epic can close on evidence instead of on the mechanism alone

Maps to: epic Success Evidence ("The first real showing, logged the same day and read back by someone who was not there"); epic success check 8 (the repository-tree half); owner answers Q67 (backfill of earlier showings that can still meet the fields, marked as backfilled) and Q69 (the epic is `done` once the record, the sustained rule and the verdict check work and one real session is logged and read back; it does not wait for a validated release).

Needs: an operator and a real client session. The consultant holds the session and writes the record; the owner names a reader who was not there. No model run, API key or hardware beyond what the session itself uses. Its timing depends on client access the project does not control.

Blocked: only through `depends_on` on `each-release-reads-its-credibility-verdict-from-its-records-in-its-changelog-entry.md` (`proposed`, blocked by Q100). Orders 1 and 2 carry no blocker.

Current state (verified on `main` at `c68b23e`, 2026-10-03): no record, check or procedure exists (orders 1 to 3 add them). Whether results were already shown to a client before the record existed is not recorded anywhere in the repository; the brief's "the first time results are shown" note suggests it may have happened.

## Acceptance

- Every earlier showing the consultant can still describe with its release, the challenger's role, the evidence offered and the criterion disputed is entered as a backfilled record; a showing that cannot meet those fields is not entered, and the delivery says how many were considered and how many entered (Q67).
- The first real session held once order 1 is delivered is logged under the procedure the same day: its log date equals its session date, and the record's commit date is that same day. The record is reported complete by the check. Its verdict line, the read-back and the done note follow once orders 2 and 3 are delivered.
- If a challenge in it was sustained, its follow-up defect or spike exists and is linked; the named release's changelog verdict line matches the check in every case.
- A reader who was not in the session, named by the owner, answers from the record alone, in writing: what was shown, from which release, who challenged what, on which criterion and bearing on which claims, and whether each challenge stood. The read-back passes only when every answer is given from the record and matches the consultant's account. A disagreement fails it: the procedure or the record format is revised, a correcting record is appended where the record was wrong, and the story waits for the next real session.
- No record, follow-up item or delivery note names the client organisation or carries client-provided material, and the repository tree holds no mapping from pseudonymous client id to client (Q61), verified by reading the record, the follow-up items, the delivery note and the tree.
- The epic's done note is drafted for the owner from this delivery: sessions per release and distinct clients, criteria challenged and by which roles, whether any challenge was sustained and what its follow-up became, whether the consultant-as-arbiter rule held, and, if no release is validated yet, that plain statement (Q69).

## Code it changes

- None. The record file gains real records and the named release's `CHANGELOG.md` verdict line is updated in the same commit; follow-up items are new backlog files when a challenge was sustained.

## Tests it needs

- None new: the checks of orders 1 to 3 run over the real records on every push.

## Evidence it publishes

- Filed under `aidd_docs/tasks/<date>_first-client-session-read-back/`, with no client name: the check's output after the record's commit, the reader's written answers and the comparison with the consultant's account, the backfill count, and the drafted done note.

## Plan shape

Not a code plan: an operator walk in three steps (backfill, log the real session, read-back).

## Cancellation

n/a: not cancelled.
