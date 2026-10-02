# Live gate run: qwen3-0.6b-q8 through the candidate gate

The shipped `qwen3-0.6b-q8` entry, declared as a candidate and taken through
all seven steps of `wave-local-ai-v2-candidate-gate` on the dev machine, under
the pinned build. **Pass**, exit `0`. Nothing was downloaded, and no results
store or roster file was written by the run.

## What matched the shipped entry

| Field | Gate read | Shipped entry / prior evidence | Match |
| ----- | --------- | ------------------------------ | ----- |
| Revision (hub `sha`) | `23749fefcc72300e3a2ad315e1317431b06b590a` <!-- pragma: allowlist secret --> | `models.json` `revision` | yes |
| sha256, off the bytes on disk | `9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031` <!-- pragma: allowlist secret --> | `models.json` `sha256` | yes |
| Bytes | `639446688` | `docs/setup.md` 3.1 size column, and the hub listing | yes |
| Chat template hash (`/props`) | `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361` <!-- pragma: allowlist secret --> | thinking-switch story `evidence/live-verification.md` | yes |
| Architecture (GGUF) | `qwen3`, expert count `0` => `dense` | `architecture.kind: dense`, `expert_count: 0` | yes |
| Total parameters (tensor-dim sum) | `596049920` | not in the roster yet (size-class story) | n/a |
| Build (`build_probe`) | `b10537` | pinned build | yes |
| Thinking control | renders differ (`<think>\n\n</think>\n\n` appended with the control) | same two renders as the thinking-switch evidence | yes |
| Licence id (hub `cardData.license`) | `apache-2.0` | `models.json` `Apache-2.0` | same licence, different casing (the hub's id, not the SPDX spelling) |
| Licence clause scan | no sentence forbidding published benchmarks in `LICENSE` | n/a | pass |

The pass record is kept, verbatim from the run's own records file, at
`evidence/candidate-record-pass.jsonl` in this task folder. It is not in the
committed store (`aidd_docs/roster/candidate-records.jsonl`): local-run results
stay out of committed stores under this run's rules.

## How it was run

A scratch script outside the repo, from the worktree root:

```sh
LLAMA_SERVER_PATH=C:/Users/Anael/llama_cpp/llama-b10537-bin-win-cuda-12.4-x64/llama-server.exe \
SLM_MODELS_DIR=D:/ia/models \
QUALITY_PROVIDERS=local \
QUALITY_RESULTS_PATH=<scratch>/unused-quality.jsonl \
RUNTIME_RESULTS_PATH=<scratch>/unused-runtime.jsonl \
uv run python -X utf8 live_gate.py <scratch>
```

- The declaration was built from the shipped entry (`repo_file`
  `Qwen3-0.6B-Q8_0.gguf`, everything else copied from `models.json`) and
  written to the scratch folder.
- `candidate_gate.main(["--candidate", ..., "--records", "<scratch>/candidate-records.jsonl"], seams=...)`
  ran with `gate.default_seams()` except the download seam, which was
  replaced by a no-op that only asserts the file is already at
  `D:\ia\models\Qwen3-0.6B\Qwen3-0.6B-Q8_0.gguf`. It was called once. The
  hash, size and GGUF metadata were then read off those bytes by the gate's
  own step 4.
- The hub listing and the `LICENSE` text were read live over the network
  (read-only, unauthenticated).
- The disk check, the build probe, the port check and the one `llama-server`
  load were the real ones. The results paths pointed into the scratch folder
  as a guard; nothing wrote to them.
