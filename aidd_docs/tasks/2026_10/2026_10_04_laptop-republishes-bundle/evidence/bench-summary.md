# Bench session summary (2026-10-04, laptop-mobile-gpu)

Machine state before the session: `machine-state.txt` (AC power, power plan "Turbo",
GPU 0 MiB used at 40 C, no llama-server, 19.3 GB of 32.9 GB RAM free, total CPU load
6%). No operator was present: the quiet window is asserted from that capture under the
owner's unattended-run instruction (orchestrator decision D8), not confirmed.

Each step ran from the fresh clone, one at a time; before each, no `llama-server`
process and GPU memory at 0 MiB (logged at the top of each step's output); after each,
no `llama-server` was left to stop. Logs: `logs/<step>.log`.

| Step | `run_id` | Reference file | Verdict |
| --- | --- | --- | --- |
| flagship runtime 1, gpu | `78e5d7ef9a6f4743b5c4985d9a79b590` | empty | `not_comparable` |
| flagship runtime 2, gpu | `12d19a0cdede4fda9512c57885d826d2` | run 1's row | `reproduced`, gen delta 0.39% |
| quality 1, local + mistral | `acb6e89475f740508b3e07b6707d2930` | empty | `not_comparable` (both) |
| quality 2, local + mistral | `68ac4f21b11d4e4fad5675bba7fb8836` | run 1's 40 rows | local `reproduced` (identical), mistral `reproduced` (divergence 0.05, `account-de-01`) |
| Qwen3-0.6B runtime 1, gpu | `49d99f73e09e4291be3ca78bcd324082` | empty | `not_comparable` |
| Qwen3-0.6B runtime 2, gpu | `a05834da5c31407db755bdd6d0223387` | gpu run 1's row | `reproduced`, gen delta 2.15% |
| Qwen3-0.6B runtime 1, cpu_only | `e4a0ef9fb77b474b9b81c0f729d22a5a` | empty | `not_comparable` |
| Qwen3-0.6B runtime 2, cpu_only | `1212b9b15c68476ea95a449eeeb8137d` | cpu_only run 1's row | `reproduced`, gen delta 0.35% |

Paid calls: 40 Mistral chat completions (2 batches x 20 items, 0 retries), plus one
model-catalog pre-flight per batch. No Google call (`google skipped: not enabled in
QUALITY_PROVIDERS`), no judge call.
