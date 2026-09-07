---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
depends_on:
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
related_to:
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
  - aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
  - aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
---

# Epic: A score is published with its interval, a difference with its test

Given any published quality score, a reviewer reads the confidence interval around it and the number of licensed, provenance-marked items it was computed over — at least 100 where the suite is built to the publication level — and any claim that two models, engines or variants differ arrives as a paired test over the same items, with its p-value, its direction and its effect size, or it is not published as a difference.

## Context and Value

The audience is the one the PRD adds for the publication: "As an academic or technical reviewer, I want the sample size, the confidence interval and the significance test behind every published claim, so that I can tell a real difference between two models from noise in a small suite." Two questions come before every other one a reviewer asks — how many items, and is the difference distinguishable from noise — and the repository currently answers neither.

Verified current state, at `0f849c8`:

- `suite_gate.py` knows one level. `MIN_SUITE_ITEMS = 20`, `MIN_LANGUAGE_SHARE = 0.25`, `MIN_PER_LANGUAGE_CELL_ITEMS = 10`, and `gate_suite` returns `indicative` with its reasons. There is no publication level, and no row field naming which level a score was produced at.
- `_VALID_PROVENANCE` already accepts `licensed`, but nothing records *which* licence, and neither an item nor a suite records a source benchmark or the rule by which a subset was selected. `contamination_risk` is already forced to `provenance == "public"`: the marking the publication suites need exists, and the items it would mark do not.
- `scoring.py` publishes `SuiteScore`, `GradedSuiteScore` and per-language cells. There is no interval anywhere in the codebase. `agreement.py` is the only module that looks inferential, and it measures two judges against each other — an agreement statistic is not an uncertainty, and neither becomes the other.
- The published arithmetic (`aidd_docs/results/README.md`): `classification-support-routing` holds 20 items, `en` n=10, `fr` n=5, `de` n=5. One item moves the suite score 5 points and a per-language cell 20. `translation-business-short-form` holds 21 items in three directions, seven per direction, and all three of its cells publish as indicative. Two models 10 accuracy points apart are two items apart. Nothing published today distinguishes that from noise, and nothing published says so beyond the word `indicative`.

The PRD already promises the whole of it, in three places, and the code implements none of it: Methodology 4 (a declared suite level, 100 items at publication level, subsets of named public benchmarks with each benchmark's licence and the selection rule recorded), Methodology 24 (a bootstrap confidence interval with its resample count, a paired Wilcoxon with p-value, direction and paired n), and acceptance criteria 131 and 135, which state both as things a published run must show. This epic is the distance between that promise and the repository.

Why both suite levels survive rather than one replacing the other: a publication-level suite drawn from public benchmarks is contamination-marked almost item for item, because a public model may have trained on it. The hand-written 20-item suites are the clean but small counterweight, uncontaminated and CC-BY 4.0 owned by the repo, and their rows are already published. A large contaminated score and a small clean one are different claims, and neither answers the reviewer alone. So the publication suites arrive as new suite ids beside the existing ones, and a published table names the level of every row rather than averaging across them.

One property of the row shape makes the paired half cheaper than it looks: a quality row is written per item and already carries `item_id` and `item_score`/`correct` beside `suite_score`/`suite_accuracy` (`row_contract.REQUIRED_FIELDS["quality"]`). Per-item scores are therefore already published, so a paired test between two configurations is a join on `item_id` over the bundle. Nothing new has to be stored per item, and a third party can recompute the test from the published bundle alone — which is the reason for publishing it at all.

## Boundaries

- Includes: **a second level in the suite gate**. `publication` requires at least 100 items, keeps the 25% per-language share, and requires every item to carry a licence and a source; `development` stays at 20 and is unchanged. `gate_suite` returns the level it certified and every row names it, so a suite that declares `publication` and holds 80 items fails to the level it declared rather than passing quietly at the other one.
- Includes: **licence and source on the item, selection rule on the suite.** Per item: the licence under which that item is redistributed — the source's own for a drawn item, CC-BY 4.0 for the repo's hand-written ones — and the source it was drawn from with that source's revision. Per suite: each benchmark it draws from, that benchmark's licence, and the selection rule as data: a recorded seed, a sampler version and the source revision, so re-running the selection returns the same item ids and the answer to "how did you pick these hundred" is a command rather than a sentence.
- Includes: **two publication-level suites, standing beside the two that exist** — one classification, one translation, each at 100 items or more, each of EN, FR and DE at 25% or more, drawn as seeded subsets of named public benchmarks. They take new suite ids. `classification-support-routing` and `translation-business-short-form` keep their identity, their items, their CC-BY 4.0 licence, their published rows and their `development` level.
- Includes: **bootstrap confidence intervals over the items of a scored batch**, on the suite score and on each per-language cell, for the exact-match and the graded scorer alike, at both levels. The row carries the interval, the resample count and the seed beside the score they qualify, the same way `language_breakdown` already rides every row of a batch.
- Includes: **a paired test between two published configurations on identical items**, named per scoring kind, reported with p-value, direction, effect size, the number of paired items and the number that could not be paired.
- Includes: **a tracked comparison record** as its own artifact in the reference bundle — the two run ids, the suite id and version both sides ran, the paired item ids, the test that was run, its statistic, p, direction, effect size and n. It is produced by a named analysis command over the bundle, not at read time by a view, and it refuses rather than reports when the two sides are not comparable.
- Includes: **the tabular export carrying the interval and the comparison record**, so the third-party researcher of the PRD's user story re-analyses the published results without cloning and running the project.
- Includes: **at least one published batch per new suite in the reference bundle**, under the row epic's established supersede-don't-backfill discipline: new rows are new rows, and no already-published row is retro-fitted with an interval it was never written with.
- Includes: **the threshold review the PRD promises.** Once a publication suite has run, a per-language cell holds 25 items or more and the 10-item indicative floor can no longer fire on its own arithmetic. The review states whether that floor still means anything, whether 20 remains the right development floor, and whether the intervals observed at 100 items make 100 look sufficient or thin — and amends Methodology 4, or leaves it, in writing either way.
- Excludes: **new use cases and new use-case suites.** `no-use-case-is-silently-absent` owns which suites exist. This epic adds a second suite to two use cases that are already exercised; the coverage record's `exercised` entry for classification and translation gains a second suite id, a field addition agreed there, never a new entry here.
- Excludes: **the suite definition shape and the registry that resolves a suite id to a definition** — the same epic. Two suites for one use case is precisely what the registry exists for; this epic consumes it and adds three fields to the shape it defines.
- Excludes: **the size, language and provenance gate itself, the row contract, the writer gate and the reproduction verdict** — `every-published-row-explains-and-reproduces-itself` owns all four. This epic adds one level to that gate and four fields to that contract, and rebuilds neither. The reproduction verdict stays a re-run verdict over one row; it does not become a statistical test, and a confidence interval never decides it.
- Excludes: **machines, compute modes, inference engines, prompt variants and agentic harnesses.** Each is a further row dimension owned elsewhere. A paired test compares two configurations on identical items whatever dimension separates them, so nothing here needs those dimensions to exist first and nothing here changes when they arrive.
- Excludes: **the judge machinery, judge independence, the agreement statistic and any rubric.** The interval and the test are scoring-kind agnostic and apply to a judged score once judged rows exist; `agreement.py` stays what it is.
- Excludes: **the runtime median-and-spread treatment of Methodology 6 and 7**, deliberately and by the PRD's own reasoning. Runtime is a repeated measurement of one machine, not a sample drawn from a population, and an interval or a significance test on it would claim more than the design supports. No runtime field changes in this epic.
- Excludes: **roster composition** — which models and families exist is its own epic — and **rendering any of this to a decision-maker.** `the-pitch-runs-from-a-browser-and-only-with-the-key` owns the views; this epic makes the numbers exist and be correct, not readable at a glance.
- Excludes: **choosing a winner.** A test says whether a difference is distinguishable from noise; it never says whether it matters (PRD Non-Goals).

Criterion ledger, so the scope is checkable rather than described:

| Criterion | Here |
| --- | --- |
| 4 suite size, level and language mix | in scope: the publication level, the source/licence/selection-rule record, and the level on every row. The development level and its constants are the row epic's and stay as they are |
| 5 item provenance | consumed. The contamination-risk marking already exists and is what the drawn items trigger; the licence field is added beside it here |
| 24 inferential statistics | in scope, in full |
| 6, 7 runtime aggregation and spread | out, and explicitly unchanged by design |
| 10, 11 judge protocol and independence | out — judge epic |
| 20, 21 machine and compute mode | out — machine epic |
| 22, 23 engine, prompt variant, harness | out. Each is a comparison this epic's test consumes, never one it defines |
| 1, 2, 3, 8, 9, 12-16, 19 | out — row epic |

### Decisions this epic takes

Six of these widen a criterion beyond the PRD's wording and are marked `→ PRD`; the PRD is where they are settled once the epic proves them.

| Subject | Decision taken here |
| --- | --- |
| The two levels coexist | A publication-level suite is a new suite id beside the hand-written one, not a new version of it and not a replacement. The hand-written items are the only uncontaminated evidence the project owns and their rows are already published; a public subset is contamination-marked item for item. A published table names the level of every row and never averages across the two. |
| The bootstrap is seeded, and the seed is on the row | An unseeded resample returns a different interval on every recomputation, which makes the row unreproducible under criterion 1 and hands the re-run verdict a difference nobody introduced. The row carries the seed, the resample count and the interval method — percentile or BCa, chosen once and named — beside the interval itself. → PRD |
| Failed generations resample with everything else | Criterion 9 puts a failed generation in the denominator as a zero. It stays in the resampled item set. An interval computed over the successes alone qualifies a score nobody published. |
| The paired test is named per scoring kind | Wilcoxon signed-rank over per-item differences is right for a graded or ordinal score — chrF, a 1-5 rubric. It is not right for a binary exact-match score: every non-zero difference is ±1, ties are dropped, and what survives is a sign test over the discordant pairs. A binary-scored suite, which classification is today, carries McNemar's exact test on the discordant pairs instead, and the comparison record names which test it ran and why. A Wilcoxon printed over a binary vector is exactly the finding this epic exists to keep out of a reviewer's hands. → PRD |
| A direction is not an effect size | The record carries a matched-pairs effect size beside p and direction: rank-biserial correlation for the signed-rank test, the discordant-pair odds ratio for McNemar's. A p-value over 100 items answers "distinguishable" and never "by how much", and a table of statistically significant half-point differences is the failure mode a larger suite introduces rather than removes. → PRD |
| Multiplicity is stated, not silently ignored | A full roster produces many pairwise comparisons, and an unadjusted family of p-values is the reviewer's second question. Each record names the comparison family it belongs to and that family's size, and carries a Holm-adjusted p beside the raw one; where no adjustment applies, the record says so rather than staying silent. → PRD |
| A comparison refuses rather than reports | A different suite id, a different suite version, a different item set or two different levels produce a refusal naming the mismatch, not a p-value over whatever happened to overlap. Silently intersecting two item sets publishes a test over a suite that has no name. |
| Unpairable items are counted, never dropped quietly | Both the paired n and the count of items present on one side only sit on the record. A resume gap, a machine refusal or a failed batch shrinks a comparison, and the shrinkage is evidence rather than noise to be tidied away. |
| The interval is published at both levels | A development-level score keeps its `indicative` marking and gains an interval as well. A wide interval on 20 items is the disclosure; withholding it below 100 items would hide the exact property that makes a small number readable. → PRD |
| The licence lives on the item, not only on the suite | A suite may draw from more than one source under more than one term, and the bundle is redistributed item by item. A suite-level licence would be a claim about items it does not describe. |
| Provenance and licence stay author declarations | Unchanged from the row epic's own statement of the limit: nothing verifies that a declared licence or a declared source is the true one. Stated so the limit is disclosed rather than discovered. |

## Success Evidence

Eight checks, each able to fail. The first six are code-level and run on constructed suites, rows and fixtures; the last two need a real run and the licence answer.

- A suite declaring `publication` with 99 items fails the gate to that level naming the count; the same suite at 100 with one language below 25% fails naming the language; `classification-support-routing` still passes at `development` unchanged, and rows from both name the level they were produced at.
- The subset selection, re-run from its recorded seed, sampler version and source revision, returns the same item ids in the same order. Changing the seed changes them; changing nothing changes nothing.
- The bootstrap reproduces a hand-computed interval on a small fixture, and on a proportion agrees with a Clopper-Pearson or Wilson reference interval within a stated tolerance — a proportion is the one case with a closed-form answer to check against, and the exact-match scorer produces proportions.
- The two paired tests reproduce a published worked example each, a signed-rank table and a McNemar 2x2, and the classification suite routes to McNemar's rather than to Wilcoxon without anyone choosing per call site.
- Two published rows from the same suite id and version produce a record carrying paired n, the test named, raw and adjusted p, direction and effect size; the same two rows with one side's `suite_version` bumped produce a refusal naming the version rather than a number.
- Recomputing every interval and every comparison from the published bundle alone, through the same analysis command and no private path, returns identical values — the third-party re-analysis of the PRD's user story, run against ourselves first.
- Both publication suites exist at 100 items or more, with EN, FR and DE each at 25% or more, every item carrying a licence and a source, and one published batch per suite sits in the reference bundle with intervals on its rows.
- The threshold review is written: whether the 10-item per-language floor ever fires again once cells hold 25 items, whether 20 remains the right development floor, and whether the intervals observed at 100 make 100 look sufficient or thin. Recorded as an amendment to Methodology 4 or as an explicit decision to leave it, never as silence.

Falsification the epic accepts in advance: if the licence spike finds no candidate source whose terms permit redistributing a subset inside the bundle's CC-BY 4.0, the outcome as written is not reachable and the manifest fallback below is what ships. That costs the reference bundle the self-sufficiency `aidd_docs/results/README.md` states as its whole property, and the trade is written there rather than absorbed in silence.

Once `done`, record here what the intervals actually were at 100 items against the ones the 20-item suites imply, how many of the paired comparisons run on real rows survived adjustment, and whether the publication and development levels ranked the roster the same way — a disagreement between them is a contamination signal and is worth more than either score alone.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| The suite definition shape and the registry resolving a suite id to a definition | dependency | `no-use-case-is-silently-absent` owns both. Two suites for one use case is what the registry exists for; this epic consumes it and adds source, licence and selection-rule fields to the shape, agreed there rather than forked. |
| The size, language and provenance gate, the row contract and the writer gate | dependency | `every-published-row-explains-and-reproduces-itself` owns them. This epic adds one level to the gate and the interval, level, licence and source fields to the contract, and rebuilds none of them. |
| Which public benchmarks seed the two publication suites, and on what terms | spike | A story-level spike before any suite is authored. Leads, not choices: MASSIVE (intent classification, multilingual) for classification; FLORES-200 or a WMT test set for translation. For each lead: its actual licence, whether that licence permits redistributing a subset inside a CC-BY 4.0 bundle, whether share-alike terms would infect the bundle, and whether EN/FR/DE splits exist at the size needed. The PRD lists this as both a dependency and an open question; nothing here asserts an answer to it. |
| Redistribute the items, or ship a manifest of item ids and a fetch script | decision, deferred to that spike | Settled by what the licences permit, not before. The manifest fallback keeps the epic deliverable and costs the bundle its self-sufficiency; whichever way it goes is written into `aidd_docs/results/README.md` beside the existing statement of what the bundle is. |
| scipy as a dependency, or the statistics implemented in-repo | decision, deferred to a story plan | Not taken here. Either way the tests assert against hand-computed or published reference values rather than against the implementation's own output, and the choice is stated with its dependency cost rather than made silently. |
| The publication-level translation suite also stands beside `translation-business-short-form` rather than replacing it | assumption | Accepted by the same reasoning that keeps the classification pair: the hand-written items are the uncontaminated counterweight, and their rows are already published. |
| Whether the 10-item per-language floor and the 20-item development floor survive the first publication-level run | decision, taken inside the epic | The PRD's own open question, reviewed once a publication suite has run and amended in writing either way. The constants are not moved silently in the meantime. |
| A judged suite's interval, and a paired test over judged scores | assumption | The machinery is scoring-kind agnostic and applies to a judged score once judged rows exist. Nothing here waits on the judge epic, and nothing there re-implements this. |
| Where the comparison record appears in the four views | assumption | The pitch epic renders it. A view stating a difference without its test is that epic's concern, raised there when its stories are written, not designed here. |
| Contamination on a publication-level score | accepted limitation | Nearly every drawn item is contamination-marked, so a publication score is a score over items a model may have trained on. It is disclosed by the marking already in the gate and by the level on the row; it is not measured, and no de-contamination is attempted. |

## Cancellation

n/a — not cancelled.
