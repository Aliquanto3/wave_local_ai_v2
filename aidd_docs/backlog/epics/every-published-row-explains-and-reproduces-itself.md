---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
related_to: aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
---

# Epic: Every published row explains and reproduces itself

Given any published benchmark row, a client's engineer can read from the row alone how it was produced — sampling, rendered prompt and template version, generation caps, hardware fiche hash, roster entry, code sha, energy method and emission factor, cost basis — and re-run it to an explicit reproduced / not-reproduced verdict.

## Context and Value

The audience is the client-side engineer the PRD names as one of the two audiences a result must survive: the one "auditing methodology and reproducibility" (PRD, Problem Statement). That engineer does not read the repo's docs first; they read a row. Today a row does not answer them.

Verified current state, at `a2ffe37`:

- **Runtime is single-shot.** One measurement per configuration, so no N, no mean, no standard deviation, no spread, and nothing to compare a re-run against. The audit records this as the open half of E10: "quality side done (pinned sampler, reproduced twice, evidence committed); runtime side single-shot, no spread" (`2026_08_21_expectations-gap-audit/audit-and-plan.md`, section 5.2).
- **The fiche is not an identity.** Its fields are flattened inline into every runtime row (`aidd_docs/results/runtime-reference.jsonl`) with no content hash, so no row can be invalidated when the fiche behind it changes, and two rows from different machines are distinguishable only by eye.
- **The machine is hardcoded, not declared.** `N_CPU_MOE = 37` and `THREADS = 8` (`src/wave_local_ai_v2/server.py:26,29`), `LLAMA_CPP_BUILD = "b10537"` (`src/wave_local_ai_v2/__init__.py:25`) and the model file are constants. A row therefore reports a build string the code asserts rather than one the running binary reported, and the project cannot be re-run on a second machine without editing source — the audit's E11.
- **Carbon is computed and thrown away.** `energy.py` returns `energy_kwh` and `energy_method` only; CodeCarbon's emissions figure, the region and the emission factor that converts between them are discarded. The audit's E3.
- **Provenance is partial.** `quality_cli.py` writes `run_id` and `captured_at`; neither row type carries the release version or commit sha, and the tracked runtime reference rows predate even `run_id`.
- **There is no roster file**, so no row cites a pinned repo revision, checksum, quant, licence or per-model flag set — and the "a dense model takes no MoE-offload flags" rule of Methodology 13 has nowhere to live. This is what makes the audit's E6 spec-only.
- **There is no prompt-template version and no stored rendered prompt for the local provider.** The quality row stores the pre-template prompt string; what llama.cpp's jinja templating actually sent is not recoverable.
- **The classification suite carries no language and no provenance tag**, and holds 10 items against Methodology 4's 20 (`src/wave_local_ai_v2/classification_suite.py`).

Two Methodology criteria in this area are already satisfied and are recorded here as done rather than as work: **12, cloud model pinning** (the dated Mistral model id is recorded and a run refuses to start when it is absent from the provider's live model list, shipped via `2026_08_21_mistral-model-preflight/`) and the **quality half of 1, sampling determinism** (seed, temperature, top_p, top_k and presence penalty are pinned and written into every quality row's `sampling` block, shipped via `2026_08_21_quality-sampling-reproducibility/`, reproduced twice with the evidence committed).

The value is the product's founding bet. The PRD's defensibility claim is not that the numbers are good; it is that a challenger can check them. Every criterion below exists so a published number can be *failed*. Without them the runtime table is, in the words of the project's own memory, "effectively unfalsifiable" (`aidd_docs/memory/architecture.md`, Gotchas) — and an unfalsifiable number is worth less in front of a sceptical engineer than no number at all.

## Boundaries

- Includes: the runtime half of criterion 1 (sampling recorded on runtime rows too); 2 prompt parity and versioning; 3 generation caps in the suite definition; 4 suite size and language mix; 5 item provenance and contamination-risk marking; 6 runtime repetition, median, N, mean and standard deviation with the raw repetitions retrievable; 7 machine state at start and the unreliable flag on excess spread; 8 the reproduction verdict for both quality and runtime; 9 failed-generation scoring and reason, never silently dropped; 13 the versioned roster file every row's fiche cites; 14 fiche integrity by SHA-256 with invalidation of the rows referencing an edited fiche; 15 energy, emissions, factor, region, method, and the cloud Scope-3 estimate with its formula id; 16 cost, cloud tokens and list price, local kWh price; 19 run provenance including release version and commit sha.
- Includes: making the hardcoded server flags, model file and llama.cpp build roster- and settings-driven rather than constants, because criteria 13 and 14 cannot be satisfied while a row's fiche is an assertion in source.
- Includes: republishing `aidd_docs/results/{runtime,quality}-reference.jsonl` under the new row schema. The tracked rows predate it and are not migrated in place.
- Includes: a **one-time migration of the classification suite** to criteria 4 and 5 — 10 items to 20, each tagged with its language under the EN/FR/DE ≥25% mix, each declaring its provenance. This is the only suite that exists, so it is the only suite this epic touches.
- Excludes: authoring or scoring any new task suite. The translation and rewriting suites belong to `quality-scored-comparison-first-three-use-cases`; their stories cite criteria 4 and 5 as acceptance and are born compliant against the gate this epic ships — they do not re-implement it.
- Excludes: criteria 10 and 11, the judge protocol and judge independence. They arrive with the second cloud provider and the judge machinery, in their own epic. This epic leaves the row schema open for the fields they add.
- Excludes: criteria 17 and 18, web-research archival and suite shape, which belong to `aidd_docs/backlog/epics/no-use-case-is-silently-absent.md`.
- Excludes: the surface that shows these fields to a decision-maker. The results service and dashboard are a separate epic; this epic makes the data exist and be correct, not readable at a glance.
- Excludes: CI, container packaging and release tagging as such — with one seam: criterion 19 needs a release version to record, so this epic records whatever version identifier exists and does not invent the tagging process.
- Excludes: revising the Methodology's thresholds. 20 items, N≥5, 10%, 25% per language are taken as the PRD's stated initial values and implemented as configured constants, not re-derived.

Criterion ledger, so the scope is checkable rather than described:

| Criterion | Here |
| --- | --- |
| 1 sampling determinism | quality half done; runtime half in scope |
| 2, 3, 4, 5 | in scope (4 and 5 as rule + gate + one-time classification migration) |
| 6, 7, 8, 9 | in scope |
| 10, 11 judge protocol and independence | out — judge epic |
| 12 cloud model pinning | done |
| 13, 14, 15, 16, 19 | in scope |
| 17, 18 web research | out — `no-use-case-is-silently-absent` |

## Success Evidence

Take one published row from the regenerated reference files, hand it to someone who did not produce it, and give them nothing else. They can name the exact model and roster entry, the exact prompt as sent, the caps, the sampling values, the machine it ran on by fiche hash, the code sha, and whether its energy figure is a measurement or an estimate. They then re-run it and receive a verdict — reproduced or not reproduced — rather than two numbers to compare by eye.

Four checks confirm or challenge it, each able to fail:

- A runtime row published without N, median, mean, standard deviation and its raw repetitions cannot be produced by the harness at all.
- Editing a hardware fiche invalidates the rows citing its hash, demonstrably: the invalidation is observable, not documented.
- A suite of fewer than 20 items, or one whose EN/FR/DE mix falls below 25%, publishes its score marked indicative — verified by deliberately shrinking a suite.
- A re-run whose median falls outside 10% of the reference median returns "not reproduced" with the thermal and load hints of both runs, not a silent pass.

Once `done`, record here what a real client engineer's audit of a row actually surfaced, and whether any of the four thresholds moved on contact with the first full-roster run.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| CPU package temperature (criterion 7) may be unreadable on Windows without an elevated vendor driver; `psutil` exposes no sensor readings on this platform | spike | Frame a spike before the criterion 7 work: establish whether a temperature is obtainable at the project's privilege level. If not, criterion 7 degrades to a declared-unavailable state with the same honesty discipline as `energy_method`, and system load alone carries the machine-state hint. |
| N≥5 repetitions multiplies every runtime measurement's wall-clock by ~5 on the single development machine | assumption | Accepted: repetition count is configurable with 5 as the default, so a development loop can lower it while a published row cannot. |
| The tracked reference rows predate the schema and cannot be retro-tagged with a fiche hash, roster entry or commit sha they never carried | assumption | Accepted: they are regenerated, not migrated. The old rows are replaced rather than reinterpreted. |
| The Methodology thresholds (20 items, N≥5, 10%, 25%, 80%) are initial values the PRD itself flags as possibly needing to move after the first full-roster run | decision | Deferred to that run, per the PRD's own Open Questions. This epic implements them as configuration so moving one is a value change, not a rewrite. |
| Emission factor and region must be declared for CodeCarbon's offline mode, and the cloud Scope-3 formula must be identified | dependency | Both patterns validated in the v1 predecessor and named in the PRD's Dependencies; this epic carries them forward and records the formula id per row rather than choosing a new method. |
| The kWh price behind a local row's energy cost | decision | Configurable, no value fixed at epic level. Cost is reported, never optimised (PRD Non-Goals). |
| The roster's model set, quants and licences | decision | Not decided here. This epic ships the roster file's shape, its pinning fields and the citation from every row; which models populate it is the neighbouring epic's output. |
| The judge epic will add fields to judged rows (judge model ids, prompt hash, rubric version, agreement) | dependency | Not blocking in either direction. The row schema stays additive so the judge epic extends it rather than reshaping it. |
| Release version and commit sha (criterion 19) need a release identifier to exist | dependency | The engineering-credibility epic owns tagging and the changelog. This epic records the identifier available at run time and degrades explicitly when there is none, rather than blocking on that epic. |
| Translation and rewriting suites must satisfy criteria 4 and 5 without this epic authoring them | dependency | Their stories in `quality-scored-comparison-first-three-use-cases` cite 4 and 5 as acceptance and are validated by the gate this epic ships. The gate, not this epic's authorship, is what makes them compliant. |

## Cancellation

n/a — not cancelled.
