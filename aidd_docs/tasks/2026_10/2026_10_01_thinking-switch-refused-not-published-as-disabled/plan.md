---
objective: "Every roster entry declares the thinking control its own template honours (or `none`), the local client sends that declaration instead of a module-wide Qwen spelling, and a batch under `thinking_policy: disabled` proves the control changes the `/apply-template` render before its first item, refusing with no row written when it does not."
status: implemented
---

# Plan: A thinking switch the template ignores is refused, never published as disabled

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Move the thinking control from `local_client`'s module default onto each roster entry, and verify a declared control live (two `/apply-template` renders of one fixed probe message, with and without it) once per batch before any generation |
| **Source** | `aidd_docs/backlog/stories/a-thinking-switch-the-template-ignores-is-refused-never-published-as-disabled.md` |

## Phases

| #   | Phase                                                                 | File                          |
| --- | --------------------------------------------------------------------- | ----------------------------- |
| 1   | The thinking-control declaration on a roster entry, its shape validation, the four shipped entries, and the export column | [`phase-1.md`](./phase-1.md) |
| 2   | The client sends the entry's control; the with-and-without render verification, called once per batch | [`phase-2.md`](./phase-2.md) |
| 3   | One live verification against `qwen3-0.6b-q8` under the pinned build, recorded as task evidence | [`phase-3.md`](./phase-3.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| The declaration is an optional entry field `thinking_control`: either the string `"none"` or a non-empty JSON object of request arguments, merged into both the `/apply-template` and `/v1/chat/completions` bodies. Absent means undeclared. Any other value (an empty object, another string, a list, `null`) is refused at load naming `thinking_control`. | Optional, like `family`, so a constructed entry without it still loads and the "undeclared entry refuses under `disabled`" rule is enforced at run time naming the entry, as the story asks. A raw request-argument object is the shape that lets a non-Qwen template declare a different spelling (`reasoning_effort`, another kwarg) without code change. |
| `roster_version` stays `2`. | The field adds no launch flag and changes no model identity; the four Qwen entries declare exactly the control they already ran under, so every published row's `roster_version` and `roster_entry_id` still resolve to an entry that describes what ran. Same reasoning the `family` field's introduction recorded. |
| The roster table of the CSV export gains one `thinking_control` column rendered as a single JSON cell (`json_cells`), not flattened. | `bundle_export` refuses any roster field its dictionary does not describe, so the export would break otherwise; flattening would produce one column per control spelling (`thinking_control_chat_template_kwargs_enable_thinking`), which changes shape with every new family. Not in the story's file list, but a forced consequence of the roster change. |
| `local_client.thinking_kwargs(policy, entry)` is resolved once per batch, before the server launches; `render_prompt` / `complete_chat` take the resolved `thinking_kwargs` mapping instead of a policy string. | An undeclared entry under `disabled` refuses before any process spawns, naming the entry. One resolution per batch means the rendered and answered requests cannot diverge. The policy-to-arguments mapping stays in `local_client`; only the spelling moves to the roster. |
| `local_client.verify_thinking_control(base_url, entry, *, chat_template, timeout)` is the named, reusable check; it renders the fixed `THINKING_PROBE_MESSAGE` with and without the entry's control and raises `ThinkingControlRefused` (a `LocalRequestError`) naming the entry, the control and the template hash when the two renders are byte-identical. It returns both strings for evidence. | The candidate gate (order 4) reuses it on a candidate entry. Subclassing `LocalRequestError` reuses `quality_cli.main`'s existing one-line stderr exit, and raising before the first item means `_score_and_write` and the cloud batches never run, so no row is written. |
| The verification runs whenever the resolved `thinking_kwargs` is non-empty, i.e. `disabled` with a declared object. `allowed` and a `none` declaration send nothing and skip it. | Exactly the story's three cases. |
| `.secrets.baseline` changes by line numbers only (the six baselined `models.json` revision/sha256 lines moved down). The hook's own rewrite also adds a `should_exclude_file` filter block the committed baseline has never carried; that block is left out. | Inserting `thinking_control` shifts lines the baseline pins; the hook passes on the line-number-only baseline once staged, so the filter block would be unrelated churn. |
| The live evidence is a Markdown file, not JSON. | The model sha256 and template hash it records are 64-hex strings the secrets hook flags; Markdown carries the repo's inline `pragma: allowlist secret` comment, JSON cannot. |
| `judge_probe` resolves and verifies the same way as `quality_cli`. | It also runs a local batch under `disabled` and writes rows carrying `thinking_policy`; with the module default removed it must read the entry's control anyway, and leaving it unverified would keep one path able to publish a policy the model never applied. |
