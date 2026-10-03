---
type: story
status: ready
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

Blocked: by no owner question since Q100 (a) (2026-10-03). Its operator work starts once orders 1 to 3 are delivered, per `depends_on`, and it waits on a real client session the project does not schedule.

Current state (verified on `main` at `c68b23e`, 2026-10-03): no record, check or procedure exists (orders 1 to 3 add them). Whether results were already shown to a client before the record existed is not recorded anywhere in the repository; the brief's "the first time results are shown" note suggests it may have happened.

## Acceptance

- Every earlier showing the consultant can still describe with its release and, for each challenge it raised (none for an accepted or dismissed showing), the challenger's role, the evidence offered and the criterion disputed, is entered as a backfilled record; a showing that cannot meet those fields is not entered, and the delivery says how many were considered and how many entered (Q67).
- The first real session with an audience outside the consultant's own firm (Q63), held once order 1 is delivered, is logged under the procedure the same day: its log date equals its session date, and the author date of the first commit adding the record is that same day. A session inside the firm is logged under the procedure but does not satisfy this story. The record is reported complete by the check. The session may precede this story's pick-up: its verdict line, the read-back and the done note follow once orders 2 and 3 are delivered. A session logged before order 2 is delivered that holds a sustained challenge files its follow-up item and links it the same day, through order 1's optional follow-up path, so order 2's committed-record test accepts it.
- If a challenge in it was sustained, its follow-up defect or spike exists and is linked; the named release's changelog verdict line matches the check in every case.
- A reader who was not in the session, named by the owner, answers from the record alone, in writing: what was shown, from which release, who challenged what, on which criterion and bearing on which claims, whether each challenge's claims list follows from the criterion as named in words (the check order 1 leaves to this read-back), and whether each challenge stood. The consultant's account is written and filed before the reader answers, and the evidence shows that order (its commit precedes the answers). The read-back passes only when every answer is given from the record and matches the consultant's account; a claims list that does not follow from its criterion fails it and is corrected by an appended record. A disagreement fails it: the procedure or the record format is revised, a correcting record is appended where the record was wrong, and the story waits for the next real session.
- No record, follow-up item or delivery note names the client organisation or carries client-provided material, and the repository tree holds no mapping from pseudonymous client id to client (Q61), verified by reading the record, the follow-up items, the delivery note and the tree.
- The epic's done note is drafted for the owner from this delivery: sessions per release and distinct clients, criteria challenged and by which roles, whether any challenge was sustained and what its follow-up became, whether the consultant-as-arbiter rule held, and, if no release is validated yet, that plain statement (Q69).

## Code it changes

- None. The record file gains real records and the named release's `CHANGELOG.md` verdict line is updated in the same commit; follow-up items are new backlog files when a challenge was sustained.

## Tests it needs

- None new: the checks of orders 1 to 3 run over the real records on every push.

## Evidence it publishes

- Filed under `aidd_docs/tasks/<yyyy_mm>/<yyyy_mm_dd>_first-client-session-read-back/`, with no client name: the check's output after the record's commit, the reader's written answers and the comparison with the consultant's account, the backfill count, and the drafted done note.

## Plan shape

Not a code plan: an operator walk in three steps (backfill, log the real session, read-back).

## Cancellation

n/a: not cancelled.
