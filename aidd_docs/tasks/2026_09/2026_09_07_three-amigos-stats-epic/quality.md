# Three Amigos — quality lens

| Field | Value |
| --- | --- |
| target | `aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md` |
| snapshot | epic, `status: ready`, read at `e8c95e7` (working tree clean) |
| role | quality |
| verdict | **revise** |

Scope of this lens: acceptance observability, states, edge cases, failure modes, verification gaps. Not scope, not priority, not solution choice. Every finding below is a place where the epic as written admits two implementations that publish different numbers, or a check that cannot fail.

## Sources inspected

| Source | Read for |
| --- | --- |
| the epic itself | Boundaries, Decisions, Success Evidence, Dependencies |
| `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` L39-41, Methodology 3, 4, 5, 6-9, 24; acceptance criteria at L131 and L135 | what the epic claims to close |
| `context_input/publication_gap_brief.md` gaps 3 and 7 | the owner's own statement of the gap |
| `src/wave_local_ai_v2/scoring.py` | the shape the interval must ride on: `SuiteScore`, `GradedSuiteScore`, `LanguageCell`, `GradedLanguageCell` |
| `src/wave_local_ai_v2/agreement.py` L34-42, `cohens_kappa` docstring | the project's existing convention for a statistic that refuses to be computed |
| `src/wave_local_ai_v2/suite_gate.py` | `MIN_SUITE_ITEMS`, `MIN_LANGUAGE_SHARE`, `MIN_PER_LANGUAGE_CELL_ITEMS`, `_VALID_PROVENANCE`, the forced `contamination_risk` |
| `src/wave_local_ai_v2/row_contract.py` L188-275 (`REQUIRED_FIELDS["quality"]`), L340-375 (`GRADED_FIELDS`), L69 (`SCHEMA_VERSION = "11"`) | what a quality row already carries and already redistributes |
| `src/wave_local_ai_v2/verdict.py` L241-301 (`compared_field`, `_comparable_field`) | the precedent for naming which field a comparison was decided on |
| `aidd_docs/results/README.md` L1-15, L22-38, L120-190 | the bundle's self-sufficiency claim, its schema lag, the n=20/21 arithmetic, the observed 0.95 -> 0.90 and the absent Mistral batch |

## Findings

### Blocking

**Q1 — "a different item set refuses" and "unpairable items are counted" cannot both hold.**
The Decisions table forbids the exact state the record is required to report. If any item-set difference refuses, the unpairable count is structurally always zero and the field is dead; if a one-sided item is instead counted, the refusal never fires on coverage and the epic's own "silently intersecting two item sets publishes a test over a suite that has no name" is exactly what happens.
Source: the epic, Decisions — "A different suite id, a different suite version, a different item set or two different levels produce a refusal naming the mismatch" against "Both the paired n and the count of items present on one side only sit on the record."
This is not hypothetical: `aidd_docs/results/README.md` L188-190 records `mistral-small-2603` producing **no rows at all** in two runs ("retry budget exhausted after 4 retries"), and `REQUIRED_FIELDS["quality"]` already carries `retries` and `resumed` because partial batches are the normal case.
Proposed amendment: split the two ideas the phrase "item set" is carrying. The *suite's declared item set* (suite id + version + `prompt_set_hash`) mismatching is a refusal. The *observed row set* (which items each side actually produced rows for) differing is not a refusal: it is the paired n plus the one-sided count, and the record additionally names which side each unpaired item was missing from. State the second explicitly, because a reviewer's first question about a shrunken comparison is which side shrank.

**Q2 — a Holm-adjusted p is not a property of one record, and the epic makes it one.**
Holm is a function of the whole family's p-values. A record written when the family holds ten comparisons carries an adjusted p that is arithmetically wrong the moment an eleventh is run, so either every sibling record is rewritten — which breaks the supersede-don't-backfill discipline this epic explicitly adopts from the row epic — or published adjusted p-values silently go stale. The family boundary is also undeclared: all pairs within one suite, one campaign, one published table, or one model-versus-all? Each choice yields a different family size and therefore a different adjusted p from identical data.
Source: the epic, Decisions — "Each record names the comparison family it belongs to and that family's size, and carries a Holm-adjusted p beside the raw one"; and Boundaries — "It is produced by a named analysis command over the bundle, not at read time by a view."
Proposed amendment: make the family the unit of the artifact, not an attribute of a member. One analysis invocation produces one *comparison family record* holding every pairwise test it ran, its declared family definition, its size, and the Holm-adjusted p of each member computed over that closed set. A family is immutable once written; adding a comparison produces a new family record that supersedes the old by id, which is the supersede discipline rather than a violation of it. Then define, in one sentence, what a family is by default. Also name when "no adjustment applies": a family of one is a family of one and its adjusted p equals its raw p — say that, rather than leaving a record able to omit the field.

**Q3 — the manifest fallback protects nothing, because every published quality row already redistributes the item verbatim.**
The falsification clause treats "ship a manifest of item ids and a fetch script" as the escape if a licence forbids redistributing items. It does not escape: `REQUIRED_FIELDS["quality"]` requires `prompt` and `expected_label` on every row, and `GRADED_FIELDS` requires `reference_output`. A published `quality-reference.jsonl` therefore contains each drawn item's input text, its gold label and its gold reference translation, item for item, whatever `suite-definitions/` does or does not hold. Withholding the suite definition while shipping the rows costs the bundle its self-sufficiency and still redistributes the content.
Source: `src/wave_local_ai_v2/row_contract.py` L243-246 (`"prompt"`, `"expected_label"`) and L361-370 (`"reference_output"` — "The text the score was computed against"); the epic, Success Evidence — "the manifest fallback below is what ships. That costs the reference bundle the self-sufficiency `aidd_docs/results/README.md` states as its whole property".
Proposed amendment: state the real fallback ladder, because it has three rungs and the epic names one. (a) Licence permits redistribution: items and rows both ship, nothing changes. (b) Licence forbids redistribution: the manifest is not enough — the *rows* must also be published with `prompt`, `expected_label` and `reference_output` redacted to a per-item content hash, which makes the score unrecomputable from the bundle and is a far larger cost than the sentence in the epic implies. Say so, or rule the source out at the spike rather than at ship time. (c) Share-alike (see Q14). Whichever rung, the spike's exit criterion must be evaluated against the row contract, not only against `suite-definitions/`.

**Q4 — the bootstrap is underspecified in four independent ways, each of which changes the published number.**
The epic requires the row to carry "the interval, the resample count and the seed" and names the method as "percentile or BCa, chosen once and named" — then does not choose. Four values are missing and none is inferable:

1. **The confidence level.** 95% is nowhere stated, in the epic, in Methodology 24, or in the criterion at L135.
2. **The resample count.** "Reported" is not "specified": two runs at 1 000 and 10 000 resamples publish different intervals for the same row and both satisfy the epic.
3. **The method.** Percentile and BCa differ materially at n=20; on the observed classification accuracies (0.80, 0.95 — `aidd_docs/results/README.md` L72-78) the difference is not academic.
4. **The resampling unit for a per-language cell.** Resampling the whole suite and recomputing each cell gives cells of varying n; resampling within each language stratum holds n fixed. Two defensible implementations, two intervals, and the epic's "on the suite score and on each per-language cell" does not pick.

Source: the epic, Boundaries — "bootstrap confidence intervals over the items of a scored batch, on the suite score and on each per-language cell"; Decisions — "the interval method — percentile or BCa, chosen once and named".
Proposed amendment: fix all four in the epic, not in a story plan, since each is a published number rather than an implementation detail. A defensible set: 95%, 10 000 resamples, BCa, stratified within language for a cell and unstratified for the suite score — and the confidence level joins the seed, method and resample count on the row, because a row that carries three of the four still does not pin its own interval.

**Q5 — a recorded seed does not reproduce an interval unless the generator is recorded too.**
`numpy.random.default_rng(7)`, `random.Random(7)` and `scipy.stats.bootstrap` seeded at 7 draw three different resample sequences. The epic defers "scipy as a dependency, or the statistics implemented in-repo" to a story plan while asserting the seed makes the interval reproducible — so the two candidate implementations publish different intervals from the same recorded seed, and nothing on the row detects it. This is precisely the "two implementations publish different numbers" failure the epic exists to prevent, sitting inside the epic's own reproducibility guarantee.
Source: the epic, Decisions — "An unseeded resample returns a different interval on every recomputation, which makes the row unreproducible under criterion 1"; Dependencies — "scipy as a dependency, or the statistics implemented in-repo ... Not taken here."
The project already solved this shape twice: a graded row carries `metric_id`, `metric_version` and `metric_params` so a third party recomputes chrF with sacreBLEU and catches us (`row_contract.py` L353-359), and a fiche carries the llama.cpp build id.
Proposed amendment: the interval block carries the generator identity and version alongside the seed, on the same reasoning as `metric_id`/`metric_version` — for example `rng_id: "numpy.random.PCG64"`, `rng_version`, and the library id and version if the resampling is delegated. Add a success check that the recorded block, replayed, returns the identical interval bit for bit; today's check ("reproduces a hand-computed interval on a small fixture") passes for both implementations and discriminates neither.

### Material

**Q6 — Wilcoxon's tie handling and the rank-biserial definition are unrecorded, and both move the published p.**
`scipy.stats.wilcoxon` takes `zero_method` in {`wilcox`, `pratt`, `zsplit`}, a continuity `correction`, and `mode` in {`auto`, `exact`, `approx`}. On this project's data ties are not exotic: Methodology 9 keeps a failed generation in the denominator as a zero, so an item both sides failed is an exact zero difference, and two identical translations score identical chrF. `wilcox` drops those pairs and shrinks n; `pratt` keeps them. Rank-biserial correlation likewise has more than one standard formula, and they disagree under ties. The epic names the test and the effect size and records neither convention.
Source: the epic, Decisions — "Wilcoxon signed-rank over per-item differences ... rank-biserial correlation for the signed-rank test"; and "Criterion 9 puts a failed generation in the denominator as a zero. It stays in the resampled item set."
Proposed amendment: name `zero_method`, the exact-versus-normal-approximation rule (and its n threshold), the continuity correction, and the rank-biserial formula by its definition, and put the tie count and the zero-difference count on the record beside the paired n. A reviewer reading a p-value over 100 items wants to know how many of those pairs actually carried information.

**Q7 — every one of these statistics has a degenerate case, and none has a null-with-a-reason rule.**
Four concrete states the epic does not name: a suite scored 1.0 or 0.0 — every percentile resample returns the same value and the interval collapses to a zero-width `[1.0, 1.0]`, publishing certainty over 20 items; McNemar with zero discordant pairs (b + c = 0) — p undefined; the discordant-pair odds ratio with c = 0 — infinite; and a per-language cell with n = 0, where `score_suite_by_language` already returns `accuracy=0.0, n=0` and a bootstrap over an empty set is undefined.
Source: `scoring.py` `score_suite_by_language` — "if n == 0: accuracy = 0.0"; `aidd_docs/results/README.md` L78 — a published `mistral-small-2603` accuracy of 0.95 on 20 items is one item from the degenerate case.
The project already has the convention and the epic does not consume it: `agreement.py` returns `(value, null_reason)` with exactly one non-null and refuses to publish a mathematically defined but misleading `κ = 0`, naming `zero_variance`, `zero_expected_disagreement` and `insufficient_items` (`agreement.py` L34-42 and the `cohens_kappa` docstring — "publishing that `0` would read as chance-level disagreement when the two may have agreed on every single item").
Proposed amendment: adopt the same shape for the interval, the p-value and the effect size — a value plus an exclusive named null reason, with the degenerate cases above enumerated as named reasons. Add a success check per named reason. Without it, a zero-width interval on a perfect score is the most quotable wrong number this epic could ship.

**Q8 — the comparison never states which field it tests, and comparing an exact-match row against a graded row is not refused.**
A quality row carries `correct` (exact-match) or `item_score` (graded, via `GRADED_FIELDS`) — the two are deliberately kept apart, and `scoring.py` says why in its module docstring ("a chrF mean is not an accuracy, and one function returning either would publish a graded score under an exact-match name"). The comparison record names the test it ran but not the field it read, and its refusal list does not include a scoring-kind mismatch. Relatedly, the routing rule "the classification suite routes to McNemar's ... without anyone choosing per call site" does not say what it routes off. There is no `scoring_kind` field on a row; presence of `item_score` is the only signal, which is inference rather than declaration, and it has only two branches while the epic asserts the machinery is scoring-kind agnostic and applies to a judged 1-5 ordinal.
Source: `src/wave_local_ai_v2/verdict.py` L241-301 already solved exactly this, and `aidd_docs/results/README.md` L155-157 records why — "every verdict block names `compared_field: 'item_score'` ... since a translation row carries no `predicted_label` for the old comparison to read".
Proposed amendment: the record carries `compared_field`, the same name `verdict.py` already uses, and a scoring-kind mismatch between the two sides is a refusal. Make the routing a declared property of the suite or the metric rather than an inference from a field's presence, so that a future binary 0/1 rubric does not route to Wilcoxon — which is the single failure the epic states it exists to keep out of a reviewer's hands.

**Q9 — the refusal list omits the generation caps Methodology 3 makes mandatory, and the metric version.**
Two sides can share a suite id and version and still be incomparable: `max_output_tokens`, `stop_sequences`, `context_length` and `thinking_policy` all ride the row (`REQUIRED_FIELDS["quality"]`), Methodology 3 requires them identical across every model compared on an item, and a truncation cap difference manufactures failures on one side that the paired test reads as quality. On a graded row, `metric_id`/`metric_version`/`metric_params` differing means chrF v1 numbers are being tested against chrF v2 numbers.
Source: PRD Methodology 3 — "are identical across every model compared on an item, and are recorded per row"; `row_contract.py` L249-256 and L352-359.
Proposed amendment: extend the refusal list to the four generation constraints and the metric triple, and have the refusal name the differing field, matching `verdict.py`'s `differing_fields` convention rather than inventing a second one.

**Q10 — "direction" has no stated sign convention, so two implementations report opposite directions from identical data.**
The record holds two run ids. Which is the reference — which side the difference is computed as minus — is not stated anywhere, and neither is how direction is expressed (a sign, a run id, a model name). A published claim whose direction can flip on an implementation detail is worse than no claim.
Source: the epic, Boundaries — "reported with p-value, direction, effect size"; Success Evidence — "a record carrying paired n, the test named, raw and adjusted p, direction and effect size".
Proposed amendment: the record names a `reference_run_id` and a `candidate_run_id`, every difference is candidate minus reference, and direction is expressed as the run id of the higher-scoring side plus the sign. `verdict.py` already carries `reference_run_id` for the runtime verdict; reuse the name.

**Q11 — nothing prevents seed-shopping, which destroys the claim the seed exists to make.**
A publication suite must hold at least 100 items with EN, FR and DE each at 25% or more. A single seed drawn over a pooled source will frequently miss that; the operator re-runs with a new seed until the gate passes. The recorded artifact is then a seed that produces a compliant suite, and nothing records how many were tried — so "the subset was selected by a recorded seed" reads to a reviewer as unbiased sampling when it may be selection on the outcome. The same applies to label balance on the classification side: a drawn subset with a degenerate class distribution is not comparable to `classification-support-routing`, and nothing in the epic constrains it.
Source: the epic, Boundaries — "the selection rule as data: a recorded seed, a sampler version and the source revision, so re-running the selection returns the same item ids"; `suite_gate.py` `MIN_LANGUAGE_SHARE = 0.25`.
Proposed amendment: make the sampler stratified by construction — per language, and per label for a classification source — so the first seed satisfies the gate by design rather than by luck, and the strata definition joins the seed in the recorded selection rule. If seeds are ever retried, record the attempt count and every seed tried; a reviewer who finds an unrecorded retry loop discards the suite.

**Q12 — the recorded seed does not reproduce the draw unless the source enumeration order is pinned.**
A seeded sample is a function of the seed *and* of the order the source rows arrive in. The same upstream revision read through two loader versions, two splits, or with a different shard order enumerates differently, and the same seed then draws different items. The success check — "re-run from its recorded seed, sampler version and source revision, returns the same item ids in the same order" — will pass on the machine that wrote it and can fail for the reviewer who reproduces it, which is the reader the epic is for.
Source: the epic, Success Evidence, second check.
Proposed amendment: the selection rule states the canonicalisation applied before sampling — source rows sorted by a named stable source key, that key named on the suite — and the loader library and version join the sampler version in the record. Then the check is a claim about the world rather than about one machine. This is the same discipline `row_contract`'s fiche hashing already applies by normalising over a projection rather than over the capture.

**Q13 — no per-item content hash, so a fetched item cannot be proven to be the item that was scored.**
An upstream revision can be retagged and an individual item edited or withdrawn. The suite carries a `prompt_set_hash` over the whole set, which detects that *something* changed but names nothing, and under the manifest fallback the fetched items are the only copy the reviewer has. The fallback is then unverifiable, not merely inconvenient.
Source: `REQUIRED_FIELDS["quality"]` carries `prompt_set_hash` at suite level; the epic, Boundaries — "one classification, one translation ... drawn as seeded subsets of named public benchmarks".
Proposed amendment: each drawn item carries a content hash over its own normalised text, beside its licence and its source. It makes the manifest fallback checkable, it makes an upstream edit nameable at the item rather than at the set, and it costs one field.

**Q14 — the falsification clause names one licence outcome and there are three; share-alike has a different fallback.**
The epic pre-accepts falsification only for "no candidate source whose terms permit redistributing a subset inside the bundle's CC-BY 4.0". The likelier branch for the named leads is share-alike: FLORES-200 ships under CC-BY-SA, which the epic itself flags as an infection risk in the same table, and the manifest fallback is the wrong remedy for it — the remedy for share-alike is segregating those items and their derived rows under their own licence file, not withholding them. The epic's own gap brief fixes the bundle at CC-BY 4.0 (gap 8, 2026-09-06 decision), so an SA source cannot simply be absorbed.
Source: the epic, Dependencies — "whether share-alike terms would infect the bundle"; Success Evidence — "if the licence spike finds no candidate source whose terms permit redistributing a subset inside the bundle's CC-BY 4.0"; `context_input/publication_gap_brief.md` gap 8 — "suite items and the reference bundle carry CC-BY 4.0".
Proposed amendment: the spike returns one of three verdicts per candidate — permissive, share-alike, or no-redistribution — and the epic names the consequence of each in advance, so the answer routes to a decision rather than to a new discussion. Q3's ladder and this one are the same amendment written from two directions.

**Q15 — the threshold-review check cannot fail.**
"Recorded as an amendment to Methodology 4 or as an explicit decision to leave it, never as silence" passes for any document that says either thing, including one that says it without evidence. It is the only one of the eight checks whose pass condition is the existence of a file. The other seven are falsifiable; this one is a deliverable dressed as a check.
Source: the epic, Success Evidence, eighth check.
Proposed amendment: give the review a falsifiable content requirement — it cites the observed interval widths at n=100 against those at n=20 for the same use case, the observed per-language cell counts, and the number of times the 10-item floor fired on the publication run — and it is wrong if any cited figure disagrees with the published rows. Then the review can be checked rather than merely produced.

**Q16 — the bootstrap validation check cannot fail either, on two counts.**
"agrees with a Clopper-Pearson **or** Wilson reference interval within a **stated** tolerance": Clopper-Pearson is conservative and Wilson is not, they differ visibly at n=20, and an implementation free to pick whichever it is closer to is validated against nothing. The tolerance is described as stated and is not stated.
Source: the epic, Success Evidence, third check.
Proposed amendment: name one reference interval, name the tolerance as a number, and name the n and the proportion the comparison is made at. A validation check whose reference is chosen after seeing the result is not a check.

**Q17 — Success Evidence promises a cross-level comparison that nothing in Boundaries produces.**
"whether the publication and development levels ranked the roster the same way — a disagreement between them is a contamination signal and is worth more than either score alone." The two levels are different suite ids over different items, so the comparison record refuses them by design (correctly). No rank-agreement artifact, statistic or command is in scope, so the epic's most interesting stated finding has no producer and no acceptance criterion.
Source: the epic, Success Evidence, closing paragraph, against Boundaries and the Decisions row "A comparison refuses rather than reports".
Proposed amendment: either state that this observation is read off the published tables by hand and is not a computed artifact — which is honest and cheap — or bring a rank-agreement statistic into scope with its own check. Leaving it as a promise in the closing paragraph makes it look like a deliverable that nothing delivers.

### Minor

**Q18 — three cheap invariants are absent, and each catches a whole class of implementation error.**
Nothing in the eight checks asserts that the point estimate lies inside its own interval; that the n the interval was computed over equals the n already published in `language_breakdown` / `score_breakdown`; or that every row of one batch carries the identical interval block, which is what makes the interval a batch statistic rather than a per-row one. The third matters specifically on a resumed batch — `retries` and `resumed` are required fields precisely because partial and resumed runs are normal here.
Source: `row_contract.py` L188-275; `aidd_docs/results/README.md` L22-32 on the `"7"` -> `"8"` bump that made those two fields required.
Proposed amendment: add the three as one success check. They are assertions, not analysis, and they fail loudly when the bootstrap and the score were computed over different item sets.

**Q19 — "one published batch per new suite in the reference bundle" inherits an unlisted cost.**
The committed bundle sits at `schema_version` `"7"` while `row_contract.SCHEMA_VERSION` is `"11"`, and `aidd_docs/results/README.md` states that regenerating it is a protocol-bound bench job filed in `aidd_docs/backlog/tech-debt.md`, not a side effect of a schema bump. Adding two publication-level batches means running that protocol, and the epic's Dependencies table does not name it.
Source: `aidd_docs/results/README.md` L22-38; `row_contract.py` L69.
Proposed amendment: name the bundle regeneration protocol as a dependency with its owner, so the last two checks are not discovered to be bench-time work after the first six pass.

## Questions

| # | Finding | Missing decision or evidence | What the answer unlocks |
| --- | --- | --- | --- |
| 1 | Q4 | The confidence level, the resample count, the interval method, and the per-language resampling unit — four values, decided in the epic rather than in a story plan | Two implementations converging on one published interval; three of the eight success checks become writable |
| 2 | Q5 | Whether scipy is taken as a dependency, given that the choice now determines a published number rather than only an implementation | Whether the recorded seed needs a generator id beside it, and what the reproduce-bit-for-bit check runs against |
| 3 | Q2 | What a comparison family is by default — one suite, one campaign, one published table, or one model against all | Whether the artifact is a per-comparison record or a family record; without it no adjusted p can be computed at all |
| 4 | Q3, Q14 | Whether the licence spike may return "share-alike" or "no redistribution" as an acceptable outcome, given that the rows themselves carry `prompt`, `expected_label` and `reference_output` verbatim | Whether the epic's outcome is reachable, and which of the three fallback rungs is being planned for |
| 5 | Q6 | The tie and zero-difference convention for Wilcoxon, and which rank-biserial formula | A p-value and an effect size that two implementations agree on; the record's field list |
| 6 | Q11 | The stratification keys for the sampler — language alone, or language and label — and whether seed retries are permitted at all | Whether the seeded selection is a reproducibility claim or also an unbiasedness claim |

## What this lens did not find fault with

Recorded so the reconcile step can tell silence from assent. The per-scoring-kind test choice (McNemar for binary, Wilcoxon for ordinal) is right and is the epic's strongest single decision. Keeping failed generations in the resample is right and consistent with Methodology 9. Publishing the interval at the development level too is right — withholding it below 100 items would hide exactly what makes a small number readable. Putting the licence on the item rather than the suite is right. Refusing rather than reporting on a genuine suite mismatch is right. Excluding runtime from inferential treatment is right and correctly reasoned. The observation that per-item rows already carry `item_id` and the score, so a paired test is a join over the published bundle, is verified against `REQUIRED_FIELDS["quality"]` and holds.
