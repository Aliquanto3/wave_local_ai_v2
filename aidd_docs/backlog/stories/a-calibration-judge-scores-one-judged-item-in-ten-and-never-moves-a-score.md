---
type: story
status: proposed
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md
order: 11
---

# Story: A calibration judge scores one judged item in ten and never moves a score

**As** an academic or technical reviewer suspicious that two judges of common geographic origin share a bias on FR and DE items
**I want** a calibration judge of a further family, GPT-5.6 Luna, to score a recorded 10% subsample of judged items, with its agreement against the pair published as its own figure, split between EN and FR/DE
**So that** a shared bias in the pair is something the publication can show or rule out, without any suite's score depending on a third provider

Maps to: PRD AC "given the calibration subsample, its agreement with the judge pair is published as its own figure and no suite score moves because of it"; Methodology 11 ("A calibration judge from a further family, GPT-5.6 Luna, scores a 10% subsample of judged items to test whether the pair carries a shared bias, in particular on FR and DE items: its result is published as its own agreement figure and is never folded into any suite's score"), Methodology 10, 12, 16; Methodology preamble threshold "a 10% judged subsample for judge calibration"; PRD Dependencies "and to the calibration judge's provider"; epic Boundaries "the calibration judge, GPT-5.6 Luna, over a 10% subsample of judged items"; epic decision "The calibration judge is a third provider client, and a third egress destination"; epic success check 3 (calibration half); owner answers Q7 (a) and Q8 (a) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

Needs: a paid API key for the calibration judge's provider (OpenAI, called through its own direct API), for the spike and for the first published calibration figure.

Blocked: by the spike `aidd_docs/backlog/spikes/which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms.md` (`blocked`; desk research done 2026-10-02 found `gpt-5.6-luna` on OpenAI's direct API, undated), which needs its live calls with a paid OpenAI key: the `/v1/models` listing, a pinned Chat Completions call at `reasoning_effort: "none"` with temperature and seed, seed repeats, the `minimal` and `low` efforts, the Responses API equivalent, the caller's cap, one captured 429, an unavailable id, and the Services Agreement read at a named revision. By owner question Q102 (Methodology 12's dated id for `gpt-5.6-luna`). By owner question Q116 (what the calibration judge's agreement "with the pair" is computed against), since Methodology 10's statistics are two-rater. And through `depends_on` on `aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (order 10, `proposed`), blocked in turn through orders 8 and 9 on their spikes and Q102. Owner question Q104 (GPT-5.6 Luna or GPT-6 Luna) is open and blocks nothing: this story is written against the PRD's model.

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- No OpenAI client, no calibration backend and no calibration family: `roster.KNOWN_FAMILIES` holds `qwen`, `mistral`, `google`, `ibm`, `liquid`, `microsoft`; `cost.PRICE_TABLES` and `cost.REASONING_TOKEN_BILLING` key only `mistral` and `google`; `settings.Settings` reads no OpenAI key.
- `agreement.agreement_for_rubric` computes one two-rater figure over `(judge_a, judge_b)` pairs (`cohens_kappa_quadratic_weighted` or `cohens_kappa_unweighted` by rubric kind, with exact-match and within-one rates and `KAPPA_NULL_*` reasons); there is no calibration figure and no per-language split.
- `row_contract.SCHEMA_VERSION` is `"22"`; `JUDGED_FIELDS` holds no calibration block; `judge_egress` (`JUDGE_EGRESS_FIELDS`) counts `judge_call_count` with no separate calibration count; `judge_cost.per_provider` already holds one entry per provider (`JUDGE_COST_PROVIDER_FIELDS`), so a calibration provider entry fits it.
- No calibration draw exists. `subset_sampler.draw` is the publication-suite sampler and splits a fixed size equally across the three languages; it is not this story's 10%-per-language rule.

## Acceptance

- The calibration judge is called through its vendor's direct API (OpenAI), never through a router, the same rule the pair follows, so the provider that answered is that vendor by construction. It is called under the same discipline orders 8 and 9 apply: a dated model id read from the serving endpoint's live catalog and refused when absent, sampling pinned by the caller, reasoning disabled or minimal and recorded with its reasoning tokens through order 7's fields, the answering provider named, finish reasons mapped with a block failing the call, one typed error with unavailable-model and retryable subclasses, and a dated list-price entry keyed by the literal dated id.
- Its family is declared, differs from `glm`, `deepseek` and every subject family on the roster, and the family-collision refusal applies to it as it applies to the pair.
- The subsample is drawn per suite and batch over that batch's judged items by a seeded draw stratified by item language: 10% of each language's items, rounded up, with at least one item for every language present in the batch. Replaying the rule returns the same item ids. The rule, its seed and the subsample's n, overall and per language, are recorded with the published figure. On a small batch this draws above 10% (three items of ten on the judged probe), a deviation the owner accepted.
- A subsampled item's row carries the calibration call as its own record, distinct from the pair's `judges` entries, with the same per-call fields. The row's egress names the calibration provider and counts the calibration call apart from the pair's judge calls.
- The calibration judge's agreement with the pair is published as its own figure per suite, under the statistic Methodology 10 names for the rubric kind, reported for EN and for FR/DE separately, each with its n. An undefined statistic publishes a null with its reason, never a number.
- No suite score moves because of calibration: for the same responses, the pair's per-item scores, the agreement figure, the contested set and the judged headline score are identical whether calibration ran or not.
- The calibration calls' tokens and cost appear in the row's `judge_cost` under their own provider entry and never in `cost_total`.
- A resumed run never re-issues a calibration call whose result is already recorded.

## Code it changes

- `src/wave_local_ai_v2/` (new client module for the OpenAI direct API): `requests` only, no SDK, no streaming, mirroring the other provider clients; its module docstring cites the spike's decision file.
- `src/wave_local_ai_v2/judge_backends.py`: the calibration backend, bound at the same seam as the pair.
- `src/wave_local_ai_v2/agreement.py`: the calibration-versus-pair figure and its EN and FR/DE split.
- `src/wave_local_ai_v2/row_contract.py`: the calibration record as a conditional block with its `SCHEMA_VERSION` bump; the egress count it implies.
- `src/wave_local_ai_v2/cost.py`, `src/wave_local_ai_v2/roster.py`, `src/wave_local_ai_v2/settings.py`, `.env.example`, `README.md`: the price entry and its `REASONING_TOKEN_BILLING` basis, the family, the key and the egress sentence.

## Tests it needs

- `tests/test_agreement.py`: the calibration figure against a hand-computed value on a fixed score matrix; an undefined case returns null with its reason.
- `tests/test_judge.py` (HTTP stubbed): the seeded rule replays to the same ids; a ten-item batch across EN, FR and DE draws three items, one per language; a batch with no DE item draws none for DE and still at least one per language present; a 100-item batch draws 10% per language, rounded up; a batch judged with and without calibration produces identical pair scores, agreement, contested set and headline.
- `tests/test_row_contract.py`: a row carrying part of the calibration block is refused naming the missing field; a judged row with no calibration block still validates.

## Evidence it publishes

- The first calibration figure against the pair, with its n and its EN versus FR/DE split, recorded in `aidd_docs/results/README.md`: the epic's closing question on whether the calibration judge's agreement differed between EN and the FR/DE items.

## Cancellation

n/a: not cancelled.
