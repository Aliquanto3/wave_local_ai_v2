---
type: story
status: ready
source: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
parent: aidd_docs/backlog/epics/no-use-case-is-silently-absent.md
depends_on:
  - aidd_docs/backlog/stories/a-suite-is-data-resolved-by-its-id-not-an-import-in-the-cli.md
  - aidd_docs/backlog/stories/every-prd-use-case-carries-a-coverage-state-or-the-record-refuses-to-publish.md
related_to:
  - aidd_docs/backlog/stories/the-published-image-runs-the-benchmark-without-a-clone.md
order: 4
---

# Story: Generated code is scored by its tests in a sandbox, or not run at all

**As** a client-side engineer whose team pays a cloud vendor for code generation today
**I want** a code-generation suite whose Python and JavaScript items are scored by executing their tests in an isolated container sandbox, which refuses to run rather than execute generated code on the host
**So that** I read a deterministic, judge-free score per language for local and cloud models, and running the benchmark never runs untrusted code on my machine

Maps to: PRD AC "Given the full use-case list, each of the nine task use cases ... has at least one task suite exercising it"; PRD Goals "Coverage spans the full set of use cases" (code generation); PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side"; Methodology 3, 4, 5, 9; epic Boundaries "six suites" (code generation), "a sandboxed runner for model-generated code, with a refusal posture"; epic Sequence step 3; epic success checks 2, 3 and 11.

Needs: a real local model run on a machine with the container runtime the published image already uses (an operator installs it where absent; the no-GPU professional PC may not have one, and there the suite refuses); a cloud subject key already configured (Mistral or Google AI Studio) for the cloud rows.

## Acceptance

- A code-generation suite is registered through the seam (order 1) with at least 20 items. Each item carries a programming-language tag (Python or JavaScript, both present in the suite), the tests its generated code must pass, a natural-language tag for its instructions with EN, FR and DE each at 25% or more, and its provenance; public-origin items are marked contamination-risk.
- Generated code runs only inside a container started from the container runtime the published image already uses, with no network, no host mount, a wall-clock cap and a memory cap; the caps are recorded per row. Where no container runtime is present, the suite refuses to start with one line naming why, and never falls back to executing on the host.
- Python items' tests and JavaScript items' tests both run inside that sandbox; JavaScript runs on Node under its built-in test runner, so the sandbox adds no compile step and no third-party JavaScript test dependency.
- An item scores 1 when every one of its tests passes and 0 otherwise. Code that fails a test, does not compile, times out, or is empty, truncated or unparseable scores 0, stays in the denominator, and records its failure reason (Methodology 9).
- Every row names its item's programming language. A per-language score is computed only over the items carrying that tag, and asking the published table for a language the suite does not tag returns nothing rather than an average (epic success check 11). No per-programming-language minimum share is invented.
- No judge is called.
- At least one local and one cloud batch are published as rows in the reference bundle, and the coverage record's code-generation entry moves to `exercised` naming this suite.

## Code it changes

- The suite's data file and its scoring rule, registered through order 1.
- The sandboxed runner, sharing the container runtime the published image (`the-published-image-runs-the-benchmark-without-a-clone`) already introduced rather than adding a second one.
- The coverage record entry.

## Tests it needs

- A planted generation that fails its tests scores 0, stays in the denominator, and names its reason; a planted correct one scores 1 (epic success check 3, verified by planting, not by unit-testing the scorer alone).
- With the container runtime absent, the suite refuses and no generated code is executed.
- A planted generation that opens a network connection, or writes outside its working directory, fails inside the sandbox and leaves nothing on the host.
- A per-language query over an untagged language returns nothing.

## Evidence it publishes

- The local and cloud batches with their per-language breakdown, the suite snapshot, and the coverage entry.
- One MoE and one tiny dense roster entry run over the same items at one suite version and published side by side, each citing its roster entry; or, for an entry that cannot run this suite, a recorded refusal naming the entry and why.

## Cancellation

n/a: not cancelled.
