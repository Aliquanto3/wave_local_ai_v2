# Three Amigos — product lens

**Target:** `aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md`
**Snapshot:** epic at `status: ready`, no stories, read at repository state `e8c95e7` (the epic's own verified-current-state section cites `0f849c8`).
**Role:** product — outcome, audience, value, scope, evidence, product assumptions.
**Verdict:** `revise` — nine findings, none blocking. Each is resolvable by amendment inside the epic; none needs evidence the project does not already hold.

## Sources inspected

- The epic itself, in full.
- `context_input/publication_ambitions.md` — the article's own statement of purpose and audiences.
- `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` — Overview, Problem Statement, Goals, Methodology 4, 5, 6, 7, 24, Non-Goals, User Stories, Acceptance Criteria, Open Questions, Dependencies.
- `aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md` — the machine and compute-mode comparisons the statistics must serve.
- `aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md` — the epic's principal downstream consumer, and its declared dependency on this one.
- `aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md` — the export whose statistical half this epic's Boundaries also claim.
- `aidd_docs/results/README.md` — the published bundle as it stands.
- `aidd_docs/tasks/2026_08/2026_08_21_expectations-gap-audit/audit-and-plan.md` section 6 — the publication objective's declared venue order and phase plan.

## Findings

### P1 — The epic serves two of the article's three questions, and does not say which

**Impact:** material.

**Claim.** The article asks which model, which engine or variant, and which machine class. This epic's outcome reaches the first two and, by its own exclusions, cannot reach the third — but nothing in the epic states that, so a reader of the backlog will assume the machine-class question is covered here.

**Evidence.** The ambitions statement is a per-machine question: "Model sizes need to be fitted per machine. For example, Granite 350M will suit the professional PC well, while I can go up to Gemma-4-class models on the tower" (`context_input/publication_ambitions.md`). The epic excludes the dimension on which that question turns: "**Excludes: the runtime median-and-spread treatment of Methodology 6 and 7**, deliberately and by the PRD's own reasoning. […] No runtime field changes in this epic." The exclusion is right — Methodology 6 and 7 describe a repeated measurement of one machine, not a sample — but it means the machine-class answer is assembled from three things this epic does not produce: a refusal record (machine epic), a throughput median with its spread flag (row epic), and a quality score the machine epic assumes is machine-invariant ("Quality is machine-independent, so a judged score is not re-earned per machine").

**Proposed amendment.** One paragraph in Context and Value naming the three questions the publication asks and which of them this epic's outputs reach: model-versus-model and variant-versus-variant on quality, yes; runtime and machine class, no, and by whose decision. The epic already carries the material for it — "A paired test compares two configurations on identical items whatever dimension separates them" — so the statement costs nothing and stops the backlog implying a coverage the epic deliberately declines.

### P2 — "Choosing a winner" is excluded more broadly than the PRD excludes it, and the resulting gap is unowned

**Impact:** material.

**Claim.** The epic reads the PRD's non-goal as forbidding any published ranking. The PRD forbids a ranking committed *before* the evidence. The article's whole value proposition is a ranking derived *from* the evidence, and no epic currently owns producing it.

**Evidence.** Epic: "**Excludes: choosing a winner.** A test says whether a difference is distinguishable from noise; it never says whether it matters (PRD Non-Goals)." PRD Non-Goals: "Selecting one 'winning' web-search tool or dense model **up front** — the comparison itself is the deliverable, not a pre-committed choice." Against that, the article's purpose: "publish a short research paper to help other people who want to run local AI on personal computers **anticipate the results** for a large number of models" (`context_input/publication_ambitions.md`). A reader who wants to anticipate a result needs a recommendation, not a matrix of pairwise p-values. The pitch epic owns rendering ("this epic makes the numbers exist and be correct, not readable at a glance"), this epic owns the numbers, and the derivation between them — "on this machine class, for this use case, these models are indistinguishable at the top and this one leads" — belongs to neither.

**Proposed amendment.** Keep the exclusion, narrow its wording to match the PRD's ("never a choice committed before the evidence"), and name where the derived recommendation lands. It is a small artifact and the epic is one definition away from making it computable: a per-(suite × machine class) leader set, defined as the models not distinguishable from the best, is a direct read of the comparison records this epic already produces.

### P3 — No published output says what difference the suite could have detected

**Impact:** material.

**Claim.** The epic publishes an interval, a p-value, an effect size and a multiplicity adjustment, and never publishes the one number a non-specialist reader needs in order to interpret "not distinguishable": the smallest difference the suite could have resolved. Without it, "indistinguishable" reads as "the same", which is the misreading the epic exists to prevent.

**Evidence.** The Boundaries enumerate every inferential output; no equivalent statement appears. The epic's own arithmetic shows why it matters: "`classification-support-routing` holds 20 items […] Two models 10 accuracy points apart are two items apart." A reader told that two models are not significantly different on that suite is not told that nothing under roughly a 20-point gap could have been called different. That is the difference between an honest small result and a misleading one, and honesty is what the project sells.

For scale, on a binary-scored 20-item suite the 95% normal-approximation half-width at p=0.5 is 1.96·√(0.25/20) ≈ ±22 points; at 100 items, ±10. The epic's bootstrap will return figures near these, so the statement needs no new machinery — it is a second read of the same resample.

**Proposed amendment.** Add a minimum-detectable-effect statement per suite per scoring kind to the Boundaries and to Success Evidence, published beside the interval and carried into the tabular export. It is the cheapest output in the epic and the one that most changes how a blog or Wavestone reader reads the table.

### P4 — The 100-item bar is justified as reviewer credibility; its actual justification is stronger, and the epic reviews it only after paying for it

**Impact:** material.

**Claim.** The epic frames 100 items as what a reviewer expects, and defers judging the threshold until after two 100-item suites exist. The binding reason for 100 is different and harder: below it, the project's own research questions cannot return anything except "indistinguishable", because of the multiplicity rule the epic itself takes. Stated that way the bar is defensible on the project's terms rather than on convention — and the review that would confirm it is computable now, before the authoring and licensing cost is paid.

**Evidence.** The epic takes multiplicity: "Each record names the comparison family it belongs to and that family's size, and carries a Holm-adjusted p beside the raw one." It takes McNemar's exact test for binary suites: "A binary-scored suite, which classification is today, carries McNemar's exact test on the discordant pairs instead."

Compose the two. The prompt-variant epic declares four variants — `baseline`, `constrained_output`, `output_compressed`, `input_compressed` — which is six pairwise comparisons per suite. Holm rejects nothing in a family of six unless the smallest raw p is at most 0.05/6 = 0.0083. McNemar's exact two-sided p over `n` discordant pairs falling all one way is 2·0.5ⁿ, which reaches 0.0083 only at `n` = 8. So a variant must flip at least eight of the twenty items, every one of them in the same direction, before the epic's own rules permit calling it a difference — a 40% swing. Mixed discordance needs more: a 13–2 split over 15 discordant pairs gives p ≈ 0.0074, and fifteen discordant pairs on a twenty-item suite means three quarters of the answers changed.

That floor is absolute rather than proportional, which is exactly why suite size resolves it: eight discordant pairs out of 100 items is an ordinary effect. Widen the family and the floor rises — eight models compared pairwise is 28 comparisons, Holm's first step is 0.0018, and the requirement becomes eleven one-directional discordant pairs.

The consequence for the engine and variant epic is direct. It excludes authoring new suites ("The campaign runs the suites that exist when it runs"), so on today's suites its flagship research question returns "no distinguishable difference" for arithmetic reasons, and its decision that "A negative result is a result" would be recording an artefact of `n` rather than a finding.

**Proposed amendment.** Two. First, add this reasoning to the Decisions table as the epic's own justification for 100 — it converts a threshold inherited from the PRD into one the project can defend and, under challenge, recompute. Second, move the first half of the threshold review forward: the minimum detectable effect and the discordance floor at 20 items are computable from the published bundle today, and they answer "is 100 enough" before two suites are authored and licensed rather than after. The epic currently sequences it the other way — "whether the intervals observed at 100 items make 100 look sufficient or thin" is check eight of eight.

### P5 — The comparison family is a field with no owner, and it decides every published p

**Impact:** material.

**Claim.** The epic requires each record to name its comparison family and that family's size, and never says who declares the family or at what granularity. As P4 shows, that choice moves the significance threshold by an order of magnitude. An undeclared family is not a recorded decision; it is a free parameter chosen after the data is in.

**Evidence.** The whole of the rule: "Each record names the comparison family it belongs to and that family's size, and carries a Holm-adjusted p beside the raw one; where no adjustment applies, the record says so rather than staying silent." Nothing in Boundaries, Decisions or Success Evidence says how a family is constituted. The check that touches it asserts presence only: "a record carrying paired n, the test named, raw and adjusted p, direction and effect size".

**Proposed amendment.** Declare the family with the campaign rather than with the analysis. The engine and variant epic already includes "**the campaign declaration as data** — which engines, which variants, which roster entries, which suites, on which machine"; the family follows from it mechanically, one per (suite × dimension). Add a Success Evidence check that a record whose declared family size disagrees with the campaign's declared cell count is refused — the same discipline as the epic's existing refusal on a mismatched suite version.

### P6 — The 25% language share makes the language cell the binding denominator, and 100 does not fix it

**Impact:** material.

**Claim.** Language mastery is one of the article's headline claims. At the publication level a per-language cell holds about 25 items, which resolves nothing under roughly a 25-point gap. The epic reads the arithmetic as a problem solved — the 10-item indicative floor stops firing — when what has changed is that the cells are no longer flagged, not that they have become readable.

**Evidence.** Epic: "Once a publication suite has run, a per-language cell holds 25 items or more and the 10-item indicative floor can no longer fire on its own arithmetic." Methodology 4 requires "each of EN, FR and DE covers at least 25% of that suite's items", so 100 items is 25 per language at the minimum share. The 95% half-width at 25 binary items is ≈ ±20 points, against ±10 for the whole suite. The ambitions statement puts language among the article's deliverables: "mastery of different languages, and even programming languages".

**Proposed amendment.** State the size target as items per language cell rather than per suite, or state explicitly in the epic that per-language claims remain indicative at the publication level and that the article says so. Either is honest. Letting the floor stop firing while the cells stay unreadable is the one option that misleads, because removing the `indicative` mark is itself a claim.

### P7 — The done gate bundles a cheap first-venue deliverable with a licence-gated preprint deliverable, and blocks the downstream epic on both

**Impact:** material.

**Claim.** All eight of the epic's checks must hold for `done`, and two of them depend on a licence spike whose failure the epic already anticipates. The half that serves the declared first venue needs neither the spike nor a new suite. As written, the engine and variant epic waits for both.

**Evidence.** The venue order is settled: "a blog or consulting article first, an arXiv preprint optional" (PRD, Overview), and section 6 of the gap audit records the same — "venue: blog/Wavestone first, arXiv optional, JOSS later-optional". The epic's checks seven and eight need real publication suites and the licence answer. Its falsification clause concedes the spike may fail: "if the licence spike finds no candidate source whose terms permit redistributing a subset inside the bundle's CC-BY 4.0, the outcome as written is not reachable and the manifest fallback below is what ships." Meanwhile the epic already publishes intervals without any new suite — "**The interval is published at both levels.** A development-level score keeps its `indicative` marking and gains an interval as well" — and the paired test is a join on `item_id` over rows that already exist ("Nothing new has to be stored per item"). The downstream epic declares its dependency on the whole: "Bootstrap intervals and the paired Wilcoxon over per-item scores | dependency | […] The research question is unanswerable without them", and its frontmatter lists this epic in `depends_on`.

**Proposed amendment.** Name a minimum publishable unit inside the epic and let the downstream epic depend on that rather than on the whole. The natural unit, and my proposal:

1. Bootstrap intervals on every score and every per-language cell, at development level, on the suites that exist.
2. The paired test, its effect size, its declared family and its refusal behaviour, over rows that exist.
3. The minimum-detectable-effect statement of P3.
4. The reader-facing verdict of P8.

None of the four touches a public benchmark, a licence or a new item. The publication-level suites, the licence spike, the selection-rule record and the manifest fallback then form a second unit, gated on the spike, serving the optional preprint and — per P4 — the suite size at which the variant and engine question can return an answer at all. Whether that split becomes two epics or one epic with two gates is a backlog-shape decision, not one this lens takes.

### P8 — Nothing on the record is legible to the two non-technical readers, and rendering cannot invent a field

**Impact:** minor.

**Claim.** The epic's Context and Value cites one audience, the academic reviewer. The PRD names three readers of published numbers. The comparison record carries raw p, adjusted p, direction, effect size, the statistic, paired n and unpairable n, and carries no single derived statement of whether the difference stands. The pitch epic can only render fields this epic creates.

**Evidence.** Epic: "The audience is the one the PRD adds for the publication: 'As an academic or technical reviewer…'" — the only audience named. The PRD's other two readers of the same numbers: "As a client decision-maker, I want to see the comparison as tables and a single headline energy figure, so that I can judge the on-prem-vs-cloud question at a glance without reading the repo", and "As someone planning local AI on ordinary hardware, I want results for a 16 GB no-GPU office PC published beside the GPU machines". Neither reads a rank-biserial correlation. The epic's boundary is correct — "this epic makes the numbers exist and be correct, not readable at a glance" — and that is precisely why the derived field has to be created here.

**Proposed amendment.** One derived, reader-facing verdict on the comparison record: distinguishable, not distinguishable, or not comparable, evaluated against the declared family at the declared alpha, with the raw inputs kept beside it. It is the seam between preprint rigor and article legibility, and it is one field.

### P9 — Which level carries the article's headline number is undecided

**Impact:** material.

**Claim.** The epic decides that both suite levels coexist and that a table never averages them. It does not decide which one the article leads with, so after this epic every model carries two accuracy numbers per use case with no stated precedence.

**Evidence.** Epic: "A published table names the level of every row and never averages across them." And on interpretation: "whether the publication and development levels ranked the roster the same way — a disagreement between them is a contamination signal and is worth more than either score alone." That is a research finding, not an editorial rule, and the article still has to print one number first.

**Proposed amendment.** Take the decision in the Decisions table with its reasoning: the publication-level score as the headline with the development-level score beside it as the uncontaminated check, or the reverse. The epic's own contamination argument — "a publication score is a score over items a model may have trained on" — is a live case for the reverse of the obvious answer, which is exactly why it should be settled in writing rather than by whichever table gets built first.

## Questions

| # | Finding | Missing decision or evidence | What the answer unlocks |
| --- | --- | --- | --- |
| Q1 | P2 | Is a derived per-(use case × machine class) leader set — the models not distinguishable from the best — a published artifact of this project, and if so, which epic owns it? | Whether the article's central deliverable has an owner in the backlog, or is assembled by hand outside it. |
| Q2 | P4, P7 | Is the first publication a blog or Wavestone article over the development suites, with honest intervals and a stated detection limit, or does it wait for the publication-level suites? | The epic's done gate, its ordering against the engine and variant epic, and whether the licence spike sits on the critical path of the first publication or the second. |
| Q3 | P5 | At what granularity is a comparison family declared — per suite per dimension, per suite across all dimensions, or per campaign? | Every published adjusted p. As P4 shows, the granularity moves the threshold by an order of magnitude, so it decides which findings survive. |
| Q4 | P6 | Is a per-language claim a headline of the article, or a secondary breakdown published as indicative? | Whether the publication suite's size target is set against the suite or against the language cell — that is, whether the target is 100 items or 300. |
| Q5 | P1 | Is quality actually invariant across machines and compute modes, or is a same-model, same-suite paired test across machines a comparison the publication wants? | Whether the machine epic's judge-budget assumption holds, and whether the article can answer "does running CPU-only on an office PC change the answer quality" — a question this epic's machinery already supports and no epic has declared. |
| Q6 | P9 | Which level is the article's headline score? | The shape of the article's central table, and what the pitch epic renders first. |

## No side effects

No artifact was created, changed or persisted beyond this report. No decision was taken on the caller's behalf; every amendment above is a proposal.
