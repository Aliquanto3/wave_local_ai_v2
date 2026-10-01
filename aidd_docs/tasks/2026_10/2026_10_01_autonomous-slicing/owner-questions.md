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
