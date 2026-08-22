# Three Amigos — product lens

- **target**: `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md`
- **snapshot**: epic as committed in `d047890`, read at repo HEAD `df8e294`
- **role**: product
- **verdict**: `revise`

## Sources inspected

| Source | Used for |
| --- | --- |
| The epic, full text | outcome, boundaries, criterion ledger, success evidence |
| `aidd_docs/product/wave-local-ai-v2.md` | audience layers, product bet, hardware-class boundary |
| `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` | Methodology 1-19, Goals, Acceptance Criteria, Dependencies, Non-Goals |
| `aidd_docs/tasks/2026_08/2026_08_21_expectations-gap-audit/audit-and-plan.md` §1, §5.2 | founding expectations E1-E16 and their current status |
| `aidd_docs/results/{runtime,quality}-reference.jsonl` | what a published row carries today |
| `src/wave_local_ai_v2/energy.py`, `__init__.py:184-197`, `classification_suite.py` | what the shipped code actually measures and labels |
| `aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md:34,45-46,69` | which fields the surface epic expects this one to produce |
| `aidd_docs/memory/architecture.md:39-48` | the Gotchas the epic cites |

## Does a decision-maker or their engineer need every field?

Mostly yes, but not for the same reason, and the epic's own framing hides that. Ranked by what each criterion returns against what it costs, from a product standpoint only:

**Buys visible credibility in a pitch.** Criterion 6 (N, median, mean, standard deviation) and 7's unreliable flag: an error bar is the single most legible rigor signal a non-technical reader recognises, and "26.0 tok/s over 5 runs, sd 0.4" survives a challenge that "26.0 tok/s" does not. Criterion 8's verdict is the PRD's headline goal restated as a mechanism (PRD Goals: "an explicit verdict of reproduced or not reproduced rather than an eyeball comparison"). Criterion 15's energy/carbon/method is the pitch's headline slide. Criterion 16's cost is the field the decision is actually made on. Criterion 14's fiche hash renders as one short string and makes the "hardware-bound" claim mechanical rather than asserted.

**Buys credibility only under challenge — invisible until then, and cheap.** Criteria 1 (runtime sampling), 2 (template version, suite hash), 3 (caps), 13 (roster), 19 (release version, commit sha). None of these ever appears in front of a decision-maker; all of them are what the client's engineer opens first. Keep all five; the cost is field plumbing, and the audience the PRD names second ("a client-side engineer auditing methodology and reproducibility") is the one the epic is correctly written for.

**Costs more than it currently returns.** Three items:

- **Criterion 7's CPU package temperature.** The epic already flags it as needing a spike because `psutil` exposes no sensor on Windows without a vendor driver. A decision-maker never reads a temperature, and criterion 8 only needs it as a *hint* attached to a failed reproduction. Recommend pre-deciding it as best-effort — declared unavailable with the same discipline as `energy_method` — so no story blocks on it. Load alone carries the hint.
- **Criterion 5's contamination-risk marking**, applied to a suite that is 100% hand-written. The field costs nothing and the value arrives with the first public-origin item; building tooling around it now does not.
- **Storing the fully rendered prompt on every row.** The runtime prompt is ~2 KB (`runtime-reference.jsonl`); at N≥5 repetitions × 20 items × a multi-model roster it dominates the file and works against the epic's own outcome sentence ("read from the row alone"). A row that cites a stored rendered-prompt artifact by hash reads better and audits identically. Criterion 2 requires the rendered prompt be *recorded*, not duplicated per repetition.

The cross-epic contract holds: `the-pitch-runs-from-a-browser-and-only-with-the-key.md:34` already lists which of these fields the runtime view surfaces, so this epic is not producing fields nobody has claimed.

## Findings

### P1 — material — the one number the decision is made on is not comparable between the two sides

Criterion 16 gives a cloud row a currency cost from tokens × list price and a local row a currency cost from kWh × a configured price, with no shared denominator. Two costs in the same currency, computed per what — per run? per item? per 1M output tokens? — is not stated anywhere. The product exists to inform on-prem versus cloud; that comparison is exactly the one criterion 16 leaves unmade.

- Source: PRD Methodology 16; epic Boundaries line 34, "16 cost, cloud tokens and list price, local kWh price".
- Excerpt: "a cloud row carries tokens in and out plus an estimated cost from the provider's list price at run time; a local row carries an energy cost derived from a configurable kWh price."
- Proposed amendment: add to criterion 16's scope one normalization unit, recorded per row and chosen once for the project (per 1k items, or per 1M output tokens). Publishing a comparable unit is reporting, not optimising — it does not touch the Non-Goal "Optimising or minimising cost, energy or carbon."

### P2 — material — `energy_method` overstates precisely on the workload the product exists to measure

`energy_kwh` is CodeCarbon's total (`data.energy_consumed` — CPU, GPU, RAM), while `energy_method` is derived from the GPU channel alone. On this bench, 37 MoE layers run on CPU, so most of the energy behind a row labelled `measured_nvml` is a TDP estimate. Both tracked reference rows carry that label. This epic republishes the row schema and carries criterion 15 forward as a binary estimate-or-measurement label, so it inherits the overstatement rather than closing it — in the one field that is the project's honesty signature.

- Source: `src/wave_local_ai_v2/energy.py:5-7, 53-56`; `aidd_docs/results/runtime-reference.jsonl` (both rows, `"energy_method": "measured_nvml"`).
- Excerpt: "`energy_method` reflects the GPU figure, since that's the one measurement channel that can actually be real on this platform" — while the returned figure is `data.energy_consumed`.
- Proposed amendment: make the label per-channel (cpu / gpu / ram), or add a `mixed` value carrying the measured share of total kWh. The epic already owns criterion 15; this is a field shape, not new scope.

### P3 — material — local and cloud carbon are computed at different scope boundaries, undisclosed per row

The PRD's Dependencies set local energy as CodeCarbon offline "(physical, Scope 2)" and cloud as a formula estimate "(Scope 3, covering datacenter overhead and hardware amortization)". A local row therefore excludes hardware amortization that the cloud row includes. The asymmetry flatters on-prem, and criterion 15's field list — factor, region, method, formula id — has no place to declare it. A client engineer finds this in one reading, in the section of the product that claims defensibility.

- Source: PRD Dependencies (CodeCarbon line); PRD Methodology 15; epic Boundaries line 34.
- Proposed amendment: record the scope boundary per row as a first-class field alongside the emission factor, and state in the epic that the two figures are not like-for-like until a local Scope-3 component exists.

### P4 — material — TTFT is published as fact while energy is published with provenance; E1 stays under-served and unowned

`ttft_ms` is server-reported, the independent cross-check was attempted and reverted, and the code says so in a comment that no published row carries. The audit has held E1 at "partial (done, uncorroborated)" since 2026-08-21. No epic in the backlog names TTFT except the dashboard's display list. TTFT is one of the three runtime metrics the PRD's Goals name, and it is the easiest of the three for a sceptical engineer to dismiss ("your own server told you that").

- Source: `src/wave_local_ai_v2/__init__.py:197`; audit §1 E1 and §5.2 E1; `the-pitch-runs-from-a-browser-and-only-with-the-key.md:34` (displays TTFT, does not source it).
- Excerpt: "keeps `ttft_ms` server-reported only, uncorroborated by an independent" measurement.
- Proposed amendment: add a `ttft_source` enum to this epic's row work — one field, the same discipline the epic already applies to `energy_method`. Actual corroboration needs slot isolation (`2026_08_21_runtime-measurement-harness/review.md:39`) and can stay out of scope; publishing the number unlabelled cannot.

### P5 — material — memory appears nowhere in the epic, and it is the field the on-prem decision turns on

The epic never names RAM or VRAM. Criterion 6 requires median, mean and standard deviation without naming which metrics they apply to, so under N≥5 repetitions the memory figures have no defined aggregation, and nothing says whether the published figure is a peak or the point sample the harness takes today. The brief's own boundary is a sizing statement ("≤20GB@Q4"), and the current rows read `vram_used_mib: 4548.7` against `process_rss_bytes: 15.2 GB` on a 31.4 GB machine — "will this fit on our box" is the first question a client engineer asks, and a sampled value cannot answer it.

- Source: epic Boundaries line 34 (criterion 6, metrics unnamed); `aidd_docs/results/runtime-reference.jsonl`; brief Boundaries; audit E4 (status done, on the point-sample schema).
- Proposed amendment: name the metric set criterion 6 aggregates, and require peak rather than sampled VRAM and RSS in the published row.

### P6 — material — the 20-item retrofit produces a language dimension too coarse to publish

Twenty items with each of EN, FR, DE at ≥25% leaves five items per minority language, spread across four labels. A per-language accuracy computed on n=5 moves in 20-point steps. Showing "German 60%" in a pitch from five items is the class of number this epic exists to prevent. Separately, criterion 4 requires each item be *tagged* with its language, and nothing in the epic requires the score be *reported* per language — so the founding multilingual expectation (E5's EN/FR/DE dimension, PRD Goals: "carried as a language dimension of the classification, translation and rewriting suites") stays half-served whichever way the retrofit lands.

- Source: PRD Methodology 4; epic Boundaries lines 37, 43; `src/wave_local_ai_v2/classification_suite.py` (10 items, four labels, all EN); PRD Goals, multilingual line.
- Proposed amendment: decide explicitly whether language is a coverage rule (tagged, never scored alone) or a reported dimension. If reported, publish n per language and mark a below-threshold language cell indicative under the same rule criterion 4 already applies to a whole suite. Thresholds stay untouched, per the epic's own exclusion.

### P7 — material — the retrofit is the right gate proof but the wrong first one

Four reasons, in order of weight:

1. Nothing in the retrofit exercises criteria 6, 7, 8 or 14 — the runtime half, which is where the "effectively unfalsifiable" charge actually bites and where the epic's own outcome sentence and three of its four success checks live.
2. The gate is provable without it. The epic's third success check already proves the rule by *deliberately shrinking* a suite; it does not require twenty real items to exist.
3. It is content authoring in two new languages, which Boundaries otherwise excludes ("Excludes: authoring or scoring any new task suite"), and it is the only scope item whose quality depends on human writing rather than code. FR and DE items machine-translated from the EN ten would measure translation artifacts, not multilingual capability.
4. It invalidates the only falsified-and-survived evidence the project owns: 40 rows, 20 `(provider, item_id)` pairs, 0 label mismatches, local 0.60/0.60 and cloud 1.00/1.00 across two consecutive runs (audit §4.1). Bumping the suite version retires that evidence, and regenerating it is real work the epic does not name.

- Source: epic Boundaries line 37, Success Evidence checks 1-4; audit §4.1.
- Proposed amendment: order the runtime half first (criterion 1 runtime, 6, 7, 8, 14, 19). Land criteria 4 and 5 as the rule plus the gate plus language and provenance tags on the existing ten items; carry the twenty-item retrofit as its own story with per-language reporting as acceptance, native authoring as an explicit rule, and regeneration of the reproduced-twice evidence as part of its done.

### P8 — minor — the epic misquotes its own source in the paragraph carrying its value claim

The Context and Value section attributes "effectively unfalsifiable" to the project's memory. `grep -i falsifi aidd_docs/memory/` returns nothing; the Gotchas line reads "A number without a fiche is meaningless." The claim survives the correction, but an epic whose subject is citation integrity should not carry a quotation its cited file does not contain.

- Source: epic line 30; `aidd_docs/memory/architecture.md:41`.
- Proposed amendment: quote the real line, or drop the quotation marks and keep the paraphrase.

### P9 — minor — replacing the reference files empties the repo of published evidence for the epic's duration

The two reference JSONL files are the only committed numbers the public repo holds, and E7 is already "hosted, not presentable". Boundaries commits to regenerating rather than migrating them, which is correct on methodology grounds, but deleting them leaves a public repo with a schema and no results until the first full-roster run lands.

- Source: epic Boundaries line 36 and Dependencies row 3 ("They are regenerated, not migrated. The old rows are replaced rather than reinterpreted."); audit §5.2 E7.
- Proposed amendment: retain the current files as superseded (renamed, marked with the schema version that produced them) rather than removing them.

## Questions

| For | Missing decision or evidence | What the answer unlocks |
| --- | --- | --- |
| P1 | The unit in which local and cloud cost, and local and cloud energy, are compared — per item, per 1k items, per 1M output tokens | Whether criterion 16 produces a number a decision-maker can act on, or two numbers in the same currency that mean different things |
| P2, P3 | Whether the project accepts a mixed-method energy label and a declared scope boundary per row, or holds the binary label and the current asymmetry | Whether the headline carbon figure survives the first engineer who reads how it was computed |
| P5 | Which memory statistic is published under N≥5 — peak or sample, per repetition or aggregated | Whether a client engineer can size the deployment from a published row, which is E4's actual product purpose |
| P6 | Whether EN/FR/DE is a coverage rule or a reported dimension | Whether the retrofit delivers the founding multilingual expectation or only satisfies a suite-composition check |
| P7 | Whether the runtime half or the classification retrofit is ordered first | The epic's first demonstrable proof, and whether the twenty-item authoring effort blocks the criteria that carry the outcome statement |
