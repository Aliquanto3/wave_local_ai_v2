---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
related_to:
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
  - aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
---

# Epic: Any open-ended output carries two judges, or an honest flag

Given any open-ended model output, a consultant gets a judged score from two cloud judges of different model families with their agreement recorded — or from the single judge independence allows, visibly flagged as such — and every judge call behind that score is reproducible from the row alone.

## Context and Value

The audience is the one the PRD's user story names directly: "As a consultant, I want open-ended task scores backed by two independent LLM judges with agreement reported, so that a client's engineer can't dismiss a score as one model's opinion." The product brief makes it one of the three legs of the bet — "judged scores always carry inter-judge agreement" (`aidd_docs/product/wave-local-ai-v2.md`, Product Bet). Of the two legs already standing, the fiche belongs to the row epic and the quality/runtime split is shipped; this leg has nothing under it.

Verified current state, at `a2ffe37`:

- **No judging exists at all.** `grep -rin "judge\|kappa\|agreement\|rubric" src/ tests/` returns two hits, both prose in `__init__.py` about energy disclosure. There is no judge prompt, no rubric, no agreement computation, and no judge field on any row.
- **A quality row is deterministic-only.** It carries `run_id`, `captured_at`, `model_id`, `provider`, `task_suite`, `item_id`, `prompt`, `expected_label`, `predicted_label`, `correct`, `suite_accuracy` and `sampling` (`src/wave_local_ai_v2/quality_cli.py:199-217`), and scoring is exact label match after normalization (`scoring.py`). An open-ended output has nothing in that row to be scored into.
- **There is one cloud provider, and it is a subject, not a judge.** `mistral_client.py` sends one prompt and returns one completion; `quality_cli.py:125` writes `provider="mistral"`. Criterion 12 is already satisfied on that path: `mistral-small-2603` is a dated id, `check_model_available` refuses a run when the id is off the live `GET /v1/models`, and a deprecation is surfaced as a notice rather than an error.
- **The second provider is documented but unwired.** `.env.example` already carries `GOOGLE_API_KEY=replace-me`, but `settings.py` reads `MISTRAL_API_KEY` only and `Settings` has no field for a second key. No Google client module exists among the twelve modules under `src/wave_local_ai_v2/`.
- **Nothing survives a rate limit.** `mistral_client` states its own contract in its first line: "No SDK, no streaming, no retries". A free-tier 429 mid-suite raises `MistralRequestError` and the run dies, so the PRD's acceptance criterion on mid-suite provider failure — every row already produced persisted, the run marked partial, the failing provider and item named — has no implementation on the path that exists today.

Three neighbours have already written this epic's seam into their own boundaries and are waiting on it. The row epic excludes criteria 10 and 11 explicitly and states that it "leaves the row schema open for the fields they add". The pitch epic's four-view table names judge model ids, agreement and the single-judge flag as exactly what its quality view waits on, and commits to refusing to render a judged score that carries neither. And `judge-scoring-with-inter-judge-agreement-proves-judged-machinery`, story 2 of the suite epic, is `ready` and cannot start: it asks for two independent judges and an agreement figure over the rewriting suite, and neither judge exists.

The value has two parts. The first is reach: deterministic scoring covers classification and translation, and every remaining use case the PRD lists — rewriting, document comparison, code generation, agentic planning, agentic tool calling, web research, RAG answer generation — is open-ended and therefore unscorable until this machinery exists. The second is the defensibility itself. A single judge's score is one model's opinion, and a judge scoring output from its own family is the precise objection a client's engineer raises first. Independence and agreement are not quality improvements to a judged score; they are what makes it admissible.

## Boundaries

- Includes: a **Google AI Studio client mirroring the Mistral pattern** — `requests` only with no SDK, a dated model id read from the provider's live catalog rather than from its documentation, a pre-flight that refuses a run when that id is absent, sampling pinned by the caller instead of inherited from a provider default, one typed error with an unavailable-model subclass, and stubbed tests. Criterion 12 extended to the second provider, not re-invented for it.
- Includes: that client as a **benchmark subject on equal terms with Mistral**, answering suite items and writing rows under its own `provider` value. A provider that only ever judges cannot itself be compared, and the PRD's comparison covers cloud subjects too.
- Includes: the **judge protocol as one reusable module**, not a rewriting-suite feature — versioned judge prompt templates with one variant per item language (EN, FR, DE), versioned rubrics, and a judge call that runs through either provider client.
- Includes: **per-row judge fields, additive** to the existing quality row — each judge's dated model id, the judge prompt id and its content hash, the rubric version, each judge's score, and either the named agreement statistic or the single-judge flag. A judged score carrying neither is not a shape the harness can produce.
- Includes: **independence enforced by model family as a refusal**, not a convention. A judge from the subject's own family is refused with the collision named; it is never silently skipped or quietly substituted. A local SLM's output is judged by both and carries an agreement figure; a cloud subject's output is judged by the other-family judge only and is flagged single-judge (criterion 11).
- Includes: **the named statistic for an ordinal rubric**, decided here. A 1-5 rubric is treated as the PRD's numeric branch, so the statistic is the absolute per-item score delta with a suite-level aggregate; a categorical rubric keeps Cohen's kappa (criterion 10).
- Includes: **the contested rule**. Per-item disagreement above 1 point on the 1-5 ordinal rubric, or a category mismatch on a categorical rubric, publishes the item contested. A contested item stays in the published table with both judges' scores visible; only the headline score excludes it. The threshold is configured per suite and this epic sets that default.
- Includes: **free-tier survival** — retry with backoff on rate limit, and an interrupted run that persists every row already produced, marks itself partial, names the failing provider and item, and resumes without re-paying for the judge calls it already made. This covers the judge calls this epic adds and the existing Mistral subject path, which has no retry today.
- Includes: **egress recorded on the calls this epic introduces**. A judged row records that the item and the subject's output left the machine and to which providers. Judging is the project's largest egress surface — one judged item is one generation plus up to two judge calls — and the PRD requires every row to record whether its prompt left the machine.
- Includes: a **judged probe of about 10 open-ended items spanning EN, FR and DE**, owned by this epic, written to its own reference file (`aidd_docs/results/judge-probe-reference.jsonl`) and never into `quality.jsonl`. It exists to drive the machinery end to end, not to publish a benchmark score: local SLM outputs so both judges run and a real agreement figure exists, plus at least one cloud-subject output so the single-judge path is proven rather than described.
- Excludes: **the rewriting suite's items and its rubric text.** Story 2 of `quality-scored-comparison-first-three-use-cases` owns them and is this machinery's first real consumer. The probe is not that suite, publishes no score, and does not pre-empt the rubric that suite will define.
- Excludes: criteria 17 and 18, web-research archival and suite shape, including anything specific to judging against a retrieved source set — `aidd_docs/backlog/epics/no-use-case-is-silently-absent.md`.
- Excludes: **showing any of this to a human.** The pitch epic renders judge ids, agreement and the flag, and enforces the refusal to render a bare judged score. This epic makes those fields exist and be correct.
- Excludes: the rest of the row schema and every other methodology criterion. Judge fields are added to the row `every-published-row-explains-and-reproduces-itself` owns, additively, as that epic's own boundaries anticipate.
- Excludes: the versioned roster file and model family as a roster field — a seam, named below.
- Excludes: adding a third provider family so that cloud subjects regain an agreement figure. The PRD carries it as an open question; this epic ships the single-judge flag as the honest answer for this release.
- Excludes: optimising what judging costs. Cost is reported, never optimised (PRD Non-Goals). Backoff and resumability exist so a free-tier limit does not destroy a run, not so a run gets cheaper.

Criterion ledger, so the scope is checkable rather than described:

| Criterion | Here |
| --- | --- |
| 10 judge protocol | in scope, in full |
| 11 judge independence | in scope, in full |
| 12 cloud model pinning | done for Mistral; extended to the second provider here |
| 1-9, 13-16, 19 | out — `every-published-row-explains-and-reproduces-itself` |
| 17, 18 web research | out — `no-use-case-is-silently-absent` |

## Success Evidence

Run the probe: about ten open-ended items in three languages, local SLM outputs judged by both providers and at least one cloud-subject output judged by one, and read the resulting rows back. Every judged score names its two judges, the prompt that produced it and the rubric it applied, and either states how far the judges were apart or says plainly that only one judged it.

Five checks, each able to fail:

- A judged row carrying neither an agreement figure nor the single-judge flag cannot be produced by the harness at all — verified by trying to write one, not by reading the writer.
- Pointing a judge at output from its own model family is refused with the collision named — verified by asking Mistral to judge the Mistral subject's own output, not by reading the guard.
- A judged FR item yields two scores, their delta, and a judge prompt each side can be shown to have received in French — read off the row, not off the template source.
- A row's judge prompt id and content hash re-render the exact prompt that was sent; editing a template changes the hash, and rows written before the edit stay attributable to the text they actually used.
- A run killed mid-probe by a rate limit persists what it produced, reports partial with the failing provider and item named, and resumes without re-issuing the judge calls already paid for — verified by forcing a 429, not by unit-testing the backoff.

Once `done`, record here what the first real two-judge agreement figure was, whether the 1-point contested threshold survived contact with genuine disagreement, and whether free-tier limits made a full-roster judged run impractical rather than merely slow.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| Google AI Studio's live catalog endpoint, its dated model ids, its sampling controls, and whether it exposes a pinnable seed at all | spike | Framed as the first delivery step, confirmed against the live API and never from documentation — the Mistral module records that the id its own docs published did not exist on the API. If no seed is exposed, judge determinism degrades to temperature 0 and the row records what was actually pinned rather than claiming a seed it could not set. |
| Free-tier access to two independent cloud providers | dependency | PRD Dependencies. Mistral is proven in use; Google AI Studio is assumed available on comparable free-tier terms and is unverified in this repo until the first live call. The same spike settles it. |
| Model family as a first-class attribute, which independence enforcement needs | dependency | The versioned roster file (criterion 13) is the row epic's output and does not exist yet. This epic declares the family of the models it judges with and refuses on a match; when the roster lands, family becomes a roster field and the refusal reads it from there. Named as a seam so it is not implemented twice. |
| The item language the judge prompt must be issued in | dependency | Criterion 4's per-item language tag is the row epic's gate. The probe items carry their own tags, so this epic does not wait; suite items get theirs from that gate. Non-blocking in either direction. |
| Ordinal rubric agreement measured as absolute delta rather than a weighted kappa | decision | Taken this session. The PRD names Cohen's kappa for a categorical rubric and absolute score delta for a numeric one; a 1-5 ordinal rubric is treated as numeric. Whether a weighted kappa is added at suite level is deferred to the first suite holding enough judged items to make one meaningful. |
| The contested threshold default: more than 1 point apart on a 1-5 rubric, or a category mismatch | decision | Taken this session, configured per suite. A contested item stays in the published table with both scores visible; only the headline score excludes it. |
| Whether a judge call's tokens count toward the subject row's cost and Scope-3 figures or are reported separately | decision | Not fixed here. Criterion 16 belongs to the row epic; this epic records judge-call token counts so either treatment remains possible, and the choice is made with that epic rather than assumed of it. |
| A third provider family would give cloud subjects a real agreement figure instead of a flag | decision | Deferred, per the PRD's own Open Question. Until then a cloud subject is single-judge and says so on the row. |
| Judging multiplies cloud calls per item | assumption | Accepted: one judged item is one generation plus up to two judge calls, so a 20-item suite across a roster becomes a free-tier question rather than a cost question. Backoff and resumable partial runs are in scope for that reason; raising a paid tier is not. |
| Sending a local model's output to two cloud providers is egress the PRD's non-goal permits | assumption | Accepted: the non-goal forbids client-provided documents and prompts and scopes egress to "the repo's own suite items". An output derived from a repo suite item is judged as such; a client document is never judged, in this release or by opt-in. |
| The probe is not a task suite | assumption | Accepted: about ten items, its own reference file, no published score, and therefore outside criterion 4's 20-item gate. If it is ever published as a benchmark score it becomes a suite and the gate applies to it. |

## Cancellation

n/a — not cancelled.
