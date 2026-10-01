---
type: epic
status: proposed
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
related_to:
  - aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
  - aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
  - aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
---

# Epic: A release is called credible only by its logged client sessions

Every time a benchmark result is shown to a client or their engineer, a tracked record states whether it was challenged, dismissed or accepted, who challenged it, on what evidence and against which acceptance criterion, and a release is called credible only once at least three such records carry no sustained challenge to fiche disclosure, table separation or judge agreement, never because time has passed.

## Context and Value

The audience is the consultant first, who has to be able to say "this release has held up" and point at something other than memory, and the project owner second, who decides which claims move from assumption to evidence. The brief makes defensibility the product: "That defensibility, not any single benchmark number, is the product", and "success is qualitative defensibility, confirmed by use rather than by a number" (`aidd_docs/product/wave-local-ai-v2.md`, Product Bet and Success). Its own feedback loop is the seed of this epic: "the first time results are shown to a client or their engineer, note what they challenge or dismiss" (Validation and Feedback).

The PRD turns that note into an acceptance criterion with a rule attached: "Given a benchmark result shown to a client or their engineer, the consultant logs in a tracked file whether it was challenged, dismissed, or accepted, with the challenger's role, the evidence offered, and the acceptance criterion disputed; a challenge counts as sustained when it is not resolved by evidence within that session. After at least 3 such logged sessions with no sustained challenge to fiche disclosure, table separation, or judge agreement, the artifact is considered validated as credible for that release; elapsed time alone never validates it, and any sustained challenge is logged as a follow-up item rather than silently accepted."

No other epic owns it. Three touch it and none takes it:

- `quality-scored-comparison-first-three-use-cases` asks, once `done`, to "record here whether reproduction actually held and whether any specific model's score was challenged in a real client session". That is a note on one epic, not a log or a rule.
- `the-pitch-runs-from-a-browser-and-only-with-the-key` asks, once `done`, to "record what a client actually asked to see that the dashboard did not show". Same shape: an afterthought on the surface, not a record of the result's reception.
- `clean-machine-runs-it-and-nothing-reaches-main-unchecked` makes a release identifier exist, which is what a "credible for that release" verdict has to name.

Verified current state, on branch `docs/slice-remaining-epics`:

- **No reception log exists in any form.** No file under `aidd_docs/`, `docs/` or the repo root records a showing, a challenge or a verdict.
- **Releases exist to be named.** `CHANGELOG.md` carries `[0.1.0] - 2026-08-22` and `[0.2.0] - 2026-09-22`, and `pyproject.toml` declares `version = "0.2.0"`. A record can therefore name the release it judged without waiting on new release machinery.
- **The PRD names an arbiter weakness it does not resolve.** The PRD shadow scan (`aidd_docs/tasks/2026_08/2026_08_22_prd-shadow-scan/report.md`) flags that "the consultant is both the challenged party and the scorer of the challenge, which is the weakest possible arbiter for a credibility claim", and that the log's location is "never named or located". The PRD answered the second partly ("a tracked file") and the first by defining "sustained" through evidence; neither is fully closed.

The value is that the product's one success claim becomes falsifiable. Without this record, "the bench held up in front of clients" is the anecdote the brief says the project exists to replace. With it, a release's credibility is a count anyone can recompute, a sustained challenge is a backlog item rather than a forgotten remark, and the three claims the whole product bet rests on (fiche, separation, agreement) are the ones the count is scoped to.

## Boundaries

- Includes: **the reception record.** One tracked, append-only record per session in which a benchmark result is shown to a client or their engineer, carrying at least the release the shown results came from, the session date, the outcome (challenged, dismissed or accepted), the challenger's role, the evidence offered, the acceptance criterion disputed, and whether each challenge was resolved by evidence within the session.
- Includes: **the sustained rule as the PRD states it.** A challenge not resolved by evidence within that session is sustained. Its resolution, when there is one, names the evidence that resolved it, so the judgement can be checked by someone who was not in the room.
- Includes: **the follow-up obligation.** Every sustained challenge produces a linked follow-up item, so no sustained challenge exists in the record without somewhere it is being worked.
- Includes: **the validation verdict per release.** A release is validated as credible once at least three of its logged sessions carry no sustained challenge to fiche disclosure, table separation or judge agreement. The verdict is derived from the records, not declared beside them, and a release with fewer qualifying sessions reads as not yet validated whatever its age.
- Includes: **the documented procedure** a consultant follows after a showing, short enough to be done the same day, in English per the repo's language rule even when the session was held in French.
- Excludes: **deal outcomes and business KPIs.** The record says how a result was received, never whether a deal was won (PRD Non-Goals: "Tracking deal outcomes or business KPIs").
- Excludes: **client-provided material.** No client document, prompt or dataset enters the record; the evidence offered is described, not attached. The PRD's egress non-goal applies to the record as much as to the suites.
- Excludes: **fixing what a sustained challenge finds.** The follow-up item is created here; the fix belongs to whichever epic owns the disputed criterion.
- Excludes: **rendering the record or the verdict on the pitch surface.** `the-pitch-runs-from-a-browser-and-only-with-the-key` owns what a client sees; whether the verdict is ever shown there is not decided here.
- Excludes: **producing the three claims the verdict is scoped to.** Fiche disclosure belongs to `every-published-row-explains-and-reproduces-itself`, table separation to the pitch epic and the row epic, judge agreement to `any-open-ended-output-carries-two-judges-or-an-honest-flag`. This epic records how they were received.
- Excludes: **release tagging and the changelog.** `clean-machine-runs-it-and-nothing-reaches-main-unchecked` owns them; a record only names a release that already exists.

## Success Evidence

The first real showing, logged the same day and read back by someone who was not there: from the record alone they can say what was shown, from which release, who challenged what, on which criterion, and whether the challenge stood.

Checks, each able to fail:

- A record missing the challenger's role, the evidence offered or the acceptance criterion disputed does not count toward a release's three sessions, verified by planting such a record and reading the verdict, not by reading the procedure.
- A challenge with no resolving evidence named reads as sustained and has a linked follow-up item, verified by tracing every sustained record to its item.
- A release with two qualifying sessions reads as not validated however long ago they were logged, and the same release with a third reads as validated, verified by adding the third record and nothing else.
- A sustained challenge to fiche disclosure, table separation or judge agreement prevents the verdict for that release, verified by planting one among three otherwise clean sessions.
- No record names a client organisation or carries client-provided material unless the owner's answer on client identity allows it, verified by reading the tracked file.

Once `done`, record here how many sessions each release reached, which criteria were challenged and by which roles, whether any challenge was sustained and what its follow-up became, and whether the consultant-as-arbiter rule survived contact with a client engineer who disagreed with the resolution.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| A release identifier for the verdict to name | dependency | Already met: `CHANGELOG.md` carries 0.1.0 and 0.2.0. Owned by `clean-machine-runs-it-and-nothing-reaches-main-unchecked`; recorded as `related_to` rather than `depends_on` because nothing here waits on it. |
| Real client showings | dependency | Outside the project's control. The record and rule can ship before any showing; the outcome is only evidenced by a real one. |
| Where the tracked record lives and in what form | decision | Open, owner question Q60. The PRD says only "a tracked file"; the shadow scan flags it as unlocated. |
| Whether a client organisation may be named in a tracked file of a public repository | decision | Open, owner question Q61. The PRD requires the challenger's role, not the client's identity. |
| Who arbitrates "resolved by evidence within that session" | decision | Open, owner question Q62. The PRD's evidence definition stands; who applies it is the open part. |
| What counts as a session | decision | Open, owner question Q63: whether only parties outside the consultant's team count, and whether repeat sessions with one client count separately. |
| How a sustained challenge scopes to releases | decision | Open, owner question Q64: whether it blocks that release's verdict for good, resets its count, or revokes an earlier verdict. |
| Where a follow-up item lives | decision | Open, owner question Q65. |
| Whether the verdict is computed by a check or written by hand, and where it is published | decision | Open, owner question Q66. Changes whether this epic ships code. |
| Showings that may already have happened before the record existed | decision | Open, owner question Q67. |
| A product-wide check-in cadence beyond the per-session log | decision | PRD Open Question, not taken here; owner question Q68. The PRD's "elapsed time alone never validates it" already rules out a time-based verdict. |
| When this epic is `done`: once the record and rule work on a real session, or once a release is actually validated | decision | Open, owner question Q69. Lifecycle is the owner's call. |
| Challenges to criteria other than the three named ones | assumption | Accepted from the PRD's literal text: they are logged and get a follow-up item when sustained, but do not prevent the verdict. |
| The consultant writes the record, so the record is self-reported | assumption | Accepted as a limit, not hidden: the mitigation inside the PRD's text is that every resolution names its evidence, which makes the self-report checkable rather than trusted. |
| The record is written in English from sessions held in French | assumption | Accepted per the repo's language rule; quotes from a session are translated, not transcribed. |

## Cancellation

n/a, not cancelled.
