# Run notes: LLMLingua-2 compressor, placement (a) CPU, live measurement

Spike: `aidd_docs/backlog/spikes/which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement.md` (Follow-up runbook, read from the worktree `C:\Users\Anael\dev\wave_local_ai_v2-night`, branch `feat/night-run-2026-10-02` @ `25fec93`).
Owner choice: Q115 (a), CPU in the same phase. Run unattended on 2026-10-04 (local time, +02:00).

STATUS: COMPLETE (all four checksum checks matched; both checkpoints run beside both subjects).

## Timeline

| Time (+02:00) | Step | Outcome |
| --- | --- | --- |
| 00:25:28 | Pre-flight | GPU RTX 3060 Laptop, driver 572.70, 0 MiB used, no compute apps; port 8080 free; no `llama-server` or Ollama process; C: 183 GB free, D: 72.9 GB free; uv 0.11.7 |
| 00:25:34 | 1. `uv venv %TEMP%\llmlingua-env --python 3.12` | CPython 3.12.13 |
| 00:25:45-00:26:00 | 1. `uv pip install` pinned set | exit 0 (`step1-install.log`) |
| 00:26 | 1. freeze + installed size | `step1-pip-freeze.txt`, 610 MB (`step1-installed-size.txt`) |
| 00:26:15-00:27:14 | 1. `hf download` both repos by revision | xlmr exit 0 at 00:26:54, mbert exit 0 at 00:27:13 (`step1-download.log`) |
| 00:27 | 1. checksums | 4/4 match (`step1-checksums.txt`) |
| 00:25 | 2. script saved to `%TEMP%\measure_compressor.py` | byte copy of spike lines 110-219, sha256 `86c39a35...028b2f`; copy in `measure_compressor.py` |
| 00:27:59-00:30:55 | 3-4. subject `qwen3-0.6b-q8` | server PID 4396 started, ready 00:28:04, xlmr 130.5 s wall, mbert 36.2 s wall, PID 4396 stopped 00:30:51 |
| 00:31:06-00:34:13 | 3-4. subject flagship `qwen3.6-35b-a3b-ud-iq4xs` | server PID 9520 started, ready 00:31:29, xlmr 118.9 s wall, mbert 39.1 s wall, PID 9520 stopped 00:34:09 |

## Pins (`uv pip freeze`, Python 3.12.13)

accelerate==1.15.0, certifi==2026.7.22, charset-normalizer==3.5.2, click==8.5.0, cloudpickle==3.1.2, colorama==0.4.6, defusedxml==0.7.1, filelock==4.0.9, fsspec==2026.9.0, huggingface-hub==0.36.2, idna==3.20, jinja2==3.1.6, joblib==1.6.0, llmlingua==0.2.2, markupsafe==3.0.4, mpmath==1.3.0, networkx==3.7, nltk==3.10.3, numpy==2.5.3, packaging==26.3, psutil==7.2.2, pyyaml==6.0.3, regex==2026.9.29, requests==2.34.2, safetensors==0.8.0, setuptools==84.0.0, sympy==1.14.0, tiktoken==0.14.0, tokenizers==0.22.2, torch==2.14.1, tqdm==4.70.1, transformers==4.57.6, typing-extensions==4.16.0, urllib3==2.8.0

Installed size of the venv: 610 MB. `torch.__version__` = `2.14.1+cpu`, `torch.version.cuda` = None, `cuda_available False` (printed by every run).

## Checksums (expected vs actual)

| File | Check | Expected | Actual | Match |
| --- | --- | --- | --- | --- |
| xlmr `model.safetensors` | sha256 | A33A153B2493BFF6BE06AF6921E69DE9C0D0BB6FF06FE5BBB68670BA8D980AE2 | A33A153B2493BFF6BE06AF6921E69DE9C0D0BB6FF06FE5BBB68670BA8D980AE2 | yes |
| mbert `model.safetensors` | sha256 | 22B9ECDE52FEC5C97E8C54A293BE768727DF95A81C6C8DCCB03F262A50C58324 | 22B9ECDE52FEC5C97E8C54A293BE768727DF95A81C6C8DCCB03F262A50C58324 | yes |
| xlmr `tokenizer.json` | sha256 | F59925FCB90C92B894CB93E51BB9B4A6105C5C249FE54CE1C704420AC39B81AF | F59925FCB90C92B894CB93E51BB9B4A6105C5C249FE54CE1C704420AC39B81AF | yes |
| mbert `tokenizer.json` | git hash-object --no-filters | 21f54a4b56685f29358f3a8de1f5b8d827357d07 | 21f54a4b56685f29358f3a8de1f5b8d827357d07 | yes |
| `cl100k_base` cache (`D:\ia\models\tiktoken-cache\9b5ad71b...`) | sha256 (extra, from the spike's Investigation; tiktoken also checks it itself) | 223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7 | 223921b76ee99bde995b7ff738513eef100fb51d18c93597a113bcffe865b2a7 | yes |
| repo totals | bytes | xlmr 2,252,919,420; mbert 713,310,011 | xlmr 2,252,919,420; mbert 713,310,011 | yes |

## Results (from `compressor-*.json`, `step4-*.stdout.txt`, derived in `derived-summary.txt`)

Per-item seconds = the `compress_prompt_llmlingua2` call alone (`time.perf_counter`), 82 calls per run (41 items x 2 segments).

| Checkpoint | Subject | load_s | peak RSS (peak_wset) | VRAM MiB before -> after | median s (all) | max s (all) |
| --- | --- | --- | --- | --- | --- | --- |
| XLM-R large (reference) | qwen3-0.6b-q8 | 7.1 | 1933 MB | 4377 -> 4377 | 1.224 | 1.625 |
| XLM-R large (reference) | flagship | 1.5 | 1903 MB | 4377 -> 4377 | 1.290 | 3.038 (first call, billing-01, warm-up) |
| mBERT (alternative) | qwen3-0.6b-q8 | 0.4 | 784 MB | 4377 -> 4377 | 0.355 | 0.424 |
| mBERT (alternative) | flagship | 0.5 | 784 MB | 4377 -> 4377 | 0.376 | 0.794 |

Host memory beside the flagship: server working set 14,265 MB, private 19,133 MB; host available 4.4 GB of 31.4 GB at server ready (before the compressor started). Before any server: 15.8 GB available. The XLM-R process peaked at 1.9 GB, inside that 4.4 GB; no failure or slowdown beyond the first-call warm-up was observed, but paging was not instrumented.

Per-language medians, reference checkpoint (XLM-R), both suites pooled (script's printed lines; n = en 17, fr 12, de 12; unchanged = 0 everywhere):

| Subject | Segment | EN s med/max, ratio | FR s med/max, ratio | DE s med/max, ratio |
| --- | --- | --- | --- | --- |
| qwen3-0.6b-q8 | whole_prompt | 1.234/1.535, 1.65 | 1.199/1.324, 1.62 | 1.187/1.289, 1.55 |
| qwen3-0.6b-q8 | payload_only | 1.258/1.625, 1.17 | 1.194/1.275, 1.23 | 1.219/1.338, 1.18 |
| flagship | whole_prompt | 1.300/3.038, 1.62 | 1.287/1.374, 1.63 | 1.325/1.438, 1.56 |
| flagship | payload_only | 1.301/1.357, 1.17 | 1.276/1.370, 1.22 | 1.271/1.410, 1.15 |

(Flagship rows above are from `derived-summary.txt` "both" lines; the script's own printout uses the upper median `sec[len//2]`, so its values can differ in the third decimal from the statistics median.) mBERT: whole_prompt ratio 1.60-1.72, payload_only 1.17-1.26, unchanged 0, per-suite split in `derived-summary.txt`.

### Examples (reference checkpoint, first classification item per language, identical beside both subjects)

- EN whole_prompt: `Classify support message categories: account, billing, technical. Reply single category word, nothing else.\n Message charged twice subscription this month, refund one?` (label `other` dropped from the instruction)
- FR whole_prompt: `... categories: account, billing, other technical. ...\n Message prélèvement automatique mois correspond montant indiqué devis, vérifier ?` (negation `ne ... pas` dropped: meaning inverted)
- FR payload_only: `... \n\nprélèvement automatique mois ne correspond pas montant devis, vérifier ?` (negation kept)
- DE whole_prompt: `Classify support message categories account, billing, technical. ...\n Message letzten Rechnung fehlt vereinbarte Rabatt Vertrag.` (label `other` dropped)
- DE payload_only: `...\n\nletzten Rechnung fehlt vereinbarte Rabatt Vertrag.`
- Translation examples (EN/FR/DE, both segments): `derived-summary.txt`.

Derived count (summarize.py): with XLM-R on whole_prompt, the label word `other` is missing from the compressed instruction in 14 of 20 classification items (both subjects); mBERT drops no label word.

## Deviations

1. Worktree instead of main repo root: cwd for install and runs = `C:\Users\Anael\dev\wave_local_ai_v2-night` (caller's instruction). The spike file in the worktree differs from the main repo's copy (the main repo lacks the Follow-up runbook); the worktree copy was used. Suite JSONs read from the worktree.
2. `LLAMA_SERVER_PATH` and `SLM_MODELS_DIR` set explicitly in the harness (values: `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`, `D:\ia\models`); the repo `.env` was not read. The runbook's commands use literal paths anyway, which match these values.
3. Steps 3-4 run by a harness (`run_subject.ps1`) instead of two terminals: `Start-Process -PassThru` with stdout/stderr redirected to `step3-<subject>-server.*.log`, the runbook's `/health` loop (with a 10 min deadline), and the server stopped by its own PID in `finally` (`Stop-Process -Id <PID>`) instead of the runbook's `Get-Process llama-server | Stop-Process -Force`, which would kill any llama-server.
4. Subject order: `qwen3-0.6b-q8` first, then the flagship (runbook lists the flagship first), because host available memory was 15.8 GB before any server against the flagship's measured 15.2 GB RSS; running the light subject first secured one complete subject. No effect on the measurement.
5. Outputs: JSONs written to `%TEMP%\compressor-<xlmr|mbert>-<subject>.json` as the runbook says (`<subject>` = `qwen3-0.6b-q8`, `flagship`), then copied here. Script stdout+stderr captured to `step4-<ckpt>-<subject>.stdout.txt`.
6. Additions (no change to the measurement): `nvidia-smi` and host-memory snapshots in the harness log; an extra sha256 check of the `cl100k_base` cache file; `summarize.py` derives per-suite stats and translation examples from the JSONs.
No runbook command needed a correction; the script ran unmodified. Only warning: transformers `torch_dtype is deprecated! Use dtype instead!` (from llmlingua 0.2.2 on transformers 4.57.6; harmless).

## Processes started / stopped

| PID | Process | Started | Stopped | How |
| --- | --- | --- | --- | --- |
| 4396 | llama-server (qwen3-0.6b-q8) | 00:28:00 | 00:30:51 | Stop-Process -Id 4396, exited=True |
| 9520 | llama-server (flagship) | 00:31:07 | 00:34:09 | Stop-Process -Id 9520, exited=True |

Python measurement processes exited normally (exit 0, 4 runs). Ollama (installed app and `D:\ia\ollama-v0.35.1`) not touched; no Ollama process was running.

## End state

GPU memory.used 0 MiB, no compute apps; port 8080 not listening; no `llama-server` process. Left on disk: venv `%TEMP%\llmlingua-env` (610 MB), weights under `D:\ia\models\llmlingua-2-*` (2.97 GB), `D:\ia\models\tiktoken-cache` (1.7 MB), `%TEMP%\measure_compressor.py`, `%TEMP%\compressor-*.json`. No repo file edited; nothing committed.

## Caveat

`vram_used_mib` reads 4377 MiB at ready for both subjects (device-wide, NVML via nvidia-smi). The flagship identity is confirmed by its host footprint (14.3 GB working set, 19.1 GB private) and its `--n-cpu-moe 37` load; the equal idle VRAM figures are what nvidia-smi returned. The before/after readings are idle-server readings, not generation peaks.
