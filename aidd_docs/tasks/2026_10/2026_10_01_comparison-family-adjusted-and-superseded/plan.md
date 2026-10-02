---
objective: "One analysis invocation writes one immutable family record (one suite crossed with one compared dimension) holding every comparison it ran, its size, its tested and refused counts and each member's Holm-adjusted p over that closed set, with each verdict read against the adjusted p, and a grown family is a new record superseding the old by id while every published record stays byte-identical."
status: implemented
---

# Plan: A comparison family carries its adjusted p-values and is superseded, not edited

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Extend `comparison.py` from a family of one to a closed multi-member family: Holm over the members' raw p-values, verdicts on the adjusted p, tested/refused/adjustment counts, a `supersedes` id list, and an analysis command that takes a declared list of comparisons, refuses one spanning two families, and supersedes the current head of its family definition |
| **Source** | `aidd_docs/backlog/stories/a-comparison-family-carries-its-adjusted-p-values-and-is-superseded-not-edited.md` |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | Holm over a closed set and the multi-member family record | [`phase-1.md`](./phase-1.md) |
| 2   | The analysis command: declared comparisons, one family per invocation, supersede by id | [`phase-2.md`](./phase-2.md) |
| 3   | The family record over the committed bundle, the published-record tests, README and memory | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| Wikipedia, "Holm-Bonferroni method" (fetched 2026-10-02) | Worked example: p = 0.01, 0.04, 0.03, 0.005 at alpha 0.05 reject H1 and H4; adjusted p = 0.03, 0.06, 0.06, 0.02; formula `p~(i) = max_{j<=i} min(1, (m - j + 1) p(j))`. Reproduced by a test. statsmodels is not installed and scipy has no Holm, so the oracle is the published example plus a hand-computed fixture, as the story asks. |

## Decisions

| Decision | Why |
| -------- | --- |
| `record_version` becomes `"2"`; the two committed `"1"` records are never rewritten. The command over the committed bundle writes one `"2"` record holding both pairs and naming both `"1"` ids in `supersedes`. | The acceptance forbids rewriting a published record, and the new fields (counts, `supersedes`, `raw_p_value`) change the bytes and therefore the id. The two `"1"` records are two parallel heads of one family definition (`classification-support-routing@2` x `model`); the default definition puts both pairs in one family, so the new record supersedes both. |
| An invocation declares its comparisons: the existing single-pair flags (a family of one, unchanged) or `--comparisons <json>`, an array of `{"reference": {"run_id", "where"}, "candidate": {...}}`. Members are sorted canonically by their sides; a comparison declared twice is refused. | The order-2 plan defers multi-member families here and keeps declared pairs; auto-enumerating every pair in the bundle would need a reference/candidate rule no source states. Canonical order makes the record independent of declaration order, so the same definition re-run is identical. A duplicate would inflate the adjustment count. |
| The family definition is `suite_id`, `suite_version`, `compared_dimension` plus the stated rule. Members whose sides agree on the suite identity must all name one suite, otherwise the invocation is refused (exit 1, nothing written). A member refused on suite identity stays in the family as a refusal. | Methodology 24's default family, and the acceptance's "one invocation writes one family record": two suites in one invocation would be two families. |
| Holm runs over every member not refused, observations included; a tested member with a null p (no discordant pair, all differences zero, paired n below minimum) enters as p = 1 and keeps its own adjusted p null with its reason; a refusal enters no count. So `multiplicity_correction.adjustment_size` (m) equals `tested_count`; the record also states `family_size` and `refused_count`. (Review round 1, non-blocking 1: m first excluded null-p members, which let the others' adjusted p come out lower.) Holm is computed in `Fraction` from the float raw p-values, ties sharing one adjusted value by the running maximum. | An observation's p was computed and published in `result`, so counting it is the conservative reading of "the comparisons it ran"; a member with no p has nothing to adjust. Exact arithmetic gives the published 0.03/0.06/0.06/0.02 without float drift. |
| A member's verdict reads its adjusted p; `raw_p_value` sits beside `adjusted_p_value`; a refused member's adjusted p is null with reason `comparison_refused`. | Acceptance 3, and the value-plus-one-reason discipline of `agreement.py`. |
| Supersede by id is computed, not declared: before writing, the command reads every family record in `--records-dir` (default `aidd_docs/results/comparisons/`). A record of the same definition whose content equals the new one except `family_id`/`supersedes` is re-emitted as is (re-run identical); otherwise the new record's `supersedes` lists the ids of every head of that definition (a record no other record supersedes), and `family_id` hashes the content including `supersedes`. | A caller cannot forget to supersede and leave two current records for one family, which is the mistake the family-as-artifact decision exists to prevent. Matching on content makes a re-run over the same bundle and definition return the identical record even after the family grew, and the console names the record superseding it. A family only grows: a declaration that leaves out any member of a current record of its definition is refused (exit 1, nothing written, the missing comparisons named), so a favourable pair cannot be re-published alone as the current record (review round 1, blocking 1). A change of `--alpha` alone supersedes too. |
| The published-record test recomputes a `"2"` record from the bundle with only the records it supersedes placed in an isolated records dir; a `"1"` record is checked against its own content hash and must be named in some `"2"` record's `supersedes`. | Recomputing against the live records dir would find the published record itself and re-emit it, which proves nothing. The self-hash proves a `"1"` file is unedited without pinning a hash literal. |
| `supersedes` is a list of `{"family_id": <id>}` objects, not bare strings. | detect-secrets flags a bare 64-hex string on its own line as a high-entropy secret; under a `family_id` key its id filter recognises it, as it already does for each record's own `family_id`. JSON holds no inline `pragma` comment, and widening the hook's exclude pattern or baselining the file would weaken the scan for every later record. |
