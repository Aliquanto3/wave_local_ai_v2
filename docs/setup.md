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
- What each model needs per compute mode (RAM, VRAM, disk) is the declared
  minimums table in [section 1.2](#12-what-each-model-needs-declared-minimums);
  read it before starting step 3, which downloads 17.7 GB for the flagship.

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

### 1.1 The results dashboard (front end)

Needs Node — the version `frontend/.nvmrc` pins (`nvm use` from `frontend/`
reads it). No GPU, no API key, and no bearing on steps 2-4 below, which are
the Python-only benchmark walkthrough.

```sh
cd frontend
npm ci
npm run build
```

This produces `frontend/dist/`, never committed (see `plan.md`'s Decisions in
the dashboard story) — reproduced by this one command on every fresh clone,
matching `uv sync`'s posture for the Python half above. Point
`DASHBOARD_BUNDLE_DIR` at it (default: `frontend/dist`, so an unset variable
already matches) and start the service (`uv run wave-local-ai-v2-serve`) to
serve the dashboard from the service's own origin.

For the TLS certificate, the key, and reaching the dashboard from a second
machine (the demo/pitch path), see `docs/demo.md`.

### 1.2 What each model needs: declared minimums

Every roster entry declares, per compute mode, the minimum it needs to start:
total system RAM, VRAM the GPU can allocate (`gpu` only) and free disk on the
models volume (`requirements` in `aidd_docs/roster/models.json`, each value
`{value, source, read_from}` in decimal GB, 10^9 bytes). Before a run looks
for the weights or starts `llama-server`, its pre-flight compares them with
what the machine reports: total RAM, the machine registry's declared
allocatable VRAM (NVML's reported total where none is declared), and free disk
only while the weights are not on disk yet. A machine below a minimum refuses
the run: it names the requirement, the mode, the declared minimum and the
observed value, exits non-zero, writes no runtime or quality row, and appends
one refusal record (roster entry, machine, mode, profile id, requirement,
declared and observed values, release version, commit sha, timestamp) to the
machine's own tracked results location,
`aidd_docs/results/machines/<machine_id>/refusals.jsonl` (`MACHINE_RESULTS_ROOT`
moves the root; see section 6). Nothing is substituted: no smaller quant, no
shorter context, no switch from `gpu` to `cpu_only`; a refused `gpu` run names
the `cpu_only` profile that exists for the same machine and runs nothing.

| Model | Mode | RAM (GB) | VRAM (GB) | Disk (GB) | Calibrated from |
| ----- | ---- | -------- | --------- | --------- | --------------- |
| `Qwen3.6-35B-A3B` `UD-IQ4_XS` | `gpu` | 15.23 | not yet declared | 17.74 | RAM: peak `process_rss_bytes` 15225831424 of the published laptop rows; disk: `bytes_on_disk` |
| `Qwen3.6-35B-A3B` `UD-IQ4_XS` | `cpu_only` | 17.74 | n/a | 17.74 | RAM: lower bound, the larger of the `gpu` peak and the weights' size (no `cpu_only` peak published) |
| `Qwen3-0.6B` `Q8_0` | `gpu` | 1.08 | not yet declared | 0.64 | RAM: peak 1077411840 B (1077 MB) of the laptop gpu row in the gpu-cpu-never-share-a-fiche task evidence |
| `Qwen3-0.6B` `Q8_0` | `cpu_only` | 4.77 | n/a | 0.64 | RAM: peak 4761899008 B of the laptop `cpu_only` rows (named-run-profiles evidence) |
| `Qwen3-1.7B` `Q8_0` | `gpu` | 2.28 | not yet declared | 1.84 | RAM: peak 2277 MB of the published laptop row |
| `Qwen3-1.7B` `Q8_0` | `cpu_only` | 2.28 | n/a | 1.84 | RAM: lower bound, as for the flagship |
| `Qwen3-4B` `Q4_K_M` | `gpu` | 4.28 | not yet declared | 2.50 | RAM: peak 4275 MB of the published laptop row |
| `Qwen3-4B` `Q4_K_M` | `cpu_only` | 4.28 | n/a | 2.50 | RAM: lower bound, as for the flagship |

The `gpu` RAM peaks are the side-by-side runtime table of
`aidd_docs/results/README.md`; each declaration's full source is its
`read_from`. No VRAM minimum is declared yet: the published `vram_used_mib` is
NVML's device-wide used memory (4527 MiB for the 0.6B, whose weights are
0.64 GB), not a model's own need, so a VRAM requirement is not checked and the
pre-flight says so on stderr. A `gpu` run on the laptop also needs an NVIDIA
GPU with CUDA 12.x support; the flagship's laptop evidence offloads experts to
CPU RAM with `--n-cpu-moe`, so system RAM, not VRAM, is its ceiling.

These minimums are declared, not verified. Nothing checks that a declaration
is right: one set too low surfaces as a run that starts and then fails (an
out-of-memory exit or a load error), not as a refusal. The `cpu_only` lower
bounds are the likeliest to be too low until a measured `cpu_only` peak
replaces them.

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
  here — the laptop's run profiles in `aidd_docs/roster/profiles.json`
  (section 4) are the bare-metal precedent to start from and re-tune per your
  own VRAM budget.

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

### 3.2 Before adding an entry: the candidate gate

A new model enters `aidd_docs/roster/models.json` only from a pass record of
the candidate gate, and a candidate that fails it leaves a refusal behind.
Declare the candidate as a JSON file:

| Key | What it is |
| --- | ---------- |
| `entry_id` | the roster id the entry will take |
| `repo`, `revision` | the Hugging Face repo and a 40-hex **commit sha** (a branch is refused) |
| `repo_file` | the GGUF's path in the repo |
| `file` | its path under `SLM_MODELS_DIR` (the roster's `file`) |
| `display_id`, `quant`, `family` | as in the roster; `family` from `roster.KNOWN_FAMILIES` |
| `thinking_control` | the request arguments that disable reasoning, `"none"` for a model that does not reason, or `"allowed"` when no control can be verified (the entry then carries none and runs under `allowed` only) |
| `active_params_b` | the card's figure |
| `client_commercial_use` | your reading of the licence, a boolean |
| `language_claim` | `languages` (subset of `en`/`fr`/`de`), `source_url`, optional verbatim `statement` |
| `server_flags` | the launch block, exactly as a roster entry holds it |
| `load_profile` | the host values the gate's one load runs with: `n_cpu_moe` (an integer, or `null` for no `--n-cpu-moe`) and `threads`; not copied into the entry (run profiles hold host values, section 4) |

Then, with `SLM_MODELS_DIR` and `LLAMA_SERVER_PATH` set as for a run and no
`llama-server` already on port 8080:

```sh
uv run wave-local-ai-v2-candidate-gate --candidate <candidate.json>
```

It runs seven steps, cheapest first, and stops at the first failure: the
revision and file exist on the hub; the licence id is read at the revision and
its text scanned (a sentence forbidding publication of benchmark results is the
one licence refusal); free disk under `SLM_MODELS_DIR` covers the file; the
file is downloaded at the revision and its sha256, size, architecture and
total parameter count are read off the bytes; one `llama-server` load under the
build the binary reports; the chat template from `/props` and the declared
thinking control verified against it (`none` by one generation that must
return no reasoning); the language claim recorded. Set `HF_TOKEN` for a gated
repository.

Every run appends one line to `aidd_docs/roster/candidate-records.jsonl`
(`--records` overrides): a pass carries the full entry block, a refusal names
the step, the evidence and the date, and an architecture the pinned build does
not load is recorded `deferred` naming the architecture and the build. The
gate never switches build. Exit `0` is a pass, `1` a refusal or deferral, `2`
means nothing was recorded (a malformed declaration, an unreachable hub, a
busy port, an unreadable build). The gate never writes `models.json`: copy the
pass record's `entry` into it as a reviewed change, and add the model's row to
the tables above.

## 4. Configure `.env` and run

```sh
cp .env.example .env       # POSIX
copy .env.example .env     # Windows
```

Fill `SLM_MODELS_DIR` (the parent directory from step 3) and
`LLAMA_SERVER_PATH` (the binary path from step 2).

Then name the machine and the compute mode. Both are required and have no
default: every runtime and quality run refuses before any server starts
until they are set, and every fiche and row records them.

- `MACHINE_ID` — one of the declared machines in
  `aidd_docs/roster/machines.json`: `laptop-mobile-gpu`,
  `tower-desktop-gpu` or `pro-pc-no-gpu`. An id names a declared
  configuration, not a box: a RAM upgrade or a GPU swap is a new entry with
  a new id, added to that file before the machine runs anything. An
  undeclared id is refused, naming the declared ones.
- `COMPUTE_MODE` — `gpu` or `cpu_only`. `gpu` launches the roster entry's
  own flag set. `cpu_only` puts every layer on the CPU: it launches with
  `-ngl 0 --device none` and no `--n-cpu-moe` (the CUDA build still drives
  the GPU during prompt processing with `-ngl 0` alone), and refuses a
  `SERVER_N_CPU_MOE` value rather than dropping it. `gpu` on a machine
  declared GPU-less is refused. A `gpu` run and a `cpu_only` run of one
  model on one machine produce two fiches and are never compared as a
  reproduction of each other.

`CAMPAIGN_ID` is optional. Unset, a run belongs to no campaign and every row
records `campaign_id: "none"`. Set, it names a campaign declaration,
`aidd_docs/campaigns/<campaign_id>.json` (`CAMPAIGNS_DIR` overrides the
directory): the run is checked against it before any server starts and
refused, naming the dimension, when its engine, prompt variant, roster entry,
suite, machine or compute mode is outside the declaration, when it runs a
cell the declaration excludes, or when a quality run enables a cloud
provider. `wave-local-ai-v2-campaign-completeness --campaign <campaign_id>`
then lists every declared cell and fails naming each one nobody ran.

### Run profiles: the host-fitted launch values

Every (roster entry x machine x compute mode) triple runs under a named run
profile, `<roster_entry_id>@<machine_id>/<compute_mode>`, declared in the
tracked registry `aidd_docs/roster/profiles.json`. The registry holds one
default per (machine, mode) and, under `entries`, only the values a given
model needs differently, so a new roster entry needs no profile of its own
unless it differs. Every value is `{value, source, read_from}`: `declared`
values were read or fitted on the machine, `not_yet_declared` values await
that read and are never guessed.

One resolution order, applied by `profiles.resolve`; `server.build_flags`, the only flag
builder, launches the result:

1. **Roster entry default** — the model-intrinsic `server_flags`
   (`aidd_docs/roster/models.json`), including the default `-ngl`.
2. **Run profile** — the (machine, mode) default with the entry's own
   overrides laid over it: `-ngl` (`cpu_only` profiles declare `0`, and the
   mode adds `--device none`), `--n-cpu-moe` (absent unless declared, so a
   dense entry carries none) and `-t`.
3. **Operator override** — `SERVER_N_CPU_MOE` and `SERVER_THREADS`, applied
   last. Unset, the profile decides. Set, the value replaces the profile's,
   and every row records it in `profile_overrides` beside the profile's own
   value, so a row never claims a profile it did not run under.

The declared profile set:

| Machine | Mode | `-ngl` | `--n-cpu-moe` | `-t` |
| --- | --- | --- | --- | --- |
| `laptop-mobile-gpu` | `gpu` | roster default (`99`) | none; `37` for `qwen3.6-35b-a3b-ud-iq4xs` | `8` |
| `laptop-mobile-gpu` | `cpu_only` | `0` (+ `--device none`) | none | `8` |
| `tower-desktop-gpu` | `gpu` | roster default | none; not yet declared for `qwen3.6-35b-a3b-ud-iq4xs` | not yet declared |
| `tower-desktop-gpu` | `cpu_only` | `0` (+ `--device none`) | none | not yet declared |
| `pro-pc-no-gpu` | `cpu_only` | `0` (+ `--device none`) | none | not yet declared |

A run whose triple has no declared profile (for example `gpu` on the
professional PC) refuses before any server starts, naming the triple and the
profiles that exist for that entry. A run under a profile with a value not
yet declared refuses the same way, naming the value and what it awaits,
unless the operator overrides it (`SERVER_THREADS=6` on the tower, for
instance), and that row then records the override.

An operator value is still checked against the model: a `SERVER_N_CPU_MOE`
above an MoE entry's `expert_count` is refused, **any** value on a dense
entry is refused (`0` included: it says "offload no experts", which a model
with no experts cannot honour), and any value under `cpu_only` is refused
naming the mode. Every refusal happens before any process is spawned.

The profile id is on every fiche and every row. On the fiche it is evidence
like `flags`, outside the hashed projection: renaming a profile does not move
a fiche hash.

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
  uv run wave-local-ai-v2-quality --suite classification-support-routing
  uv run wave-local-ai-v2-quality --suite translation-business-short-form
}
```

```sh
for id in qwen3-0.6b-q8 qwen3-1.7b-q8 qwen3-4b-q4km; do
  ROSTER_ENTRY_ID=$id uv run wave-local-ai-v2
  ROSTER_ENTRY_ID=$id uv run wave-local-ai-v2-quality --suite classification-support-routing
  ROSTER_ENTRY_ID=$id uv run wave-local-ai-v2-quality --suite translation-business-short-form
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
reference row was configured or none matches on all five verdict-blocking
fields (`engine_id`, `engine_build`, `quant`, `gpu_name`, `flags`, all read
from each row's stored fiche — CPU, RAM, driver and OS never block a
comparison). A reference fiche written before the engine fields carries
neither, so it never matches a current run.
Point `RUNTIME_REFERENCE_PATH` at an empty or absent file to opt out: that
is `not_comparable`, not a failure.

A quality batch is decided per item against the matching reference batch.
A `local` subject must reproduce every item's `predicted_label` (or
`item_score`) exactly. A cloud subject (`mistral`, `google`) is decided under
its suite's declared `divergence_tolerance` (`suite_data/<suite_id>.json`:
value, unit `fraction_of_items`, and the reason for the value): `reproduced`
while the share of diverging items stays within it, `not_reproduced` beyond
it, and the block's `differing_fields` names the diverging items either way.
From row schema "29" the block also names `subject_rule` (`identical` or
`within_tolerance`), the `tolerance` with the `suite_id`/`suite_version` that
declared it, the observed `divergence`, and `single_run_indicative`: a cloud
batch sent with no seed is marked `no_seed` and is `not_comparable`, never
`not_reproduced`; a cloud model whose dated id is no longer served is named
`model_not_served` on stderr when its pre-flight is refused.

**4.3 — second run, set `MISTRAL_API_KEY` and `GOOGLE_API_KEY` first:**

```sh
uv run wave-local-ai-v2-quality         # --suite classification-support-routing
uv run wave-local-ai-v2-quality --suite translation-business-short-form
```

One row per (item, model) lands in `QUALITY_RESULTS_PATH` (default
`aidd_docs/results/quality.jsonl`) for each of three providers: `local`,
`mistral`, `google`.

`--suite` picks what is scored, by registered suite id. It defaults to
`classification-support-routing`, so an invocation written without the flag
behaves exactly as it did. The short names `classification` and
`translation` it once took are refused like any unregistered id, with the
registered ids named; they survive as each row's `task_suite`. The suites'
definitions are data in `src/wave_local_ai_v2/suite_data/`.

| `--suite` | Items | Caps | How it is scored | The headline it prints |
| --------- | ----- | ---- | ---------------- | ---------------------- |
| `classification-support-routing` (default) | 20 support messages, one of four routing labels each | 32 output tokens | exact label match | `accuracy=` |
| `translation-business-short-form` | 21 short business sentences, `en→fr` / `fr→de` / `de→en`, seven each | 128 output tokens | chrF against a hand-written reference (`chrf.py`) | `suite_score=` |

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

## 6. Returning a machine's rows: promote, branch, pull request

Every machine returns its evidence the same way, and the published bundle is
only ever derived from what came back. The live stores a run appends to
(`RUNTIME_RESULTS_PATH`, `QUALITY_RESULTS_PATH`) are untracked; each declared
machine instead owns one tracked location,
`aidd_docs/results/machines/<machine_id>/`, holding `runtime.jsonl`,
`quality.jsonl` and `refusals.jsonl`. Its fiches go to the shared, tracked,
content-addressed registry `aidd_docs/results/fiches/`, where two machines'
pull requests add different file names and never conflict.

### 6.1 The per-machine loop

1. **Declare.** The machine is an entry of `aidd_docs/roster/machines.json`
   and every entry it runs has a profile in `aidd_docs/roster/profiles.json`.
   `MACHINE_ID` and `COMPUTE_MODE` are set in `.env` (section 4).
2. **Run.** Run the benchmark (section 4). Each invocation is one `run_id`, carried
   by every row it wrote: the last line of the live store names the latest
   run. A refused run needs no promotion: the
   pre-flight already appended its record to the location's `refusals.jsonl`.
3. **Promote** the runs to publish, by `run_id`:

   ```bash
   uv run wave-local-ai-v2-promote --run-id <run_id> [--run-id <run_id> ...]
   ```

   It copies those runs' runtime and quality rows line-for-line into the
   machine's location and their fiches file-for-file into the tracked
   registry. It refuses, writing nothing, a `run_id` with no row, a row whose
   `machine_id` is another machine's (only the machine that produced a row
   promotes it; a cloud subject's `not_applicable` row travels with the
   machine that ran it), and a fiche the live registry lacks or that differs
   from the tracked copy. Promoting the same run twice changes nothing.
   `--machine` overrides `MACHINE_ID`; `FICHE_REGISTRY_DIR` is where the run
   wrote its fiches, `TRACKED_FICHE_REGISTRY_DIR` (default
   `aidd_docs/results/fiches`) where they are published.
4. **Branch.** One branch per machine and batch, for example
   `git switch -c results/<machine_id>-<yyyy-mm-dd>`, from an up-to-date
   `main`.
5. **Regenerate the bundle on the same branch.** Run

   ```bash
   uv run wave-local-ai-v2-merge-bundle
   uv run wave-local-ai-v2-merge-bundle --check
   ```

   The first command writes `aidd_docs/results/runtime-reference.jsonl`,
   `quality-reference.jsonl` and `refusals-reference.jsonl` from every
   location on the branch; the second must print that the committed bundle
   equals the merge. Commit the machine's location, the new fiche files and
   the three bundle files together, in one commit. The merge refuses,
   writing nothing, when two rows claim one fiche hash under two machine ids
   (it names both rows, both machine ids and the hash, and never chooses),
   when a row's or a refusal's `machine_id` is not a declared machine, when a
   row sits in another machine's location, when a row carries no `run_id`,
   and when one `run_id` appears in two locations.
6. **Pull request.** Push the branch and open one pull request into `main`.
   It runs the same check suite as any code change, including the
   **Derived bundle** step (`wave-local-ai-v2-merge-bundle --check`), which
   fails when the committed bundle differs from what the merge derives: the
   bundle is never edited by hand. Merge it once `required` is green.
7. **If another machine's pull request lands first**, the bundle files
   conflict. Never resolve that conflict by hand: rebase the branch onto
   `main`, take `main`'s bundle files, re-run step 5 (`merge-bundle`, then
   `--check`), amend or add the regenerated bundle, and push again.

**Until the bundle republication story.** The committed `*-reference.jsonl`
files are still the schema-"7" snapshot, pinned by digest
(`aidd_docs/results/README.md`). While it stands, committing any location
record, a promoted row or a pre-flight refusal alike, turns the **Derived
bundle** step red, and the merge in write mode refuses to overwrite the
snapshot. The loop starts with the republication story, which supersedes the
snapshot (`git mv` to `*-reference.schema-7.jsonl`) and runs the first merge.

### 6.2 Fallback: a machine that cannot push

When a machine cannot push (no git credentials, a managed network), its
evidence is carried by the operator to a machine that can. It is recorded as
carried, never passed off as the machine's own push.

1. On the source machine, run steps 1 to 3 of section 6.1 as usual.
2. Copy `aidd_docs/results/machines/<source_machine_id>/` and every fiche file
   its rows cite from `aidd_docs/results/fiches/` to removable media.
3. On the carrying machine, from an up-to-date `main`, create the branch
   `results/<source_machine_id>-<yyyy-mm-dd>` and copy both into the same
   paths. Do not promote again there: `MACHINE_ID` on the carrier is the
   carrier, and its promotion would rightly refuse the source's rows.
4. Commit with these trailers, exactly (with step 5's bundle files):

   ```text
   feat(results): promote <source_machine_id> records

   Transport: operator-carried
   Source-machine: <source_machine_id>
   Carried-by: <carrying_machine_id>
   Transport-verification: declared, not verified
   ```

   The transport is a declaration, under the same declared-not-verified
   honesty as the energy labels: nothing proves the bytes left the source
   machine unchanged, and the commit says so.
5. On the same branch, regenerate and check the bundle (section 6.1 step 5),
   then commit the three bundle files with the carried location in the same
   commit as the trailers above. Open the pull request as in step 6; if
   another pull request lands first, follow step 7.
