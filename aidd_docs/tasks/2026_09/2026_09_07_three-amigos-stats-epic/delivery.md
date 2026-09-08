# Three Amigos — Delivery lens

| Field | Value |
| --- | --- |
| target | `aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md` |
| snapshot | `status: ready`, unmodified, read at `e8c95e7` (`main`) |
| role | delivery |
| verdict | `revise` |

Two findings block scheduling as the epic is written (D1, D2); five are material to how it is built and sequenced (D3-D7); three are minor (D8-D10). Every one is resolvable by an amendment to this epic or by an agreement with a named sibling. Nothing here disputes the outcome.

## Sources inspected

- The target epic, in full.
- The eight sibling epics' frontmatter, and the `Boundaries` of `no-use-case-is-silently-absent`, `one-download-holds-the-tables-their-licences-and-how-to-cite-them`, `the-same-suite-runs-on-three-machines-or-names-why-it-cannot`, `the-engine-and-the-prompt-variant-are-measured-not-assumed`, `every-size-class-spans-two-families-or-says-it-does-not`.
- `src/wave_local_ai_v2/`: `scoring.py`, `suite_gate.py`, `aggregation.py`, `row_contract.py`, `read_model.py`, `results.py`, `suite_snapshot.py`, `quality_cli.py`, `retry.py`, `settings.py`, `classification_suite.py`.
- `aidd_docs/results/`: `quality-reference.jsonl` (80 rows), `quality.jsonl` (591 rows, 29 batches), `runtime.jsonl`, `runtime-reference.jsonl`, `README.md`, `suite-definitions/`, `fiches/`.
- `pyproject.toml`, `uv.lock`, `.venv/Lib/site-packages`, `aidd_docs/memory/architecture.md`, `aidd_docs/memory/coding-assertions.md`, `aidd_docs/roster/models.json`, `tests/`.
- Measurements run for this report: a stdlib bootstrap over the published rows, an exact McNemar over the published classification pair, a Wilson cross-check, and a campaign-time model built from the published per-item token counts and the published throughput figures.

## Findings

### D1 — `blocking` — the declared dependency on `no-use-case-is-silently-absent` serialises this epic behind six suites, a code sandbox and a RAG corpus

The epic needs one thing from that sibling — the suite definition shape and the registry that resolves a suite id to a definition. It declares the whole epic as `depends_on`.

> Excludes: **the suite definition shape and the registry that resolves a suite id to a definition** — the same epic.

What that sibling actually contains, from its own `Boundaries`:

> Includes: **six suites, one per remaining buildable use case** [...] code generation (test execution in a sandbox [...]), RAG answer generation ([...] over a repo-owned corpus, with `llamaindex` as its retrieval harness) [...]
> Includes: **the agentic harness as a recorded row dimension, owned here.**
> Includes: **a sandboxed runner for model-generated code** [...]

The suite seam is the first bullet of that epic and is independent of the other nine. The code already knows this, and names the seam by story rather than by epic (`quality_cli.py:13-17`):

> `_SUITES` is a two-entry dispatch table, not a registry: the full suite registry belongs to the `no-use-case-is-silently-absent` story

Read as written, this epic cannot start its suite work until a container sandbox, a retrieval corpus, two search-tool adapters and an agentic transcript capability exist. That in turn stalls `the-engine-and-the-prompt-variant-are-measured-not-assumed`, which declares `depends_on` on *this* epic and consumes its paired tests. One over-broad dependency edge serialises three epics.

Proposed amendment: replace the epic-level edge with a story-level one — depend on the suite seam (definition shape plus registry) alone, named as such, and state in `Dependencies and Unknowns` that the remaining nine deliverables of that epic are not on this epic's path. If the framework requires epic-granularity `depends_on`, the alternative is to lift the suite seam into a story both epics consume and let both declare it.

### D2 — `blocking` — the tabular export is claimed by two epics, and the coupling between them runs both ways

This epic:

> Includes: **the tabular export carrying the interval and the comparison record**, so the third-party researcher of the PRD's user story re-analyses the published results without cloning and running the project.

`one-download-holds-the-tables-their-licences-and-how-to-cite-them`:

> Includes: **a tabular export command over the published bundle.** Four flat tables [...]
> Includes: **CSV as the contract, Parquet as a release-time convenience.**

That epic also consumes this one, by name:

> Which items are drawn and on what terms is consumed from that epic, never reopened here.

So the bundle epic needs this epic's per-item licence decision, and this epic needs the bundle epic's export command. Neither declares the other in `depends_on` — the bundle epic lists the row epic and the clean-machine epic; this epic lists the row epic and the use-case epic. There is no export command in the codebase to extend: `grep -rniE "csv|export|parquet" --include=*.py src/` returns only prose in docstrings and one suite item's text. The seam does not exist yet, and neither epic is currently scheduled to build it before the other needs it.

Proposed amendment: state the split explicitly in both — the bundle epic owns the export command, its column dictionary and its schema; this epic owns the *columns* the interval and the comparison record contribute, and delivers them as a column contribution plus its own analysis command, never as an exporter. Add a `related_to` edge in both directions so the two-way coupling is visible. Then decide the order: the bundle epic's own gap-brief note says its work is "continuous" rather than queued behind the run campaign, which argues for the export command landing first and this epic contributing columns into an existing table.

### D3 — `material` — the comparison record does not name the dimension that differs, which is the one thing a reader needs to know what the comparison is a comparison of

The record's declared content:

> the two run ids, the suite id and version both sides ran, the paired item ids, the test that was run, its statistic, p, direction, effect size and n

The refusal rule names four mismatches: suite id, suite version, item set, level. Correct, and none of them is the *reason for the comparison*. The epic is explicit that the dimension is deliberately unconstrained:

> A paired test compares two configurations on identical items whatever dimension separates them, so nothing here needs those dimensions to exist first

That is the right architectural call, and it leaves a hole. A record carrying two run ids and a p-value cannot be read as a claim: nothing on it says whether the two sides differed by model, by engine, by prompt variant, by machine, by compute mode, or by nothing at all. The consumer already exists and already depends on this, from the engine epic:

> Includes: **item scores staying per item across every variant and engine** [...] so the paired tests and bootstrap intervals E-G ships apply across the new dimensions with no second statistics path.

Two concrete failure modes. A `gpu` row paired against a `cpu_only` row of the same model on the same items produces a well-formed record whose expected answer is "no difference" — a significant p there is a bug signal, and nothing on the record lets a reader see that this was the comparison. And a record where *two* dimensions differ at once (a different model on a different engine) is a confounded comparison that the four refusal rules pass without comment. The engine epic already recognises this class of problem for artifacts and refuses it there:

> A campaign cell whose two engines do not both report `same_gguf` is published as an observation, never as a paired engine comparison — the engine and the artifact would be confounded

Proposed amendment: the record carries the set of row fields on which the two sides differ, computed rather than declared, and the epic states what happens when that set has more than one member — publish as an observation naming the confound, or refuse. The field *names* come from whatever dimensions exist when the comparison runs, so this stays dimension-agnostic and costs no dependency on the machine or engine epics.

### D4 — `material` — the cloud path's retry budget and resume granularity were calibrated against 20-item batches and become the failure mode at 100

Three constants, all sized in a 20-item world:

- `settings.py:89` — `DEFAULT_CLOUD_RETRY_MAX_ATTEMPTS = 4`, and `retry.RetryBudget` is explicit that this is a batch total, not a per-item allowance:

  > A run-scoped count of retries left, shared across every item of one batch. One instance per provider batch, not one per call

- `settings.py:87-88` — `DEFAULT_MISTRAL_REQUEST_PACING_S = 1.1`, `DEFAULT_GOOGLE_REQUEST_PACING_S = 4.1`, and `quality_cli._make_google_complete_item` calls `pacer.wait()` twice per item (context pre-flight, then generation). At 100 items that is 200 paced requests and a floor of **13.7 minutes of wall clock per Google batch**, against 2.7 minutes today. Mistral: 1.8 minutes.

- `quality_cli.py:337-345` — `--resume` is per provider batch, not per item:

  > a provider whose rows for that run_id and this suite are already complete is skipped, never re-paid for; an incomplete one is re-run from item 1

Compose them. A 100-item Google batch is 200 chances to consume a shared budget of 4; the fifth retryable 429 anywhere in those 200 requests fails the batch, and the resume re-runs it from item 1 — 13.7 minutes and 100 items of tokens re-paid. The CLI docstring records that this project's Mistral workspace is on a free tier whose "rate floor 429s a request burst like this suite's 20-item loop", so the retryable path is exercised in practice, not hypothetically. At 20 items the arithmetic was survivable; at 100 it is a coin flip, and it lands on the most expensive artifact the epic produces.

Proposed amendment: name this in `Dependencies and Unknowns` as a delivery precondition — either scale the retry budget with the item count, or make resume per item rather than per batch — and decide which epic owns it. It is arguably the row epic's story `a-rate-limited-run-persists-resumes-and-never-re-pays`, revisited at the new size; it is not a statistics problem, and discovering it during the publication campaign is the expensive way to find out.

### D5 — `material` — a seed does not make a bootstrap reproducible; the resampling algorithm has to be pinned too

The epic's decision:

> The row carries the seed, the resample count and the interval method — percentile or BCa, chosen once and named — beside the interval itself.

Seed, count and method are three of four. The fourth is the draw procedure. `random.Random(seed)` followed by `randrange(n)` per draw, `random.choices(population, k=n)`, and `numpy.random.default_rng(seed).integers` produce three different resample sequences from one seed, and CPython's helper implementations are not contract-stable across versions the way the Mersenne Twister core is. Under criterion 1 that is exactly the failure the epic names for the unseeded case, arriving one level down:

> An unseeded resample returns a different interval on every recomputation, which makes the row unreproducible under criterion 1 and hands the re-run verdict a difference nobody introduced.

The same sentence applies verbatim to an unpinned draw procedure. It also decides the recomputation check, which is one of the epic's eight pieces of Success Evidence:

> Recomputing every interval and every comparison from the published bundle alone [...] returns identical values

A third party recomputing with their own bootstrap library will not reproduce the interval bit for bit no matter what seed they use, unless the procedure is published.

Proposed amendment: add the draw procedure to the row's interval block as a named, versioned algorithm id, and state that the published definition of that algorithm — generator, draw order, tie handling, percentile interpolation rule — is what the reproduction check is against. The same reasoning bears on the percentile-versus-BCa choice: BCa needs an inverse normal CDF and a jackknife, each with its own convention choices; percentile has none and is the cheaper commitment.

### D6 — `material` — scipy is not needed, and the evidence to settle it exists today

The epic defers the choice:

> scipy as a dependency, or the statistics implemented in-repo | decision, deferred to a story plan

Four facts settle it in favour of in-repo, and all four are checkable now.

**Performance is not an argument.** A pure-stdlib percentile bootstrap, 10,000 resamples over 100 items, runs in **0.18 s** on the dev machine. A whole six-batch campaign at four cells each (suite plus EN, FR, DE) is **4.4 s**. There is nothing to optimise.

**Every statistic the epic names has a stdlib-exact form.** McNemar's exact test is a two-sided binomial on the discordant pairs — `math.comb`. Rank-biserial correlation and the Holm adjustment are arithmetic and a sort. The closed-form reference the epic asks the bootstrap to be checked against needs an inverse normal CDF, and `statistics.NormalDist().inv_cdf` is in the standard library. Run against the published rows, the stdlib bootstrap gives `[0.570, 0.750]` where Wilson gives `[0.563, 0.745]` — agreement to 0.007, which is the epic's own proposed check passing. The one genuinely error-prone piece is the exact signed-rank null distribution with its tie and zero conventions, and at n of 100 or more the normal approximation with a named tie correction is standard anyway.

**The project has a stated precedent, and a gate scipy would have to pass.** The bundle epic took the same decision one dimension over:

> The packaged command emits CSV with the standard library alone, adding no runtime dependency to a harness whose target machines include one with 16 GB and no GPU and whose published image carries the same dependency set.

And `aidd_docs/memory/coding-assertions.md` records a third CI gate, `uv run python scripts/audit_dependencies.py`, resolving vulnerabilities via OSV — a new runtime dependency is a permanent addition to that surface.

**One trap to name.** `numpy` 2.5.2 and `pandas` 3.0.5 are already in `uv.lock` and installed, but only transitively, via `codecarbon`. `scipy` appears zero times in the lock. Reaching for numpy because it happens to be importable would be an undeclared runtime dependency on a transitive edge that `codecarbon` can drop at any release.

Proposed amendment: take the decision in the epic rather than deferring it, as in-repo and stdlib only, with one addition the epic's current test rule does not cover. The epic says:

> the tests assert against hand-computed or published reference values rather than against the implementation's own output

Add `scipy` as a **dev-only** dependency used purely as a test oracle. That gives an independent implementation to cross-validate against — stronger than a hand-computed fixture and far cheaper to maintain — while the shipped harness, the container image and the OSV surface stay untouched. Where a convention differs from scipy's, the test that shows the difference documents the convention.

### D7 — `material` — the epic states no slice order, and the first two slices are provable today on the published bundle at zero compute and zero API cost

Six of the eight Success Evidence checks are code-level and need no run:

> The first six are code-level and run on constructed suites, rows and fixtures; the last two need a real run and the licence answer.

The epic does not say that the first ones are also provable on *real published rows*, and they are. `aidd_docs/results/quality-reference.jsonl` already contains two complete pairable comparisons — same `suite_id`, same `suite_version`, same 20 item ids, two models — because a quality row is already per item and already carries `correct` beside `item_id`, exactly as the epic observes. Computed for this report against those rows:

| run | model A | model B | paired n | discordant | McNemar exact p | odds ratio |
| --- | --- | --- | --- | --- | --- | --- |
| `5e13166d` | Qwen3.6-35B-A3B 0.80, CI [0.60, 0.95] | mistral-small-2603 0.95, CI [0.85, 1.00] | 20 | 4 / 1 | **0.375** | 4.00 |
| `d20afbda` | Qwen3.6-35B-A3B 0.80, CI [0.60, 0.95] | mistral-small-2603 0.90, CI [0.75, 1.00] | 20 | 4 / 2 | **0.688** | 2.00 |

That is the epic's entire thesis, demonstrated on already-published numbers: a 15-point accuracy gap at p = 0.375 and a 10-point gap at p = 0.688, with confidence intervals that overlap across more than half their width. It costs nothing to produce and it is the strongest available argument for the epic existing.

A slice order that follows from this, first slice provable on today's 20-item suites:

| # | Slice | Depends on | Compute and API cost | Proves |
| --- | --- | --- | --- | --- |
| 1 | Bootstrap module, stdlib, seeded, pinned draw procedure. Interval block on the suite score and each language cell, both scorers. `SCHEMA_VERSION` bump, new rows only. | nothing | one re-run of the existing 20-item classification batch: about 2 min local, 0.06 EUR cloud | Wilson and Clopper-Pearson agreement, a hand-computed fixture, and a real interval about 0.18 wide on n=20 — which *is* the disclosure the epic wants |
| 2 | The two paired tests and the per-scoring-kind routing, offline over the published bundle. | slice 1 | **zero** | The table above, reproduced by the code rather than by this report |
| 3 | The comparison record artifact, its analysis command, the refusal rules, Holm, and the differing-dimension field from D3. | slice 2 | zero | Refusal on a bumped `suite_version`; a family of p-values adjusted |
| 4 | The licence spike (MASSIVE, FLORES-200 or a WMT set). Runs **in parallel from day one** — desk research, no bench time. | nothing | zero | The redistribute-versus-manifest decision, which gates slice 6 and nothing before it |
| 5 | The `publication` gate level, the licence and source item fields, the selection rule as data, on constructed fixtures. | the suite seam (D1), and slice 4's answer for the licence field's shape | zero | 99 items fails naming the count; 100 with a short language fails naming the language; the seeded selection replays |
| 6 | Author and run the two publication suites; one published batch each in the reference bundle. | slices 1-5 | the only expensive slice — see D8 | The last two Success Evidence checks |
| 7 | Threshold review; export columns handed to the bundle epic (D2). | slice 6 | zero | Methodology 4 amended, or explicitly left |

Slices 1-3 deliver the reviewer-facing half of the outcome — every score with an interval, every difference with a test — against the suites that exist, long before the licence question is answered. Proposed amendment: state this order, or one like it, in the epic, and state that the interval and the test are not withheld until a publication suite exists. The epic's own decision already implies it:

> A development-level score keeps its `indicative` marking and gains an interval as well.

### D8 — `minor` — the campaign is cheap; the cost story points at the wrong resource

Built from the published per-item token counts (`quality.jsonl`, the current thinking-disabled batches: classification 1286 in and 40 out per item; translation 966 in and about 340 out) and the published throughput figures (`runtime.jsonl`):

| Model | classification, 100 items | translation, 100 items |
| --- | --- | --- |
| Qwen3.6-35B-A3B (25.4 gen tok/s, 273 prompt tok/s) | 10.5 min | 28.2 min |
| Qwen3-4B (33.6 / 275) | 9.8 min | 22.7 min |
| Qwen3-1.7B (116 / 3092) | 1.3 min | 5.4 min |
| Qwen3-0.6B (208 / 4118) | 0.8 min | 3.1 min |

**Both new suites, all four roster models, one pass, one machine: 1.4 hours.** Cloud subject cost for the same pass, from the published `cost_total` fields: **0.16 EUR** — 0.037 EUR for a 100-item Gemini classification batch, 0.095 EUR for translation, 0.023 EUR for Mistral classification. Two judges over 100 items, at a plausible 0.0005 to 0.002 EUR per call, is 0.10 to 0.40 EUR per judged batch.

The multiplication the sibling dimensions produce, on the same basis:

| Configuration | Local hours |
| --- | --- |
| 1 machine x 1 engine x 1 variant (this epic's own campaign) | 1.4 |
| 3 machines, GPU only | 4.1 |
| 3 machines x 2 compute modes | 8.2 |
| 1 machine x 2 engines x 4 variants (the engine epic) | 10.9 |
| 3 machines x 2 engines x 4 variants | 32.7 |
| 8-model roster x 3 machines x 2 engines x 4 variants | 65.5 |

Three qualifications, all of which push the real figure up and none of which changes the conclusion. The throughput figures come from a `max_tokens=128` runtime probe, not the quality path, so they are indicative. `cpu_only` is materially slower than these GPU numbers, and the machine epic's DDR4/DDR5 pair runs there by design. And a thinking-allowed configuration multiplies output tokens by five or six times — the published rows show it directly: Qwen3-0.6B on translation went from 2688 output tokens per item to 354 once the thinking policy was set.

So the binding constraints are, in order: the **Google pacer** (13.7 min per 100-item batch, with D4's retry budget on top of it), the **flagship's prefill** at 273 tok/s, which makes a 1286-token classification prompt prompt-bound rather than generation-bound, and **operator attention** across three machines. Money is not a constraint at any point — the full 48-cell matrix above is under 10 EUR of API spend. Proposed amendment: none required, but the epic's cost story is better told in hours and pacing than in API cost, and D4 is the item that actually threatens the campaign.

### D9 — `minor` — 100-plus drawn items have no declared representation, and today's items are Python source

`classification_suite.py` holds its 20 items as `_item(...)` literals in module source; the same for `translation_suite.py`. `suite_snapshot.py` exports them to JSON for bundle readers but is explicit that it is not a registry:

> These are snapshots, not a live registry [...] it is not consulted at read time by anything the suite itself runs through

The epic decides *whether the item text may be redistributed* (redistribute versus manifest plus fetch script, deferred to the spike) but never *where a publication suite's 100-plus items live in the repository*. Generated Python source is the path of least resistance from here and the wrong answer: a 100-item seeded subset regenerated from a source revision is data, and expressing it as source code makes the selection rule's replay a code-generation step. This is a decision the suite seam (D1) may well take on this epic's behalf — another reason to name that seam precisely rather than depending on the whole sibling epic.

### D10 — `minor` — every field this epic adds forces a decision inside the pitch epic's view partition, which this epic excludes

`read_model.py:20-25`:

> The field sets each view renders are *partitioned* against `row_contract` rather than hand-maintained beside it [...] A field added to the contract fails the build until it is either rendered or deliberately declared unrendered

This epic adds, at minimum: the suite level, the item licence, the item source and its revision, the interval, the resample count, the seed, the interval method, and the draw procedure of D5. Eight or more contract fields, each of which fails the build until someone touches a view field set — while the epic states:

> Excludes: [...] **rendering any of this to a decision-maker.** `the-pitch-runs-from-a-browser-and-only-with-the-key` owns the views

Declaring a field unrendered is not rendering it, so there is no contradiction — but it is a file this epic must edit in an area another epic owns, and it is worth saying so before a story plan discovers it. Proposed amendment: one line in `Boundaries` stating that new contract fields are declared unrendered in the view partition by this epic, and that whether the pitch renders them is that epic's call.

## Questions

**Q1 (D1)** — Can the suite definition shape and registry be split out of `no-use-case-is-silently-absent` as a story both epics declare, or must this epic's `depends_on` name that epic whole? *Unlocks:* slice 5, and with it the whole publication-suite half. Until it is answered, this epic's realistic scope is slices 1-4 and it should be sized that way.

**Q2 (D2)** — Which epic ships the export command, and in which order relative to this one? *Unlocks:* whether this epic delivers an exporter or a column contribution, and whether the Success Evidence check "recomputing from the published bundle alone" runs through this epic's own analysis command or through the bundle epic's export.

**Q3 (D6)** — Is a dev-only `scipy` acceptable as a test oracle, given the project's stated stdlib-at-runtime posture and its OSV audit gate? *Unlocks:* the story plan's test strategy, and removes the hand-computed-reference-values maintenance burden the epic currently accepts.

**Q4 (D4)** — Who owns raising the cloud retry budget and the resume granularity to 100-item scale: this epic as a precondition, or the row epic's rate-limit story revisited? *Unlocks:* whether the slice-6 campaign can be started with confidence, or is expected to fail and re-pay.

**Q5 (D7)** — Is there an objection to publishing intervals and paired tests over the existing 20-item development suites before any publication suite exists? *Unlocks:* the first two slices starting immediately, at zero compute and zero API cost, on rows already in the bundle.

**Q6 (D5)** — Percentile or BCa, decided now rather than in a story plan? *Unlocks:* the size of the reproducibility contract — percentile needs a draw procedure pinned; BCa needs that plus a jackknife convention and an inverse-normal convention, for an accuracy gain that 100 items does not obviously earn.

## One thing this report does not answer

The MASSIVE and FLORES-200 licence leads are named in the epic as a spike, and this assessment did not resolve them — deliberately, because a licence read from memory is the class of claim the spike exists to prevent. One note for whoever runs it: check the share-alike question **first**. If a lead's terms are share-alike, mixing its items into a CC-BY-4.0 bundle is precisely the infection the epic already names, and the manifest-plus-fetch-script fallback becomes the default rather than the fallback — which changes the bundle epic's self-sufficiency claim, and therefore D2's ordering. That single check, answerable in an afternoon at zero cost, has more leverage over this epic's shape than anything else in slice 4.
