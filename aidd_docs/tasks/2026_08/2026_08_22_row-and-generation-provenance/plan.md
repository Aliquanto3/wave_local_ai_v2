---
objective: "Every runtime and quality row names the code and tree it was captured from, the endpoint and prompt template that produced its prompt, and — for quality rows — the reason a failed generation scored zero, so a row is falsifiable and reproducible rather than merely plausible."
status: implemented
---

# Plan: Rows name their code, call path and failure reason

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Implement stories order 3, 4, 5 of `every-published-row-explains-and-reproduces-itself` as one increment: code/tree provenance, endpoint/prompt-template provenance, and failed-generation scoring. |
| **Source** | `aidd_docs/backlog/stories/rows-name-the-code-and-the-tree-that-produced-them.md`, `aidd_docs/backlog/stories/rows-name-the-endpoint-and-prompt-template-that-produced-them.md`, `aidd_docs/backlog/stories/a-failed-generation-scores-zero-and-names-its-reason.md`; epic `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md` |

## Overview of the increment

Three stories share one row contract (`row_contract.py`) already gating both writers on required fields; every story only widens `REQUIRED_FIELDS`, never forks it. `mistral_client.complete_prompt` changes its return shape twice across the increment (phase 2 adds `endpoint`, phase 3 adds `finish_reason` and `generated_tokens` to the same structure) rather than being redesigned once — each phase ships and is fully tested on its own.

## Phases

| #   | Phase                                             | File                          |
| --- | -------------------------------------------------- | ----------------------------- |
| 1   | Rows name the code and the tree that produced them | [`phase-1.md`](./phase-1.md)  |
| 2   | Rows name the endpoint and prompt template          | [`phase-2.md`](./phase-2.md)  |
| 3   | A failed generation scores zero and names its reason | [`phase-3.md`](./phase-3.md) |
| 4   | Changelog, codebase map and reference evidence note | [`phase-4.md`](./phase-4.md)  |

## Resources

None consulted beyond the repository itself.

## Decisions

| Decision | Why |
| --- | --- |
| `provenance.py` reuses a single shared git-invocation helper refactored out of `build_info.py` (`_run_git`), rather than a second `shutil.which`/`subprocess.run` pair. | Story 3's explicit constraint: "never a second git resolver." `commit_sha()` becomes a thin wrapper over the same helper so its existing tests keep passing unchanged. |
| `release_version` = the tag `git describe --tags --exact-match HEAD` finds at the package dir, or `f"{build_info.version()}+untagged"` when no tag matches HEAD or git is unavailable. | Makes the PRD's "the fallback is visible in the value rather than silent" concrete and testable: a reader sees `+untagged` in the value itself, never has to cross-reference a separate flag. |
| `tree_dirty` is computed from `git status --porcelain`, true when any line's first two characters are not `??` (untracked files never count). | Matches the acceptance text exactly ("uncommitted changes to **tracked** files") and reuses the same shared git helper. |
| Endpoint field values: local rows always record the literal path `/completion`; cloud rows record `mistral_client.CHAT_COMPLETIONS_URL`, returned by `complete_prompt` itself rather than read off the module constant at the call site. | Story 4's explicit line: "`mistral_client.py` — reports the endpoint it called, so a cloud row is not labelled by the local path's constants." Keeps the value sourced from the module that actually made the call. |
| Today's Mistral chat-completions call is *not* granted `prompt_template_id = "none"`. It gets its own id `mistral-chat-user-message` with a hash of the fixed structural wrapper (`{"role": "user", "content": <prompt>}`), because a chat endpoint structures the request even though no human-authored template varies the text. `none` stays reserved for the raw `/completion` path, which sends the prompt byte-for-byte as the request's `prompt` field. | This is what makes the writer-gate consistency rule ("an endpoint that applies a template can't declare `none`") checkable against *today's* real code, not only a hypothetical future migration — satisfying the story's third test case "the inconsistent pair is rejected" with a real row shape, not a contrived one. |
| The consistency rule (`RAW_ENDPOINTS` vs. `prompt_template_id`) lives in `prompt_provenance.py` as a pure function `is_consistent(endpoint, prompt_template_id) -> bool`; `row_contract.validate_row` calls it after the missing-field check and raises `RowContractError` on `False`. | Keeps the taxonomy's own knowledge (which endpoints are template-free) next to the constants that define it, while the writer gate stays the single place a bad row is refused, per the story's "refused by the writer gate" wording. |
| Failure-reason taxonomy decision lives inside `scoring.score_item`, driven by three caller-supplied facts (`truncated: bool`, `generated_tokens: int`, `max_output_tokens: int`) rather than provider-shape knowledge. `quality_cli.py` alone maps each provider's raw response fields (`stopped_limit`/`tokens_predicted` for local, `finish_reason == "length"`/`usage.completion_tokens` for Mistral) onto those three facts. | Keeps `scoring.py` provider-agnostic and pure (its docstring's "no network, deterministic" claim survives), while still letting `score_item` be the one place that decides the four-way outcome the story requires. `truncated_max_tokens` vs `truncated_context` is exactly `generated_tokens >= max_output_tokens` vs `<`, matching the task's instruction verbatim. |
| `score_suite`'s return type widens from a bare `float` to a `SuiteScore` TypedDict (`accuracy`, `failure_counts`), rather than a second function. | Story 5: "`score_suite` reports the failure counts it aggregated over" — one call already iterates every scored item, so the aggregate belongs there, not in a sibling walk over the same list. |
