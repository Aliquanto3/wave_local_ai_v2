---
objective: "Every runtime and quality row cites a stored, content-addressed hardware fiche by hash instead of flattening it inline, a validator can prove an edited or missing fiche invalidates the rows citing it, and a re-run against a named reference receives a stored reproduced / not_reproduced / not_comparable verdict."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Fiche hash, invalidation validator, and reproduction verdict

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship stories 14, 15, 16 of `every-published-row-explains-and-reproduces-itself` as one increment: the fiche becomes a stored, hash-cited artifact; a named command proves invalidation; a re-run gets a stored three-state verdict. |
| **Source** | `aidd_docs/backlog/stories/the-fiche-carries-a-normalised-hash-every-row-cites.md` (14), `aidd_docs/backlog/stories/editing-a-fiche-invalidates-the-rows-that-cite-it.md` (15), `aidd_docs/backlog/stories/a-re-run-receives-a-three-state-reproduction-verdict.md` (16); PRD Methodology 8 and 14; epic `every-published-row-explains-and-reproduces-itself.md` |

## Phases

| #   | Phase        | File                         |
| --- | ------------ | ---------------------------- |
| 1   | Fiche projection, hash, registry, rows cite the hash | [`phase-1.md`](./phase-1.md) |
| 2   | Invalidation validator | [`phase-2.md`](./phase-2.md) |
| 3   | Three-state verdict, both CLIs attach it | [`phase-3.md`](./phase-3.md) |
| 4   | Live run, evidence, docs and memory | [`phase-4.md`](./phase-4.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| PRD Methodology 8 (`aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md:43`) | Reproduction verdict wording, the four verdict-blocking fields, reported deltas and machine state |
| PRD Methodology 14 (same file, line 49) | Fiche fields, normalised-projection hash, flags excluded from the hashed content, invalidation on edit |
| Epic decisions table, criterion 8 and 14 rows | Resolves the tension PRD 8 leaves open (see Decisions below): the epic explicitly separates "verdict-blocking" fields from the fiche's full identity hash |
| `aidd_docs/roster/models.json` | `sha256` and `validated_host.fiche_summary` already exist per entry; `fiche_summary` is unrelated free text, no naming collision with the new hash mechanism |
| `.gitignore` | `aidd_docs/results/*.jsonl` is ignored, `!aidd_docs/results/*-reference.jsonl` re-included; the fiche registry directory is a new path, not matched by either pattern, so it is tracked by default — confirmed by `git status` after a scratch write in phase 1 |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| The fiche's SHA-256 identity (criterion 14) hashes cpu, ram_gb, gpu_name, gpu_driver_version, os, cuda_ceiling, llama_cpp_build, quant, roster_entry_id and the roster entry's sha256 — never the raw flag list, never a filesystem path, host or port. | Literal story 14 text: "the raw flag list stays on the fiche as evidence and is not part of the hashed projection." Excluding flags from the hash also removes the one thing that historically carried the moving `SLM_MODELS_DIR` path, without needing to scrub paths inside the flag list itself. |
| Reference-row matching for the runtime verdict (criterion 8) is a field-by-field comparison of exactly the four verdict-blocking fields — `llama_cpp_build`, `quant`, `gpu_name`, and the raw `flags` list — resolved from each row's own stored fiche via `fiche_registry`. It is **not** a full `fiche_hash` equality check. | PRD Methodology 8 says both "shares the re-run's normalised fiche hash" and, two sentences later, "CPU, RAM, driver and OS ... never block a comparison" — the fiche hash (criterion 14) is sensitive to CPU/RAM/driver/OS, so a literal hash-equality match would contradict the second sentence. The epic's own decision row for criterion 8 resolves this by naming the blocking fields explicitly (build, quant, flags, GPU), separate from the fiche's identity hash, and the user's own instructions restate that same narrower set. Recorded here because it overrides a literal PRD sentence and a later story/PRD conflict here should point back to this line, not rediscover it. |
| One fiche per quality-CLI invocation, cited by both the local-provider row and the cloud-provider row it also writes in that run. | `quality_cli.py` already reuses the single local `roster_entry` and its `roster_version` across the cloud row (`_score_and_write`'s `roster_entry=roster_entry` call for the mistral batch) — the run-specific fiche (built from the one local launch that invocation performs) follows the same established reuse pattern rather than inventing a cloud-only fiche shape or leaving cloud rows with a null `fiche_hash`, which the story text does not carve out as an exception ("every runtime and quality row cites its fiche by hash"). |
| The validator (criterion 14 / story 15) takes one or more results-file paths as CLI arguments and defaults to the two live settings-configured paths (`results_path`, `quality_results_path`) when none are given; it never special-cases the `*-reference.jsonl` files. | Story 15: "reads published artifacts only ... recomputes nothing about the run." A results file is a results file regardless of whether it is curated evidence or a live per-machine store; phase 4's live check simply passes the reference paths explicitly. |
| A row whose `schema_version` predates `row_contract.FICHE_HASH_SCHEMA_VERSION` (fixed at "3", the version this increment introduced) is reported under a third, non-fatal `legacy` class — never `missing` — even when it carries no `fiche_hash` at all; a row at or after that version with no `fiche_hash` stays `missing` (fatal). | Discovered during phase 4: every pre-existing row (the live store's four old rows, both reference files' rows) predates the fiche-hash contract entirely, so the plain two-class design made the validator exit 1 against exactly the artifacts phase 4 expected to pass cleanly. Reading the threshold from `row_contract` rather than hardcoding it in the validator keeps the two modules' contracts from silently drifting apart; the version is fixed at "3" forever regardless of later `SCHEMA_VERSION` bumps, so a future schema change doesn't retroactively reclassify these rows. |
| The verdict block is a required field on both row kinds, always present — `not_comparable` with a named reason when no reference is configured or none matches — never an optional/absent key. | Story 16: "a run with no reference records `not_comparable` and still writes." An optional field would let a reader mistake "absent because unconfigured" for "absent because the row predates the field," the exact ambiguity `schema_version` already exists to prevent (epic, "row contract" decision row). |
| The validator names *which* fiche field changed by comparing the current registry file against `git show HEAD:<path>` — the last committed version — rather than by keeping a second stored copy or reconstructing anything about the run. | A write-once content-addressed store has no independent original to diff against once its one file is edited in place; the registry directory is git-tracked by design (phase 1 Resources), so the committed blob *is* the "published artifact" story 15 restricts the validator to reading. Degrades to a named `"unavailable"` reason outside a git repository rather than guessing. |

