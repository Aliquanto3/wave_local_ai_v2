# Setup: from a fresh clone to two results rows

This walk takes a fresh machine to one runtime row (`runtime.jsonl`) and one
set of quality rows (`quality.jsonl`). Steps 1-3 need no GPU and no API key —
they work on a CI-class Linux container. A GPU-bearing machine becomes
mandatory only at step 4.2 (the first `wave-local-ai-v2` run), since that's
where `llama-server` actually loads the model and runs inference.

## 1. Prerequisites and install

- Python 3.12+
- [`uv`](https://docs.astral.sh/uv/) installed
- `git`
- **~18 GB free disk** for the weights and the binary, **32 GB system RAM**, and
  an **NVIDIA GPU with CUDA 12.x support** to reach a runtime row comparable to
  the committed evidence — see
  [the README's hardware section](../README.md#hardware-you-need-before-downloading-anything)
  before starting step 3, which downloads 17.7 GB.

The GPU/CUDA driver is only required to *run* the benchmarks (step 4 onward),
not to reach this point.

```sh
git clone <this-repo-url>
cd wave_local_ai_v2
uv sync
uv run pre-commit install
```

`uv sync` is the only command needed to reach the platform-specific steps
below, and it needs no GPU or API key. `uv run pre-commit install` is the
contributor step: it installs both the commit-stage and push-stage hooks in one
command — see `aidd_docs/memory/coding-assertions.md` for what each stage runs.
Running the benchmarks does not require it.

## 2. Get `llama-server`, build `b10537`

Every command below is pinned to `b10537` — the build the committed reference
evidence (`aidd_docs/results/*-reference.jsonl`) was produced under. A
different build is not wrong to use, but its results are not comparable to
the committed evidence without saying so.

All assets are on the release page:
<https://github.com/ggml-org/llama.cpp/releases/tag/b10537>

**Windows, NVIDIA GPU** (matches this project's own laptop fiche):

Download and extract both into the same folder:

- `llama-b10537-bin-win-cuda-12.4-x64.zip`
- `cudart-llama-bin-win-cuda-12.4-x64.zip`

Set `LLAMA_SERVER_PATH` to the extracted `llama-server.exe`.

**Windows, CPU-only** (no NVIDIA GPU):

Download and extract `llama-b10537-bin-win-cpu-x64.zip`. Set
`LLAMA_SERVER_PATH` to the extracted `llama-server.exe`.

**Linux x86_64:**

Download and extract `llama-b10537-bin-ubuntu-x64.tar.gz`. Set
`LLAMA_SERVER_PATH` to the extracted `llama-server`.

Both of the last two are **CPU builds**. They run, and they produce rows, but
those rows measure a different backend than the committed reference evidence,
which was produced on the CUDA build. Just as with the build tag: not wrong to
use, not comparable without saying so.

**Any other platform, or a future build tag missing your asset:**

Build from source per
<https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md>, checking
out the matching build tag first. This is not conditioned on today's release
actually missing an asset for your platform — it's the fallback for whenever
one eventually does.

### NVIDIA GPU (documented, untested in CI)

The published container image (see the
[README's pull-and-run section](../README.md#pull-and-run-no-clone)) is
**CPU-only** — it does not ship the CUDA build above. A GPU deployment would
need, instead:

- **Base image:** `nvidia/cuda:12.4.1-runtime-ubuntu22.04` (matching the
  CUDA 12.x this project's hardware section already requires), not
  `python:3.12-slim` — the shipped `Dockerfile` builds the CPU image only.
- **Docker runtime flag:** `--gpus all` (or `--runtime=nvidia`, depending on
  your Docker Engine / NVIDIA Container Toolkit setup).
- **`llama-server` flags that change:** the CPU build's `-ngl 99` (from the
  roster entry's `server_flags`, `aidd_docs/roster/models.json`) and
  `--n-cpu-moe 37` (the `SERVER_N_CPU_MOE` host setting, no longer a
  `server.py` constant) exist to force every layer onto GPU and then push
  MoE experts back to CPU RAM under a 6 GB-VRAM ceiling; a GPU deployment
  with more VRAM would lower or drop `SERVER_N_CPU_MOE` to keep more experts
  resident on the GPU. There is no second set of magic numbers documented
  here — the roster's `validated_host` block and this project's own `.env`
  are the bare-metal precedent to start from and re-tune per your own VRAM
  budget.

**Untested in CI** — no GitHub-hosted runner carries a GPU, so this path is
documented, not built or exercised by this repository's CI.

### Building the image from a clone

`compose.yaml` runs the published image and carries no build section, so that
a reader who pulled the image and fetched that one file never triggers a build
they have no context for. From a clone, layer the developer overlay on top:

```sh
docker compose -f compose.yaml -f compose.build.yaml build
docker compose -f compose.yaml -f compose.build.yaml run --rm runtime
```

The overlay tags the build under the same name `compose.yaml` runs
(`ghcr.io/aliquanto3/wave_local_ai_v2:${WAVE_IMAGE_TAG:-latest}`), so plain
`docker compose run --rm runtime` afterwards reuses the local build instead of
pulling.

### Publishing: the one-time GHCR visibility switch

A package first pushed to GHCR by a workflow's `GITHUB_TOKEN` is **private**,
whatever the repository's own visibility, and there is no API to pre-create a
public user package. After the first `v*` tag publishes, the owner sets it
public once, by hand:

**github.com/Aliquanto3?tab=packages** → `wave_local_ai_v2` → *Package
settings* → *Danger zone* → *Change visibility* → *Public*.

Until that is done, the README's `docker pull` fails with an authentication
error for anyone signed out. It is a one-time step per package, not per
release.

### Docker Desktop memory (WSL2)

Running the full 35B roster model inside a container needs the Docker
Desktop WSL2 VM to actually have enough RAM to load it — the container does
not automatically see the host's full memory. On Windows, Docker Desktop's
default WSL2 memory cap can sit well under the ~18 GB the model file alone
needs; `llama-server` fails at load time (`failed to fit params to free
device memory`) rather than falling back to something smaller. If you hit
this, raise the limit in `%UserProfile%\.wslconfig`:

```ini
[wsl2]
memory=24GB
```

then restart Docker Desktop (or `wsl --shutdown` from PowerShell) for it to
take effect. Even with enough memory, CPU-only inference of a 35B MoE model
inside a container is slow — expect the same order of magnitude as the
bare-metal CPU path in the previous section, not the CUDA-build numbers in
the committed reference evidence.

## 3. Get the model weights and verify the checksum

- Repo: `unsloth/Qwen3.6-35B-A3B-GGUF` on Hugging Face
- Revision: `main` (commit `a483e9e6cbd595906af30beda3187c2663a1118c` at the
  time this was written)
- File in the repo: `Qwen3.6-35B-A3B-UD-IQ4_XS.gguf` (17.7 GB) — the name the
  download commands below ask Hugging Face for
- File under `SLM_MODELS_DIR` (the roster entry's `file` field):
  `Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`
- sha256: `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`

The weights live in a per-model subdirectory, not flat under
`SLM_MODELS_DIR` — that is what the `--local-dir` in the download command
below produces, and it is what the roster entry's `file` field pins. Download
to this **exact** relative path, which is what `wave-local-ai-v2` and
`wave-local-ai-v2-quality` resolve `SLM_MODELS_DIR` against:

```
<SLM_MODELS_DIR>/Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
```

The repo, revision, checksum and that relative path are the four values the
shipped roster entry (`aidd_docs/roster/models.json`, entry
`qwen3.6-35b-a3b-ud-iq4xs`) pins, verbatim. A mismatch between this section
and the roster file is a bug, not a choice — the roster is the source of
truth the running code reads, this section exists so a human downloading the
weights doesn't have to parse JSON to find the same four values.

Using the `hf` CLI:

```sh
hf download unsloth/Qwen3.6-35B-A3B-GGUF Qwen3.6-35B-A3B-UD-IQ4_XS.gguf \
  --local-dir <SLM_MODELS_DIR>/Qwen3.6-35B-A3B
```

Or the direct URL:
`https://huggingface.co/unsloth/Qwen3.6-35B-A3B-GGUF/resolve/main/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf`

Verify the checksum:

```sh
# POSIX
sha256sum <SLM_MODELS_DIR>/Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf
```

```powershell
# Windows
Get-FileHash -Algorithm SHA256 "<SLM_MODELS_DIR>\Qwen3.6-35B-A3B\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
```

The output must match `649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3`.

### 3.1 The three dense models

The roster also holds a dense size ladder — Qwen3 at 0.6B, 1.7B and 4B — so
the same suites can be scored on a dense architecture and on the MoE
flagship, and the difference read off rows rather than assumed. **The ladder
is cheap.** All three files together are 4.63 GiB, and the largest single one
is 2.33 GiB, against the flagship's 17.7 GiB. A machine that cannot host the
flagship can still run every suite in this project on these three.

The same rule as above applies to every value below: the roster file
(`aidd_docs/roster/models.json`) is the source of truth the running code
reads, and this section exists so a human downloading the weights doesn't
have to parse JSON to find the same values. A mismatch between the two is a
bug, not a choice.

Each entry pins a **commit sha**, not `main`, so the file a reader downloads
is the file the published rows were measured on. (The flagship entry above
pins `main` with its sha recorded in prose; that inconsistency is filed as
tech debt, not fixed here.)

| Entry id | Repo | Revision | File in the repo | Under `SLM_MODELS_DIR` | Quant | Size |
| -------- | ---- | -------- | ---------------- | ---------------------- | ----- | ---- |
| `qwen3-0.6b-q8` | `Qwen/Qwen3-0.6B-GGUF` | `23749fefcc72300e3a2ad315e1317431b06b590a` | `Qwen3-0.6B-Q8_0.gguf` | `Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf` | `Q8_0` | 639,446,688 B (0.60 GiB) |
| `qwen3-1.7b-q8` | `Qwen/Qwen3-1.7B-GGUF` | `90862c4b9d2787eaed51d12237eafdfe7c5f6077` | `Qwen3-1.7B-Q8_0.gguf` | `Qwen3-1.7B/Qwen3-1.7B-Q8_0.gguf` | `Q8_0` | 1,834,426,016 B (1.71 GiB) |
| `qwen3-4b-q4km` | `Qwen/Qwen3-4B-GGUF` | `bc640142c66e1fdd12af0bd68f40445458f3869b` | `Qwen3-4B/Qwen3-4B-Q4_K_M.gguf` | `Qwen3-4B/Qwen3-4B-Q4_K_M.gguf` | `Q4_K_M` | 2,497,280,256 B (2.33 GiB) |

The quants are not uniform because that is what the vendor publishes: the
0.6B and 1.7B GGUF repos each contain exactly one quant (`Q8_0`), while the
4B repo publishes a range and `Q4_K_M` is the one taken. Read the ladder as
a size ladder, not as a quant-controlled one.

sha256, per file:

```
qwen3-0.6b-q8   9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031
qwen3-1.7b-q8   061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a
qwen3-4b-q4km   7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5
```

Download each at its pinned revision:

```powershell
# Windows
hf download Qwen/Qwen3-0.6B-GGUF Qwen3-0.6B-Q8_0.gguf `
  --revision 23749fefcc72300e3a2ad315e1317431b06b590a `
  --local-dir <SLM_MODELS_DIR>\Qwen3-0.6B

hf download Qwen/Qwen3-1.7B-GGUF Qwen3-1.7B-Q8_0.gguf `
  --revision 90862c4b9d2787eaed51d12237eafdfe7c5f6077 `
  --local-dir <SLM_MODELS_DIR>\Qwen3-1.7B

hf download Qwen/Qwen3-4B-GGUF Qwen3-4B-Q4_K_M.gguf `
  --revision bc640142c66e1fdd12af0bd68f40445458f3869b `
  --local-dir <SLM_MODELS_DIR>\Qwen3-4B
```

```sh
# POSIX
hf download Qwen/Qwen3-0.6B-GGUF Qwen3-0.6B-Q8_0.gguf \
  --revision 23749fefcc72300e3a2ad315e1317431b06b590a \
  --local-dir <SLM_MODELS_DIR>/Qwen3-0.6B
# ...and the same two lines for Qwen3-1.7B and Qwen3-4B.
```

Verify each checksum:

```powershell
# Windows -- .ToLower() matters: the roster stores lowercase hex.
(Get-FileHash -Algorithm SHA256 "<SLM_MODELS_DIR>\Qwen3-0.6B\Qwen3-0.6B-Q8_0.gguf").Hash.ToLower()
```

```sh
# POSIX
sha256sum <SLM_MODELS_DIR>/Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf
```

## 4. Configure `.env` and run

```sh
cp .env.example .env       # POSIX
copy .env.example .env     # Windows
```

Fill `SLM_MODELS_DIR` (the parent directory from step 3) and
`LLAMA_SERVER_PATH` (the binary path from step 2).

Two more env vars set the host-fitted launch flags that are not part of the
roster's model data: `SERVER_N_CPU_MOE` and `SERVER_THREADS` (default `8`),
matching `--n-cpu-moe` and `-t` on this project's own laptop fiche. They
exist to be overridden on different hardware; leave them unset to reproduce
the committed reference evidence on comparable hardware.

`SERVER_N_CPU_MOE` has two states, and the difference matters:

- **Unset** — the selected entry decides. Its own `validated_host.n_cpu_moe`
  is used: `37` for the MoE flagship (so its launch command is byte-identical
  to the validated baseline), and `null` for a dense entry, which puts no
  `--n-cpu-moe` on the command line at all. This is what a reader following
  this walkthrough wants, whichever entry they select.
- **Set** — the operator overrides the entry. A value above an MoE entry's
  `expert_count` is refused, and **any** value on a dense entry is refused,
  `SERVER_N_CPU_MOE=0` included: `0` says "offload no experts", which a model
  with no experts cannot honour. Both refusals name the entry and happen
  before any process is spawned.

`ROSTER_PATH` (default `aidd_docs/roster/models.json`) and `ROSTER_ENTRY_ID`
(default `qwen3.6-35b-a3b-ud-iq4xs`) select which of the roster's four
entries runs: the MoE flagship, or one of the three dense models from step
3.1.

### Running one entry after another

There is no runner script and no fleet orchestrator. `ROSTER_ENTRY_ID`
already selects the entry, and the CLIs read it through
`load_dotenv(override=False)`, so a value set in the shell wins over `.env`
(which does not set `ROSTER_ENTRY_ID` at all). The whole multi-model recipe
is a loop:

```powershell
foreach ($id in 'qwen3-0.6b-q8','qwen3-1.7b-q8','qwen3-4b-q4km') {
  $env:ROSTER_ENTRY_ID = $id
  uv run wave-local-ai-v2
  uv run wave-local-ai-v2-quality --suite classification
  uv run wave-local-ai-v2-quality --suite translation
}
```

```sh
for id in qwen3-0.6b-q8 qwen3-1.7b-q8 qwen3-4b-q4km; do
  ROSTER_ENTRY_ID=$id uv run wave-local-ai-v2
  ROSTER_ENTRY_ID=$id uv run wave-local-ai-v2-quality --suite classification
  ROSTER_ENTRY_ID=$id uv run wave-local-ai-v2-quality --suite translation
done
```

Each invocation is its own `run_id`, so the rows stay selectable per model
and per suite afterwards. Each also launches and stops its own
`llama-server`, so nothing has to be torn down between iterations — but port
8080 must be free when the loop starts, or the first run refuses rather than
measuring a process it did not spawn.

On this project's own laptop (RTX 3060 Laptop, 6144 MiB) all three dense
entries reached ready at `-ngl 99` — every layer resident — at 32768
context, at 4377 MiB / 5537 MiB / 5961 MiB of card-wide `nvidia-smi` usage
once loaded (the runtime rows report a little more, measured during
generation rather than at load). The 4B leaves under 200 MiB of headroom; a
machine with less VRAM will need a lower `n_gpu_layers` in that entry. Lower
`n_gpu_layers`, not `context_size`: both suites publish a 32768 context cap
on every row, and an entry launched below it would make that published cap
false.

Fitting is not the same as running well: the 4B's measured prompt throughput
collapses to a tenth of the 1.7B's at that occupancy. See the side-by-side
section in `aidd_docs/results/README.md` for what each entry actually
produced — it is the reason the loop above exists.

**4.1 — everything up to here runs on a GPU-less container.**

**4.2 — first run, needs a GPU-bearing machine, no cloud credential:**

```sh
uv run wave-local-ai-v2
```

This runs one warm-up plus `RUNTIME_REPETITIONS` counted repetitions (default
5, ~N× the cost of a single request) with a `RUNTIME_COOLDOWN_S` cooldown
(default 10.0s) between them, so a default run takes roughly 5x a single
request's time plus 50s of cooldown. Lower `RUNTIME_REPETITIONS` and
`RUNTIME_COOLDOWN_S` for a faster development loop; the published defaults
are what the aggregates in `runtime.jsonl` are computed under. One row lands
in `RUNTIME_RESULTS_PATH` (default `aidd_docs/results/runtime.jsonl`) if
every repetition succeeds; a single failing repetition (empty output, an
unusable timings block, or the model's context exceeded) fails the whole
run and writes nothing.

Every repetition in that row (warm-up and counted) carries a `machine_state`
block: `gpu_temp_c` and `gpu_throttle_reasons` (decoded NVML clock event
reasons, read via NVML), plus `cpu_temp_c` / `cpu_temp_source` (`"psutil"`
when a package sensor was read, `"unavailable"` when the platform has none
at ordinary privilege). The row itself also carries, per counted-repetition
set: `gen_tok_per_s_spread`, `ttft_ms_spread`, `prompt_tok_per_s_spread`
(each the sample sd over the median) and `unreliable`, set only when
`gen_tok_per_s_spread` exceeds `RUNTIME_SPREAD_THRESHOLD` (default `0.10`,
overridable in `.env`); `thermal_posture` (today: `"fixed_cooldown"`); and
`ttft_source` (today: `"server_reported"`, naming that `ttft_ms` is
llama-server's own reported timing rather than an independent measurement).

The row also carries a `verdict` block, computed against the reference file
at `RUNTIME_REFERENCE_PATH` (default
`aidd_docs/results/runtime-reference.jsonl`; the quality command uses
`QUALITY_REFERENCE_PATH`, default `aidd_docs/results/quality-reference.jsonl`).
A runtime re-run counts as `reproduced` when its `gen_tok_per_s` is within
`RUNTIME_REPRODUCTION_TOLERANCE` (default `0.10`) of the matching reference
row's; `not_reproduced` when it is outside; `not_comparable` when no
reference row was configured or none matches on all four verdict-blocking
fields (`llama_cpp_build`, `quant`, `gpu_name`, `flags`, all read from each
row's stored fiche — CPU, RAM, driver and OS never block a comparison).
Point `RUNTIME_REFERENCE_PATH` at an empty or absent file to opt out: that
is `not_comparable`, not a failure.

**4.3 — second run, set `MISTRAL_API_KEY` and `GOOGLE_API_KEY` first:**

```sh
uv run wave-local-ai-v2-quality                      # --suite classification
uv run wave-local-ai-v2-quality --suite translation
```

One row per (item, model) lands in `QUALITY_RESULTS_PATH` (default
`aidd_docs/results/quality.jsonl`) for each of three providers: `local`,
`mistral`, `google`.

`--suite` picks what is scored. It defaults to `classification`, so an
invocation written before the flag existed behaves exactly as it did.

| `--suite` | Items | Caps | How it is scored | The headline it prints |
| --------- | ----- | ---- | ---------------- | ---------------------- |
| `classification` (default) | 20 support messages, one of four routing labels each | 32 output tokens | exact label match | `accuracy=` |
| `translation` | 21 short business sentences, `en→fr` / `fr→de` / `de→en`, seven each | 128 output tokens | chrF against a hand-written reference (`chrf.py`) | `suite_score=` |

The two suites write two different score shapes into the same store, and a
row is never both. A classification row carries `correct`, `suite_accuracy`
and `language_breakdown`; a translation row nulls all three and carries the
graded block instead — `item_score` and `suite_score` on `0..1`,
`score_breakdown` per source language, `metric_id`/`metric_version`/
`metric_params`, and both `reference_output` and `subject_output`. Reading a
graded row means recomputing it if you want to: the two texts and the metric
parameters are all on the row, and `sacrebleu -m chrf` over them should give
the same number `×100`. The `-m chrf` is load-bearing — sacreBLEU's CLI
defaults to BLEU, and `--chrf-char-order 6 --chrf-beta 2` (the row's
parameters, and sacreBLEU's own defaults) are ignored without it. Select by
`task_suite` before comparing any score column.

That chrF is measured against a *single* reference translation, so it
penalises a valid alternative wording. It compares models against identical
references; it is not an absolute measure of translation quality.

The translation batch costs ~3 minutes of Google pacing (21 items at two
paced calls each, `GOOGLE_REQUEST_PACING_S` 4.1) — about 8 seconds more than
the classification suite, which runs one item fewer at the same pacing.

Both cloud providers behave the same way when something goes wrong: a
missing `MISTRAL_API_KEY` or `GOOGLE_API_KEY`, a provider absent from
`QUALITY_PROVIDERS` (default `local,mistral,google`), or a provider's own
pre-flight/batch call failing (a rate limit, a retired model id) all degrade
to the same thing — one stderr line naming the provider and why, zero rows
for it, and the run still exits `0` as long as the local batch succeeded.
Nothing aborts the whole run for a cloud provider's sake. If `quality.jsonl`
has no rows for a provider you expected, check stderr before assuming
something is broken.

Google's free tier caps at 15 requests/minute; each suite item costs two
Google calls (a context-fits pre-flight, then the generation itself), so
`quality_cli` paces those calls (`GOOGLE_REQUEST_PACING_S`) rather than
firing all ~40 at once. A full google batch on the 20-item suite therefore
takes a few minutes by design, not a hang.

**4.4 — validate the fiches a run cited:**

Every runtime and quality row cites its hardware/run fiche by `fiche_hash`
rather than carrying it inline; the fiche itself is stored once, write-once,
under `FICHE_REGISTRY_DIR` (default `aidd_docs/results/fiches/`, tracked in
git). To prove none of those stored fiches were edited or went missing after
the fact:

```sh
uv run wave-local-ai-v2-validate
```

With no arguments this checks the two live stores
(`RUNTIME_RESULTS_PATH`, `QUALITY_RESULTS_PATH`); pass one or more result-file
paths to check something else instead, e.g. the committed reference files.
Exits `0` and prints the checked row count when every cited fiche is intact
(or predates the `fiche_hash` contract entirely — reported separately as a
non-fatal `legacy` count); exits `1` and names the affected run id and row
position when a fiche was edited in place or is missing from the registry.

## 5. Energy, emissions and cost configuration

Six env vars, all optional — every one has a default, listed with its source:

| Var | Default | Source |
| --- | ------- | ------ |
| `EMISSION_COUNTRY_ISO_CODE` | `FRA` | CodeCarbon's offline grid-mix selector (3-letter ISO code) — no live geolocation call. |
| `EMISSION_REGION` | `FR` | The 2-letter region label published on the row; distinct from CodeCarbon's own `region` kwarg, which this project does not use (that kwarg only supports US states / Canadian provinces). |
| `EMISSION_FACTOR_KG_PER_KWH` | `0.056039` | CodeCarbon's own `"FRA"` grid-carbon-intensity entry, 56.039 gCO2eq/kWh (year 2023), from `global_energy_mix.json`. |
| `SCOPE3_WH_PER_TOKEN` | `0.0003` | Median energy per output token for a frontier-scale cloud model (~3×10⁻⁴ Wh/token), Joule (2026) "Energy use of AI inference, efficiency pathways, and test-time scaling." One order-of-magnitude estimate for the project's whole Scope-3 path, not model-specific. |
| `KWH_PRICE_EUR` | `0.1940` | EDF Tarif Bleu (French residential regulated tariff, Base option), effective February 2026. |
| `KWH_PRICE_RECORDED_AT` | `2026-02-01` | The tariff's own effective date above — a configured value, not a live retrieval. |

**Scope 2 vs. Scope 3, and why they are not directly comparable.** A local run
(`wave-local-ai-v2`, and a quality row's `local`-provider batch) is measured
on this machine by CodeCarbon: its `emissions_scope` is `"scope_2"`,
`emissions_scope_formula_id` is `null`, and `scope_comparability` is `null` —
there is nothing to caveat, the number came from a real per-channel
measurement (CPU: TDP-estimated, GPU: NVML-measured when present, RAM:
constant-estimated). A cloud run (a quality row's `mistral`-provider batch)
has no on-machine energy to measure at all, so its energy and emissions are
instead *estimated* from `SCOPE3_WH_PER_TOKEN` and the batch's total token
count (`emissions.scope3_cloud_emissions`, `emissions_scope_formula_id` set
to a named formula id, `emissions_scope` `"scope_3"`). The row's own
`scope_comparability` field states in words why the two are not like-for-like:
the Scope-3 estimate has no local counterpart yet for facility overhead or
hardware amortization, so a Scope-2 number and a Scope-3 number on the same
dashboard describe different boundaries, not the same thing measured two
ways. Read `emissions_scope` before comparing any two rows' `emissions_kg`.
