# Three Amigos — reconciliation

- **target**: `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md`
- **snapshot**: epic as committed in `d047890`, repo at `df8e294`. All three reports name the same target and the same snapshot; roles are distinct; every finding carries a source pointer. Input accepted.
- **verdict**: `revise` — unanimous across the three lenses, and the merged set resolves to amendments rather than to blocks. Four findings entered as `blocking` (Q1, Q2, Q3, Q4); three are now applied to the epic and one (Q4) is retired by contradicting evidence. Nothing remaining prevents the epic being sliced.
- **result**: 20 confirmed findings, 4 conflicts, 24 amendments applied to the epic, 14 items referred to the PRD, 5 questions left open.

Where the reports converged, the merged finding retains every role and evidence pointer. Where they contradicted each other, both positions are stated below with a recommended decision and the evidence that decides it — the recommendation is the caller's to accept, not a ranking of one lens above another.

The epic's boundaries against its four sibling epics are unchanged. Two amendments touch that seam and both *record* an existing boundary rather than move it; see C3.

## 1. Agreed changes — applied to the epic

### 1.1 Facts the epic states incorrectly

| # | Roles | Change | Evidence |
| --- | --- | --- | --- |
| A1 | D9 vs Q4 | The Context bullet claiming "what llama.cpp's jinja templating actually sent is not recoverable" is replaced. Both CLIs post to the raw `/completion` endpoint, which takes `prompt` verbatim; today's stored string *is* what was sent. The real gap is that no row records the call path. | `__init__.py:202`, `quality_cli.py:146` both `POST /completion`; `--jinja` (`server.py:62`) governs `/v1/chat/completions`, which nothing calls. Verified. |
| A2 | P8 | The "effectively unfalsifiable" quotation attributed to project memory is replaced with the line that file actually carries. | `grep -i falsifi aidd_docs/memory/` returns nothing (exit 1). `architecture.md` Gotchas reads "A number without a fiche is meaningless." Verified. |
| A3 | Q15 | The provenance bullet said only the runtime reference rows predate `run_id`. Both files do. The "reproduced twice with the evidence committed" claim is qualified: the reproduction happened, the committed file cannot show it. | `grep -c run_id aidd_docs/results/quality-reference.jsonl` returns 0 across 40 rows. Verified. |
| A4 | Q8 + P2 | A new Context bullet records that `energy_method` is derived from the GPU channel alone while the reported figure is CodeCarbon's CPU+GPU+RAM total, so both tracked rows publish `measured_nvml` over a number whose largest component is a TDP estimate. | `energy.py:52-55` sets the label from `data.gpu_energy`, returns `data.energy_consumed`. Verified. Two independent lenses reached this from different starting points. |
| A5 | D4 | The criterion 7 unknown said "system load alone carries the machine-state hint" if temperature is unavailable. `psutil.getloadavg()` on Windows is an emulation returning `(0.0, 0.0, 0.0)` against a real 2-3% CPU. The fallback is fabricated data. | Re-probed on this machine: psutil 7.2.2, `hasattr(psutil, 'sensors_temperatures')` is `False`, `getloadavg()` `(0.0, 0.0, 0.0)`, `cpu_percent(interval=1)` 2.0. Verified independently of the report. |

### 1.2 The four criteria that name a state without naming what produces it

This is where the findings concentrate, and all three lenses arrived in the same place. Applied as a new `Decisions this epic takes` table after the criterion ledger, so a story author reads one decision rather than re-deriving it.

| # | Roles | Criterion | Decision recorded |
| --- | --- | --- | --- |
| A6 | Q1, D3 | 7 — the unreliable flag | The statistic and its denominator behind the 10% are named, with the flag rate they imply on the validated baseline. Range-over-median and sd-over-mean disagree by more than the threshold at N=5: the consultant's own ±1.4 tok/s against ~26 tok/s is ~5.4% sd, which a max-min rule exceeds routinely and an sd rule almost never does. The epic currently ships "the flag never fires" or "the flag always fires" depending on a choice it does not record. |
| A7 | Q2 | 8 — which metric decides | One primary metric carries the verdict, the others are reported as deltas. A runtime row has several medians and TTFT is the most volatile: the two tracked rows differ by 74.7 ms of TTFT on runs that differ by 0.56 tok/s. |
| A8 | Q3 + D6 | 8 — a third state | `not comparable`, naming the differing fields, plus a statement of which fiche fields are verdict-blocking (build, quant, flags, GPU) and which are recorded only. Driver and build drift without anyone touching the benchmark, and the client engineer reproducing on their own machine is this epic's stated audience — two states hand them a false `not reproduced`. |
| A9 | Q5 | 14 — what invalidation *does* | A named validator command exiting non-zero, the only observation that survives this epic's exclusion of the results surface. The fiche is a stored addressable artifact, not a reconstruction from a row. |
| A10 | Q8 + P2 | 15 — the method label | Per-channel (`cpu_energy_method`, `gpu_energy_method`) with component values, so a composite figure is not labelled by its smaller measured half. |

### 1.3 Aggregation, repetition and the row contract

| # | Roles | Change |
| --- | --- | --- |
| A11 | P5, D7, Q6 | Criterion 6 names the metric set it aggregates; every non-timing measurement on an aggregated row declares its aggregation (which repetition or which statistic). Memory is published as a peak, not a point sample — `vram_used_mib: 4548.7` against `process_rss_bytes: 15.2 GB` on a 31.4 GB machine is the sizing question a client asks first, and a sample cannot answer it. |
| A12 | Q6, D2 | The repetition protocol becomes row data: warm-up discarded, process restart or not, repetition index, and the named location of the raw repetitions. Added to Unknowns as a delivery decision, with the discarded-first-repetition option stated and "measure model load time once" named as its cheap prerequisite. |
| A13 | D3 | The inter-repetition thermal posture is declared on the row. This machine's only sustained-session evidence is a 34% swing from GPU thermals against ~3.9% across the curated rows, so five back-to-back repetitions change the regime the measurement is taken in. Recorded as "the flag firing is the honest outcome, not a threshold to tune away". |
| A14 | Q9 | The failed-repetition rule is stated, and criterion 9's taxonomy distinguishes `max_tokens`-cap truncation from context truncation. Evidence that the gap is live, not theoretical: four quality rows carry `"predicted_label": null, "correct": false` with no reason, so the local suite's 0.60 is four unparseable outputs indistinguishable from four wrong answers. |
| A15 | D11 | `schema_version` on the row contract, plus a stated rule for a live store holding pre-schema rows. Without it the surface epic's declared-absent contract cannot tell a stale row from an honest degradation, and those are opposite claims. |
| A16 | Q13 + D12 | Run provenance records the sha plus a dirty-tree flag; the version falls back to the packaged version. |
| A17 | D5 | Criterion 8 gains a reference-selection rule: the row records the run id of the reference it was compared against. The reference files are curated snapshots no CLI writes to, and the surface epic computes nothing at read time, so the verdict must be produced and stored by the harness against a named reference. |

### 1.4 Fiche, roster and prompt

| # | Roles | Change |
| --- | --- | --- |
| A18 | D1 | The fiche hash is computed over a normalised projection — model by roster entry id and checksum, not filesystem path; host and port excluded; raw flag list kept as evidence. Today's flag list opens with `-m D:\ia\models\...`, so the hash moves when `SLM_MODELS_DIR` moves and no second machine can ever match it. This is the single change that decides whether cross-machine reproduction is possible in principle. |
| A19 | Q10, D-slice3 | The roster entry carries model architecture (dense/MoE, expert count). Without it Methodology 13's "a dense model takes no MoE-offload flags" rule has nothing to check and `--n-cpu-moe`'s ceiling has no bound. |
| A20 | D10 | The roster's first entry reproduces the validated baseline flag set byte for byte, and the quality path's per-request sampler override stays the single source of quality sampling once flags are roster-driven. |
| A21 | Q7 | A runtime row either pins a seed — departing from the frozen baseline command and requiring its re-validation — or records the absence of one as a named spread source. Recording sampling values that did not determine the output is not enough. |
| A22 | D9 | Criterion 2 is scoped to endpoint + template id + template content hash, with `none` legitimate for the raw path. Shippable now, correct after the sibling's chat-endpoint migration, and what makes rows on either side of it distinguishable. |

### 1.5 Success Evidence and publication

| # | Roles | Change |
| --- | --- | --- |
| A23 | Q14, product cost note | The success test is restated as "the row plus the published reference bundle", with the bundle named (fiche registry, roster file, suite definitions, prompt templates), and Boundaries now commits to publishing the bundle rather than only the two JSONL files. This also removes the pressure to duplicate a ~2 KB rendered prompt on every repetition of every item of every model. The epic states plainly that the row alone is *deliberately* insufficient — pointers are the point of criteria 13 and 14. |
| A24 | Q16, D-testability | The four checks become six, split into four code-level checks runnable on constructed rows and stubs, and two needing the bench machine. Verdict *logic* is falsified against constructed rows; the 10% tolerance is *calibrated* from real runs. A new first check — the writer gate refuses a row missing a required field — is what makes the eight schema-shaped criteria (2, 3, 5, 9, 13, 15, 16, 19) able to fail; the quality lens counted them as entering the epic with no stated way to fail at all. |
| A25 | P9 | The current reference files are retained as superseded and marked with their schema version rather than deleted, so the public repo is not empty of published numbers for the epic's duration. |
| A26 | Q11 | Boundaries state that item provenance is an author declaration gated for presence and consistency, not a verified property. |
| A27 | P4 | `ttft_source` on every runtime row, marked in the epic as a deliberate widening beyond the PRD's 19 criteria. One enum, the same discipline `energy_method` already carries. Corroboration needs slot isolation and stays out of scope; publishing the number unlabelled does not. |
| A28 | P1, P3 | The row carries a cost normalization unit and the scope boundary behind its emissions figure, and the epic states that local Scope 2 and cloud Scope 3 are not like-for-like until a local Scope-3 component exists. Both are field-shape changes here; the *choice* of unit and the asymmetry itself go to the PRD (see §3). |

## 2. Disagreements

Four. In each the two positions are stated as their authors made them; the recommendation is mine and is the caller's to accept or reject.

### C1 — Q4 vs D9: does criterion 2 need a spike?

- **Quality (Q4, blocking)**: the rendered prompt may not be recoverable from llama-server; frame a spike alongside criterion 7's, and if the answer is no, label the field a reconstruction rather than a capture — otherwise the test verifies the client-side renderer against itself.
- **Delivery (D9, material)**: the premise is wrong. Both CLIs call the raw `/completion` endpoint, which applies no template, so the stored string is already byte-identical to what was sent.

**Recommended: D9. No spike.** The disagreement is factual and the code settles it — I read both call sites rather than take either report at face value. But Q4's concern is not void, it is early: after the chat-endpoint migration that `no-use-case-is-silently-absent` owns, the stored string stops being the bytes the model received and Q4's question becomes live *in that epic*. Applied as A22: recording the endpoint here is what lets that epic detect the transition instead of silently changing what the field means. Q4's honesty degradation (capture vs reconstruction) is the right shape for that epic to inherit.

### C2 — P7 vs the delivery slice order: runtime half first, or the suite gate first?

- **Product (P7, material)**: order the runtime half first. The classification retrofit exercises none of criteria 6, 7, 8 or 14 — where the "unfalsifiable" charge bites and where three of four success checks live. It is content authoring in two languages, which Boundaries otherwise excludes, and it retires the only falsified-and-survived evidence the project owns (40 rows, 20 pairs, 0 mismatches across two runs).
- **Delivery (slice 5)**: pull the suite slice forward if a consumer epic starts, because the use-case epic's six suites and two `ready` quality stories wait on that gate.

**Recommended: split the scope item, which satisfies both.** These conflict only because the epic treats "criteria 4 and 5" and "ten items to twenty" as one thing. They are not. What the siblings wait on is the *gate* — `no-use-case-is-silently-absent:53` says its suites are "born compliant against that gate", not "against twenty items" — and the epic's own third success check proves the gate by deliberately shrinking a suite, which needs no new items. Applied as an amended Boundaries bullet: the rule, the gate and the per-item tags on the ten existing items are one piece, orderable early for the consumers; the 10→20 retrofit is a second piece carrying native authoring as an explicit rule and the regeneration of the reproduced-twice evidence in its done. Both lenses' objections survive intact and neither blocks the other. The epic does not set story order; the split is what makes the order a free choice.

### C3 — D8: does the suite definition shape move into this epic?

- **Delivery (D8, material)**: this epic must invent the suite definition shape in order to migrate classification onto it, and that shape is exactly the seam `no-use-case-is-silently-absent` claims. Both statements cannot hold; state the split — shape and gate here, registry and suites two through seven there.

**Recommended against, as a boundary change; recorded instead.** D8 identifies a real ambiguity, but the fix it proposes moves ownership across an epic boundary, and the caller's constraint is that those boundaries stay put. The sibling claims the shape explicitly at line 40 ("a suite definition shape and a registry"), and one suite does not justify either. Applied as an added `Excludes` bullet: this epic ships the gate and puts the criteria 3/4/5 fields on the one suite that exists, in whatever form that module already takes; the shape those fields become and the registry that resolves a suite id arrive with the second suite. The gate validates fields, not a shape, so it survives the generalisation unchanged — which is what makes the split work without either epic reimplementing the other. If the caller prefers D8's version, it is a two-sided edit and the sibling's line 40 must move in the same change.

### C4 — criterion 7's temperature: pre-decide, or spike?

- **Product**: pre-decide it as best-effort — declared unavailable with `energy_method`'s discipline — so no story blocks on it. A decision-maker never reads a temperature, and criterion 8 needs it only as a hint. Load alone carries the hint.
- **Delivery (D4, material)**: keep the spike but rescope it from "can we read CPU package temperature" to "which signals actually explain observed variance here". GPU temperature and clock event reasons are already reachable through the repo's own NVML path; CPU package temperature would be an operability cost paid for the less informative signal.

**Recommended: D4.** The product position rests on load carrying the hint, and load does not: `getloadavg()` returns a fabricated `(0.0, 0.0, 0.0)` on this platform, which I re-probed rather than accept from the report. Dropping the spike would therefore ship the epic's own failure mode — a number that cannot be wrong because it is not a measurement. D4's rescope costs the same half day and lands on the signal that actually explained this machine's one observed regression. The product's substantive point is preserved: CPU package temperature degrades to declared-unavailable, and no story blocks on it. Applied to the Unknowns row.

## 3. To the PRD — criterion changes, listed only

None of these are edits I have made. Each is a place where the epic had to widen, sharpen or contradict a Methodology criterion in order to be implementable, and the PRD is where that belongs. Fourteen items; the first four are the ones that change what a published number *means*, the rest are field-shape.

| # | Criterion | Change to record | Why the epic could not just implement it |
| --- | --- | --- | --- |
| 1 | 7 | Name the spread statistic and its denominator behind "spread exceeds 10%" | Range-over-median and sd-over-mean disagree by more than the threshold itself at N=5; the choice decides whether the flag never fires or always fires |
| 2 | 8 | Name the deciding metric (or the metric set plus a roll-up rule) | A runtime row carries several medians; the epic's headline outcome is the one criterion whose test cannot be written from the text |
| 3 | 8 | Admit a third verdict state, `not comparable`, and name which fiche fields are verdict-blocking | The PRD's acceptance criterion admits two states, so a re-run with nothing to compare against must publish a false `not reproduced` — the default outcome for the client engineer the PRD names as the audience |
| 4 | 15 | Replace the binary estimate-or-measurement label with per-channel methods, and add the scope boundary (local Scope 2 vs cloud Scope 3) to the field list | A single label over a composite figure has no true value; and a local row excludes hardware amortization the cloud row includes, with nowhere to declare it. This is the project's honesty signature field |
| 5 | 16 | Add one normalization unit, chosen once, recorded per row | Two costs in the same currency computed per unstated units do not make the on-prem versus cloud comparison the product exists to inform |
| 6 | 16 | Store the list price value, currency and retrieval timestamp, not only the derived cost | A later auditor recomputing against today's prices cannot tell whether the row was wrong or the price moved. Criterion 15 already sets the pattern with factor and region |
| 7 | 6 | Name the metric set the aggregation applies to; require peak rather than sampled memory | "Median, mean and standard deviation" with no metric list leaves VRAM and RSS with no defined aggregation under N≥5 |
| 8 | 6 + 9 | State what a failed repetition does to N | Dropped-and-re-run biases toward success, kept-as-zero destroys the median, failing the row is a third rule. The criteria do not compose as written |
| 9 | 9 | Extend the failure taxonomy to distinguish `max_tokens`-cap truncation from context truncation | Criterion 9 names only the context limit; the cap is what the current rows actually hit at 128 tokens, and criterion 3 makes it a disputable suite-level choice |
| 10 | 4 | Decide whether language is a coverage rule or a reported dimension; if reported, publish n per language and mark a below-threshold cell indicative | Twenty items at ≥25% leaves five per minority language across four labels, so a per-language accuracy moves in 20-point steps. Either way, the PRD's multilingual goal is currently half-served |
| 11 | 13 | Add model architecture (dense/MoE, expert count) to the roster entry fields | The PRD's own "a dense model takes no MoE-offload flags" rule is stated over an attribute no listed field carries |
| 12 | 14 | State that the hash is over a normalised projection, with the model identified by roster id and checksum rather than path, and host/port excluded | Hashing the flag list as written hashes a machine-local absolute path: the same machine changes hash when the models directory moves, and no second machine can ever match |
| 13 | 19 | Add a dirty-tree state alongside the commit sha | A sha stamped from a modified working tree names code that never existed, and it fails silently |
| 14 | new | A TTFT provenance field | The PRD's Goals name TTFT as one of three headline runtime metrics; no criterion covers how it was obtained, and it is server-reported and uncorroborated |

Items 3, 4 and 12 are widenings the PRD's own discipline demands rather than relaxations — each replaces a number that cannot be wrong with one that can. Item 10 is the only one where the PRD may reasonably answer "coverage rule, leave it", and the epic ships either answer.

## 4. Open questions

Five remain unresolved. Each names what is missing and what the answer unlocks; none is resolved by silence, majority or severity.

| # | From | Missing decision | Unlocks |
| --- | --- | --- | --- |
| 1 | Q1, D2, D3 | The repetition topology (one process with the cold repetition discarded, or one process per repetition) and the inter-repetition posture (back-to-back, fixed cooldown, cooldown to a temperature ceiling) | The real wall-clock cost of a published runtime row, and whether criterion 7's flag measures machine state or the harness's own cold-start artifact. All of the criterion 6, 7 and 8 work |
| 2 | Q2, Q1 | Which statistic, over which metric, the 10% is computed on — and the same for the verdict | Both are PRD items (§3.1, §3.2); until answered the epic can build the machinery but not the threshold |
| 3 | D11, Q6 | Whether a live per-machine store rotates on a schema change or is filtered by `schema_version` at read time; and where the raw repetitions live (inline, sidecar, run directory) | The surface epic's declared-absent contract, and the shape of the criterion 6 story's storage |
| 4 | P6 | Coverage rule or reported dimension for EN/FR/DE | Whether the retrofit delivers the founding multilingual expectation or satisfies a composition check. PRD item 10 |
| 5 | P7, C2 | Which piece is ordered first now that the classification scope is split: the runtime half, or the gate-and-tags piece the sibling epics wait on | The epic's first demonstrable proof. The split makes this a free choice rather than a forced one, but it is still a choice |

Questions 2 and 4 are PRD questions and are listed in §3; they appear here because a story cannot be written while they are open, not because the epic can answer them.

## 5. What was not changed

- **The framing, the audience and the value argument.** All three lenses accepted them without a finding.
- **The criterion ledger's in/out split**, and the boundaries against all four sibling epics. C3 is the only finding that proposed moving one, and it is recommended against; A22 and the new suite-shape `Excludes` bullet record boundaries that already existed on the sibling's side.
- **The "done, not work" treatment of criterion 12 and the quality half of criterion 1.** Q15 corrected what the epic *says* about the evidence, not its status.
- **The thresholds** (20 items, N≥5, 10%, 25%, 80%). The epic's exclusion holds: they are implemented as configuration and deferred to the first full-roster run, per the PRD's own Open Questions. Every finding above changes what a threshold is computed *over*, never its value.
