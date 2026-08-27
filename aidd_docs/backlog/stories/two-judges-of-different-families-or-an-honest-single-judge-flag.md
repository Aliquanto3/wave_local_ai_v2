---
type: story
status: ready
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/a-judge-call-carries-its-versioned-prompt-and-rubric.md
order: 4
---

# Story: Two judges of different families, or an honest single-judge flag

**As** a consultant defending a judged score to a client's engineer
**I want** the two judges to be of different model families, their agreement measured and published, disagreement marked contested, and a single-judge score visibly flagged
**So that** the score cannot be dismissed as one model's opinion, and no judged score exists whose independence is left unstated

## Acceptance

- Methodology 11: a judge never scores output from its own model family. Pointing a judge at its own family's output is refused with the collision named — never silently skipped, never quietly substituted by another judge.
- Model family is declared by this story as an attribute of the models it judges with. When the versioned roster file (Methodology 13) carries family, the refusal reads it from there instead; the declaration is written as the seam it is, not duplicated.
- Methodology 11: a local SLM's output is scored by both judges and carries an agreement figure. A cloud subject's output is scored by the other-family judge only, carries no agreement figure, and is flagged single-judge.
- A judged row carrying neither an agreement figure nor the single-judge flag cannot be written: the writer refuses it and names which is absent.
- Methodology 10, the statistic named per suite: a 1-5 ordinal rubric publishes quadratic-weighted Cohen's kappa over the suite's judged items, with raw agreement beside it — the exact-match rate, and the within-one-point rate reported alongside. A categorical rubric publishes unweighted Cohen's kappa with the same raw agreement figures. The suite declares which rubric kind it uses, and the row names the statistic it published.
- Kappa is undefined when either judge's scores have zero variance across the judged items. That case publishes kappa as an explicit null naming the reason, with raw agreement beside it — never a `0`, which would read as chance-level disagreement when the judges in fact agreed on every item.
- Both judges' per-item scores stay on the row whatever the suite-level statistic says, so any other agreement statistic can be recomputed later from the rows alone rather than re-running the judges.
- PRD acceptance: an item whose judges disagree by more than 1 point on the 1-5 ordinal rubric, or on the category of a categorical rubric, is published contested. A contested item stays in the published table with both judges' scores visible; only the headline score excludes it, and the headline states how many items it excluded.
- The contested threshold is configured per suite; this story sets the default at more than 1 point, or any category mismatch.
- A judged row records that the item and the subject's output left the machine, and to which providers — one judged item is one generation plus up to two judge calls, and the row says so.

## Code it changes

- `src/wave_local_ai_v2/agreement.py` (new) — quadratic-weighted and unweighted Cohen's kappa, exact-match and within-one raw agreement, the undefined-kappa case, and the contested rule with its per-suite threshold.
- `src/wave_local_ai_v2/judge.py` — judge selection by family, and the family-collision refusal.
- `src/wave_local_ai_v2/roster.py` — model family declared here as the attribute independence is enforced on, positioned to be read from a roster entry once Methodology 13's roster carries it.
- `src/wave_local_ai_v2/row_contract.py` — the agreement, single-judge-flag and contested fields, and the refusal to write a judged row that carries neither statistic nor flag.
- `src/wave_local_ai_v2/settings.py` and the suite definition — the per-suite contested threshold and its default.

## Tests it needs

- `tests/test_agreement.py` (new) — quadratic-weighted kappa against a hand-computed value on a small fixed score matrix; the zero-variance case returns null with its reason rather than 0; a more-than-1-point delta and a category mismatch each mark contested while a 1-point delta does not; the headline excludes contested items and reports how many.
- `tests/test_judge.py` (HTTP stubbed) — asking a Mistral judge to score the Mistral subject's own output is refused with the collision named; a cloud subject is judged once and its row is flagged single-judge; a local subject is judged twice and its row carries an agreement figure.
- `tests/test_row_contract.py` — a judged row carrying neither an agreement figure nor the single-judge flag is refused, naming what is missing.

## Evidence it publishes

- The same-family refusal shown by attempting the call, not by reading the guard — the epic's second success check.
- The suite-level statistic, the raw agreement figures and the contested set on the probe's rows, which order 6 records against the epic's Success Evidence.

## Cancellation

n/a — not cancelled.
