# Three Amigos — reconciliation

| Field | Value |
| --- | --- |
| target | `aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md` |
| snapshot | epic at `status: ready`, read at `e8c95e7` by all three lenses |
| inputs | `product.md` (9 findings, verdict `revise`), `delivery.md` (10 findings, verdict `revise`), `quality.md` (19 findings, verdict `revise`) |
| verdict | **`revise`** — 29 amendments applied to the epic; 1 cross-lens conflict and 8 open decisions remain, none of which the reports resolve |

Validation: three distinct roles, one target, one snapshot, every finding carrying a source pointer. No report rejected.

The epic's boundaries against its siblings are unchanged. Three findings that would have moved one — the `depends_on` edge (D1), the export ownership split (D2), and coupling the comparison family to a sibling's campaign declaration (P5) — are recorded as open items in the epic's `Dependencies and Unknowns` rather than applied.

---

## 1. Applied to the epic

29 amendments. Each names the finding ids it came from and the section it landed in.

### Convergent — two or more lenses, one amendment

| # | Amendment | From | Landed in |
| --- | --- | --- | --- |
| A1 | A seed alone does not reproduce an interval: the row carries the generator identity and version and a versioned draw-procedure id (draw order, tie handling, percentile interpolation) beside it, on the same reasoning that already puts `metric_id`/`metric_version` on a graded row | D5 + Q5 | Decisions, row renamed *A seed alone does not reproduce an interval*; Boundaries, bootstrap bullet |
| A2 | The statistics ship in-repo on the standard library, with `scipy` as a **dev-only** test oracle — decided rather than deferred, since it determines a published number | D6 (0.18 s stdlib bootstrap; stdlib-exact forms; bundle epic precedent; OSV gate; numpy/pandas transitive-only via `codecarbon`) + Q5 (demands the decision) | Decisions, new row; `Dependencies`, scipy row now `taken` |
| A3 | The comparison family is the unit of the artifact, not an attribute of a member: one immutable family record per analysis invocation, superseded by id, default one suite × one dimension, family of one states adjusted = raw | Q2 (staleness breaks supersede discipline) + P5 (undeclared family is a free parameter) + P4 (it moves the threshold by an order of magnitude) | Boundaries, new bullet; Decisions, *Multiplicity* row rewritten |
| A4 | The licence spike returns one of three verdicts with its consequence pre-written; the manifest fallback is deleted as a remedy, because the rows already redistribute `prompt`, `expected_label` and `reference_output` verbatim | Q3 + Q14 + delivery's closing note (check share-alike first) | Decisions, new row; Success Evidence, falsification clause rewritten |
| A5 | The inferential half is demonstrable on rows already in the bundle, with the two published McNemar results stated | D7 (measured) + P7 (minimum publishable unit) | Success Evidence, preamble |

### Single-lens, uncontested

| # | Amendment | From | Landed in |
| --- | --- | --- | --- |
| A6 | The publication asks three questions; this epic reaches two, and says which | P1 | Context and Value, new paragraph |
| A7 | The exclusion is a winner *committed before the evidence* — the PRD's actual wording — not any derived ranking | P2 | Boundaries, exclusion rewritten |
| A8 | A minimum detectable effect is published beside every interval, per suite and scoring kind | P3 | Boundaries, new bullet; Decisions, new row |
| A9 | 100 items justified on the project's own arithmetic: Holm over six comparisons needs raw p ≤ 0.0083, McNemar exact reaches that only at 8 one-directional discordant pairs — a 40% swing on a 20-item suite | P4 | Decisions, new row |
| A10 | A 25-item language cell resolves nothing under ~25 points; the floor ceasing to fire is not the cell becoming readable, and removing an `indicative` mark is itself a claim | P6 | Boundaries, threshold-review bullet |
| A11 | One derived reader-facing verdict on the record — distinguishable / not distinguishable / not comparable — with every raw input beside it | P8 | Boundaries, comparison-record bullet |
| A12 | The record names the set of row fields on which the two sides actually differ, computed not declared; more than one member is an observation naming the confound, never a clean test | D3 | Boundaries, comparison-record bullet; Success Evidence, new check |
| A13 | The cloud retry budget (4, shared per batch) and per-batch resume are named as a delivery precondition at 100-item scale, with the 13.7-minute Google pacer floor | D4 | Dependencies, new row |
| A14 | New contract fields are declared unrendered in `read_model.py`'s view partition by this epic; whether the pitch renders them is that epic's call | D10 | Boundaries, new include |
| A15 | Where a 100-plus item suite's items live is a decision for the suite seam; generated Python source is the wrong answer | D9 | Dependencies, new row |
| A16 | Declared item set (`suite_id` + `suite_version` + `prompt_set_hash`) mismatch refuses; **observed** row set difference does not — it is the paired n plus the one-sided count | Q1 (blocking: the two rules as written cannot both hold) | Decisions, refusal row rewritten |
| A17 | Confidence level (95%), resample count (10 000) and per-language resampling unit (stratified within language for a cell, unstratified for the suite score) fixed in the epic | Q4 | Boundaries, bootstrap bullet |
| A18 | Wilcoxon's zero-difference convention, exact-vs-approximation rule and threshold, continuity correction, and the rank-biserial formula are named on the record, with tie and zero-difference counts beside the paired n | Q6 | Boundaries, paired-test bullet |
| A19 | A named null reason wherever a statistic is undefined or misleading, on `agreement.py`'s value-plus-one-reason shape; four degenerate cases enumerated | Q7 | Boundaries, new bullet; Decisions, new row; Success Evidence, new check |
| A20 | The record names its `compared_field` (`verdict.py`'s existing name) and a scoring-kind mismatch is a refusal | Q8 | Boundaries, paired-test bullet; Decisions, refusal row |
| A21 | The refusal list extends to Methodology 3's four generation constraints and the metric triple, naming the differing field on `verdict.py`'s `differing_fields` convention | Q9 | Decisions, refusal row; Success Evidence |
| A22 | Direction is `candidate` minus `reference` against a declared `reference_run_id`/`candidate_run_id`, reusing `verdict.py`'s name | Q10 | Boundaries, paired-test bullet |
| A23 | The sampler is stratified by construction (language, and label for a classification source); any seed retry records the attempt count and every seed tried | Q11 | Boundaries, selection-rule bullet |
| A24 | The selection rule states the canonicalisation before sampling — source rows sorted by a named stable source key — with the loader library and version beside the sampler version | Q12 | Boundaries, selection-rule bullet |
| A25 | Each drawn item carries a content hash over its own normalised text | Q13 | Boundaries, selection-rule bullet |
| A26 | The threshold review gets a falsifiable content requirement: it cites observed interval widths at n=100 against n=20, cell counts, floor firings and the observed MDE, and is wrong if any figure disagrees with the published rows | Q15 | Success Evidence, last check |
| A27 | The bootstrap validation names **one** reference (Wilson 95%), a numeric tolerance (0.01 per bound) and the n and p it is checked at; a replay check is added that returns the interval bit for bit; three invariants added (estimate inside its interval, n matches the published breakdown, identical interval block across a batch) | Q16 + Q18 + D6's measured [0.570, 0.750] vs Wilson [0.563, 0.745] | Success Evidence, checks 3–6 |
| A28 | The cross-level rank comparison is stated as read off the tables by hand, explicitly not a computed artifact | Q17 | Success Evidence, closing paragraph |
| A29 | The reference bundle regeneration protocol named as a dependency (`schema_version` `"7"` committed vs `SCHEMA_VERSION` `"11"`, a protocol-bound bench job in tech-debt) | Q19 | Dependencies, new row |

Net effect on the epic: Success Evidence goes from 8 checks to 13; the Decisions table from 11 rows to 16, with the `→ PRD` count corrected from a stated six (only five were marked) to an actual nine; Dependencies from 10 rows to 21.

---

## 2. Conflict

One, and only one, where the lenses contradict each other on the same section.

### C1 — percentile versus BCa

| Lens | Position | Evidence |
| --- | --- | --- |
| quality (Q4) | **BCa**, in a proposed fixed set of 95% / 10 000 / BCa / stratified-per-cell | "Percentile and BCa differ materially at n=20; on the observed classification accuracies (0.80, 0.95) the difference is not academic." |
| delivery (D5, D6) | **Percentile** | "BCa needs an inverse normal CDF and a jackknife, each with its own convention choices; percentile has none and is the cheaper commitment." |
| product | silent | — |

Neither position is ranked. Both are preserved in the epic: the other three of Q4's four values are applied, and the method is the one value left explicitly open in `Dependencies`.

**Recommendation: percentile.** The binding constraint this epic sets itself is a third party recomputing an identical number from the published bundle alone — that is Success Evidence check 11 and the reason the epic exists. Every additional convention (jackknife leave-one-out order, inverse-normal implementation, bias-correction estimator) is one more place that reproduction diverges, and neither lens quantified BCa's accuracy gain at n=100. Q4's counter-argument holds only at n=20, where the honest disclosure is the interval's width, not its second-order correction. Decide before the first interval is published; the row carries the method either way, so the decision is reversible at the cost of a schema bump and a supersede.

---

## 3. Open decisions

Recorded in the epic's `Dependencies and Unknowns`, none taken. Ordered by how much else they block.

| # | Decision | From | Recommendation |
| --- | --- | --- | --- |
| O1 | **Does the done gate split?** Two of thirteen checks depend on a licence spike whose failure the epic anticipates, while the downstream engine/variant epic declares `depends_on` on the whole. | P7, D7, product Q2 | **One epic, two gates.** Gate one — intervals at both levels, the paired tests, the detection limit, the reader verdict, the family record, the refusals — touches no benchmark, licence or new item and is demonstrable on published rows today. The downstream epic depends on gate one. Gate two is the publication suites and the licence spike. Two epics instead of two gates is a backlog-shape call; neither lens took it. |
| O2 | **Who owns the tabular export?** Both this epic and `one-download-holds-the-tables-their-licences-and-how-to-cite-them` claim it; neither declares the other; no exporter exists in `src/`. | D2 (blocking) | The bundle epic owns the command, column dictionary and schema; this epic contributes the interval and comparison-record columns plus its own analysis command. **Not applied** — it moves a boundary against a sibling, which this reconciliation was told to leave alone. Settle it in both epics at once, with a `related_to` edge in each direction. |
| O3 | **Does the `depends_on` edge on `no-use-case-is-silently-absent` narrow to the suite seam?** As written it serialises this epic behind six suites, a container sandbox and a RAG corpus, and stalls the downstream epic in turn. | D1 (blocking) | Lift the suite definition shape and registry into a story both epics declare, and let both depend on that. **Not applied** — same reason as O2. The epic's `Dependencies` row now states that only the seam is on its path; the frontmatter still names the sibling whole. |
| O4 | **What declares a comparison family?** The epic now defaults to one suite × one dimension, closed at analysis time. | P5, quality Q3 | Let a campaign declaration own it where one exists, with a record whose family size disagrees with the campaign's cell count refused — the same discipline as the existing suite-version refusal. **Not applied**: it couples this epic to the engine/variant epic's artifact. The granularity moves the threshold by an order of magnitude, so this is the highest-leverage of the open items after O1. |
| O5 | **Which level is the article's headline number?** | P9, product Q6 | The development-level score leads, with the publication-level score beside it as the scale check — the hand-written items are the only uncontaminated evidence the project owns. The obvious answer is the reverse, which is why it should be written down rather than settled by whichever table gets built first. |
| O6 | **Is the publication size target 100 items or 300?** At the 25% minimum share, 100 items is 25 per language, resolving nothing under ~25 points. | P6, product Q4 | Answer "is a per-language claim a headline of the article" first. If yes, 300. If no, 100 with the cells published as indicative and said to be. The epic now states the arithmetic either way. |
| O7 | **Who owns a derived leader set** — the models not distinguishable from the best, per suite and machine class? | P2, product Q1 | It is a direct read of the comparison records, and it is what a reader wanting to "anticipate the results" needs. Neither this epic nor the pitch epic owns it. Assign it or accept it is assembled by hand outside the backlog. |
| O8 | **Who raises the retry budget and resume granularity to 100-item scale?** | D4, delivery Q4 | The row epic's `a-rate-limited-run-persists-resumes-and-never-re-pays`, revisited at the new size. It is not a statistics problem, and the publication campaign is the expensive place to discover it. |

Two further open items are recorded in the epic without a recommendation, because no lens produced evidence either way: whether a same-model cross-machine paired test is a comparison the publication wants (product Q5), and where a publication suite's items live in the repository (D9, deferred to the suite seam).

---

## 4. PRD-level changes — listed, not applied

`aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`. The epic marks nine decisions `→ PRD`; four of the nine are new here. Nothing below is edited.

| # | PRD target | Change | Source |
| --- | --- | --- | --- |
| R1 | Methodology 24 | The interval block is six values, not three: confidence level, resample count, method, seed, generator identity and version, and a versioned draw-procedure id. A seed alone does not make a bootstrap reproducible. | A1 |
| R2 | Methodology 24 | A minimum detectable effect is a published output per suite per scoring kind, beside the interval. | A8 |
| R3 | Methodology 24 | The comparison family, not the individual comparison, is the unit of the published artifact; a family record is immutable and superseded by id. Define what a family is by default. | A3 |
| R4 | Methodology 24 | An undefined or misleading statistic publishes a named null reason, never a number — the `agreement.py` convention extended to intervals, p-values and effect sizes. | A19 |
| R5 | Methodology 24 (already `→ PRD`) | The paired test is named per scoring kind — McNemar's exact for binary, Wilcoxon signed-rank for ordinal — and the record names which and why, with its tie conventions and effect-size formula. | epic, extended by A18, A20 |
| R6 | Methodology 3 + 24 | The comparison refusal list covers `max_output_tokens`, `stop_sequences`, `context_length`, `thinking_policy` and the metric triple, not only the suite identity — Methodology 3 already requires the first four identical across compared models. | A21 |
| R7 | Methodology 4 | The selection rule is a seed **plus** a canonical source ordering key, a loader library and version, and stratification keys; drawn items carry a per-item content hash. A seed without them does not replay for a third party. | A23, A24, A25 |
| R8 | Methodology 4 + 5 | Per-item licence field beside the existing provenance marking, with the source and its revision. | epic, unchanged |
| R9 | Methodology 4 | A per-language cell at the 25% minimum share holds ~25 items and does not become readable when the 10-item floor stops firing. Either the size target moves to the cell, or per-language claims are published as indicative and said to be. Amended by the threshold review either way. | A10, O6 |
| R10 | Open Questions + Dependencies | The licence question has three outcomes, not two — permissive, share-alike, no-redistribution — each with a pre-written consequence, and the exit criterion is evaluated against the row contract rather than against `suite-definitions/`. | A4 |
| R11 | Non-Goals | Only if O7 is answered yes: the non-goal is a winner committed *up front*, and a leader set derived from the published tests is not one. The PRD's wording is already correct; the epic was over-reading it. | A7, O7 |

---

## 5. What the lenses explicitly did not fault

Recorded so the next reader can tell silence from assent. From the quality report, verified against the code: the per-scoring-kind test choice, keeping failed generations in the resample, publishing the interval at development level too, the licence on the item rather than the suite, refusing on a genuine suite mismatch, excluding runtime from inferential treatment, and the observation that per-item rows already make a paired test a join over the published bundle. From delivery: the campaign is cheap — both new suites, four models, one machine is 1.4 hours local and 0.16 EUR of cloud subject cost, and the full 48-cell sibling matrix is under 10 EUR — so the cost story is told in operator hours and API pacing, not money, and D4 is the item that actually threatens the campaign. No amendment was required for that finding and none was made.

## 6. Status

The epic's frontmatter still reads `status: ready`. With C1 and O1–O8 open it arguably is not. Not changed here — that is the caller's call, and the open items are all recorded in the epic itself where a story-slicing pass will hit them.
