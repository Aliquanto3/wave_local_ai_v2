# Top class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`,
nothing listening on 8080, D: free space read and the run stopped if the download
would leave under 20 GB (logged at the top of each log). After each step: GPU 0 MiB,
no `llama-server` left (each command started and stopped its own server).

## Stage A: the gate

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, Gemma 4 12B it (dense) | `wave-local-ai-v2-candidate-gate --candidate candidates/gemma-4-12b-it-iq4xs.json` | exit 0, `passed`; 6,375,734,080 bytes downloaded, sha256 `b0037d0e...6774` (the spike's), `gemma4`, no expert count (dense), 11,907,350,576 params; build `b10537`; template hash `aa3185df...d61b`; the thinking switch verified (two different renders) | `gate-gemma-4-12b-it-iq4xs.log` |

D: had 70,268,579,840 bytes free before the download and 63,892,844,544 after;
6,375,735,296 bytes fewer, within 1,216 bytes of the file's 6,375,734,080.

Not gated: Gemma 4 26B-A4B it (declaration in `candidates/`, `n_cpu_moe` 28 of its 30
layers, the flagship's ratio). Gemma 4 12B is non-Qwen and dense and the flagship is
the class's MoE, so its pass ends the search (owner answers Q127 (a), Q129 (a)),
subject to both suites completing in stage B. The epic's dependency "whether the tower
holds a Gemma-4-class 26B-A4B MoE at a usable quant" stays untested.

Spike resolution line: `gemma4` loaded, closed by the pass record of
`gemma-4-12b-it-iq4xs` (build, template hash and verified thinking control in its
`observed` block).

Launch, declared against launched: the gate's one load ran the declared block
(`-ngl 99`, `-c 32768`, `-fa on`, `-t 8`, no `--n-cpu-moe`, `--load-mode auto`) and
the server came up and answered, so no load refusal occurred and no stepped-down
`-ngl` was re-declared: the launched value equals the declared one. Dedicated GPU
memory, sampled every 2 s (`gate-gemma-4-12b-it-iq4xs.vram.csv`), went 0 -> 5,931 ->
5,959 MiB of 6,144 while the server was up. The weights alone are 6.38 GB, so part of
the model sat outside dedicated VRAM, in the shared system memory the Windows driver
falls back to (inferred from the sizes; nvidia-smi reports dedicated memory only).
`--fit` (on by default in b10537) adjusts only unset arguments, and `-ngl` and `-c` are
set, so it did not change them.

Composition check after the entry: `composition-check.txt` (exit 0, `PASS`; no
failure left).

No `src/` change.
