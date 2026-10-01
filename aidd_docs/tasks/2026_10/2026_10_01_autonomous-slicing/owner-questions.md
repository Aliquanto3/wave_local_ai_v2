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
