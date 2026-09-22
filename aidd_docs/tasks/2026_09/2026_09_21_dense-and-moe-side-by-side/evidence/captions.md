# Phase 3 evidence: comparison screen over the live store

Captured 2026-09-22 from `wave-local-ai-v2-serve` (HTTPS, loopback) over the
untracked live stores `aidd_docs/results/quality.jsonl` (591 rows, 0
unreadable at schema floor 7) and `aidd_docs/results/runtime.jsonl`, with
`frontend/dist/` rebuilt from commit `d2915c8` plus this phase's working tree.
Screenshots are element captures of each suite section, taken by headless
Chrome at a 1900 px viewport.

Every item is shared across every column in both suites: the live store holds
**no not-compared cell** (task 1.4), so neither screenshot shows one. The
not-compared state is covered by `ComparisonView.test.tsx` and
`test_a_comparisons_columns_each_name_their_own_suite_version` instead.

## `phase-3-comparison-classification.png`

Version caveat shown: `columns at suite_version "2", "3" -- not unified, shown as captured.`

| Column | Provider / model | suite_version | run_id | fiche (prefix) | Suite accuracy | README |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen3-0.6b-q8` | local / Qwen3-0.6B | 3 | `e716ce86ddc7448b8583e0d24387649a` | `f804bee0d215` | 0.45 | 0.45 (chat-templated table) |
| `qwen3-1.7b-q8` | local / Qwen3-1.7B | 3 | `91ee67b104db49f89ef73c75dd0f9bd9` | `067530efd694` | 0.60 | 0.60 |
| `qwen3-4b-q4km` | local / Qwen3-4B | 3 | `ebce4da610a04167827ef911d4a60e82` | `dfd5a5eaa441` | 0.70 | 0.70 |
| `qwen3.6-35b-a3b-ud-iq4xs` | google / gemini-3.5-flash-lite | 2 | `1f3c94b9f253439b99b3a9c6d05f69c3` | `b9d1af56db2b` | 1.00 | 1.00 (`1f3c94b9...`) |
| `qwen3.6-35b-a3b-ud-iq4xs` | local / Qwen3.6-35B-A3B | 3 | `d4d2e0d5d9a94aa98d7c2eb1569fd60c` | `b9d1af56db2b` | 1.00 | 1.00 |
| `qwen3.6-35b-a3b-ud-iq4xs` | mistral / mistral-small-2603 | 2 | `d20afbda710c40378e6ad5ca8d9b6558` | `b9d1af56db2b` | 0.90 | 0.90 (`d20afbda...`, reference table) |

## `phase-3-comparison-translation.png`

Version caveat shown: `columns at suite_version "1", "2" -- not unified, shown as captured.`

| Column | Provider / model | suite_version | run_id | fiche (prefix) | Suite score (chrF) | README |
| --- | --- | --- | --- | --- | --- | --- |
| `qwen3-0.6b-q8` | local / Qwen3-0.6B | 2 | `108fc07ecd6f43d685dd491119f601fa` | `f804bee0d215` | 0.5121 | 0.5121 (chat-templated table) |
| `qwen3-1.7b-q8` | local / Qwen3-1.7B | 2 | `41ac932af26a4736ad55f02a13c896f2` | `067530efd694` | 0.7107 | 0.7107 |
| `qwen3-4b-q4km` | local / Qwen3-4B | 2 | `42bd9d8b0fb34f459f04043764360c80` | `dfd5a5eaa441` | 0.7252 | 0.7252 |
| `qwen3.6-35b-a3b-ud-iq4xs` | google / gemini-3.5-flash-lite | 1 | `696b53768b97499898564d3f4ae3deea` | `b9d1af56db2b` | 0.8400 | 0.8400 |
| `qwen3.6-35b-a3b-ud-iq4xs` | local / Qwen3.6-35B-A3B | 2 | `79e95271e6714f7d8ba78da787e35698` | `b9d1af56db2b` | 0.8002 | 0.8002 |

The gemini translation column is backed by its later run `696b5376...`, the
latest `captured_at` for that model on that suite; the README's chat-templated
table cites the earlier `80803767...`. Both score 0.8400, and every item cell
on screen reads `reproduced vs 80803767...`, which is the README's own
two-run finding.

## Observed, not fixed here

- Per-language cells render `indicative ()` with empty parentheses:
  `ComparisonView.tsx` passes `reasons={[]}` to `IndicativeLabel`. Logged to
  `aidd_docs/backlog/tech-debt.md`.
