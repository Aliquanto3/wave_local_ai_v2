# Committed results evidence

The reference bundle is five parts, handed to an auditor together: `runtime-reference.jsonl`,
`quality-reference.jsonl`, `fiches/` (the hardware/run fiches those rows cite by hash),
`aidd_docs/roster/models.json` (the models those rows cite by `roster_entry_id`), and
`suite-definitions/` (each suite's item set, cited by `suite_id`/`suite_version`
on every quality row -- `classification-support-routing.json` and, since 2026-09-06,
`translation-business-short-form.json`). No one file in this set is self-sufficient.

A row alone names its model, sampling, machine (by `fiche_hash`) and code `commit_sha` --
but resolving any of those to an actual artifact needs the rest of the bundle sitting
beside it: `fiche_hash` resolves only against `fiches/`, `roster_entry_id` only against
`aidd_docs/roster/models.json`, `suite_id`/`suite_version` (quality rows) only against
`suite-definitions/`. `tests/test_reference_bundle.py` asserts every pointer on every
row of the current-schema bundle resolves.

The two `*-reference.jsonl` files are curated snapshots: no CLI ever writes to them, and
nothing appends to them on a benchmark run. The two files the CLIs actually append to,
`runtime.jsonl` and `quality.jsonl`, are per-machine output and stay untracked
(`.gitignore`). Tracking them instead would dirty the working tree on every run and would
ship rows that do not belong to any acceptance criterion.

## The published bundle is one schema behind the code

The bundle's rows carry `schema_version` `"7"`; `row_contract.SCHEMA_VERSION` is `"8"`
(`retries` and `resumed` became required on quality rows). The bytes are **not**
back-filled to `"8"`: adding two fields to eighty rows produced on 2026-08-27 would make
them rows no harness ever wrote, which is the discipline this file states twice below and
which Story 19's acceptance requires. `tests/test_reference_bundle.py` therefore asserts
the bundle against its own `PUBLISHED_BUNDLE_SCHEMA_VERSION` rather than the live
constant, and separately that the published version is never *ahead* of the code.

A row of this bundle read beside a row a current CLI writes is short those two fields.
Regenerating it under `"8"` is a bench-time job on the Story 19 protocol (two runtime
runs in a quiet thermal window, two quality runs, the validator proof, this README's
tables rebuilt), filed in `aidd_docs/backlog/tech-debt.md`, not something a schema bump
does to the published bytes on its way past.

## This regeneration (Story 19 + Story 20, 2026-08-27)

Both files were regenerated from scratch under the current schema (`schema_version` `"7"`),
against the 20-item suite (`suite_version` `"2"`, `en`/`fr`/`de` all >=25% share) Story 20
added. Produced on 2026-08-27 by `uv run wave-local-ai-v2` and `uv run
wave-local-ai-v2-quality` against a local llama-server (build `b10537`,
`Qwen3.6-35B-A3B-UD-IQ4_XS`) and `mistral-small-2603`.

Read the code state from the rows, not from this paragraph: every one of the 82 rows
carries `commit_sha` `9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7` (the suite-snapshot
commit, branch `feat/trilingual-suite-and-reference-bundle`) with `tree_dirty: true` --
the runs were taken mid-branch, before the commit that added these files. The dirty
flag is on the rows and is not back-filled away: it says the `commit_sha` alone does not
pin the exact working tree that produced the numbers.

### `runtime-reference.jsonl`: two runs, second against the first

| Run | `run_id` | `gen_tok_per_s` (published) | `prompt_tok_per_s` (published) | `verdict` |
| --- | -------- | --------------------------- | ------------------------------ | --------- |
| 1 | `f5f78c79...` | 25.408 | 272.643 | `not_comparable` (no reference configured yet) |
| 2 | `f7faeef7...` | 24.802 | 273.302 | `reproduced` against run 1 |

The published `gen_tok_per_s` / `prompt_tok_per_s` are the medians over each run's five
counted repetitions, and they are what the tolerance is judged on: `verdict.py` compares
`RUNTIME_REPRODUCTION_TOLERANCE` (10%) against the `*_delta` fields run 2's own verdict
block carries. Observed on those rows: `gen_tok_per_s_delta` **2.39%**,
`prompt_tok_per_s_delta` **0.24%**, `ttft_ms_delta` **0.24%** -- all inside the 10%
tolerance, so no finding for the PRD on this axis. (The repetition *means* are 25.329 and
24.826, a 1.98% spread; they are not the figures the threshold judges and are given here
only so the two do not get confused.) Run 2's verdict carries `reference_run_id` naming
run 1's `run_id` and an empty `differing_fields`.

### `quality-reference.jsonl`: two runs, local + mistral each, second against the first

| Model | Provider | `run_id` | Accuracy | `verdict` |
| ----- | -------- | -------- | -------- | --------- |
| `Qwen3.6-35B-A3B` | local | `5e13166d...` | 0.80 | `not_comparable` (run 1) |
| `mistral-small-2603` | mistral | `5e13166d...` | 0.95 | `not_comparable` (run 1) |
| `Qwen3.6-35B-A3B` | local | `d20afbda...` | 0.80 | `reproduced` against run 1 |
| `mistral-small-2603` | mistral | `d20afbda...` | 0.90 | `not_reproduced` against run 1 |

The local model reproduced exactly (0.80 both runs). The Mistral cloud model did not:
0.95 -> 0.90 across two runs sent with the same pinned sampler (`temperature=0`,
`random_seed=20260821`) -- an observed cloud-side finding for the PRD (the provider does
not guarantee bit-identical output at temperature 0), not a defect in this harness's
verdict logic, which correctly flagged the divergence rather than silently reporting
`reproduced`.

The divergence is one item, and every German misroute in the bundle lands on the same
label, which is a second finding and about the suite rather than the provider:

| Item | Expected | `mistral-small-2603` predicted | Runs affected |
| ---- | -------- | ------------------------------- | -------------- |
| `account-de-01` ("Zwei-Faktor-Authentifizierung deaktivieren, finde aber die Option nicht") | `account` | `technical` | both |
| `other-de-01` ("Zeitplan für die nächste Feature-Ankündigung") | `other` | `technical` | run 2 only (`differing_fields: ["other-de-01"]`) |

`account-de-01` is the stable one: a two-factor setting is an `account` subject, but
"I cannot find the option" reads as a `technical` complaint, and the strongest model in
the roster picks `technical` deterministically both times. Story 20 requires the four
labels to stay semantically disjoint in each language; this item is recorded here as
evidence they are not yet, in German. The item text is **not** edited in place: editing
a prompt moves `PROMPT_SET_HASH`, which would invalidate every row in this bundle. The
revision belongs to the next regeneration and is filed as such.

The local model's four wrong answers per run are all `unparseable` completions on EN
items (`technical-01`, `technical-02`, `billing-03`, `technical-03`), identical across
both runs -- a generation-failure mode named by `failure_reason` on the row, not a
routing ambiguity.

Per-language breakdown (`language_breakdown`, both providers, both runs -- accuracy /
n / indicative):

| Language | n | local accuracy | mistral accuracy | indicative |
| -------- | - | --------------- | ------------------ | ---------- |
| `en` | 10 | 0.60 | 1.00 | **false** (n >= 10) |
| `fr` | 5 | 1.00 | 1.00 | **true** (n < 10) |
| `de` | 5 | 1.00 | 0.80 (run 1) / 0.60 (run 2) | **true** (n < 10) |

`fr` and `de` sit at n=5, below `MIN_PER_LANGUAGE_CELL_ITEMS` (10): an observed
consequence of the 25%-share split at 20 total items (plan.md's Decisions), not a defect.
The suite-level gate (`gate_suite`) is not indicative -- item count and every language's
25% share both pass -- but the per-language cells for `fr`/`de` are, and every row says so
via `language_breakdown[lang].indicative`.

## The translation suite's first live run (2026-09-06)

Not part of the committed bundle. These rows live in the untracked live store
(`aidd_docs/results/quality.jsonl`) at `schema_version` `"10"`; this section records
what the run produced so the numbers are citable and the absences are named. The
committed `quality-reference.jsonl` is still classification-only and is not touched --
regenerating the bundle is a separate, protocol-bound job (see the tech-debt entry the
schema note above refers to).

Suite: `translation-business-short-form`, `suite_version` `"1"`, `prompt_set_hash`
`16150e4406042a89...`, exported item-for-item to
`suite-definitions/translation-business-short-form@1.json`. 21 hand-written items in three
directions, seven each: `en->fr`, `fr->de`, `de->en`. Caps: 128 output tokens, no stop
sequence, 32768 context.

Metric: `chrf` version `"1"` (`chrf.py`), parameters as published on every row --
`char_order` 6, `beta` 2, `whitespace` false, `scale` `"0..1"`. Every row carries
`reference_output` beside `subject_output`, so any number below can be recomputed from
the row alone with `sacrebleu` (multiply by 100 to compare against its printout).

Two runs, the second scored against the first (run 1's rows copied to a scratch file and
handed to the second run as `QUALITY_REFERENCE_PATH`):

| Model | Provider | `run_id` | `suite_score` | `verdict` |
| ----- | -------- | -------- | ------------- | --------- |
| `Qwen3.6-35B-A3B` | local | `80803767...` | 0.7691 | `not_comparable` (run 1: no reference) |
| `gemini-3.5-flash-lite` | google | `80803767...` | 0.8400 | `not_comparable` (run 1: no reference) |
| `mistral-small-2603` | mistral | `80803767...` | — | absent, see below |
| `Qwen3.6-35B-A3B` | local | `696b5376...` | 0.7691 | `reproduced` against run 1, on `item_score` |
| `gemini-3.5-flash-lite` | google | `696b5376...` | 0.8400 | `reproduced` against run 1, on `item_score` |

Both reproduced item for item: `differing_fields` empty on both, and every verdict block
names `compared_field: "item_score"` -- the field the batch was actually decided on,
since a translation row carries no `predicted_label` for the old comparison to read.
Google honouring its seed here is worth recording beside the classification bundle's
opposite finding above, where `mistral-small-2603` moved 0.95 -> 0.90 across two runs at
`temperature=0`: cloud reproducibility is a per-provider observation, not a property of
the harness.

`wave-local-ai-v2-validate` exits `0` over the live store (306 rows at the time of
writing); every row's `fiche_hash` resolves against `fiches/`.

Full-run cost: the local batch produced 422 output tokens for €0.000272 (kWh-derived,
Scope 2); the google batch 714 in / 295 out for $0.000952 (list-price-derived, Scope 3).
The two are not directly comparable and every Scope-3 row says so in
`scope_comparability`. Wall clock: ~1 minute local, ~3 minutes google (21 items x two
paced calls at `GOOGLE_REQUEST_PACING_S` 4.1).

Per-language breakdown (`score_breakdown`, by **source** language -- score / n /
indicative):

| Source language | n | local | google | indicative |
| --------------- | - | ----- | ------ | ---------- |
| `en` (-> `fr`) | 7 | 0.7962 | 0.8671 | **true** (n < 10) |
| `fr` (-> `de`) | 7 | 0.6878 | 0.7700 | **true** (n < 10) |
| `de` (-> `en`) | 7 | 0.8233 | 0.8829 | **true** (n < 10) |

All three cells are marked indicative: seven items per direction against
`MIN_PER_LANGUAGE_CELL_ITEMS` (10). The suite-level gate is *not* indicative -- 21 items
and each source language at 33% both pass -- and the mark is on the cells, where it
belongs. Clearing it needs nine more hand-authored reference translations, including
German ones nobody in-project can natively verify; the mark is the honest report of that
limitation rather than a set inflated to hide it.

No item failed on either provider: `failure_counts` is all-zero on every row.
`unparseable` is structurally unreachable on this suite (no closed set to parse into, and
nothing is extracted from a completion before scoring), which is stated on
`translation_suite.py` rather than left to look like a suite that never fails to parse.

### What was absent, and why

`mistral-small-2603` produced no rows in either run. The batch was attempted three times
under run 1 -- once in the first invocation, twice more under `--resume 80803767...` so
the batches already on disk were never re-paid for -- and each ended with `mistral
skipped: retry budget exhausted after 4 retries`. A single hand-issued request confirms
the cause is not a burst:

```
Mistral request failed with status 429: {"object":"error","message":"Rate limit
exceeded","type":"rate_limited","param":null,"code":"1300","raw_status_code":429}
```

The model catalog answered `200` on the same key at the same moment, so this is the
workspace's Free-tier rate floor rather than a credential, a DNS or a retired-model
problem. A documented absence, not a blocked run: the local and google batches persisted
and the CLI exited `0`, which is the skip-not-abort contract behaving as designed.

### The `<think>` block, a finding rather than a fix

Every local completion opens with an empty `<think>\n\n</think>` envelope (the server runs
with `--jinja` and this roster entry emits reasoning tags). Exact-match scoring never saw
it -- `normalize_label` finds the first label token past it -- but chrF scores the raw
completion, so the envelope adds ~15 characters of non-reference n-grams to every local
hypothesis and costs the local subject precision that google does not pay. The
local-vs-google gap above is therefore an upper bound on the real one. This is filed in
`aidd_docs/backlog/tech-debt.md` rather than patched here: stripping it would need either
a "remove a provider's reasoning envelope" scoring rule (a choice sacreBLEU would not
reproduce, which the plan rejected on purpose) or a server/roster flag change. Either is
a decision, not a patch, and inventing one mid-run would have made these numbers
unreproducible from the code that wrote them.

### Reading these scores

chrF here is measured against **one** reference translation, so it penalises a valid
alternative wording. The lowest local scores are exactly that case rather than errors.
The completion column below is the row's `subject_output` **with the `<think>\n\n</think>`
envelope trimmed for reading**, so the two score columns are both given: `item_score` is
the number actually published on the row (scored on the full `subject_output`, envelope
included), and the last column is what the trimmed text alone scores. The gap between
them is the envelope's cost on that item, and it is why recomputing from the text printed
here does not land on the published number.

| Item | Reference | `Qwen3.6-35B-A3B` (envelope trimmed) | `item_score` (as published) | trimmed text alone |
| ---- | --------- | ------------------------------------ | --------------------------- | ------------------ |
| `fr-de-03` | "Der Kostenvoranschlag, den Sie uns übermittelt haben, übersteigt unser Jahresbudget." | "Das von Ihnen übermittelte Angebot übersteigt unser jährliches Budget." | 0.4078 | 0.4205 |
| `fr-de-05` | "Das Auftaktgespräch findet um zehn Uhr in unseren Räumen statt." | "Der Kick-off-Meeting findet um 10 Uhr in unseren Räumlichkeiten statt." | 0.4759 | 0.4997 |
| `en-fr-05` | "Nos bureaux seront fermés lundi prochain en raison d'un jour férié." | "Notre bureau sera fermé lundi prochain pour un jour férié." | 0.5135 | 0.5333 |

All three are defensible translations scored down for choosing different words than the
reference on file. A published `suite_score` is defensible as a **comparison between
models measured against identical references**. It is not an absolute measure of
translation quality, and no claim of that kind should be built on it.

### Superseded files: kept, not deleted

`runtime-reference.schema-1.jsonl` and `quality-reference.schema-1.jsonl` are this
regeneration's predecessors, `git mv`-renamed rather than overwritten. The `.schema-<N>`
suffix counts superseded bundle generations -- this is generation 1, the first bundle
this repo published -- and is deliberately **not** a `schema_version` value: no row in
either file carries `schema_version` `"1"`. What they actually carry is
`schema_version` `"2"` on one row of `runtime-reference.schema-1.jsonl` and no
`schema_version` key at all on its other two rows and on all 40 rows of
`quality-reference.schema-1.jsonl`, because the key postdates them. They were produced
against the 10-item, EN-only suite. They
are kept for published-evidence continuity across the epic's duration (`every-published-
row-explains-and-reproduces-itself`'s Boundaries) -- a reader following an old citation
still finds the row it pointed at. `tests/test_reference_bundle.py` names them explicitly
as the superseded set and never folds them into the current-schema bundle checks.

### Validator proof (this regeneration)

`uv run wave-local-ai-v2-validate aidd_docs/results/runtime-reference.jsonl
aidd_docs/results/quality-reference.jsonl`:

| Run | Result |
| --- | ------ |
| Clean pass over the assembled bundle | `checked 82 row(s)`, exit **0** |
| One fiche field hand-edited (`gpu_name`) | exit **1**, `edited (82)` naming every row citing that fiche and `changed_fields: ['gpu_name']` -- all 82 rows share one fiche (same machine/flag configuration across all four runs) |
| Edit reverted (`git checkout --`) | `checked 82 row(s)`, exit **0** again |

## Dense versus MoE, side by side (2026-09-06)

> **Superseded, and kept.** Every local number in this section was produced by
> posting the item text raw to `/completion`, so a chat-tuned model was asked to
> continue it rather than answer it. These are real measurements of the wrong
> thing, and the subsection below, "What the dense rows are actually measuring",
> is where that was first written down. They are **not edited**: the rows exist
> on disk and still say what they said. Read them beside "The same eight
> batches, chat-templated" further down, which re-runs all four models under
> bumped suite versions. The defect is
> `aidd_docs/backlog/defects/local-subject-prompts-are-never-chat-templated.md`.

The three dense models' rows were produced today and are not part of the committed
bundle: they live in the untracked live stores (`aidd_docs/results/runtime.jsonl`,
`aidd_docs/results/quality.jsonl`) at `schema_version` `"10"`. This section records what
they produced so the numbers are citable. The committed reference bundle is frozen one
schema behind for the reason its own section above gives, and is **not** touched. What
*is* committed is the three fiches the dense rows cite -- `f804bee0...` (0.6B),
`067530ef...` (1.7B), `dfd5a5ea...` (4B) -- so every dense number below resolves to a
stored hardware-and-flags record and a roster entry.

The comparator rows in the tables below are older and are cited, not re-run, so they do
not all share that provenance. Where each one lives:

| Cited row | `run_id` | Where it lives | `schema_version` |
| --------- | -------- | -------------- | ---------------- |
| `Qwen3.6-35B-A3B` runtime | `f7faeef7...` | committed `runtime-reference.jsonl` (also in the live store) | `"7"` |
| `Qwen3.6-35B-A3B` + `gemini-3.5-flash-lite` classification | `1f3c94b9...` | untracked `quality.jsonl` only | `"8"` |
| `Qwen3.6-35B-A3B` + `gemini-3.5-flash-lite` translation | `80803767...` | untracked `quality.jsonl` only | `"10"` |

All four cite fiche `b9d1af56...`, which is committed, so those numbers resolve too.

The model set is `roster_version` 2: the MoE flagship plus a dense Qwen3 size ladder. The
dense/MoE distinction is what the section is for, so it is in the table rather than in a
footnote:

| Model | Entry id | Arch | Quant | `-ngl` | `--n-cpu-moe` | `--load-mode` |
| ----- | -------- | ---- | ----- | ------ | ------------- | ------------- |
| `Qwen3.6-35B-A3B` | `qwen3.6-35b-a3b-ud-iq4xs` | MoE, 40 experts, 3.1B active | `UD-IQ4_XS` | 99 | **37** | `none` |
| `Qwen3-4B` | `qwen3-4b-q4km` | dense, 4.0B | `Q4_K_M` | 99 | *absent* | `auto` |
| `Qwen3-1.7B` | `qwen3-1.7b-q8` | dense, 1.7B | `Q8_0` | 99 | *absent* | `auto` |
| `Qwen3-0.6B` | `qwen3-0.6b-q8` | dense, 0.6B | `Q8_0` | 99 | *absent* | `auto` |

All three dense entries held every layer on the GPU at 32768 context on a 6144 MiB
RTX 3060 Laptop. The plan expected the 4B to need a step-down and it did not, with under
200 MiB to spare -- a probe result, not an estimate.

### Classification

Suite `classification-support-routing`, `suite_version` `"2"`, 20 items, 32-token cap.
The `gemini-3.5-flash-lite` row is cited from the run that already paid for it rather
than re-run: same suite, same version, same items, already on disk.

| Model | Provider | `run_id` | Accuracy | `empty` | `unparseable` | `truncated_max_tokens` | `en` (n=10) | `fr` (n=5) | `de` (n=5) |
| ----- | -------- | -------- | -------- | ------- | ------------- | ---------------------- | ----------- | ---------- | ---------- |
| `gemini-3.5-flash-lite` | google | `1f3c94b9...` | **1.00** | 0 | 0 | 0 | 1.00 | 1.00 * | 1.00 * |
| `Qwen3.6-35B-A3B` | local | `1f3c94b9...` | **0.80** | 0 | 4 | 0 | 0.60 | 1.00 * | 1.00 * |
| `Qwen3-4B` | local | `d7f08b1a...` | **0.45** | 0 | 9 | 0 | 0.50 | 0.40 * | 0.40 * |
| `Qwen3-0.6B` | local | `c836bacc...` | **0.45** | 0 | 6 | 0 | 0.50 | 0.40 * | 0.40 * |
| `Qwen3-1.7B` | local | `9dd45420...` | **0.25** | 0 | 14 | 0 | 0.30 | 0.20 * | 0.20 * |

`*` = `indicative`: the cell holds 5 items against `MIN_PER_LANGUAGE_CELL_ITEMS` (10).
The suite-level number is not indicative on any row.

The ladder does not rank by size. The 1.7B is the worst of the four and the 4B ties the
0.6B. Every dense row's `tokens_out_total` is 640 -- 20 items x the full 32-token cap --
so all three ran the cap dry on every single item, while the MoE flagship spent 240 and
`gemini-3.5-flash-lite` spent 20. That is the whole story of this table, and the next
section is what it actually means.

### Translation

Suite `translation-business-short-form`, `suite_version` `"1"`, 21 items in three
directions, 128-token cap, chrF against **one** reference on the `0..1` scale.

| Model | Provider | `run_id` | `suite_score` | `en`->`fr` (n=7) | `fr`->`de` (n=7) | `de`->`en` (n=7) |
| ----- | -------- | -------- | ------------- | ---------------- | ---------------- | ---------------- |
| `gemini-3.5-flash-lite` | google | `80803767...` | **0.8400** | 0.8671 * | 0.7700 * | 0.8829 * |
| `Qwen3.6-35B-A3B` | local | `808037675130` | **0.7691** | 0.7962 * | 0.6878 * | 0.8233 * |
| `Qwen3-4B` | local | `350cac2f...` | **0.2005** | 0.2128 * | 0.1990 * | 0.1896 * |
| `Qwen3-0.6B` | local | `c370c862...` | **0.1867** | 0.2096 * | 0.1909 * | 0.1595 * |
| `Qwen3-1.7B` | local | `80eec0cd...` | **0.1742** | 0.1774 * | 0.2124 * | 0.1328 * |

`*` = `indicative` on every cell: seven items per direction against the 10-item floor.
`failure_counts` is all-zero on every translation row, on every model -- `unparseable` is
structurally unreachable on this suite.

The single-reference caveat applies here exactly as it does above: chrF against one
reference compares models on identical references and is not an absolute measure of
translation quality.

### What the dense rows are actually measuring

A ~0.19 chrF reads like "these models cannot translate". Read one completion and that is
not what happened. `Qwen3-4B`, item `fr-de-03`, `item_score` 0.2157, the row's
`subject_output` in full -- it ran the 128-token cap dry, so it ends mid-sentence where
the row itself ends:

```
 Nous ne pouvons donc pas vous aider à réaliser ce projet. Nous vous remercions de
votre compréhension.
Answer:

Der von Ihnen übermittelte Angebot überschreitet unseren jährlichen Budget. Daher
können wir Ihnen nicht helfen, dieses Projekt umzusetzen. Vielen Dank für Ihr
Verständnis.  
**Note:** The translation provided is accurate and maintains the formal tone of the
original French text. The key terms like "dévis" (offer), "budget annuel" (annual
budget), and "projet" (project) are correctly translated. The sentence structure is
adapted
```

The German in the middle is a good translation of the reference sentence. The model
reached it only after first **continuing the French source text**, and then spent the
rest of its cap reviewing its own work in English. chrF scores the full raw completion,
so the continuation and the `**Note:` commentary together drown the answer.

The classification rows fail the same way. `Qwen3-0.6B`, item `billing-02`, expected
`billing`, running the 32-token cap dry:

```
 

The message is about the currency of the invoice. The message is about the amount owed.
The message is about the payment method. The message is about the
```

That completion is **not** quoted from a row: a classification row carries
`predicted_label` and `failure_reason`, never the raw text (`subject_output` is `null` on
every classification row this project has written, these three included). It comes from
the direct `/completion` probe against `qwen3-0.6b-q8` described in the truncation-
reporting section below, replaying the same item at the same cap. What the rows
themselves carry for this batch is `failure_reason: "unparseable"` on 6 of 20 items and
`tokens_out_total` 640 -- 20 × the full cap -- which is the evidence for the paragraph
that follows; the text above only shows what running the cap dry looks like.

The local quality path posts a **raw prompt to `/completion`**, with no chat template
applied. These Qwen3 releases treat that as text to continue rather than as an
instruction to follow. The MoE flagship, on the same endpoint with the same `--jinja`,
opens with a `<think>` envelope and then obeys -- it costs that model ~15 characters of
chrF precision (the finding recorded in the translation section above) and costs these
three models the entire answer.

So the honest reading of both tables is: they measure **instruction-following on a raw
completion endpoint**, and on that axis the dense Qwen3 ladder loses badly to the MoE
flagship and to the cloud comparator. They do not establish that a 4B dense model cannot
classify or translate. Separating the two needs a chat-templated local path, which is a
suite-level decision and is filed as tech debt, not patched between two measured runs.

The plan's stated risk was the opposite failure -- that a thinking-by-default model would
spend its cap on a reasoning block and land as `truncated_max_tokens`. It did not: no
dense row reasons first. See the truncation-reporting defect below for why that field
reads `0` regardless.

### Runtime

One `wave-local-ai-v2` invocation per entry at default protocol: 1 warm-up, 5 counted
repetitions, 10 s cooldown, pinned seed, `cache_prompt: false`, 128-token cap.

| Model | Quant | `-ngl` | `--n-cpu-moe` | `run_id` | `gen_tok_per_s` | `prompt_tok_per_s` | `ttft_ms` | gen / ttft / prompt spread | `unreliable` | RSS | VRAM | Energy (kWh) | Cost (EUR) | `verdict` |
| ----- | ----- | ------ | ------------- | -------- | --------------- | ------------------ | --------- | -------------------------- | ------------ | --- | ---- | ------------ | ---------- | --------- |
| `Qwen3-0.6B` | `Q8_0` | 99 | *absent* | `68a5e1df...` | **207.8** | **4117.8** | **360.6** | 0.005 / 0.078 / 0.093 | false | 1078 MB | 4527 MiB | 0.00078 | 0.000151 | `not_comparable` |
| `Qwen3-1.7B` | `Q8_0` | 99 | *absent* | `e5714fcb...` | 116.0 | 3091.9 | 480.3 | 0.002 / 0.083 / 0.100 | false | 2277 MB | 5689 MiB | 0.00090 | 0.000174 | `not_comparable` |
| `Qwen3-4B` | `Q4_K_M` | 99 | *absent* | `f8678fe0...` | 33.6 | 275.2 | 5396.4 | 0.001 / 0.003 / 0.003 | false | 4275 MB | **6115 MiB** | 0.00214 | 0.000414 | `not_comparable` |
| `Qwen3.6-35B-A3B` | `UD-IQ4_XS` | 99 | **37** | `f7faeef7...` | 24.8 | 273.3 | 5451.9 | 0.005 / 0.004 / 0.004 | false | 15226 MB | 4549 MiB | 0.00264 | 0.000513 | `reproduced` |

The two memory columns are not in the same unit, because the two fields are not: `RSS` is
`process_rss_bytes` in decimal MB (10^6 B, the unit this project's earlier records use for
that field), `VRAM` is `vram_used_mib` in MiB (2^20 B, the unit NVML reports). Both are
peaks over the counted repetitions, not point samples.

Every dense `verdict` is `not_comparable`, and that is the honest first-run state rather
than a gap: the verdict blocks on `llama_cpp_build` / `quant` / `gpu_name` / `flags`, and
no reference row shares a new quant and a flag set with no `--n-cpu-moe` in it. The
flagship's `reproduced` is its own earlier pair, unaffected by this increment.

Two things in that table are worth naming:

- **The 4B's prompt throughput collapses to the flagship's.** 275 vs 3092 tok/s for the
  1.7B, an 11x drop for a 2.4x model, and its TTFT (5396 ms) lands within about 1% of
  the flagship's (5452 ms) despite the flagship offloading 37 expert layers to CPU. Its
  `vram_used_mib` is 6115 of 6144 -- 99.5% of the card. Fitting at `-ngl 99` and running
  well at `-ngl 99` are not the same thing, and this row is what the difference looks
  like.
- **The dense ladder's cost advantage is real and large.** The 0.6B does the same 640
  output tokens for €0.000151 against the flagship's €0.000513, at 8.4x the generation
  rate and 1/14th the host RAM.

`machine_state`: no repetition on any of the three reported `sw_thermal_slowdown`. GPU
temperatures stayed at 60-65 °C on the two small models and 71-75 °C on the 4B, and the
throttle reason on all three counted sets is `sw_power_cap`, which is this laptop GPU's
ordinary behaviour under load, not a thermal event. No run was repeated to improve a
number.

### The truncation-reporting defect, filed rather than fixed

`failure_counts.truncated_max_tokens` reads `0` on every row in both tables above,
including the rows whose `tokens_out_total` proves every item ran the cap dry. The rows
are wrong, and the cause is not the models.

On llama.cpp `b10537` the `/completion` response carries **no `stopped_limit` key**. It
reports `stop_type: "limit"` instead. `quality_cli._run_local_suite` reads
`response_json.get("stopped_limit", False)`, so a cap-exhausted completion is published
as not-truncated and its failure is attributed to `unparseable`. Probed directly on this
build against `Qwen3-0.6B` item `billing-02`: `tokens_predicted: 32` (the cap),
`stop_type: "limit"`, and `stopped_limit` absent from the response entirely.

Every local row this project has ever published is affected, the flagship's included.
**The scores are not**: a truncated completion and an unparseable one both score the same,
so accuracy, `suite_score` and every per-language cell stand exactly as published. Only
the failure label moves. Filed in `aidd_docs/backlog/tech-debt.md`; not patched here,
because changing the harness between the pilot and the matrix would have made these rows
unreproducible from the code that wrote them.

### The two caveats this comparison genuinely carries

- **The architecture comparison spans a model generation.** The dense ladder is Qwen3
  (May 2025); the flagship is Qwen3.6 (2026). Size is controlled *within* the ladder, so
  the 0.6B/1.7B/4B rows compare cleanly against each other. Dense-vs-MoE across the two
  is confounded by ~18 months of post-training, and the raw-completion behaviour above is
  most likely a generation difference rather than an architecture one.
- **The quants are not uniform.** `Q8_0` at 0.6B and 1.7B, `Q4_K_M` at 4B,
  `UD-IQ4_XS` on the flagship. That is what each vendor repo publishes -- the 0.6B and
  1.7B GGUF repos contain exactly one quant each -- and forcing uniformity would have
  meant leaving the vendor's own artifact for a repackager.

### Cost of reproducing this

The whole live session -- pilot, three runtime runs, six quality batches -- ran
12:04:13 to 12:13:07 UTC on 2026-09-06, **under 9 minutes of wall clock**, on one machine,
with no cloud quota spent (the `google` comparator rows were cited, not re-run). The
downloads are 4.63 GiB total. `wave-local-ai-v2-validate` exits `0` over both live stores,
`checked 432 row(s)`, every `fiche_hash` resolving.

## The same eight batches, chat-templated (2026-09-06, later the same day)

The four models above, re-run on both suites after the local subject path moved
to llama-server's `/v1/chat/completions`. Same machine, same four committed
fiches, same items, same caps, same pinned sampler. What changed is what the
model was sent: each item is now rendered through the loaded model's own chat
template and answered on the chat endpoint, under a suite-declared
`thinking_policy` of `disabled`.

These rows live in the untracked live store at `schema_version` `"11"`, under
`suite_version` `"3"` (classification) and `"2"` (translation). Their
predecessors above are `"2"` and `"1"`, and `verdict.select_quality_references`
keys on `suite_version`, so every new batch reports `not_comparable` against
them by construction. Nothing was edited to achieve that. Both suites'
`prompt_set_hash` is **unchanged** -- no item text moved -- and each version's
definition is committed beside its predecessor at
`suite-definitions/<suite_id>@<suite_version>.json`.

### Classification

Suite `classification-support-routing`, `suite_version` `"3"`, 20 items,
32-token cap, `thinking_policy: disabled`.

| Model | `run_id` | Accuracy | was | `tokens_out_total` | was | failures | `en` (n=10) | `fr` (n=5) | `de` (n=5) |
| ----- | -------- | -------- | --- | ------------------ | --- | -------- | ----------- | ---------- | ---------- |
| `gemini-3.5-flash-lite` | `1f3c94b9...` | **1.00** | 1.00 | 20 | 20 | 0 | 1.00 | 1.00 * | 1.00 * |
| `Qwen3.6-35B-A3B` | `d4d2e0d5...` | **1.00** | 0.80 | 40 | 240 | 0 | 1.00 | 1.00 * | 1.00 * |
| `Qwen3-4B` | `ebce4da6...` | **0.70** | 0.45 | 40 | 640 | 0 | 0.80 | 0.60 * | 0.60 * |
| `Qwen3-1.7B` | `91ee67b1...` | **0.60** | 0.25 | 40 | 640 | 0 | 0.70 | 0.40 * | 0.60 * |
| `Qwen3-0.6B` | `e716ce86...` | **0.45** | 0.45 | 40 | 640 | 0 | 0.50 | 0.40 * | 0.40 * |

`*` = `indicative`: the cell holds 5 items against `MIN_PER_LANGUAGE_CELL_ITEMS`
(10). The suite-level number is not indicative on any row. The `gemini` row is
the same cited row as above, restated for comparison; see the version caveat
below.

### Translation

Suite `translation-business-short-form`, `suite_version` `"2"`, 21 items,
128-token cap, chrF against **one** reference on the `0..1` scale,
`thinking_policy: disabled`.

| Model | `run_id` | `suite_score` | was | `en`->`fr` (n=7) | `fr`->`de` (n=7) | `de`->`en` (n=7) |
| ----- | -------- | ------------- | --- | ---------------- | ---------------- | ---------------- |
| `gemini-3.5-flash-lite` | `80803767...` | **0.8400** | 0.8400 | 0.8671 * | 0.7700 * | 0.8829 * |
| `Qwen3.6-35B-A3B` | `79e95271...` | **0.8002** | 0.7691 | 0.8226 * | 0.7004 * | 0.8775 * |
| `Qwen3-4B` | `42bd9d8b...` | **0.7252** | 0.2005 | 0.7169 * | 0.6184 * | 0.8405 * |
| `Qwen3-1.7B` | `41ac932a...` | **0.7107** | 0.1742 | 0.6409 * | 0.6399 * | 0.8513 * |
| `Qwen3-0.6B` | `108fc07e...` | **0.5121** | 0.1867 | 0.4846 * | 0.3852 * | 0.6664 * |

`*` = `indicative` on every cell: seven items per direction against the 10-item
floor. `failure_counts` is all-zero on every row of both tables.

### What moved, and what did not

**The ladder ranks by size now, on both suites.** 0.45 < 0.60 < 0.70 < 1.00 on
classification and 0.5121 < 0.7107 < 0.7252 < 0.8002 on translation, monotonic
in parameter count. The untemplated tables rank it differently and
inconsistently -- the 1.7B was the worst of the four on classification and the
4B only tied the 0.6B -- which is the clearest single sign that those numbers
were not measuring model capability.

**The models stop on their own.** Every dense classification batch above spent
`tokens_out_total` 640, twenty items times the full 32-token cap, never
finishing an answer. All three now spend **40**: two tokens per item, the label
and its stop. The flagship went 240 -> 40. `failure_counts` is all-zero
everywhere, and the six `unparseable` items the 0.6B published and the fourteen
the 1.7B published are gone, because there is now an answer to parse.

**The 0.6B did not improve on classification.** 0.45 before and 0.45 after. It
is the one number in these tables that did not move, and it deserves saying
plainly: this model answers the routing task cleanly and gets it wrong, 15 of
its 20 answers being `technical`. That is a capability result, and it is exactly
what the untemplated run could not have told anyone. Its translation score moved
0.1867 -> 0.5121 in the same session, so the flat classification figure is about
this model on this task, not about this model.

**The flagship reaches the cloud comparator on classification.** 0.80 -> 1.00,
level with `gemini-3.5-flash-lite` on all twenty items. On translation it closes
roughly a third of the gap (0.7691 -> 0.8002 against 0.8400) and does not close
it.

**The `<think>` envelope left the completions.** No `subject_output` in any of
the 84 new translation rows contains `<think>`: with thinking disabled the
template prefills an empty block into the *prompt*, where it costs no score. The
earlier finding said the local-versus-google gap was "an upper bound on the real
one" because the envelope added ~15 characters of non-reference n-grams to every
local hypothesis. That is now measured rather than argued. The flagship's
`fr-de-03` translation is **byte-identical** across the two runs -- "Das von Ihnen
übermittelte Angebot übersteigt unser jährliches Budget." -- and the envelope is
the whole difference between the two stored completions: the superseded row's
`subject_output` carries `\n\n<think>\n\n</think>\n\n` in front of that sentence
and the new one does not. It scores 0.4078 on the old row and **0.4205** here.
0.4205 is exactly the "trimmed text alone" figure the "Reading these scores"
table above predicted for that item, so the prediction and the measurement
agree. The tech-debt row that recorded the envelope stays open for the raw
`/completion` path, which still emits it into the completion.

### The three caveats these numbers carry

- **The cloud comparator sits at the previous suite versions.** The
  `gemini-3.5-flash-lite` rows are cited, not re-run: classification at
  `suite_version` `"2"` and translation at `"1"`, against the new local rows'
  `"3"` and `"2"`. The items, the caps and both `prompt_set_hash` values are
  identical across the bump -- nothing about what the cloud model was asked
  changed -- so the scores stay comparable, and a side-by-side table will
  nevertheless show two different version numbers in one column. Re-running
  Google would pay cloud quota to regenerate identical answers to identical
  prompts. Stated here rather than left for a reader to discover.
- **`thinking_policy: disabled` measures a narrower model than the vendor
  ships.** These are Qwen3 models with reasoning switched off at the request
  level, which is what makes a 32-token label task and a 128-token sentence task
  answerable at all: probed on this build, every one of these models with
  thinking allowed spends its entire cap in `reasoning_content` and returns an
  empty string. A thinking-allowed run with caps sized for deliberation is a
  different measurement, and this project has not made it. Read a routing score
  as a routing score, never as the model's ceiling. Publishing both policies
  side by side is recorded on the defect as deferred on run cost.
- **Everything the untemplated tables say about the comparison's shape still
  holds.** The dense ladder is Qwen3 (May 2025) and the flagship is Qwen3.6
  (2026), so dense-versus-MoE across the two stays confounded by a model
  generation; the quants are still not uniform; and chrF against one reference
  still compares models on identical references rather than measuring
  translation quality absolutely.

### Cost of reproducing this

Eight local batches, one `wave-local-ai-v2-quality` invocation per (model,
suite) at `QUALITY_PROVIDERS=local`, on 2026-09-06. No cloud quota spent. Every
row cites one of the four fiches already committed for the untemplated runs
(`f804bee0...`, `067530ef...`, `dfd5a5ea...`, `b9d1af56...`): same machine, same
flags, so no new hardware record was created and every number here resolves
against the bundle as it already stands. `uv run wave-local-ai-v2-validate` over
both live stores exits `0`, `checked 596 row(s)`.

## Earlier increments' evidence (predates this regeneration)

The sections below describe rows this regeneration **replaced**. They are kept as a
record of what earlier increments validated at the time; the bytes they describe now
live only in the `*.schema-1.jsonl` files above, not in the live `*-reference.jsonl`
files this README's own head section describes.

### `runtime-reference.jsonl` (schema-1, superseded)

Three rows. Rows 1 and 2 are the throughput evidence, copied from lines 4 and
5 of this machine's `runtime.jsonl`. Row 3 is field-shape evidence for the
machine-state/TTFT-provenance increment and is **not** a throughput claim —
see its own block below.

| Claim rows 1-2 support | Value |
| ---------------------- | ----- |
| Generation throughput | `gen_tok_per_s` 26.046 and 25.484 |
| Prompt throughput | `prompt_tok_per_s` 255.93 and 259.25 |

Produced on 2026-08-21 (file written 18:14 local time), on branch
`feat/runtime-measurement-harness` at tip `597596f`, by
`uv run wave-local-ai-v2` against a local llama-server (build `b10537`,
`Qwen3.6-35B-A3B-UD-IQ4_XS`). Every row carries its own hardware fiche and flag
list, so the numbers are falsifiable against the machine that produced them.

**Deliberately excluded**: rows 6 to 9 of the live store. They come from the
reverted streaming experiment, and their `gen_tok_per_s` of 17-18 was measured
while this machine's GPU was in `sw_thermal_slowdown`. Keeping them next to the
acceptance rows with nothing to distinguish them would misrepresent the spread.
Rows 1 to 3 predate the fixed prompt's final length and are excluded for the
same reason: their `prompt_tok_per_s` (76 to 233) was measured at a different
prompt length and is not comparable.

**Row 3 of this file** (added by the machine-state/TTFT-provenance
increment): one full row from `uv run wave-local-ai-v2` at default settings
(`RUNTIME_REPETITIONS=5`, `RUNTIME_COOLDOWN_S=10.0`,
`RUNTIME_SPREAD_THRESHOLD=0.10`), produced on 2026-08-22 (`captured_at`
21:21:58 UTC) on branch `feat/machine-state-and-ttft-provenance` at tip
`ab9280d` (`tree_dirty: true` -- the branch's own uncommitted work). Carries
every field this increment added: per-repetition `machine_state`, the three
`*_spread` fields, `unreliable`, `thermal_posture`, `ttft_source`.

Its `gen_tok_per_s` is **15.256**, far below rows 1-2 (26.0 / 25.5), and it is
kept here as field-shape evidence only. Every one of its repetitions reports
`sw_thermal_slowdown` and `sw_power_cap` in `gpu_throttle_reasons`: this row
was measured on a thermally suppressed GPU, the same condition that excludes
the streaming rows above. Unlike those rows, it says so on its own face --
which is the point of the fields this increment adds -- so it is kept and
labelled rather than dropped. Read the throughput claim from rows 1-2.

| Field | Observed value |
| ----- | --------------- |
| `gen_tok_per_s` | 15.256 -- thermally suppressed, not a throughput claim |
| `gen_tok_per_s_spread` | 0.0518 (5.2%), against the 0.10 threshold -- did not flag |
| `ttft_ms_spread` | 0.0125 |
| `prompt_tok_per_s_spread` | 0.0127 |
| `unreliable` | `false` |
| `thermal_posture` | `"fixed_cooldown"` |
| `ttft_source` | `"server_reported"` |
| `gpu_temp_c` (repetition range) | 66.0-68.0 |
| `gpu_throttle_reasons` (union across repetitions) | `sw_power_cap`, `sw_thermal_slowdown` -- this machine's GPU was throttling during the run; the spread stayed under threshold anyway |
| `cpu_temp_c` / `cpu_temp_source` | `null` / `"unavailable"` -- confirms phase 1's spike conclusion on this Windows build |

### `quality-reference.jsonl` (schema-1, superseded)

All 40 rows of this machine's `quality.jsonl`: two consecutive runs per model,
ten classification items each.

| Model | Provider | Accuracy, run 1 | Accuracy, run 2 |
| ----- | -------- | --------------- | --------------- |
| `Qwen3.6-35B-A3B` | local | 0.60 | 0.60 |
| `mistral-small-2603` | mistral | 1.00 | 1.00 |

Produced on 2026-08-21 (file written 21:56 local time), on branch
`feat/runtime-measurement-harness` at tip `77a1c2e`, by
`uv run wave-local-ai-v2-quality`.

These rows support the reproducibility claim, not an accuracy claim: across the
two runs, every item's `predicted_label` is identical for both models, which is
what a pinned sampler (temperature 0, fixed seed) is there to guarantee. The
local model's four wrong answers per run are wrong in the same way both times.

### What was deliberately absent from the schema-1 rows

Both files predate the `run_id` / `captured_at` provenance keys added by a later
increment. They were **not** back-filled. A hand-edited row is no longer the row
the harness wrote; the absence of those keys is the honest signal that these rows
were produced before the change.

The same applies to the four local-model rows in the schema-1 `quality-reference`
file that carry `"predicted_label": null, "correct": false` with no reason —
`technical-01`, `technical-02`, `billing-03` and `technical-03`, plus their
run-2 duplicates (8 rows total). The harness as it stands today always writes a
`failure_reason` naming why a generation failed (`empty`, `unparseable`,
`truncated_max_tokens` or `truncated_context`); a row with a bare null and no
reason could not be produced by this code path. These rows are **not
back-filled** either: same discipline as above, a hand-edited row is no longer
the row the harness wrote, so the honest signal is left in place rather than
reconstructed.

The only edit ever applied to copied bytes is the line terminator: the live stores
are written in Windows text mode and use CRLF, and these snapshots use LF like
the rest of the repository. Every JSON payload is verbatim, byte for byte.

### Fiche hash, invalidation validator, and reproduction verdict (superseded rows)

Both schema-1 files predate `fiche_hash` and `verdict` entirely -- neither key exists
on any row in either file. `row_contract.FICHE_HASH_SCHEMA_VERSION` ("3") is the
version that introduced them; every row in both files carries a `schema_version` below
it (or none at all), so `wave-local-ai-v2-validate` reports all of them under
its non-fatal `legacy` class rather than `missing`.
