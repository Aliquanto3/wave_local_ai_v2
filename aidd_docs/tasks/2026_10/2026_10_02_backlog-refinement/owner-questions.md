# Owner questions: backlog refinement run (2026-10-02)

Questions this unattended run could not decide under its bounded authority. Each entry names the artifact, the question, the options, the recommended default with its reason, and what it blocks. Numbering starts at Q100 to stay clear of `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`.

## Judge providers

Spikes: `aidd_docs/backlog/spikes/is-deepseek-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/is-z-ai-glm-callable-as-a-pinned-judge-and-on-what-data-terms.md`, `aidd_docs/backlog/spikes/which-endpoint-serves-gpt-5-6-luna-as-a-pinned-calibration-judge-and-on-what-terms.md`. All three stay `blocked`: their Bounds require captured live calls, which this run may not make. Desk research found the same gap in all three, asked once here.

### Q102. How does Methodology 12 pin a judge whose provider publishes no dated model id?

- Artifact: PRD Methodology 12 ("A cloud row records the provider's dated model id, never a floating alias, and the API version; a run refuses to start when that id is absent from the provider's live model list"); `aidd_docs/backlog/stories/a-glm-judge-answers-through-z-ai-under-the-pinning-discipline.md` (order 8), `aidd_docs/backlog/stories/a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md` (order 9), `aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md` (order 11).
- Question: none of the three judge providers documents a dated id for the candidate model. DeepSeek lists only names it repoints in place (`deepseek-v4-pro` received new weights on 2026-08-13 with "Model names remain unchanged"). Z.ai publishes release ids (`glm-5.2`) with no snapshot policy and documents no model-list endpoint at all. OpenAI lists `gpt-5.6-luna` as the model's only snapshot, undated. Read literally, Methodology 12 makes all three a no-go. The Google subject already runs on a release id plus the catalog's read-only `version` string (`aidd_docs/memory/external/google-ai-studio-api.md`), which is the closest precedent. How is Methodology 12 read for a judge?
- Options: (a) extend the Google precedent to judges: pin the provider's release or snapshot id; the pre-flight reads the live model list where one exists, and where none exists sends a one-token probe to the pinned id, recorded on the row as a probe; every row records each build marker the provider returns (listing `version`, `name` or `created`, response `system_fingerprint`), and a run refuses to start when a recorded marker differs from the pinned one; Methodology 12's text is amended to say so; (b) literal reading: every provider without a dated id is a no-go, the judge pair and the calibration judge are reopened, and new spikes look for families that publish dated ids; (c) decide per provider after the live calls, keeping the literal rule as the default.
- Recommended default: (a). It is the reading the project already applies to its Google subject, it keeps the pair and the calibration model the PRD names, and the live calls the spikes list still capture whatever marker each provider actually returns. Cost: a silent weight change under an unchanged name and marker (DeepSeek's 2026-08-13 update is one) is not detected; judged scores are then reproducible only within a dated window, and the inter-judge agreement and the calibration figure are the only drift signals. Only the owner can amend PRD text.
- Blocks: orders 8, 9 and 11 of `any-open-ended-output-carries-two-judges-or-an-honest-flag`, and through orders 8 and 9 every story that needs a judged score (order 10, the judged probe, the rewriting suite, document comparison, RAG, web research, and the judged re-run verdict).

### Q103. Is DeepSeek's training opt-out requested before the first paid call?

- Artifact: `aidd_docs/backlog/stories/a-deepseek-judge-answers-through-deepseek-under-the-pinning-discipline.md` (its egress acceptance bullet), and the results README's egress statement.
- Question: DeepSeek's Privacy Policy (last updated 2026-02-10) lets it use API inputs for training unless the user opts out by email to privacy@deepseek.com; inputs are processed and stored in the PRC with no fixed retention. This is compatible with the PRD egress non-goal (only the repo's own suite items and outputs derived from them leave the machine), but the suite items would then risk entering a training set. Is the opt-out requested?
- Options: (a) request it from the account owner's address before the first paid call, keep the reply, and state the opt-out and its date in the README; (b) do not opt out, and state in the README that suite items and local outputs sent to DeepSeek may be used for training; (c) send the request, and state in the README that it was sent and whether DeepSeek confirmed it.
- Recommended default: (c). One email lowers the contamination risk for the publication suites, and the policy promises no confirmation, so the README claims only what was sent and received. Cost: one owner email.
- Blocks: the wording of order 9's egress statement only, not its code.

### Q104. Does the calibration judge stay GPT-5.6 Luna now that GPT-6 Luna exists?

- Artifact: PRD Methodology 11 (names GPT-5.6 Luna) and `aidd_docs/backlog/stories/a-calibration-judge-scores-one-judged-item-in-ten-and-never-moves-a-score.md` (order 11).
- Question: OpenAI released `gpt-6-luna` on 2026-09-22 at about half the price of `gpt-5.6-luna` ($0.10 / $0.50 against $0.20 / $1.20 per 1M input / output tokens). GPT-5.6 Luna is not deprecated, and neither has a dated id. Which model calibrates?
- Options: (a) keep `gpt-5.6-luna`, as the PRD names it; (b) switch to `gpt-6-luna` and amend Methodology 11; (c) keep `gpt-5.6-luna` and switch only when OpenAI publishes a deprecation notice.
- Recommended default: (a). The PRD names it, it is not deprecated, the saving is about a dollar per large campaign (the spike's projection puts calibration well under the ten-dollar estimate either way), and switching changes nothing for Q102. Cost: a calibration judge one generation behind OpenAI's current Luna.
- Blocks: nothing; order 11 is written against the PRD's model.

## Publication suites

Spikes: `aidd_docs/backlog/spikes/which-public-classification-benchmark-seeds-the-publication-suite-and-on-what-terms.md`, `aidd_docs/backlog/spikes/which-public-translation-benchmark-seeds-the-publication-suite-and-on-what-terms.md`. Both licence rungs are settled from evidence (permissive in both cases); what remains in each is a choice only the owner can make.

### Q105. Which public benchmark seeds the classification publication suite?

- Artifact: the classification spike, and `aidd_docs/backlog/stories/a-publication-level-classification-suite-stands-beside-the-hand-written-one.md` (interval epic order 7).
- Question: two CC BY 4.0 sources meet the size and language bounds; the rung is permissive either way. MInDS-14 (`PolyAI/minds14` at `40ce77cb32a384e4d50a568e1ec39ac804019d33`) carries 14 e-banking customer-service intents, spoken natively in FR and DE and transcribed by ASR, 539 to 611 rows per language, licence stated on the card only. MASSIVE 1.1 (`AmazonScience/massive` at `ff6bd8e4b27c3543e4f8fe2108f32bb95a6f8740`), the epic's named lead, carries 18 voice-assistant scenarios translated in parallel, 2,974 test rows per language, licence in a LICENSE file and the publisher's NOTICE, loaded from a tarball because its HF loader is a script `datasets` 4.x cannot run. Which one seeds the suite?
- Options: (a) MInDS-14, 300 items, 100 per language, stratified by intent; (b) MASSIVE 1.1, `test` partition, `scenario` label, 300 items, stable key `locale/id`; (c) both, as two publication suites, at the cost of a second published batch.
- Recommended default: (a). The story's outcome is to show whether a finding on the hand-written support-routing suite survives at a scale where a 10-point gap can be resolved; MInDS-14 is the only candidate whose labels are customer-service routing, while a MASSIVE score would measure a different task. Cost: its licence evidence is the card's identifier and a prose line, not a licence file (the loader records any licence file the source ships, and a different licence reopens the spike); ASR noise lowers the exact-match ceiling; the pool is small enough that a later redraw overlaps.
- Blocks: interval epic order 7, hence order 9 (`the-threshold-review-is-written-from-the-first-publication-run.md`) and the bundle epic's order 7 (`a-drawn-item-reaches-the-download-under-its-own-terms-or-as-a-visible-hole.md`).

### Q106. Is Google's Apache-2.0 label over WMT24 source text accepted for the translation publication suite?

- Artifact: the translation spike, `aidd_docs/backlog/stories/a-publication-level-translation-suite-stands-beside-the-hand-written-one.md` (interval epic order 8), and `LICENSE-DATA` section 3.
- Question: the only candidate that meets size and the three directions without share-alike or no-redistribution terms is WMT24++ (`google/wmt24pp` at `fd7405c06494bc66a57b25f55d217a72f96e60dc`, 998 aligned segments per pair, Apache-2.0 on the card, ungated). Its English sources are the WMT24 test set's, which WMT released as "freely used for research purposes"; Google's Apache-2.0 label covers text Google did not author. FLORES+ is CC-BY-SA 4.0 and its gate forbids re-hosting where crawlers reach it; the original WMT sets are research-only; NTREX-128 is CC-BY-SA 4.0. Is the Apache-2.0 declaration accepted for 300 items published in a public repository?
- Options: (a) accept it on the permissive rung: items ship with `licence` `Apache-2.0`, the Apache-2.0 text ships beside them, and `LICENSE-DATA` section 3 discloses the WMT24 research-use origin as a declaration, on the same footing as the two declarations already there; (b) keep WMT24++ but publish its items on the no-redistribution rung: `prompt` and `reference_output` redacted to the per-item content hash, with source, revision and `segment_id` per item and one fetch instruction per source (Q41 (a)); (c) take NTREX-128 on the share-alike rung instead, segregated under its own licence file.
- Recommended default: (a). The dataset's publisher licenses it Apache-2.0 at a pinned revision, the repository already ships declarations of exactly this kind, and the disclosure makes the reliance visible to a reviewer rather than hidden. Cost: the published items rest on Google's declaration; if it is ever withdrawn, the items move to (b), which the supersede-don't-backfill discipline allows. (b) is the zero-risk option and costs readers a fetch step per item.
- Blocks: interval epic order 8, hence order 9 and the bundle epic's order 7.

## Size-class candidates

Spike: `aidd_docs/backlog/spikes/which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them.md` (`blocked`). Every shortlisted family has a pinnable GGUF in each class, and every architecture is in b10537's source table; what remains is one live load per architecture.

### Q107. Which LFM2 models stand for the LFM2 line at ~0.5B and ~2B?

- Artifact: `aidd_docs/backlog/stories/the-half-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md` (order 5) and `aidd_docs/backlog/stories/the-two-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder.md` (order 6).
- Question: Q12 names "the smallest LFM2" at ~0.5B and "LFM2" at ~2B. The hub now holds two LFM2 generations; the literal smallest is `LFM2.5-230M`, released after the epic was written and described by its card as distilled from the 350M and "not recommended for reasoning-heavy workloads". Which models stand for the line?
- Options: (a) the current generation at the size nearest the class's Qwen entry: `LFM2.5-350M` at ~0.5B and `LFM2.5-1.2B-Instruct` at ~2B; (b) the literal smallest: `LFM2.5-230M` at ~0.5B and `LFM2.5-1.2B-Instruct` at ~2B; (c) the first generation: `LFM2-350M` and `LFM2-1.2B`.
- Recommended default: (a). It keeps the comparison about the family rather than a 0.23B model against Qwen3-0.6B, takes Liquid's current release, and both templates carry no thinking switch, so `none` is verifiable. Cost: about 133 MB more than (b), and in strict smallest-download order Granite 4.0 H 350M is tried first anyway. `LFM2.5-2.6B` stays out under every option because it always thinks.
- Blocks: the LFM2 gate run in orders 5 and 6; the Granite runs are unaffected.

### Q108. Are the spike's remaining live loads folded into the class stories' gate runs?

- Artifact: the spike, and orders 5 to 8 of `every-size-class-spans-two-families-or-says-it-does-not`.
- Question: what the spike still needs is one `llama-server` load under b10537 per architecture, plus the `/props` template. That load is exactly what `wave-local-ai-v2-candidate-gate` does as the first step of each class story, and each story already handles both outcomes: a pass enters the roster, a refusal or a deferred architecture is recorded under the epic's defer-by-default rule. As written, the stories wait on the spike and the spike waits on the stories' commands. Does the spike close on the stories' first gate runs, so that the class stories can be `ready`?
- Options: (a) yes: the spike's Follow-up becomes the stories' first gate run per architecture; the spike is resolved by the first pass or refusal per architecture, and the stories drop it from their `Blocked:` lines once the owner answers; (b) no: an operator runs the eight loads as a separate session first, the spike closes, then the stories become `ready`; (c) re-scope the spike to existence only and resolve it now, leaving loading to the stories.
- Recommended default: (a). The load result changes no story's acceptance, since a refusal is already a recorded outcome, so a separate session repeats work. Cost: a class story's first run can end in a recorded refusal rather than a roster entry, which the epic allows.
- Blocks: orders 7 and 8 entirely (no other blocker), and orders 5 and 6 together with Q107.

