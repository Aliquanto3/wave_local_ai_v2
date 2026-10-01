---
type: story
status: ready
source: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
parent: aidd_docs/backlog/epics/a-score-is-published-with-its-interval-a-difference-with-its-test.md
order: 2
---

# Story: Two configurations on the same items receive a paired test or a refusal

**As** an academic or technical reviewer reading a claim that one model beats another
**I want** the claim to arrive as a tracked comparison record carrying the paired test that fits the scoring kind, its p-value, direction, effect size and paired n, or as a refusal naming why the two sides cannot be compared
**So that** I can tell a real difference from noise in a small suite, and a 15-point gap on 20 items is never published as a finding it is not

Maps to: PRD AC "given a claim that two models, engines or prompt variants differ, it is shown with a paired Wilcoxon test's p-value and effect direction, or it is not presented as a difference" (refined by Methodology 24 to McNemar's exact test for a binary score); PRD User Story "As an academic or technical reviewer..."; Methodology 2, 3, 9, 24; epic decisions "The paired test is named per scoring kind", "A direction is not an effect size", "A comparison refuses rather than reports, and 'item set' means the declared one", "Unpairable items are counted, and named to a side", "An undefined statistic publishes a named reason, never a number"; epic success checks 5 (test reasons), 7, 8, 9 and 11.

Needs: none. Constructed rows prove the computation and the committed bundle supplies the real pairs; no model run, API key, hardware or operator is required.

Current state: `aidd_docs/results/quality-reference.jsonl` holds two pairable comparisons on `classification-support-routing` version `"2"`, each pairing `Qwen3.6-35B-A3B` and `mistral-small-2603` over the same 20 item ids under one shared `run_id` (`5e13166d...`, `d20afbda...`). Both sides of each pair share a run id, so a side is not identified by run id alone. Those rows sit at `schema_version` `"7"` and carry no `thinking_policy` field.

## Acceptance

- A named analysis command, run over the published bundle, writes a comparison record as its own tracked artifact; nothing computes a comparison at read time.
- The two sides are declared as a reference and a candidate. The record carries `reference_run_id` and `candidate_run_id` (the name `verdict.py` already uses) plus whatever further row field selects a side's rows within its run, because both published pairs share one run id. Every difference is computed as candidate minus reference.
- The test is chosen by scoring kind, never per call site: a binary exact-match score gets McNemar's exact test over the discordant pairs; a graded or ordinal score gets Wilcoxon signed-rank over per-item differences. The record names the test and why it was chosen.
- The record carries the suite id and version both sides ran, the paired item ids, the `compared_field`, the statistic, the p-value, the direction, the effect size with its formula (rank-biserial for Wilcoxon, the discordant-pair odds ratio for McNemar), the paired n, the tie and zero-difference counts, and the count of items present on one side only with which side each was missing from.
- For Wilcoxon, the record names its zero-difference convention, its exact-versus-normal-approximation rule and that rule's n threshold, and whether a continuity correction was applied. An item both sides failed is an exact tie under Methodology 9 and is handled by the named convention, never dropped silently.
- The record carries the set of row fields on which the two sides actually differ, computed from the rows, on `verdict.py`'s `differing_fields` convention. A comparison whose sides differ on more than the compared field is published as an observation naming its confound, never as a clean test: a `gpu` row against a `cpu_only` row of the same model produces a well-formed record whose differing-field set says so.
- A comparison is refused, naming the differing field, when the two sides differ on `suite_id`, `suite_version`, `prompt_set_hash`, `max_output_tokens`, `stop_sequences`, `context_length`, `thinking_policy`, the metric identity and version on a graded row, the scoring kind or the `compared_field`, or when they declare two different suite levels (order 4 adds the level). One of the four generation constraints or the metric identity absent on one or both sides is never read as a match: the refusal names it as absent, applying Methodology 8's "two unknown values never count as a match". A partially observed row set is not a refusal; it shrinks the paired n and raises the one-sided count.
- Undefined statistics publish a named reason in place of the number: McNemar with no discordant pairs, an odds ratio with an empty cell, every paired difference zero, a paired n below the test's own minimum.
- The record carries one reader-facing verdict, `distinguishable`, `not distinguishable` or `not comparable`, evaluated at the declared alpha, with every raw input kept beside it.
- Each record is written as a family of one, its adjusted p equal to its raw p and stated, so the record shape does not change when multi-member families arrive (order 3).
- Re-running the analysis command over the published bundle alone, through no private path, returns identical records.

## Code it changes

- `src/wave_local_ai_v2/` (new comparison module): pairing on `item_id`, test selection per scoring kind, McNemar exact via `math.comb`, Wilcoxon signed-rank with its named conventions, effect sizes, null reasons, the refusal list and the differing-field set.
- A new CLI entry point in `pyproject.toml` for the analysis command; its output file under `aidd_docs/results/`.
- `src/wave_local_ai_v2/verdict.py`: reused for the `differing_fields` convention, not changed in meaning.

## Tests it needs

- A published worked example each: a McNemar 2x2 and a signed-rank table, plus scipy as dev-only oracle.
- A classification suite routes to McNemar's and a translation suite to Wilcoxon without the caller choosing.
- Refusals, each naming its own field: a bumped `suite_version`, a differing `max_output_tokens`, a differing `thinking_policy`, a differing metric version on a graded row, a scoring-kind mismatch, and a field absent on both sides.
- Unpaired items counted and named to their side; the confound case produces an observation, not a test.

## Evidence it publishes

- The analysis command's output over the two committed pairs, recorded in `aidd_docs/results/README.md`. While the bundle holds the schema-7 rows, the rule above refuses both, naming `thinking_policy` as absent because those rows predate the field; that refusal is itself the published evidence, and the README says so rather than reporting a p-value. Once the bundle is regenerated (`the-laptop-proves-both-modes-and-republishes-the-bundle-once`), the same command over the regenerated pairs publishes their records. The McNemar arithmetic the epic states for those pairs (run `5e13166d`: 4/1 discordant, p = 0.375; run `d20afbda`: 4/2 discordant, p = 0.688) is reproduced by a test over constructed rows carrying the same per-item outcomes. Whether rows predating a constraint field may instead be compared as an observation naming the absence is an owner question (`aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`); a different answer changes this bullet only.

## Cancellation

n/a: not cancelled.
