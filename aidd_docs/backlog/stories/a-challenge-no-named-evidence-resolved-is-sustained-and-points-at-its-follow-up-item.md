---
type: story
status: ready
source: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
parent: aidd_docs/backlog/epics/a-release-is-called-credible-only-by-its-logged-client-sessions.md
depends_on: aidd_docs/backlog/stories/each-client-showing-is-logged-as-a-record-someone-who-was-not-there-can-read-back.md
order: 2
---

# Story: A challenge no named evidence resolved is sustained and points at its follow-up item

**As** the project owner deciding which claims move from assumption to evidence
**I want** every challenge whose record names no evidence presented within the session as resolving it to read as sustained, and every sustained challenge to point at a backlog item that exists
**So that** a sustained challenge is never a remark left in a log: it is either answered by evidence someone can check afterwards, or it is being worked somewhere I can find

Maps to: PRD AC "a challenge counts as sustained when it is not resolved by evidence within that session ... any sustained challenge is logged as a follow-up item rather than silently accepted"; epic Boundaries "the sustained rule as the PRD states it" and "the follow-up obligation"; owner answers Q62 (the consultant records the resolution and must name the evidence that resolved it), Q65 (a defect when a claim is shown wrong, a spike when it is merely unresolved, under `aidd_docs/backlog/`, linked from the record) and Q61 (the follow-up item carries the pseudonymous client id only); epic success checks 2 and 8 (the follow-up half).

Needs: code only. No model run, API key, hardware or operator.

Current state (verified on `main` at `c68b23e`, 2026-10-03): no reception record and no sustained rule exist (order 1 adds the record, its resolving-evidence field and its optional follow-up path). `aidd_docs/backlog/defects/` holds one defect and `aidd_docs/backlog/spikes/` the project's spikes; each is a Markdown file whose YAML frontmatter carries `type` and `status`. The project's runtime dependencies include no YAML parser. No backlog item links to a client session.

## Acceptance

- Sustained is derived, never typed: a challenge is sustained exactly when its resolving-evidence field is null, an empty string or whitespace only. The record format carries no separate "sustained" or "resolved" field, so the two cannot disagree. Evidence found after the session never resolves a challenge: the procedure says it goes into the follow-up item instead, and the PRD's "within that session" is part of the field's definition (Q62).
- Every sustained challenge names one follow-up item by its repository path, and the check refuses, naming the session and the challenge, a sustained challenge whose follow-up is missing, points outside `aidd_docs/backlog/defects/` and `aidd_docs/backlog/spikes/`, points at a file that does not exist, or points at a file whose frontmatter `type` does not match its folder (`defect` under `defects/`, `spike` under `spikes/`) (Q65). The path is repository-relative with forward slashes; the check refuses `..`, an absolute path and a backslash. The frontmatter is read with the standard library.
- The follow-up item contains its pseudonymous client id and the session id of a record in the correction chain that cites it (order 1's correction rule), and the check refuses an item missing either; the procedure states that the item, like the record, never names the client organisation and never carries client-provided material (Q61).
- Order 1's committed-record test runs these refusals on every push, so a pushed record with a sustained challenge but no item, or whose cited item was renamed or deleted, fails CI; the procedure commits the record and its item together. One item may serve several sustained challenges; a resolved challenge may also link an item, which the check accepts without making it sustained.
- A follow-up item's path is frozen once a record cites it: the item is never renamed or deleted, and a cancelled item keeps its file with its Cancellation section. A cancelled or `done` item never turns the challenge into a resolved one, because sustained is read from the record alone. If a path must change anyway, the record is corrected by an appended record under order 1's correction rule.
- Which kind the consultant files is recorded, not inferred: a defect when the session showed a claim to be wrong, a spike when it left a claim unresolved; the procedure from order 1 gains this step.
- The fix a follow-up leads to is not built here; the item is created and linked, and the epic owning the disputed criterion works it.

## Code it changes

- The record check's module from order 1 and its tests (the sustained derivation and the follow-up refusals), the procedure document (the follow-up step).

## Tests it needs

- A planted challenge whose resolving-evidence field is null, empty, or whitespace only reads as sustained; one with evidence named reads as resolved.
- One planted record per refusal: sustained with no follow-up, follow-up outside the two folders, follow-up path that does not exist, follow-up whose `type` is another kind, follow-up item missing the session id, follow-up item missing the client id; each fails naming the session and the challenge. A sustained challenge pointing at an existing defect, and one pointing at an existing spike, both containing both ids, pass; a type that does not match its folder, a path with `..`, an absolute path and a backslash path each fail; an item containing only the session id of the record a later correction replaced still passes; two challenges sharing one item pass; a resolved challenge linking an item passes and stays resolved; a planted item whose status is `cancelled` leaves its challenge sustained; a cited item renamed after the record is committed fails the committed-record test.

## Evidence it publishes

- None beyond the tests: the first real sustained challenge, if any, is logged under order 4.

## Plan shape

One phase: the derivation, the follow-up refusals and the procedure step.

## Cancellation

n/a: not cancelled.
