---
type: story
status: proposed
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on:
  - aidd_docs/backlog/stories/a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md
  - aidd_docs/backlog/stories/a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md
order: 10
---

# Story: GLM and DeepSeek are the only judges, and Mistral and Google never judge again

**As** a consultant defending a judged score to a client's engineer
**I want** every judged row on the current roster to be scored by GLM and DeepSeek together, and no configuration able to bind Mistral or Google as a judge
**So that** no judge ever shares a family with a roster subject, every judged row on this roster is a two-judge row with an agreement figure, and the single-judge flag stays a guard against a future roster rather than a live path

Maps to: PRD Goal "Judged (open-ended) scores carry inter-judge agreement between two cloud LLM judges of different model families"; PRD AC "Given an open-ended task result from a subject independent of both judge families, it is never presented without both judges' scores and their agreement level"; Methodology 11 ("Google and Mistral are benchmark subjects and are never judges"); epic Boundaries "the retirement of Mistral and Google as judges", "independence enforced by model family as a refusal"; epic Dependencies "The judge families must enter `roster.KNOWN_FAMILIES` and `MODEL_FAMILIES`, and the retired judge bindings must leave `judge_backends.py`"; epic success check 2.

Needs: none. The binding change and the forced collision are proven with stubbed backends; the live calls belong to orders 8 and 9.

Blocked: only through `depends_on` on `aidd_docs/backlog/stories/a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md` (order 8, `proposed`) and `aidd_docs/backlog/stories/a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md` (order 9, `proposed`). Each waits on its `blocked` spike's live calls with a paid key (`aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`).

Current state (verified on `main` at `c68b23e`, 2026-10-03):
- `judge_backends.py` holds `mistral_judge_backend` and `google_judge_backend` (`PROVIDER_MISTRAL`, `PROVIDER_GOOGLE`); `judge_probe.py`, `tests/test_judge.py` and `tests/test_judge_probe.py` are the only modules that import `judge_backends`.
- `judge_probe._run` binds both as judges; `_run_cloud_subject_item` judges the Google-generated item (`CLOUD_SUBJECT_ITEM_ID`) with Mistral alone, `single_judge_reason=judge.SINGLE_JUDGE_REASON_CLOUD_SUBJECT`.
- `judge.select_judges` refuses a judge of the subject's own family (`JudgeFamilyCollisionError`); nothing refuses a judge of a subject-only family.
- `roster.KNOWN_FAMILIES` is `{"qwen", "mistral", "google", "ibm", "liquid", "microsoft"}`; no subject-only declaration exists beside it.
- `cost.REASONING_TOKEN_BILLING` holds `mistral` and `google` entries read only by `cost.judge_cost_fields`, so they become unused once the retired backends go.
- `README.md` still lists `GOOGLE_API_KEY` as reserved "for the planned second LLM-as-a-judge", and `aidd_docs/memory/architecture.md` still names Mistral and Google as the two judge providers.

## Acceptance

- `judge_backends.py` binds only the GLM and DeepSeek backends. No Mistral or Google judge backend exists, and a judge declared with family `mistral` or `google` is refused at binding, naming the family and stating that it is a subject family only. The refusal is not configurable.
- `mistral_client.py`, `google_client.py`, their price tables, their `provider` values and the Google spike's decision file are unchanged: they remain cloud-subject infrastructure. `mistral` and `google` stay in `roster.KNOWN_FAMILIES` as subject families.
- No runner in the repo binds a Mistral or Google judge: every judge binding names GLM and DeepSeek.
- Every subject the roster holds today, local and cloud, is judged by both GLM and DeepSeek and carries an agreement figure; a judged row from the current roster is never single-judge.
- The family-collision refusal is proven by forcing a collision: a subject declared into `glm` or `deepseek` is refused with the collision named before any backend is invoked, asserted on the stub's call count. The writer still refuses a judged row carrying neither an agreement figure nor the single-judge flag.
- The README and `aidd_docs/memory/` state that every judged row on the current roster is a two-judge row, and name the judge pair and the subject providers separately.

## Code it changes

- `src/wave_local_ai_v2/judge_backends.py`: the Mistral and Google judge backends removed; its docstring names the pair.
- `src/wave_local_ai_v2/judge.py`: the binding-time refusal of a subject-only family.
- `src/wave_local_ai_v2/roster.py`: subject-only families declared as such beside `KNOWN_FAMILIES`.
- `src/wave_local_ai_v2/judge_probe.py`: its judges rebound to the pair; the probe's own acceptance is order 6's.
- `README.md`, `aidd_docs/memory/architecture.md`: the pair and the retirement.

## Tests it needs

- `tests/test_judge.py` (HTTP stubbed): binding a `mistral` or `google` judge is refused naming the family; a local subject and a cloud subject are each judged twice and carry an agreement figure; a subject forced into `glm` is refused before any stubbed call is made.
- `tests/test_judge.py`: neither retired backend is reachable from the judge seam.
- `tests/test_judge_probe.py` (HTTP stubbed): the probe runner binds the pair and no Mistral or Google judge.

## Evidence it publishes

- The forced-collision refusal, shown by attempting the call rather than reading the guard: the epic's second success check under the new pair.

## Cancellation

n/a: not cancelled.
