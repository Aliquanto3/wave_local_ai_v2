# Three Amigos — quality lens

**Target:** `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md`
**Snapshot:** epic at working-tree state, repo at `df8e294` (epic's own Context is stated against `a2ffe37`)
**Role:** quality
**Verdict:** `revise`

## Sources inspected

- `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md`
- `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md`, section Benchmark Methodology (criteria 1-19) and Acceptance Criteria
- `aidd_docs/memory/architecture.md`, Gotchas
- `context_input/baseline_qwen36.md`, sections "Methode de bench validee" and "Pieges runtime"
- `src/wave_local_ai_v2/energy.py`, `server.py`, `hardware.py`, `scoring.py`, `quality_cli.py`
- `aidd_docs/results/runtime-reference.jsonl` (2 rows), `aidd_docs/results/quality-reference.jsonl` (40 rows)

## Falsifiability ledger

One line per in-scope criterion: what a test could actually assert today, and what it could not.

| Criterion | Falsifiable by | Not falsifiable as written | Finding |
| --- | --- | --- | --- |
| 1 runtime half (sampling on runtime rows) | schema assertion that the block is present | that the recorded values determined the output; no seed is pinned for runtime generation | Q7 |
| 2 prompt parity and versioning | schema assertion; suite content hash recomputable offline | that the stored string equals what llama.cpp actually sent | Q4 |
| 3 generation caps | schema assertion plus cross-model equality on an item | which truncation kind (cap vs context) triggers criterion 9 | Q9 |
| 4 suite size and language mix | shrink a suite, assert `indicative`; count per language | — | — |
| 5 item provenance | schema assertion that provenance is declared and public items are marked | that a declaration is true; provenance is self-asserted | Q11 |
| 6 repetition and spread | schema assertion on N, median, mean, sd | which metrics are aggregated; whether repetitions share one server process; where raw repetitions live | Q6 |
| 7 machine state | load at start is readable; temperature is the subject of a declared spike | "spread exceeds 10%" has no formula, so the unreliable flag cannot be implemented or tested | Q1 |
| 8 reproduction verdict | a verdict field exists and takes both values | which metric decides; what happens when the fiche hash differs; cloud-side determinism | Q2, Q3 |
| 9 failed generation | schema assertion on reason + denominator | how a failed repetition counts toward N in criterion 6 | Q9 |
| 13 model roster | schema assertion, checksum verification, per-entry flag set | the "a dense model takes no MoE-offload flags" rule needs an architecture field the epic never asks the roster to carry | Q10 |
| 14 fiche integrity | recompute SHA-256 over the fiche; edit it and re-check | what "invalidates" observably does; edit and machine drift produce the same signal | Q5 |
| 15 energy and carbon | schema assertion on factor, region, method, formula id | one `energy_method` label over a composite CPU+GPU figure has no true value on Windows | Q8 |
| 16 cost | schema assertion; local cost recomputable from kWh price | a cloud list price "at run time" is unverifiable later unless the price itself is stored | Q12 |
| 19 run provenance | schema assertion on run id, timestamp, sha | a sha recorded from a dirty working tree names code that was never committed | Q13 |

Coverage note: 14 criteria are in scope, and Success Evidence carries four checks (touching 6, 14, 4 and 8). Criteria 2, 3, 5, 9, 13, 15, 16 and 19 enter the epic with no stated way to fail.

## Findings

### Q1 — `blocking` — "spread exceeds 10%" names no statistic, so the unreliable flag cannot be implemented or tested

Criterion 7 makes an observable state ("flagged unreliable") depend on an undefined quantity. Range over median, standard deviation over mean, interquartile range and max-min divided by min all give different verdicts on the same five repetitions, and at N=5 they differ by more than the threshold itself.

> PRD, Methodology 7: "a metric whose repetition spread exceeds 10% is flagged unreliable"

The consultant's own baseline puts this squarely in the contested zone rather than at the margin: `context_input/baseline_qwen36.md` records "les ecarts-types atteignent +/-1,4 tok/s" against a ~26 tok/s generation figure, i.e. a standard deviation near 5.4% of the mean. Under a max-min definition, a normal five-repetition sample from that distribution exceeds 10% routinely, and every published runtime row would carry the unreliable flag. Under a standard-deviation definition, almost none would. The epic ships either "the flag never fires" or "the flag always fires" depending on a choice it does not record.

**Proposed amendment:** name the statistic and its denominator in the epic's Boundaries (the ledger already fixes the threshold at 10%), and state the expected flag rate on the validated baseline so the first full-roster run can falsify the choice rather than discover it.

### Q2 — `blocking` — the reproduction verdict does not say which metric decides it

Criterion 8's runtime half compares "the re-run's median" to "the reference row's median". A runtime row carries several medians: generation tok/s, prefill tok/s, TTFT, VRAM, RSS, energy. A re-run that lands within 10% on generation throughput and 30% off on TTFT has no verdict under the rule as stated, and TTFT is the most volatile of them — the two tracked rows differ by 74.7 ms of TTFT on runs that differ by 0.56 tok/s.

> Epic, Success Evidence: "A re-run whose median falls outside 10% of the reference median returns 'not reproduced'"

This is the epic's headline outcome ("re-run it to an explicit reproduced / not-reproduced verdict"), and it is the one criterion whose acceptance test cannot be written from the text.

**Proposed amendment:** designate the deciding metric set explicitly — one primary metric with a verdict, the others reported as deltas — or state that the verdict is per-metric and the row carries a verdict per metric plus a roll-up rule.

### Q3 — `blocking` — the verdict has no "not comparable" state, so fiche drift silently becomes "not reproduced"

Criterion 8 qualifies the runtime verdict with "on the same hardware fiche", and criterion 14 makes the fiche a SHA-256 over fields that include the GPU driver version and the llama.cpp build. Both drift without anyone touching the benchmark: `hardware.py:47-58` reads the driver version from NVML at capture time, and `runtime-reference.jsonl` shows `"gpu_driver_version": "572.70"` and `"llama_cpp_build": "b10537"` inside the same record as the measurement.

A driver update, a llama.cpp rebuild, or a BIOS change therefore produces a different fiche hash, and the re-run is no longer "on the same hardware fiche". The epic offers two states only. The client engineer who updates their driver between the published run and their verification gets either a false "not reproduced" (the code is fine; the machine moved) or a silent pass that ignores the very disclosure the fiche exists to enforce. This is the epic's own stated reason for existing — `architecture.md` Gotchas: "Runtime metrics are NOT reproducible across machines" — applied to the same machine across time.

**Proposed amendment:** add a third verdict state (`not comparable`, naming the fiche fields that differ) and state which fiche fields are verdict-blocking (build, quant, flags, GPU) versus merely recorded (OS patch level, driver revision), so a rebuild is an explicit disqualification rather than a numeric failure.

### Q4 — `blocking` — the rendered prompt may not be recoverable, and the epic lists no unknown for it

Criterion 2 requires "the final prompt string as rendered for that provider (after llama.cpp jinja templating)". The epic's own Context states the current gap correctly — "what llama.cpp's jinja templating actually sent is not recoverable" — and then places the criterion in scope with no entry in Dependencies and Unknowns, unlike criterion 7 which got a spike for exactly this shape of uncertainty.

If the server does not return the templated prompt, the only available implementation is re-rendering the template client-side and storing the reconstruction. A test can then assert that the stored string matches the client-side renderer, which is a tautology: it verifies the reconstruction against itself, not against what the model received. The criterion's audit value — an engineer replaying the exact bytes — is lost without the row ever declaring it.

**Proposed amendment:** add a spike alongside criterion 7's, framed as "does llama-server expose the post-jinja prompt (response field, verbose flag, or log) at the project's configuration", with the same honesty degradation: if not, the row labels the field a reconstruction rather than a capture.

### Q5 — `material` — "invalidation" is required to be observable but is never given an observation, and cannot distinguish an edit from machine drift

Criterion 14 and the epic's second check both hinge on a state change the epic does not name.

> Epic, Success Evidence: "Editing a hardware fiche invalidates the rows citing its hash, demonstrably: the invalidation is observable, not documented."

A test author must choose between at least three incompatible designs: a stored flag written into affected rows, a validator command that exits non-zero, or a read-time check computed by whatever consumes the rows (a surface this epic explicitly excludes). Each has a different failure mode, and the epic's exclusion of the results service removes the most natural home for a read-time check.

Second, a fiche in this codebase is captured, not authored (`hardware.py:24-35`). "Editing a fiche" is an operation the current design has no user for; what actually happens in the field is that the machine changes and the next capture hashes differently. Hash mismatch conflates the two, and the audit story cares about them differently: an edited fiche is tampering, a drifted fiche is honest change.

**Proposed amendment:** state the observation (a named validator command and its exit behaviour is the only option that survives this epic's exclusion of the surface), and state whether the fiche is stored as a standalone addressable artifact or reconstructed from the row.

### Q6 — `material` — the repetition protocol is unstated, so the median is not reconstructible from the row

Criterion 6 fixes N≥5 and the statistics, and says nothing about how the repetitions are produced. Whether the server process is restarted between them, whether the first repetition (cold cache, model load, GPU clock ramp) is discarded, and whether repetitions of different models are interleaved or blocked all move the median by more than the 10% the verdict is decided on. `context_input/baseline_qwen36.md` prescribes `llama-bench` with `-r 5` — a tool with its own warm-up convention — but the harness measures through the server's own timings (`timings.py`), not `llama-bench`, so that convention does not transfer implicitly.

"Keeps the raw repetitions retrievable" has the same gap: retrievable from where. Inline in the row, a sidecar file per run, or a run directory are three different schemas and three different tests.

**Proposed amendment:** record the repetition protocol as row fields (warm-up count discarded, process restarted between repetitions yes/no, repetition index) so a re-run can match the protocol rather than guess it, and name where the raw repetitions live.

### Q7 — `material` — recording sampling on a runtime row does not make the runtime measurement reproducible, and pinning a seed collides with the frozen baseline command

The runtime half of criterion 1 is in scope as "sampling recorded on runtime rows too". The validated command in `context_input/baseline_qwen36.md` pins temperature, top-p, top-k, min-p and presence penalty but no seed, and `server.py:30-34` mirrors it. llama-server defaults to a fresh random seed per request, so generation length and content vary between repetitions; generation throughput is then measured over a variable token count, and the recorded sampling block does not determine what was measured.

The project has already met this wall on the quality side and documented the constraint (`quality_cli.py:36-45`): "`server.build_flags` must not change, because the runtime harness is required to reproduce its validated command exactly, so the sampler is pinned per request instead". The runtime harness cannot use that escape hatch, because the per-request override is itself part of what the runtime row claims to measure.

**Proposed amendment:** state whether a runtime row pins a seed (and therefore departs from the validated baseline command, requiring a re-validation) or records the absence of one as a declared source of spread feeding criterion 7.

### Q8 — `material` — one `energy_method` label over a composite figure has no true value on this platform

Criterion 15 asks each row for "energy_method stating whether the figure is an estimate or a measurement". `energy.py:52-55` sets that label from the GPU channel alone while reporting `data.energy_consumed`, which is the CPU plus GPU plus RAM total:

> `method = ("measured_nvml" if data.gpu_energy and data.gpu_energy > 0 else "estimated_tdp")`

The two tracked runtime rows are consequently published as `"energy_method": "measured_nvml"` on a number whose CPU component is a TDP estimate — with a 37-of-40-layer MoE offload to CPU, that component is the larger share of the work. `architecture.md` Gotchas states the split plainly: "GPU draw via NVML is a real measurement; CPU is not", and warns the TDP fallback "can be off by a factor of 2-3 on a laptop under thermal throttling".

The epic's Success Evidence promises the auditor can tell "whether its energy figure is a measurement or an estimate". For a mixed figure, that question has no correct single answer, and the current label answers it in the flattering direction.

**Proposed amendment:** require per-channel method (`cpu_energy_method`, `gpu_energy_method`) with the component values, or a composite label whose weakest channel governs. Either is testable; the current form is testable only against itself.

### Q9 — `material` — criteria 6 and 9 do not compose, and the current null-label rows show the gap already

Criterion 9 puts a failed generation in the denominator with a reason. Criterion 6 takes the median of at least five repetitions. Neither says what a failed repetition does to N: dropped and re-run (biasing toward success), kept as a zero (destroying the median), or failing the whole row.

The gap is already visible in tracked evidence. `scoring.py:21-30` returns `None` when no label token is found, and `quality-reference.jsonl` carries four local-model rows with `"predicted_label": null, "correct": false` and no reason field — the local suite's 0.6 accuracy is four unparseable outputs, indistinguishable in the published file from four wrong answers. Criterion 3's caps add a second unhandled kind: criterion 9 names truncation "at the context limit", not truncation at the row's `max_tokens` cap, which is what the current runtime rows hit at 128 tokens.

**Proposed amendment:** state the failed-repetition rule in Boundaries, and extend criterion 9's failure taxonomy to distinguish cap truncation from context truncation, since criterion 3 makes the cap a suite-level choice a challenger can dispute.

### Q10 — `material` — the "a dense model takes no MoE-offload flags" rule has no field to check against

Criterion 13 is quoted in the epic as the home for that rule, and the rule is stated over an attribute — model architecture — that the epic's list of roster fields (repo revision, file name, quant, checksum, server flag set) does not include. A validator can assert that a flag set is well-formed, but cannot decide whether `--n-cpu-moe` belongs there without knowing the entry is dense.

`architecture.md` Gotchas confirms the rule is load-bearing, not cosmetic: `--load-mode none` is mandatory when `--n-cpu-moe` is set, so a dense entry that carries the MoE flag by copy-paste also drags in a flag pair that changes memory behaviour.

**Proposed amendment:** add architecture (dense/MoE, and expert count for MoE) to the roster entry fields the epic ships, which turns the rule into a schema check and also gives criterion 13 something to validate the `--n-cpu-moe` ceiling against.

### Q11 — `minor` — item provenance is a declaration, and the epic presents it as a verification

Criterion 5 marks any public-origin item contamination-risk. A test can assert that every item declares a provenance and that public ones carry the mark; nothing can detect a public item declared hand-written. This is an acceptable limit, but the epic's audience is a sceptical engineer, and an undeclared limit reads as an overclaim when found.

**Proposed amendment:** state in Boundaries that provenance is an author declaration gated for presence and consistency, not a verified property.

### Q12 — `minor` — a cloud list price "at run time" is not verifiable after the fact unless the price is stored

Criterion 16 derives cloud cost from "the provider's list price at run time". If the row stores only the computed cost and the token counts, a later auditor recomputing against today's price list gets a different number and cannot tell whether the row was wrong or the price moved. The epic already applies the right pattern elsewhere (emission factor and region stored alongside `energy_kwh`).

**Proposed amendment:** require the price value, its currency, and its retrieval timestamp on the row, mirroring criterion 15's factor-and-region treatment.

### Q13 — `minor` — a commit sha recorded from a dirty working tree names code that never existed

Criterion 19 records the commit sha of the code that produced a row. Reference rows are produced on the development machine by running an editable install against the working tree, which is not guaranteed to match HEAD at the moment a run starts. A row stamped with HEAD's sha while running modified source is precisely the unfalsifiable artifact this epic exists to eliminate, and it fails silently.

**Proposed amendment:** record a dirty-tree flag next to the sha, and state whether a dirty tree blocks publication of a reference row or only annotates it.

### Q14 — `material` — "hand them the row and nothing else" contradicts the hash-by-reference design

The epic's goal sentence and its Success Evidence both stake the outcome on the row alone: "read from the row alone how it was produced", "hand it to someone who did not produce it, and give them nothing else". Criteria 13 and 14 make the fiche, the roster entry, the suite prompt set and the prompt template pointers — a hash and an id. Handed one JSONL line, an outside engineer can verify nothing until they can resolve those pointers, and the epic explicitly excludes the surface that would serve them.

Note the direction of travel: the epic's Context correctly identifies inline flattening as today's defect (no invalidation, machines distinguishable only by eye), so the fix moves away from self-contained rows. That is the right call for integrity and the wrong one for the stated success test.

**Proposed amendment:** restate the success test as "the row plus the published reference bundle" and name what the bundle contains (fiche registry, roster file, suite definitions, prompt templates), so the regeneration scope in Boundaries covers publishing them rather than only the two JSONL files.

### Q15 — `material` — the tracked quality reference rows carry no run id either, so "reproduced twice, evidence committed" is not checkable from the artifact

The epic's Context records the quality half of criterion 1 as done, "reproduced twice with the evidence committed", and describes the provenance gap as "`quality_cli.py` writes `run_id` and `captured_at`; ... the tracked runtime reference rows predate even `run_id`".

The tracked quality rows predate it too: `grep -c run_id aidd_docs/results/quality-reference.jsonl` returns 0 across 40 rows (2 models × 10 items × 2 runs). The two runs are byte-identical apart from ordering and cannot be separated, so the committed file demonstrates that 40 rows exist, not that two runs agreed. The claim may well be true; the artifact does not carry it.

This matters beyond bookkeeping: the epic treats the quality half of criterion 1 as done and out of scope, which means nothing in this epic re-establishes the evidence when the reference files are regenerated.

**Proposed amendment:** correct the Context sentence, and state that the regenerated quality reference carries `run_id` per row so the reproduction claim is readable from the file.

### Q16 — `material` — the fourth Success Evidence check can fail for environmental reasons, which makes it a poor gate

"A re-run whose median falls outside 10% of the reference median returns 'not reproduced'" is verified by performing two real runs on one laptop. Thermal state between them is uncontrolled — the epic itself flags throttling as the reason the energy estimate can be off by 2-3x — and `context_input/baseline_qwen36.md` warns that "aucune conclusion sous 10 % d'ecart n'est fiable", i.e. the tolerance the verdict uses sits at the noise floor the consultant already measured.

The check as written cannot distinguish "the verdict logic works" from "the machine happened to cooperate". A verdict-logic test wants synthetic reference and re-run rows; a threshold-calibration test wants real runs and belongs to the first full-roster run the epic already defers thresholds to.

**Proposed amendment:** split the check — verdict logic falsified against constructed rows (fast, deterministic, run every change), tolerance calibration recorded as an observation from the first full-roster run — and mark in Success Evidence which of the four checks are cheap and which require the machine.

## Questions

| Q | Finding | Missing decision or evidence | Unlocks |
| --- | --- | --- | --- |
| 1 | Q1 | Which statistic "spread" denotes, over which metric, at N=5 | Criterion 7's unreliable flag becomes implementable and its firing rate predictable on the known baseline |
| 2 | Q2 | Which metric (or metric set) the runtime verdict is computed on | The epic's headline outcome becomes testable; the row schema gets its verdict fields |
| 3 | Q3 | Whether fiche drift yields a third verdict state, and which fiche fields are verdict-blocking | A client engineer on an updated driver gets a meaningful answer instead of a false failure |
| 4 | Q4 | Whether llama-server can return the post-jinja prompt at this project's configuration | Criterion 2 either verifies what was sent or declares a reconstruction; decides whether a spike precedes the work |
| 5 | Q5 | What observation "invalidates" produces, and whether a fiche is a stored artifact | The second Success Evidence check becomes writable as a test |
| 6 | Q6 | The repetition protocol (warm-up, process restarts, ordering) and where raw repetitions are stored | A re-run can match the reference run's conditions rather than approximate them |
| 7 | Q7 | Whether the runtime harness pins a seed, departing from the validated baseline command | Runtime rows either carry determinism or declare a named spread source |
| 8 | Q8 | Whether `energy_method` becomes per-channel or weakest-channel | Criterion 15 stops labelling a composite estimate as a measurement |
| 9 | Q9 | What a failed repetition does to N, and how cap truncation is classed | Criteria 6 and 9 compose; the failure taxonomy covers what the harness actually produces |
| 10 | Q10 | Whether the roster entry records model architecture | Methodology 13's dense/MoE flag rule becomes a schema check |
| 14 | Q14 | What accompanies a published row, and whether the epic publishes that bundle | The success test stops contradicting the integrity design; regeneration scope becomes complete |
| 16 | Q16 | Which Success Evidence checks are code-level and which need the machine | The epic gains a gate that fails on defects rather than on thermal luck |

## Assessment note

Nothing here disputes the epic's framing, its boundaries, or its criterion ledger — the scope split against the judge, web-research and surface epics is clean, and the "done, not work" treatment of criteria 12 and the quality half of 1 is the right shape. The findings concentrate in one place: the criteria whose acceptance is stated as a verdict or a flag (7, 8, 14, 15) name a state without naming the quantity or the observation that produces it, and the epic's own Success Evidence inherits the gap. Four of the sixteen findings are marked blocking because a test author cannot write the test from the text; the rest are amendable in place.
