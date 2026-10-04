---
objective: "A registered code-generation suite (Python and JavaScript items, EN/FR/DE instructions) is scored 1/0 by running each item's tests inside a no-network, no-mount, capped Docker container, refuses to start where no container runtime or sandbox image is present and never executes generated code on the host, and publishes per-row programming language, sandbox caps and failure reason plus a per-programming-language breakdown that answers nothing for an untagged language."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Generated code is scored by its tests in a sandbox, or not run at all

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | `code_sandbox.py` (Docker runner behind a `SandboxRunner` seam, availability preflight, refusal), a `unit_tests_pass` scoring rule with a per-rule preflight and item check, the `code-generation-python-javascript` suite data + snapshot, the coverage entry, the code block on rows (schema "30"), export docs and the per-language read |
| **Source** | `aidd_docs/backlog/stories/generated-code-is-scored-by-its-tests-in-a-sandbox-or-not-run-at-all.md`; parent epic `no-use-case-is-silently-absent.md`; night-run owner decision D2 (no paid API call) |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Sandbox runner, scoring rule, preflight and refusal | [`phase-1.md`](./phase-1.md) |
| 2   | Suite data, snapshot, coverage entry, row contract "30", export docs, per-language read | [`phase-2.md`](./phase-2.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| Code rows reuse the graded block: `item_score` 1.0/0.0, `suite_score` the pass rate, `score_breakdown` per natural language, `metric_id` `unit_tests_pass`, `reference_output` the item's tests. | No third score shape; the contract's "a named failure is a zero" and "graded never beside exact-match" rules apply unchanged. The tests are what the score was computed against. |
| A conditional code block (`programming_language`, `sandbox`, `programming_language_breakdown`), required only on a row carrying any of it, bumps the schema to "30" (additive; older rows validate unchanged). | Same conditional shape as the graded block ("10"); a bump tells a reader the field set grew. |
| Sandbox = `docker run --rm -i --pull never --network none --read-only --tmpfs /work --user 65534:65534 --cap-drop ALL --security-opt no-new-privileges --memory/--memory-swap --pids-limit --cpus`, payload on stdin, harness passed as `-c`/`-e` argument, wall clock enforced by the host with `docker kill`. Images: `python:3.12-slim` (the published image's base) and `node:22-slim`, overridable by `CODE_SANDBOX_PYTHON_IMAGE`/`CODE_SANDBOX_NODE_IMAGE`. | No host mount, no network, no pull; Docker is the runtime the published image already uses. `--pull never` makes a missing image a refusal, never a download. |
| Refusal: a per-rule preflight (`scoring_rules.PREFLIGHTS`) runs right after `--suite` resolves, before settings or any process: no `docker` on PATH, daemon unreachable, or an image absent locally raises `SandboxUnavailable` with one line. A runner failure mid-batch (exit 125, daemon gone) raises too, aborting rather than scoring. There is no host execution path. | "Refuses to start ... never falls back to executing on the host." |
| Failure taxonomy for code rows adds `compile_error`, `tests_failed`, `timeout` beside `empty`/`truncated_*`/`unparseable` (an opened, never-closed code fence). | Methodology 9: every zero names its reason and stays in the denominator. |
| Code extraction: the first fenced block if any, else the whole completion. | Deterministic, documented; anything else is a scoring choice. |
| `programming_language_breakdown` holds a cell only for languages the suite tags; `read_model.programming_language_score` returns `None` for any other. | Epic success check 11: an untagged language answers nothing, never an average. |
| Suite at `development` level, 24 hand-written items (12 Python, 12 JavaScript; 8 EN/8 FR/8 DE), CC-BY-4.0, contamination_risk false, tolerance 0.10 `fraction_of_items` declared provisional (no cloud re-run observed, D2), mirroring the two shipped suites. | Publication needs 100 items; the story asks for at least 20. |
