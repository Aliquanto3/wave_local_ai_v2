---
type: story
status: proposed
source: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
parent: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
depends_on:
  - aidd_docs/backlog/stories/every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens.md
  - aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md
  - aidd_docs/backlog/stories/the-judged-probe-runs-both-paths-in-three-languages.md
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
order: 2
---

# Story: The rewriting use case gets a quality score from two independent judges

**As** a consultant
**I want** the rewriting task suite's results for one local SLM and one cloud model scored by the GLM and DeepSeek judge pair, with their agreement reported
**So that** the third use case gets its quality score, and I can compare local and cloud rewriting quality under two independent judges the way classification and translation are already compared

Maps to: PRD AC "Given an open-ended task result from a subject independent of both judge families, it is never presented without both judges' scores and their agreement level; given one from a subject sharing a family with a judge, it carries the other judge's score only and is visibly flagged single-judge"; PRD AC "Given a judged item whose two judges disagree beyond the suite's stated threshold, the item is published as contested and excluded from that suite's headline score"; PRD AC "Given a judged item, its row names the judge provider that actually answered, the reasoning effort the call was issued with, and its reasoning-token count separately from its output tokens", enforced by the row contract that `every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens` ships, with `judge_cost` kept apart from `cost_total`; Methodology 2, 3, 4, 5, 10, 11; epic Success Evidence; owner answers Q50 to Q57 (all (a)) in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

Needs: a real local model run of one roster entry on the development laptop, paid API keys for Z.ai and DeepSeek (the judge pair), and the chosen cloud subject's key (Mistral or Google).

Current state (verified on `main` at `c68b23e`, 2026-10-03):

- `suite_registry.registered_ids()` returns only `classification-support-routing` and `translation-business-short-form` (`src/wave_local_ai_v2/suite_data/`, both `level: development`); resolving `rewriting-business-email` raises `SuiteRegistryError`. A definition declares every key of `suite_registry._CORE_KEYS`, `level` included; `prompt_set_hash` is computed at load, never declared.
- `src/wave_local_ai_v2/use_case_coverage.json` already declares `text-rewriting` `exercised` by `rewriting-business-email` and lists that id under `multilingual-en-fr-de`. The coverage story chose the id; the record refuses on both entries until this story registers it or the record is edited, and `tests/test_use_case_coverage.py::test_run_today_the_command_refuses_naming_what_is_not_yet_covered` asserts that refusal.
- `scoring_rules.SCORING_RULES` holds only `exact_label_match` and `chrf_against_reference`: no rule scores an item by judges, and the registry refuses a suite naming an unknown rule.
- The judged pieces exist: `judge_protocol` renders an EN, FR or DE judge prompt shell per item language; `agreement` computes quadratic-weighted Cohen's kappa with raw agreement, and `is_contested` against `DEFAULT_CONTESTED_THRESHOLD` (`settings.DEFAULT_CONTESTED_ORDINAL_MAX_DELTA = 1`); `row_contract.JUDGED_FIELDS` requires the judged block, `judge_cost` included and kept out of `cost_total`. `judge_protocol.OPEN_ENDED_QUALITY_1_TO_5` is the probe's generic rubric, not this suite's.
- `judge_backends.py` binds only `mistral` and `google` judges and `judge_probe.py` calls them; no GLM or DeepSeek backend exists.

Blocked: only through `depends_on`. `aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (judge epic order 10, `proposed`) waits on the GLM and DeepSeek judge stories (orders 8 and 9, `proposed`), each blocked by its spike's outstanding live calls with a paid key (`aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`, both `blocked`) and by owner question Q102 (pinning a judge that has no dated id under Methodology 12). `aidd_docs/backlog/stories/the-judged-probe-runs-both-paths-in-three-languages.md` (`proposed`) waits on order 10. The other two predecessors are `done`. Neither waits on calibration (Q54).

## Acceptance

- Running the rewriting task suite against one local SLM and one cloud model produces a judged quality score for each, from the judge pair Z.ai's GLM and DeepSeek, each called through its own direct API. No Mistral or Google judge scores any rewriting row. The roster-wide rewriting run stays with order 5.
- A rewriting result from a subject independent of both judge families carries both judges' scores and their agreement level; one from a subject sharing a family with a judge carries the other judge's score only and is visibly flagged single-judge. On the current roster every rewriting row is a two-judge row.
- The rewriting suite carries its own versioned rubric, a 1-5 ordinal rubric whose agreement is published as quadratic-weighted Cohen's kappa with raw agreement beside it. The rubric is the suite's own, not the probe's generic one.
- The suite's contested threshold is the shipped default of more than 1 point apart on the 1-5 rubric, unless the suite argues for another value in writing. A contested item stays in the published table with both judges' scores visible, is excluded from the headline score, and the excluded count is stated beside the headline.
- Each judge prompt is issued in the item's own language: an FR item's judge prompt is in French and a DE item's in German, readable off the row.
- Methodology 2: every rewriting row carries the suite id, the suite version and the content hash of the suite's prompt set; editing any prompt or the rubric bumps the suite version.
- Methodology 3: maximum output tokens, stop sequences, context length and `thinking_policy` are declared by the suite, identical across both subjects on an item, and recorded per row.
- Methodology 4: the suite holds at least 20 items, each of EN, FR and DE covers at least 25% of them, and the published score is broken down per language with its n and the indicative mark on any cell below the cell threshold.
- Methodology 5: every item declares its provenance, and any public-origin item is marked contamination-risk with its own licence and source.
- The suite is declared as data and resolved by its id, under the suite seam its predecessor ships, rather than imported by the CLI.
- Judged results appear in the same quality table structure as deterministic results, distinguishable as judged.
- The rewriting score does not wait for a calibration figure: the batch is published under the pair alone, no rewriting score depends on calibration, and its results README section states whether the calibration subsample has run on this batch.

## Cancellation

n/a: not cancelled.
