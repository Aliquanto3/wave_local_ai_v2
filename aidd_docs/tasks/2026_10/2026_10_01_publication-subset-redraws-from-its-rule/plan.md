---
objective: "A publication subset is drawn by a recorded, stratified, seeded rule that replays to the same item ids in the same order, every drawn item carries a content hash that names it on replay when its source text moved, and the drawn subset certifies at `publication` on its first seed."
status: implemented
---

# Plan: A publication subset redraws to the same items from its recorded rule

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | A pure sampler module (canonical ordering, stratified seeded draw, recorded retries, per-item content hash, the selection-rule record and its validation), the registry checking those fields wherever a definition declares them, and a replay command that re-draws a suite's subset from its recorded rule over a source table |
| **Source** | `aidd_docs/backlog/stories/a-publication-subset-redraws-to-the-same-items-from-its-recorded-rule.md` (owner answers Q1 (a), Q70 (a)) |

## Phases

| #   | Phase                                                                 | File                          |
| --- | --------------------------------------------------------------------- | ----------------------------- |
| 1   | The sampler: canonical ordering, stratified seeded draw, retries, content hash, rule record, and the registry's check of the added fields | [`phase-1.md`](./phase-1.md) |
| 2   | The replay command and the docs naming it | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Two modules: `subset_sampler.py` (pure: no registry import, no I/O) and `subset_replay.py` (the `python -m` command, resolving a suite through the registry). | The registry validates the added fields through the sampler, so the sampler cannot import the registry; the command needs the registry. Same split as `chrf.py` (pure) vs its caller. |
| The fields are added to the existing definition shape, not a second one: a top-level `selection_rule` object (carried in `SuiteDefinition.extra`, exported by the snapshot unchanged) and an item key `content_hash`. The registry checks both wherever declared and refuses a malformed one. | Acceptance: "proposed to the suite definition shape ..., not forked from it". The registry docstring already names these keys as landing as data; the previous story's rule is that every added key is validated rather than carried unchecked. |
| The rule is strict: exactly the keys `sampler_version`, `seed`, `attempts`, `seeds_tried`, `loader` {`library`, `version`}, `stable_source_key`, `canonical_ordering`, `stratify_by`, `content_fields`, `size`, `benchmarks` [{`source`, `licence`, `source_revision`}]. `seeds_tried` must hold `attempts` distinct seeds ending with `seed`. | "A retry loop that records only the final seed is refused" is enforced at load, not by convention. An unknown key would be an unversioned extension of a versioned rule. |
| Sampler v1: rows sorted by (`source`, string form of the stable key); strata in fixed order (language `en`, `fr`, `de`, then label values sorted); `size` split equally across the three languages, then equally across a language's labels, remainders to the first strata; one `random.Random(seed)` drawing `sample(stratum, k)` per stratum in that order; output in stratum order, drawn order within. Retry seeds are `first_seed + attempt_index`. | Equal language allocation gives each language >= 33%, so the 25% publication share holds by construction on the first seed. A single seeded generator over canonically ordered rows makes the canonical ordering load-bearing, which is the property the PRD records. A stratum the source cannot fill is refused naming it rather than silently topped up from another. |
| `stratify_by` is `["language"]` for a non-classification suite and `["language", <label field>]` for a classification one; the registry refuses any other shape against the suite's `task_suite`. | "By language always, and by label as well where the source is a classification benchmark", checked rather than declared. |
| Content hash v1: SHA-256 over compact sorted-key JSON of `{"text": [NFC-normalised, whitespace-collapsed value of each rule `content_fields` entry, in order], "licence", "source", "source_revision"}`. A classification rule names its label field among `content_fields`. | Acceptance names text, licence, source and revision; including the label in the hashed text is what makes an upstream retag nameable at the item, as the epic requires. |
| Drawn item id is `<source>:<stable key>`; a drawn item carries `provenance` `public`, `contamination_risk` true, and its benchmark's licence and revision. | Ids are a function of the source key only, so an edited text keeps its id and is named by the content-hash check instead of disappearing from the redraw. Methodology 5 marks every drawn item contamination-risk. |
| A publication suite is not required to carry a `selection_rule`; the gate's level contract stays order 4's. | No acceptance line asks for it, and two existing publication fixtures register without one. Noted as a follow-up for orders 7 and 8. |
| The replay command reads a JSONL source table with the standard library; the recorded `loader` is printed, not enforced. | The canonical ordering removes the arrival-order dependency the loader introduces; a real loader is orders 7 and 8's. |
| The dependency story's seam test (`test_the_interval_epics_fields_are_additions_to_the_one_shape`) carried a placeholder `selection_rule` `{"seed": 1, "n": 3}` and `content_hash` `"sha256:00"`; it now keeps the licence/source/revision half with a well-formed hash, and the rule half moves to the drawn-suite registry test. | The placeholders were declared before the fields had a meaning; now that they do, an unreplayable rule must not load. The property the test protected (additions to one shape, exported in the snapshot) is asserted by the drawn-suite test with real values. |
| The rule also records `generator` (`{"library": "CPython random.Random", "version": "<major.minor>"}`), and a golden test pins seed 7's ids, their order and the drawn definition's SHA-256 (review findings 1 and 2). | Python does not promise `random.sample` stays stable across versions; the CI matrix now fails on a drift instead of silently drawing other items, and the rule says which generator drew it. |
