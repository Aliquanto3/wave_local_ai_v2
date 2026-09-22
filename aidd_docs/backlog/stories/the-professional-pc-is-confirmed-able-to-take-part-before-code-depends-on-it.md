---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
order: 0
---

# Story: The professional PC is confirmed able to take part before any code depends on it

**As** the consultant who owns the three target machines
**I want** the no-GPU professional PC checked for the rights the campaign needs, every machine's undeclarable facts written down, and one CPU-only launch observed on each machine
**So that** the machine the publication most needs is not discovered to be unusable during its proving pass, and the `cpu_only` flag set is chosen from an observed launch rather than assumed

Maps to: PRD Dependencies "Continued availability of the three target machine configurations"; PRD Methodology 21 ("every layer on the CPU"); epic Dependencies rows 1 (corporate-managed PC) and 3 (the `-ngl 0` spike).

## Acceptance

- **Pro-PC checklist, every item answered yes, no, or blocked-by-whom, never skipped:**
  - git: the repository clones over HTTPS, and a throwaway branch pushes to the GitHub remote, or the push is refused and the reason is recorded. A refusal selects the operator-carried transport for this machine now, not during the proving pass.
  - network egress: `github.com` (release assets) and `huggingface.co` (weights) are reachable, through the corporate proxy if there is one, with the proxy setting that worked recorded.
  - disk headroom: free space on the volume that will hold the models, stated in GiB against what the three dense entries need (the flagship is not downloaded on this machine; see order 8).
  - install rights: `uv` installs the pinned Python and the project's dependencies without administrator rights; the `llama-server` `b10537` CPU asset unzips and `llama-server --version` runs (no SmartScreen, AppLocker or antivirus block, or the block is named).
  - permission: the machine's owner (employer or IT) allows installing and running the benchmark on it, recorded as a yes with who gave it, or as the blocker.
- **Declared facts for all three machines**, read from the machine rather than recalled: CPU model, core and thread count, instruction-set notes that affect CPU inference (AVX2, AVX-512), installed RAM, memory type, rated and configured speed, channel count, GPU model and nominal and allocatable VRAM where a GPU exists, OS build, and the volume models live on. Each fact records how it was read (tool or panel), so a later reader can tell a measured value from a label.
- **One `cpu_only` launch per machine**, `Qwen3-0.6B` under the roster's own flag set with the GPU offload set to zero: the server reaches `/health`, one completion returns, and the record states whether `-fa on` and the entry's `--load-mode` were accepted. On the two GPU machines the record also states **whether the GPU was used anyway** (process VRAM and GPU utilisation observed during prompt processing): if the CUDA build still offloads work with `-ngl 0`, the record names the additional setting that made the run genuinely CPU-only, and that setting, not `-ngl 0` alone, is what order 1's `cpu_only` flag set emits. [PRD M21 "every layer on the CPU"]
- The binary each machine ran is recorded by asset name (CUDA build or CPU build), since the pro PC cannot run the CUDA asset and the fiche does not yet distinguish the two.
- Nothing is committed to the results bundle and no runtime row is written: this story produces a record, not evidence.

## Code it changes

- None. A setting or doc gap found here is filed against the story that owns it (order 1 for flags, order 8 for the no-GPU setup path), not fixed here.

## Tests it needs

- None. The proof is the checklist record; a checklist answered from memory rather than from the machine fails this story.

## Evidence it publishes

- `aidd_docs/tasks/2026_09/<date>_machine-readiness/evidence.md`: the checklist with its answers, the three machines' declared facts with their source, the three launch records (command line, `/health`, one completion, GPU-use observation), and the transport each machine will use (push or operator-carried).

## Plan shape

1. Laptop: declared facts and the `cpu_only` launch with the GPU-use observation (agent-executable on the laptop).
2. Tower: the same, by hand.
3. Pro PC: the checklist, then the declared facts and the launch, by hand.
4. Consolidate the record and file each gap against its owning story.

## What the operator runs by hand

On the tower and the pro PC, from a PowerShell prompt:

```powershell
git clone https://github.com/Aliquanto3/wave_local_ai_v2.git
cd wave_local_ai_v2
git switch -c probe/<machine>; git push -u origin probe/<machine>   # then delete the remote branch
uv sync
Get-CimInstance Win32_PhysicalMemory | Select-Object Manufacturer, PartNumber, Speed, ConfiguredClockSpeed, SMBIOSMemoryType, Capacity
Get-CimInstance Win32_Processor | Select-Object Name, NumberOfCores, NumberOfLogicalProcessors
Get-PSDrive -PSProvider FileSystem
<llama-server path> --version
<llama-server path> -m <Qwen3-0.6B-Q8_0.gguf> -ngl 0 -c 32768 -fa on --jinja -np 1 --load-mode auto --port 8080
```

On the GPU machines, `nvidia-smi -l 1` in a second window while one completion runs. Paste every output into the evidence file; the agent turns it into the record.

## Cancellation

n/a — not cancelled.
