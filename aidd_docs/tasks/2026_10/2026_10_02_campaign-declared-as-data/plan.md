---
objective: "A campaign is a tracked declaration loaded against the caps and every registry, a run under it is checked before any server starts and stamps its id on every row, and a completeness command fails naming each declared cell nobody ran."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A campaign is declared as data, and an empty cell fails it

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `campaigns.py`: the declaration loader (caps of 2 engines and 4 variants, every id resolved against its registry, one machine with its mode, refused or dropped cells with their reason), the pre-launch run check behind `CAMPAIGN_ID`, and the completeness command `wave-local-ai-v2-campaign-completeness`; `campaign_id` on every row from schema "24" |
| **Source** | `aidd_docs/backlog/stories/a-campaign-is-declared-as-data-and-an-empty-cell-fails-it.md`; parent epic `the-engine-and-the-prompt-variant-are-measured-not-assumed.md` (Boundaries "the campaign declaration as data", decision "Campaign shape"); PRD Methodology 22 and its AC "the campaign declares at most two engines and at most four variants" |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Campaign declaration loader and completeness command | [`phase-1.md`](./phase-1.md) |
| 2   | `campaign_id` on every row and the pre-launch run check in the three writers | [`phase-2.md`](./phase-2.md) |
| 3   | Docs, memory and CHANGELOG | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Declarations live at `aidd_docs/campaigns/<campaign_id>.json` (`CAMPAIGNS_DIR` overrides the directory), the file stem must equal its `campaign_id`, and `CAMPAIGN_ID` names the campaign a run belongs to. No declaration is committed by this story. | "A tracked directory beside the results": `aidd_docs/campaigns/` sits beside `aidd_docs/results/` and outside the committed stores. The stem rule is the suite registry's own (a file name and its id must match). The campaign itself (order 12) publishes the first declaration. `CAMPAIGN_ID` mirrors `MACHINE_ID`: an environment input every writer reads the same way. |
| Declaration shape: `campaign_id`, `description`, `engines` (engine ids), `prompt_variants` (`{id, version}`), `roster_entries`, `suites` (suite ids), `machine` (`{machine_id, compute_mode}`), `exclusions`. Unknown top-level keys refuse the load. | Each acceptance dimension is one key; refusing an unknown key keeps a mistyped dimension from being silently ignored, and a later dimension (the harness list) is added to the loader and to the cell product, never as a second file. |
| Every id is resolved against its registry at load: engines through `engines.load_registry` (so an incomplete engine entry refuses the load under order 1's rule), variants against `prompt_variants.REGISTRY`, roster entries through `roster.load_roster`, suites through `suite_registry.registered_ids`, the machine through `machines.load_registry`, the mode against `COMPUTE_MODES` (and `gpu` on a GPU-less machine refuses, as `require_run_profile` does). The registry paths are parameters defaulting to the tracked ones. | Acceptance bullet 1; parameters let a test point at an incomplete engine registry without editing the tracked one. |
| Caps: more than 2 distinct engines or more than 4 distinct (variant id, version) pairs refuse, naming the declared values; an empty dimension or a duplicate value refuses too. | Methodology 22; an empty dimension declares no cell, a duplicate would double-count one. |
| `exclusions`: each entry names a subset of cells by any of `engine_id`, `prompt_variant` (`{id, version}`), `roster_entry_id`, `suite_id` (an omitted coordinate covers every declared value on that axis), an `outcome` of `refused` or `dropped`, a non-empty `reason` and an `evidence` pointer. A coordinate outside the declaration, or two exclusions covering one cell, refuse the load. | Order 8's "no mechanism" outcome is a dropped cell with its reason and the spike as evidence; a machine refusal (order 12: "a roster entry the machine refuses is listed as refused") covers every cell of one roster entry, hence the omitted-coordinate rule. The machine epic's published refusal record does not exist yet, so the declaration carries the reason and points at its evidence. |
| A cell is filled by quality rows whose `campaign_id`, `engine_id`, `prompt_variant_id`/`_version`, `roster_entry_id`, `suite_id`, `machine_id` and `compute_mode` all equal the cell's and the campaign's; its run ids are listed sorted. An excluded cell holding rows is `contradicted` and fails like an empty one. Exit `0` when no cell is empty or contradicted, `1` naming each that is, `2` when the declaration or the rows do not load. Rows come from `--rows` (repeatable), default `QUALITY_RESULTS_PATH`. | Acceptance bullets 3 and 4: the listing is a pure function of declaration and rows, ordered by the declaration, so a re-run returns the same text. Runtime rows name no suite and so fill no (engine x variant x roster x suite) cell. The 0/1/2 split is the candidate gate's and the composition check's. |
| `campaign_id` is required on both row kinds from schema "24" (`CAMPAIGN_SCHEMA_VERSION`): a declared campaign's id, or `NO_CAMPAIGN = "none"` for a run started under none; `"none"` is refused as a campaign id. A row from a cloud provider must carry `"none"`. Rows below "24" are never back-filled. | Acceptance bullet 2: a run with no campaign records that it belongs to none, stated rather than null (the `not_applicable` precedent). A campaign declares engines and a cloud subject runs on none, so a cloud row can never belong to one. |
| The run check (`campaigns.require_run_campaign`) runs in each writer after the machine and the variant are resolved and before the build probe, the fiche or any spawn. It refuses, naming every offending dimension: an engine, variant, roster entry, suite or machine/mode outside the declaration, and a run of a cell the declaration excludes. The quality CLI under a campaign also refuses a cloud provider in `QUALITY_PROVIDERS`. The runtime CLI has no suite, so its suite is not checked. | Acceptance bullet 2 ("refuses before any server starts"). A dropped cell that is then run would contradict its own declaration. |
| The judge probe refuses any `CAMPAIGN_ID` and stamps `"none"`. | Its suite (`judge-probe-open-ended`) is not a registered suite and its two judges are cloud calls, so no campaign could ever declare it; the epic excludes the judge machinery. |
| `campaign_id` joins the resume configuration check (quality CLI, judge probe), is bookkeeping for `comparison.EXCLUDED_FROM_DIFFERING`, is listed as not rendered by the read model, and is described in the export's column dictionary. | One batch never spans two campaigns; campaign membership is not a configuration, so a campaign row against a no-campaign baseline is not a confound; the read-model partition and the export dictionary both refuse an unplaced field. |
