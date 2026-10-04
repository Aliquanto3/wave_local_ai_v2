# Four-billion class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`,
nothing listening on 8080, D: free space read and the run stopped if the download
would leave under 20 GB (logged at the top of each log). After each step: GPU 0 MiB,
no `llama-server` left (each command started and stopped its own server).

## Stage A: the gate

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, Granite 3.1 3B-A800M (MoE) | `wave-local-ai-v2-candidate-gate --candidate candidates/granite-3.1-3b-a800m-instruct-q4km.json` | exit 0, `passed`; 2,016,888,384 bytes downloaded, sha256 `48e0edcd...82b3` (the spike's), `granitemoe`, 40 experts (8 used), 3,298,793,472 params; build `b10537`; template hash `22da3019...d800`; `none` verified | `gate-granite-3.1-3b-a800m-instruct-q4km.log` |

D: had 72,285,470,720 bytes free before the download and 70,268,579,840 after;
2,016,888,384 bytes downloaded in all.

Not gated: Ministral 3 3B Instruct 2512, Phi-4-mini-instruct and Phi-tiny-MoE-instruct
(declarations in `candidates/`): Granite 3.1 3B-A800M is non-Qwen and MoE at once, so
its pass ends the search (owner answers Q127 (a), Q128 (a)), subject to both suites
completing in stage B.

Spike resolution lines: `granitemoe` already closed at `~2B`, loaded again here (pass
record of `granite-3.1-3b-a800m-instruct-q4km`); `mistral3`, `phi3`, `phimoe` not
reached: class stopped at `granite-3.1-3b-a800m-instruct-q4km`.

Launch: the gate's one load ran the declared block (`-ngl 99`, `-c 32768`, no
`--n-cpu-moe`, `-t 8`) and the server came up, so the declared offload fits.

Composition check after the entry: `composition-check.txt` (no `~4B` failure; one
failure left, in `~8B-and-up`).

No `src/` change.
