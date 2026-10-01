# Owner questions: autonomous slicing run (2026-10-01)

Questions this unattended run could not decide under its bounded authority. Each entry names the artifact, the question, the options, the recommended default with its reason, and what it blocks.


## Interval and paired test

Epic: `aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md`. The epic's open "percentile or BCa", "which level carries the headline number" and "default comparison family" rows are not repeated here: PRD Methodology 4 and 24 now settle all three (percentile; the development-level score leads; one suite by one compared dimension), and the stories follow the PRD.

### Q1. Does the suite seam become one story both epics declare, and do 100-plus item suites live as data?

- Artifact: `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md`, `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md` (and transitively `the-threshold-review-is-written-from-the-first-publication-run.md`).
- Question: the suite definition shape, the registry resolving a suite id, and where a publication suite's items are stored belong to `no-use-case-is-silently-absent`, which has no stories yet. Does that seam become one story in that epic which both epics declare in `depends_on`, or does the edge stay epic-wide? And are 100 to 300 drawn items stored as data or as generated Python source like today's `_item(...)` literals?
- Options: (a) one seam story in `no-use-case-is-silently-absent`, declared by both epics, items stored as data; (b) keep the epic-wide `depends_on` and let the first suite story settle storage; (c) this epic builds the seam itself.
- Recommended default: (a). The epic itself says only the seam is on its path and the epic-wide edge overstates it; storing a seeded subset as generated source makes the selection-rule replay a code-generation step.
- Blocks: orders 7 and 8 (both `proposed`), hence order 9.

### Q2. Confirm the tabular-export split, and whether comparison records get their own export table

- Artifact: `aidd_docs/backlog/stories/the-tabular-export-carries-the-interval-and-the-comparison-record.md`.
- Question: `one-download-holds-the-tables-their-licences-and-how-to-cite-them` states a split (export mechanism, schema, column dictionary and release asset there; existence and correctness of the statistical columns here), while this epic records the boundary as open and unowned. That epic's four tables have no place for a comparison or family record. Is the split confirmed, and do comparison and family records become a fifth export table?
- Options: (a) accept the stated split; the bundle epic adds a fifth table for comparison and family records, with the column definitions supplied from this epic; (b) this epic ships its own export of the statistics; (c) the bundle epic owns everything including the statistical columns' definitions.
- Recommended default: (a). It matches the split one sibling has already written down and avoids two exporters over one bundle.
- Blocks: order 6 (`proposed`).

### Q3. Who owns the cloud retry budget and per-item resume at publication scale?

- Artifact: orders 7 and 8 (cloud batches only).
- Question: `DEFAULT_CLOUD_RETRY_MAX_ATTEMPTS = 4` is a batch total and `--resume` re-runs an incomplete batch from item 1; a 100-item Google batch is 200 paced requests. The epic names `a-rate-limited-run-persists-resumes-and-never-re-pays` as the likely owner, but that story is `done` and parented to `any-open-ended-output-carries-two-judges-or-an-honest-flag`, not to the row epic the epic text suggests. Which epic gets a new story for a budget that scales with item count or for per-item resume?
- Options: (a) a new story under `any-open-ended-output-carries-two-judges-or-an-honest-flag`, beside the done one; (b) a new story under `every-published-row-explains-and-reproduces-itself`; (c) a new story under this epic.
- Recommended default: (a). The done story is never reopened (a changed need is a new story), and its parent already owns the retry and resume behaviour.
- Blocks: a cloud batch on either publication suite. Not the one required published batch per suite, which can be local.

### Q4. Is a comparability field absent on both sides a refusal, or an observation naming the absence?

- Artifact: `aidd_docs/backlog/stories/two-configurations-on-the-same-items-receive-a-paired-test-or-a-refusal.md`.
- Question: the committed quality rows are `schema_version` `"7"` and carry no `thinking_policy`, one of the four Methodology 3 constraints. Should a comparison whose two sides both lack it be refused naming the field, or published as an observation naming the absence?
- Options: (a) refuse, applying Methodology 8's "two unknown values never count as a match"; (b) publish as an observation, never as a test, naming the absent field.
- Recommended default: (a). It is the rule the PRD already applies to comparability, and the bundle regeneration (`the-laptop-proves-both-modes-and-republishes-the-bundle-once`) removes the case. Cost: until then, the epic's zero-cost demonstration on the two committed pairs publishes refusals, not p-values.
- Blocks: nothing. Order 2 is written to the default and is `ready`; a different answer changes one Evidence bullet.

### Q5. One epic with two done gates, or two epics?

- Artifact: the epic, and `the-engine-and-the-prompt-variant-are-measured-not-assumed` (which declares `depends_on` on the whole of this epic).
- Question: the inferential half (orders 1, 2, 3, and 6 once unblocked) needs no licence, no public benchmark and no new item; the publication half (orders 4, 5, 7, 8, 9) waits on two spikes and a real run. Does the done gate split?
- Options: (a) one epic, two gates, with the downstream epic depending on gate one; (b) split into two epics; (c) one gate.
- Recommended default: (a), the epic's own recommendation; it unblocks the engine and variant epic without waiting on a licence answer.
- Blocks: no story here; it decides when the downstream epic may start.

## Judge amendment

Epic: `aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md`. New stories are orders 7 to 11; the three API-surface unknowns (Z.ai, DeepSeek, the calibration endpoint) are open spikes under `aidd_docs/backlog/spikes/`, not questions here.

### Q6. What happens to the judged probe story written for the retired Mistral and Google judges?

- Artifact: `aidd_docs/backlog/stories/the-judged-probe-runs-both-paths-in-three-languages.md` (order 6, `ready`), and transitively `aidd_docs/backlog/stories/glm-and-deepseek-are-the-only-judges-and-mistral-and-google-never-judge-again.md` (order 10).
- Question: order 6 is `ready` but cannot produce a row: its acceptance binds Mistral and Google as judges and requires one cloud-subject row judged by the other family alone and flagged single-judge, a path the new pair leaves with no live trigger. Its runner `judge_probe.py` exists and imports both retired judge backends, so retiring them (order 10) and rebinding the probe land together. The epic says order 6's acceptance "is rewritten with it, as a story change". Is it rewritten in place, cancelled and superseded, or left as it is?
- Options: (a) rewrite order 6 in place: two-judge rows under GLM and DeepSeek for every item, the single-judge path proven by order 10's forced collision rather than by a row, one item in ten also calibrated once order 11 lands, its `depends_on` moved to orders 10 and 11, and its README answers extended to the calibration figure and the actual campaign cost; (b) cancel order 6 with the reason recorded and create a new story that `supersedes` it with that acceptance; (c) leave order 6 unchanged and blocked until the owner revisits.
- Recommended default: (a). The epic already states the acceptance is rewritten as a story change, the story is not `done` so no completed work is overwritten, and its runner and ten items are provider-agnostic and survive. Cost: order 6's history no longer shows the single-judge row it once promised; the epic's success check 2 already replaces it with the forced collision.
- Blocks: order 6, order 10 (`proposed`), and through them order 11 and the epic's Success Evidence run.

### Q7. Which endpoint serves the calibration judge, GPT-5.6 Luna?

- Artifact: `aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md` (order 11), and its spike `aidd_docs/backlog/spikes/which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms.md`.
- Question: Methodology 11 names the pair's providers and requires each to be called through its own direct API, but names only the calibration model, not its provider; its router clause ("where a router is used its provider order is fixed, fallbacks disabled") leaves a router open. Is GPT-5.6 Luna called through its vendor's direct API, or through a router?
- Options: (a) the vendor's direct API (OpenAI), the same rule the pair follows; (b) a router with a fixed provider order, fallbacks disabled and the answering provider on the row; (c) whichever the spike finds cheaper.
- Recommended default: (a). It matches the pair's rule, keeps the calibration judge at one egress destination rather than a router plus an upstream, and makes "the provider that actually answered" true by construction. Cost: one more provider account and key to hold.
- Blocks: order 11 (`proposed`); the spike can investigate the direct API first under this default.

### Q8. How is the 10% calibration subsample drawn, and what is its floor?

- Artifact: `aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md` (order 11).
- Question: Methodology 11 sets "a 10% subsample of judged items" to test for a shared bias "in particular on FR and DE items", but not the unit (per batch, per suite, per campaign), the draw, or a floor. A plain 10% of the ten-item probe is one item, which cannot carry an agreement figure nor an EN versus FR/DE split, and a uniform draw over a small suite can contain no FR or DE item at all.
- Options: (a) per suite and batch, a seeded draw stratified by language, rounded up, with at least one item per language present; the n is published beside each figure and an undefined statistic publishes a null with its reason (on the probe this is 3 items of 10, above 10%); (b) a plain seeded 10% rounded up, uniform over the items, accepting that a small suite may calibrate no FR or DE item; (c) a fixed minimum count per language (for example 5) regardless of suite size, at a higher calibration cost.
- Recommended default: (a). It is the smallest rule that can answer the FR/DE question the PRD gives the calibration judge, and it keeps the 10% rate on publication-size suites where stratified rounding is negligible. Cost: a deviation above 10% on small suites, which the PRD's revisable-threshold clause allows but only the owner can accept.
- Blocks: order 11 (`proposed`).

### Q9. What happens when the found catalogue prices put a judged campaign over the ten-dollar estimate?

- Artifact: orders 8, 9 and 11, and the spikes behind them, which each return a list price.
- Question: the PRD accepts "a small judging budget, on the order of ten dollars per campaign at catalogue rates" and states cost is reported, never optimised. Nothing says what a run does if the projected or actual spend exceeds it, for example if the calibration judge's rate is far above the pair's.
- Options: (a) no cap: every judged row reports its judge cost, the first campaign's actual total is compared against the estimate in the results README, and the owner revisits the budget then; (b) a per-campaign spend ceiling that stops issuing paid calls when reached and marks the run partial, through the shipped partial-and-resume machinery; (c) shrink the calibration subsample when its share of the budget passes a set fraction.
- Recommended default: (a). It follows the PRD's "reported, never optimised" rule and the epic's own closing question about actual versus estimated cost; (b) is a budget control the PRD does not ask for, and (c) changes a methodology threshold for cost reasons. Cost: a mispriced campaign is noticed after it is paid for, bounded by one campaign.
- Blocks: nothing today. Answering (b) or (c) adds a story under this epic.

## Size-class families

Epic: `aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md`. New stories are orders 1 to 8; which candidate GGUFs exist per class and whether the pinned build loads them is an open spike (`aidd_docs/backlog/spikes/which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them.md`), not a question here. The licence policy, the defer-by-default rule for an unsupported architecture and the per-entry thinking control are decided by the epic and are not repeated.

### Q10. Which figure do the four size-class bands read, and where are the edges?

- Artifact: `aidd_docs/backlog/stories/the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one.md` (order 3), and transitively orders 5 to 8.
- Question: the epic fixes four classes "roughly ~0.5B, ~2B, ~4B and ~8B-and-up by nominal size", and in the same decision bounds them "by the footprint bands the 16 GB no-GPU PC, the 6 GB-VRAM laptop and the 8 GB-VRAM tower separate", while rejecting classing by total parameters alone. At the quants in use the two readings disagree: the three dense Qwen files are 0.60, 1.71 and 2.33 GiB and fit every machine, so machine-derived bands would put the bottom three nominal classes into one, and the order 3 check cannot tell a declared class from a wrong one until one measure is chosen.
- Options: (a) the class is banded on total parameters, with edges at 1B, 3B and 6B (which yields the epic's four nominal classes and places every shipped entry where its name suggests), and bytes on disk is recorded and published beside it as the footprint figure without banding; per-machine fit stays with the machine epic's profiles; (b) the class is banded on bytes on disk, with edges where the machines separate (about 5 GB allocatable laptop VRAM, 8 GB tower VRAM, about 12 GB usable RAM on the 16 GB PC), accepting that the nominal names no longer describe the classes; (c) both: a nominal class banded as (a) plus a separate machine-fit band per entry, checked independently.
- Recommended default: (a). It is the only option that keeps the four classes the epic and the gap brief name, it is checkable from the entry, and the epic itself excludes per-machine fit ("the per-machine decision of whether a given entry runs is not taken here"). Cost: the epic's "bounded in practice by the footprint bands" clause becomes descriptive rather than the measure, which only the owner can accept; edges stay revisable after the first full-roster run.
- Blocks: order 3 (`proposed`), hence orders 5 to 8.

### Q11. Is a model family its vendor lineage or its model line?

- Artifact: `aidd_docs/backlog/stories/every-roster-entry-states-its-family-its-licence-and-its-language-claim.md` (order 1).
- Question: this epic lists the families `KNOWN_FAMILIES` must accept as `gemma`, `granite`, `ministral`, `lfm2` and `phi`, while the judge epic reads Gemma as sharing Google's family ("Google cannot judge a Gemma row") and Ministral as making `mistral` a local subject family. One attribute serves both the composition rule and the judge-independence guard, so it needs one meaning.
- Options: (a) vendor lineage, reusing the existing values: Gemma resolves to `google`, Ministral to `mistral`, and `ibm` (Granite), `liquid` (LFM2) and `microsoft` (Phi) are added; `display_id` keeps the model line visible; (b) model line: `gemma`, `granite`, `ministral`, `lfm2`, `phi`, with a separate vendor mapping for the independence guard; (c) model line for the composition rule and vendor for judging, as two fields.
- Recommended default: (a). It matches the judge epic's reading, keeps one field with one meaning, and needs no second mapping; for the composition rule, two vendors are two families either way. Cost: a published family column reads `google` beside a Gemma model, which the `display_id` column beside it disambiguates.
- Blocks: nothing. Order 1 is written to the default and is `ready`; a different answer changes literal family values before any non-Qwen row is published, which is when changing them is still free.

### Q12. Which candidate models does each size class take, in which order, and at which quant?

- Artifact: orders 5 to 8 (`the-half-billion-class-...`, `the-two-billion-class-...`, `the-four-billion-class-...`, `the-top-class-spans-two-families-with-dense-and-moe-or-says-why-not.md`).
- Question: the epic names the families (Gemma 4 including the 26B-A4B MoE, Granite at 350M and 1B, Ministral, LFM2, Phi) and a stopping rule ("pursued until the rule is satisfied in every class the machines can hold, not pursued as a fixed shopping list"), and the PRD defers "which specific dense and MoE models make the initial roster" as a model-selection decision. Neither names the exact model per class, the order candidates are tried in, or the quant, and quants differ today within the Qwen ladder (`Q8_0` at 0.6B and 1.7B, `Q4_K_M` at 4B, `UD-IQ4_XS` for the MoE). `context_input/model_candidates.md` also lists GPT-OSS 20B, Qwen3-Coder-30B-A3B and Mellum2-12B-A2.5B, which are outside the epic's family list.
- Options: (a) take the spike's per-class shortlist, restricted to the epic's families: Granite 350M and the smallest LFM2 at ~0.5B; Granite 1B and LFM2 at ~2B; Ministral 3B and the Phi mini model at ~4B; Gemma 4 26B-A4B (MoE) and Gemma 4 12B (dense) at the top; any sub-4B MoE the spike finds is taken at its class; candidates tried smallest download first; one passing non-Qwen family per class suffices; each taken at the quant matching the Qwen entry of its class where its publisher ships it, otherwise the nearest one with the difference stated; (b) the same shortlist, but every passing candidate enters rather than stopping at the first second family; (c) (a) plus GPT-OSS 20B and Mellum2 at the top class as further MoE families.
- Recommended default: (a). It is the epic's own stopping rule applied literally (the outcome is the composition, not a count of models), it bounds bench time and disk, and quant matching keeps a family comparison from being read as a quant comparison, the confusion this epic exists to remove. Cost: a class satisfied by its first passing family reports one rival, not the best one; (b) is the option that answers "which small model is best", at several times the bench cost.
- Blocks: orders 5 to 8 (`proposed`), together with the spike.

## Engine and prompt variant

Epic: `aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md`. The epic's four Ollama and compressor unknowns that evidence can settle are open spikes under `aidd_docs/backlog/spikes/`, not questions here. This epic depends on the interval and paired-test epic through its stories orders 1, 2 and 3 only, which is Q5's option (a) taken as the working assumption.

### Q20. Does llama.cpp's own configuration hash enter the fiche's hashed projection in this epic?

- Artifact: `aidd_docs/backlog/stories/every-row-names-the-engine-that-produced-it-and-the-fiche-hashes-it.md` (order 1).
- Question: the epic decides that "the engine's effective configuration carries a content hash over a path-free normalisation, and that hash enters the projection", and its Boundaries name llama.cpp's normalisation (the flag list with the absolute model path replaced by the roster entry reference). The same decision row then hands "whether llama.cpp's own flags should therefore be hashed through a normalised digest" back to the row epic, unanswered. Applied to llama.cpp, the first sentence answers the handed-back question. Which reading holds?
- Options: (a) the engine configuration hash enters the projection for both engines now, llama.cpp's computed over its normalised flag list; the raw `flags` stay outside the projection as evidence; (b) only the comparator's configuration hash enters the projection, llama.cpp's is recorded on the fiche as evidence until the row epic decides; (c) neither enters the projection; both are evidence only.
- Recommended default: (a). It is the epic's own decision applied without exception, and Methodology 8 already lists "the server flag set" as verdict-blocking (`verdict._RUNTIME_BLOCKING_FIELDS` carries `flags`), so hashing the normalised set aligns the hash with the verdict instead of creating a new rule. Cost: an operator thread-count override moves the fiche hash, so a re-run under a different override becomes `not comparable` rather than `reproduced`, which is the M8 reading anyway; and (b) would make the two engines' identities asymmetric.
- Blocks: nothing. Order 1 is written to the default and is `ready`; a different answer changes one acceptance bullet.

### Q21. Which roster model does the "what the defaults cost" side-run use?

- Artifact: `aidd_docs/backlog/stories/what-a-default-ollama-install-costs-is-published-as-its-own-figure.md` (order 11).
- Question: the epic fixes the side-run to "one named roster model" and does not name it. The choice decides what the figure can say: a small dense entry is cheap and fits any machine; the MoE flagship is where Ollama's own offload and context defaults would cost a laptop user the most, but whether the Ollama library carries a matching tag is unverified.
- Options: (a) `qwen3-0.6b-q8` (roster quant `Q8_0`), the machine epic's proving model; (b) the MoE flagship `qwen3.6-35b-a3b-ud-iq4xs`; (c) `qwen3-4b-q4km` (roster quant `Q4_K_M`).
- Recommended default: (a). Cheapest to run under the full runtime protocol, runnable on every reference-machine candidate, and its roster quant is pinned explicitly so any different quant Ollama chooses is readable on the figure. Cost: the figure says nothing about MoE offload defaults, the case a consultant is most likely asked about; (b) can follow as a second side-run if spike `can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol` finds a matching library tag.
- Blocks: order 11 (`proposed`).

### Q22. Which machine is the campaign's declared reference machine?

- Artifact: `aidd_docs/backlog/stories/the-campaign-answers-whether-each-variant-helps-or-hurts-a-small-model.md` (order 12), and the bounds of spike `which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement`.
- Question: the epic runs the full 2 engines x 4 variants campaign "on one declared reference machine" and every claim names it, but never names the machine; its compressor unknown reasons about "a 6 GB laptop", which implies the laptop without stating it.
- Options: (a) the laptop (RTX 3060 Laptop, 6 GB VRAM, about 5.1 GB allocatable, per `context_input/hardware.md`), in its `gpu` mode; (b) the tower (RTX 3050, 8 GB VRAM); (c) the laptop in `cpu_only` mode.
- Recommended default: (a). It is the development machine where every command is agent-executable, the existing bundle and the machine epic's proving runs are taken there, and it is the machine the epic's VRAM-pressure reasoning names. Cost: the tightest VRAM of the GPU machines, so the compressor's placement is most likely forced to CPU or a separate phase.
- Blocks: order 12 (`proposed`); the compressor spike can proceed on the laptop under this default.

### Q23. May the input compressor bring a heavy ML dependency into the project, and how?

- Artifact: `aidd_docs/backlog/stories/the-input-compression-variant-records-its-compressor-as-a-step-of-its-own.md` (order 9).
- Question: an LLMLingua-2-class compressor is a neural token classifier; the reference implementation's package depends on a deep-learning runtime that the project does not carry today. The container image ships no weights and the reproduction path is documented around llama.cpp alone. How may the compressor enter the project?
- Options: (a) an optional, pinned dependency group used only by the `input_compressed` variant, excluded from the default install and the published container, its weights downloaded by revision with a checksum like a roster entry; (b) the compressor runs out of process in its own pinned environment, called by the harness through a narrow interface; (c) a required dependency of the project.
- Recommended default: (a). It keeps the default install and the container unchanged for every reader who does not reproduce the compression cells, and reuses the pin-and-checksum discipline the roster already applies. Cost: a reproduction of the `input_compressed` cells needs one extra documented install step, and the dependency scan must cover the optional group.
- Blocks: order 9 (`proposed`), together with its spike.

### Q24. How are TTFT, tokens and energy measured per variant and per task family?

- Artifact: `aidd_docs/backlog/stories/each-quality-item-records-the-tokens-and-the-first-token-time-its-generation-took.md` (order 10), and order 12.
- Question: the epic's statement reports each variant's effect "per task family, on quality, TTFT, tokens and energy", each difference carrying a paired test. Today a quality row is per item but carries tokens and energy only as batch totals and no TTFT, and the runtime protocol (Methodology 6) measures TTFT and energy on one fixed prompt, not on suite items. No row today could supply a per-item paired test on any of the three.
- Options: (a) quality rows gain per-item engine-reported TTFT (with its `ttft_source`) and per-item tokens in and out, so TTFT and tokens get paired tests over items; energy stays measured per batch, and per-variant energy differences are published as observations; (b) as (a), plus the energy tracker started and stopped around each item so energy is paired too; (c) per-item tokens on quality rows, while TTFT and energy come from the runtime protocol run per variant on a declared representative item per task family, with no paired test on either.
- Recommended default: (a). Paired tests need per-item values, the engine already reports per-generation timings, and per-item energy on items of a few dozen tokens sits below what the tracker can resolve, so (b) would publish noise as a paired result. Cost: per-item TTFT on a quality batch is not the Methodology 6 runtime figure (no warm-up exclusion, no repetitions) and must be labelled as a distinct measurement; no paired energy claim is possible.
- Blocks: order 10 (`proposed`) and through it order 12.

## No use case silently absent

Epic: `aidd_docs/backlog/epics/no-use-case-is-silently-absent.md`. New stories are orders 1 to 10, plus one task (`aidd_docs/backlog/tasks/register-the-closed-harness-candidate-set-and-its-three-row-fields.md`). The epic's two named spikes (tool-calling maturity per model and harness; search-tool selection) are open spikes under `aidd_docs/backlog/spikes/`, not questions here. Q1's recommended default (a) is written as order 1, `a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md`: the epic's own Boundaries already state a suite is "data plus a named scoring rule", so the story stores items as data. Which harnesses a campaign compares, and whether the comparison runs on every agentic model, are not repeated here: the epic defers both to the campaign declaration of `the-engine-and-the-prompt-variant-are-measured-not-assumed`.

### Q30. Is an incomplete coverage record ever published, or only refused until every entry resolves?

- Artifact: `aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md` (order 2).
- Question: the epic says a record with a use case missing or stateless "is not a shape the harness can publish". Read strictly, no coverage record is published until the last of the six new suites lands (or is marked out of scope), and until then the pitch overview states the record's absence. Should interim bundles instead publish a partial record?
- Options: (a) strict: the record is refused until every entry resolves, and the refusal output is the interim coverage reading; (b) interim entries are published as `out-of-scope-this-release` with the reason "not yet built" and the owning story, flipped as suites land; (c) add a fourth state such as `planned`.
- Recommended default: (a). It is the epic's own wording, and (b) puts an "out of scope this release" label on use cases the epic intends to ship, which a reader cannot tell from a real scoping decision; (c) widens a three-state set the epic and PRD fix. Cost: the pitch shows no coverage card state until the epic is nearly done.
- Blocks: nothing. Order 2 is written to the default and is `ready`; (b) or (c) changes one acceptance bullet and the pitch epic's rendering.

### Q31. What sandbox posture runs model-generated code?

- Artifact: `aidd_docs/backlog/stories/generated-code-is-scored-by-its-tests-in-a-sandbox-or-not-run-at-all.md` (order 4).
- Question: the epic's Sequence makes "sandbox posture decided" the gate before the code-generation story, and its unknowns table recommends one posture without deciding it. Which posture is adopted?
- Options: (a) container-based, no network, no host mount, wall-clock and memory caps, refusing to run where no container runtime is present, sharing the runtime the published image already uses; (b) a host subprocess under OS-level limits, with no container dependency; (c) a WebAssembly or language-level sandbox per programming language.
- Recommended default: (a), the epic's recommendation. The project already ships a container image, so the runtime is not a new dependency, and refusing rather than falling back is the only posture that never runs untrusted code on the host. Cost: an operator must have a container runtime on each bench machine for this suite, and the no-GPU professional PC may not.
- Blocks: order 4 (`proposed`).

### Q32. Which programming language joins Python in the code-generation suite?

- Artifact: `aidd_docs/backlog/stories/generated-code-is-scored-by-its-tests-in-a-sandbox-or-not-run-at-all.md` (order 4).
- Question: the epic requires "Python plus at least one other language, named on the item and on the row" and names none. Which one?
- Options: (a) JavaScript (Node, its built-in test runner); (b) TypeScript; (c) a compiled language such as Java, C# or Go; (d) more than one.
- Recommended default: (a). It is the most common second language in client codebases, needs no compile step in the sandbox, and its test runner ships with the runtime. Cost: no claim about a typed or compiled language is publishable; (b) or (c) adds a compile step and a build failure mode to the scoring.
- Blocks: order 4 (`proposed`).

### Q33. How is a harness's per-call prompt overhead measured?

- Artifact: `aidd_docs/backlog/tasks/register-the-closed-harness-candidate-set-and-its-three-row-fields.md`, and through it orders 5, 6, 7, 8 and 9.
- Question: Methodology 23 requires every agentic row to report "the tokens the framework adds around the user prompt" but does not define the subtraction; the epic records a recommendation open to contradiction. Which rule is adopted, and are an item's own tool definitions part of the item or of the overhead?
- Options: (a) per call, the token count of what the engine finally received minus the token count of the item's own rendered prompt (including the item's tool definitions as rendered under `direct`), under the tokenizer the row already names; a framework that rewrites rather than wraps the item's prompt is recorded unmeasurable, not zero; (b) the framework's own reported prompt-token count minus `direct`'s for the same item; (c) report the total only and drop the separate field.
- Recommended default: (a), the epic's recommendation. It reads what the engine actually received rather than trusting a framework's self-report, and counting tool definitions as item content keeps `direct`'s overhead from being inflated by the task itself. Cost: it needs the engine-side prompt to be readable per call, which the tool-calling spike checks per framework; (c) contradicts the PRD acceptance criterion.
- Blocks: the harness task (`proposed`), hence orders 5, 6, 7, 8 and 9.

### Q34. Is web research a retrieve-then-answer pipeline, or agentic tool use?

- Artifact: `aidd_docs/backlog/stories/a-web-research-score-recomputes-offline-from-its-archived-search-responses.md` (order 9), and order 10.
- Question: the epic recommends pipeline-first, open to contradiction: the harness issues the search, archives the response, and the model answers over it. The alternative lets the model decide when and what to search through a tool call.
- Options: (a) pipeline-first: web research is independent of the tool-calling spike, sits outside the harness comparison this release, and records harness `direct`; an agentic variant is deferred until the tool-calling spike reports; (b) agentic from the start, sharing order 6's transcript capture and the spike's risk; (c) both, as two scoring rules over one query set.
- Recommended default: (a). It keeps the heaviest suite off the riskiest gate and makes every archived response a function of the query alone, which is what makes offline recompute straightforward. Cost: the suite measures answer writing over search results, not a model's search strategy.
- Blocks: orders 9 and 10 (`proposed`).
