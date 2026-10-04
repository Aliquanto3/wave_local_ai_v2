---
objective: "A challenge reads as sustained exactly when its resolving evidence is null, empty or whitespace only, with no field that could disagree; every sustained challenge names an existing defect or spike under `aidd_docs/backlog/` that carries the record's client id and a session id of its correction chain, and the record check refuses every other case naming the session and the challenge, so the committed-record test fails CI on a pushed record whose item is missing, renamed or deleted."
status: implemented
---

# Plan: A challenge no named evidence resolved is sustained and points at its follow-up item

## Overview

| Field      | Value |
| ---------- | ----- |
| **Goal**   | The sustained derivation and the follow-up refusals in `client_sessions.py`, their tests, and the follow-up step of `docs/client-session-record.md` |
| **Source** | `aidd_docs/backlog/stories/a-challenge-no-named-evidence-resolved-is-sustained-and-points-at-its-follow-up-item.md` (credible epic order 2, owner decision D5; builds on order 1 at `e1e768f`) |

## Phases

| #   | Phase | File |
| --- | ----- | ---- |
| 1   | The derivation, the follow-up refusals and the procedure step | [`phase-1.md`](./phase-1.md) |

## Decisions

| Decision | Why |
| -------- | --- |
| `resolving_evidence: null` is now accepted and reads as sustained, reversing order 1's "`null` is refused". The key itself stays required: left out is still refused. | The acceptance names null, empty and whitespace only as the three sustained forms; a required key keeps "the consultant forgot the field" apart from "nothing resolved it". |
| `is_sustained(challenge)` is the only place the state is decided; the read-back line prints the count of sustained challenges per record. | Sustained is derived, never typed: one function, no stored field. |
| A `follow_up` given on any challenge (sustained or resolved) is validated the same way: path shape, folder, existence, frontmatter `type`, both ids. Sustained additionally requires one. | A resolved challenge "may link an item, which the check accepts": a broken link is still a broken link; validating it never turns the challenge sustained. |
| Path rules: a string, no backslash, not absolute (POSIX root or Windows drive), no `..` segment, under `aidd_docs/backlog/defects/` (frontmatter `type: defect`) or `aidd_docs/backlog/spikes/` (`type: spike`). | Acceptance wording; the item kind follows its folder so the two cannot disagree. |
| Frontmatter: the block between a leading `---` line and the next `---` line, read line by line for `type:` with surrounding quotes stripped. | Standard library only; the project has no YAML parser at runtime. |
| The id requirement: the item text contains the record's `client_id` and the `session_id` of at least one record of the citing record's correction chain (records linked by `corrects`, in either direction). Checked after the whole file is read, so a chain resolves regardless of which line cites. | Q61/Q62 and order 1's correction rule; "an item containing only the session id of the record a later correction replaced still passes". |
| Item files are read through a `read_item(path) -> str | None` callable passed to `check_records` (default: no item exists); `check_file` reads them from the changelog's repository, like `git_commit_exists`. | Same injection shape as the commit predicate; tests plant items in a temporary repository. |
| A record with a follow-up refusal leaves the read-back list, like any refused record. | One meaning for "accepted". |
| The procedure's worked example stays a resolved challenge; the sustained case is described in prose. | A sustained example would need a real backlog item to point at, and the example is checked by a test. |
| Skills `aidd-dev:01-plan` / `02-implement` / `03-assert` were applied as their layout and gates (plan, phase file, full gate run) rather than invoked interactively. | Orchestrator instruction for this run: code only, small pieces, fast. |
