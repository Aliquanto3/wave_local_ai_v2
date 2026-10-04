# Two-billion class: gate and suite runs (2026-10-04, laptop-mobile-gpu)

Build: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`
(`b10537`), models in `D:\ia\models`. Before each step: GPU 0 MiB, no `llama-server`,
nothing listening on 8080, D: free space read and the run stopped if the download
would leave under 20 GB (logged at the top of each log). After each step: GPU 0 MiB,
no `llama-server` left (each command started and stopped its own server).

## Stage A: the gate

| Step | Command | Outcome | Log |
| --- | --- | --- | --- |
| Gate, LFM2.5-1.2B-Instruct | `wave-local-ai-v2-candidate-gate --candidate candidates/lfm2.5-1.2b-instruct-q8.json` | exit 0, `passed`; 1,246,253,888 bytes downloaded, sha256 `f6b981dc...d26a` (the spike's), `lfm2`, dense, 1,170,340,608 params; build `b10537`; template hash `f05bf4b9...8176`; `none` verified | `gate-lfm2.5-1.2b-instruct-q8.log` |
| Gate, Granite 3.1 1B-A400M (MoE) | `wave-local-ai-v2-candidate-gate --candidate candidates/granite-3.1-1b-a400m-instruct-q8.json` | exit 0, `passed`; 1,422,239,776 bytes downloaded, sha256 `72430235...7650` (the spike's), `granitemoe`, 32 experts, 1,334,628,352 params; build `b10537`; template hash `22da3019...d800`; `none` verified | `gate-granite-3.1-1b-a400m-instruct-q8.log` |

D: had 74,953,969,664 bytes free before the first download and 73,707,712,512 before
the second; 2,668,493,664 bytes downloaded in all.

Not gated: Granite 4.0 H 1B and Granite 4.0 1B (declarations in `candidates/`): once
LFM2.5-1.2B-Instruct, a non-Qwen family, passed, further dense candidates are skipped
and only the MoE candidate is still tried (owner answer Q127 (a)).

Spike resolution lines: `granitemoe` loaded (pass record of
`granite-3.1-1b-a400m-instruct-q8`); `lfm2` loaded (pass record of
`lfm2.5-1.2b-instruct-q8`); `granitehybrid` closed at `~0.5B`; `granite` not reached:
class stopped at `granite-3.1-1b-a400m-instruct-q8`.

Composition check after the entries: `composition-check.txt` (no `~2B` failure; three
failures in `~4B` and `~8B-and-up`).

No `src/` change.

## Stage B: the suites

Pending: both suites per entry from the commit that adds the entries.
