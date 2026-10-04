---
objective: "Every quality suite declares a per-item divergence tolerance (value, unit, reason) refused by the gate when absent; a cloud subject batch is decided per item under it (reproduced within it, naming every diverging item; not_reproduced beyond it), a batch that cannot be re-run deterministically is marked single-run indicative and never not_reproduced, a local batch keeps the identical-output rule, and the verdict block names the rule, the tolerance and the suite version that declared it (schema \"29\")."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: A cloud subject re-run is decided per item under its suite's declared tolerance

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `suite_gate.gate_divergence_tolerance` refuses a suite with no tolerance; both shipped suites declare one (version bump, new snapshots beside the old ones); `verdict.quality_verdict(..., provider=, tolerance=, rerun_blocker=)` applies the identical rule to `local` and the tolerance rule to a cloud provider; the verdict block gains `subject_rule`, `tolerance`, `divergence`, `single_run_indicative`, required on quality rows from schema "29"; `quality_cli` passes the suite's tolerance, the provider and a missing-seed blocker |
| **Source** | `aidd_docs/backlog/stories/a-cloud-subject-re-run-is-decided-per-item-under-its-suites-declared-tolerance.md`; parent epic `every-published-row-explains-and-reproduces-itself.md`; night-run owner decision D2 (no paid API call) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Declared tolerance: gate, registry, suite data and snapshots | [`phase-1.md`](./phase-1.md) |
| 2   | Per-item cloud verdict, verdict fields (schema "29"), CLI wiring, export docs | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Suite key `divergence_tolerance: {value, unit, reason}`, unit `fraction_of_items` (share of the batch's items whose compared per-item value differs from the reference), value in `[0, 1]`. Checked by a separate gate function `suite_gate.gate_divergence_tolerance`, called by the registry on every load beside `gate_suite`. | One unit works for both the exact-match and the graded suite, since the verdict already compares one per-item value (`compared_field`); a separate gate function keeps the 29 item-only `gate_suite` callers unchanged while still refusing any loaded suite that declares none. |
| Classification `0.10` (2 of 20 items), reason cites the committed `mistral-small-2603` re-run pair in `quality-reference.jsonl` (run `d20afbda...` vs `5e13166d...`: 1 of 20 items diverged, `other-de-01`). Translation `0.10` declared provisional: no cloud re-run of that suite exists and D2 forbids one tonight; its reason says so. | The PRD states no value; the story asks for one set against an observed re-run. The committed pair is a real observation that costs no call; the translation value stays disputable and flagged pending calibration. |
| Declaring the tolerance bumps both suite versions (classification 4 -> 5, translation 3 -> 4) and exports new snapshots `@5`/`@4` beside the old ones. | The snapshot exporter refuses to overwrite a published snapshot with different content, and the verdict must name the suite version that declared the tolerance. Items are unchanged, so `prompt_set_hash` is unchanged. |
| Single-run indicative keeps the three-state verdict: `verdict: not_comparable`, `single_run_indicative: "model_not_served" \| "no_seed"`, reason naming it. Never `not_reproduced`. | A fourth verdict state would ripple into `leader_set`, `comparison` and the export vocabulary; "cannot be compared to a re-run" is what `not_comparable` already means. |
| `no_seed` is derived from the batch's own `sampling` (no `seed`/`random_seed` key); `model_not_served` is passed when the provider's pre-flight raised its `ModelUnavailableError`, which writes no rows, so the CLI prints the mark on stderr. Marking an already-published row is a store republication, out of scope. | Both providers accept a seed today; the rule is data-driven so a seedless provider is caught without a new table. |
| A local verdict block carries `subject_rule: "identical"` and `tolerance: null`; a cloud block `subject_rule: "within_tolerance"` and `tolerance: {value, unit, suite_id, suite_version}`. | The local rule is unchanged and decided under no tolerance; naming one there would suggest it was applied. |
| The judge probe (a code-defined suite outside the registry) declares `DIVERGENCE_TOLERANCE` `0.0`, gated by `gate_divergence_tolerance`, and its always-`not_comparable` verdict block carries the four new keys via `verdict.subject_rule_fields`. | Its rows are quality rows at schema "29"; every quality suite declares a tolerance. The value is never applied (the probe publishes no label or score), and its reason says so. |
| A cloud item whose compared value is null on either side counts as diverging. | "A cloud batch is never decided off null values": a null agreeing with a null is not evidence of reproduction. The local rule is left exactly as it was. |
