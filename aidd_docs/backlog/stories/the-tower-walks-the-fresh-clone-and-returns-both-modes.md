---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/the-laptop-proves-both-modes-and-republishes-the-bundle-once.md
order: 7
---

# Story: The tower walks the fresh clone and returns both modes

**As** a reader comparing the two 32 GB machines
**I want** the tower to reach both modes from a fresh clone following the repo alone, return its rows through its own pull request, and the laptop-versus-tower `cpu_only` result published as what it is
**So that** the second GPU machine is evidence rather than a claim, and the memory comparison is never published as cleaner than the design allows

Maps to: PRD AC "Given the repo cloned fresh onto a different machine... without undocumented manual fixes"; PRD AC "Given a GPU-bearing machine, running a declared `cpu_only` profile..."; PRD Goal on the DDR4-3200 versus DDR5-6000 comparison; Methodology 21; epic decision "The DDR4/DDR5 comparison is published as machine-versus-machine".

## Acceptance

- The tower, from a fresh clone, following `docs/setup.md` alone, installs the toolchain, fetches `llama-server` `b10537` and the `Qwen3-0.6B` weights with their checksum verified, and runs under its declared machine id. Every step taken that the document did not name is added to it. [PRD AC fresh clone]
- `Qwen3-0.6B` runs under the tower's `gpu` profile and its `cpu_only` profile, two runs each, the second against the first. Every row names the tower, the mode and the profile; `cpu_only` rows carry VRAM not applicable; the two modes never receive a verdict against each other. [PRD AC cpu_only rows]
- No tower row receives a throughput verdict against a laptop row: the verdict-blocking fields differ and the verdict says which.
- The tower's rows, fiches and refusal records (if any) reach `main` through the tower's own branch and pull request with CI green, and the merged bundle passes `tests/test_reference_bundle.py` with two machines in it.
- **The laptop-versus-tower `cpu_only` result is published as machine-versus-machine**: memory generation named as the headline difference (DDR4-3200 against DDR5-6000, each marked declared), and **the CPU difference stated beside it** (Ryzen 7 5800H, 8 Zen3 cores, no AVX-512, against Ryzen 5 7600, 6 Zen4 cores, AVX-512), never as a clean DDR4-versus-DDR5 measurement. The observed `cpu_only` generation-throughput ratio is set against the ~2.4x bandwidth ratio the source notes assert, and the text says which term the design cannot separate. [epic decision; PRD Goal]

## Code it changes

- `docs/setup.md`: whatever the walk proves missing.
- `aidd_docs/results/`: the tower's tracked location, fiches, merged bundle.
- `aidd_docs/results/README.md`: a dated section for the tower pass and the machine-versus-machine comparison.

## Tests it needs

- None new unless the walk uncovers a regression; the merged bundle is asserted by the existing `tests/test_reference_bundle.py`.

## Evidence it publishes

- The tower's rows in the bundle.
- The results README section: rows cited by `run_id`, both verdicts per mode, the setup gaps, and the machine-versus-machine comparison with its stated confound.

## Plan shape

1. The operator walks the fresh clone on the tower and reports each gap.
2. The operator runs the two-mode bench session and promotes the runs.
3. The tower's pull request; merge; bundle assertions green.
4. The comparison section and the setup-doc fixes.

## What the operator runs by hand

On the tower, in PowerShell, after closing other GPU and CPU load. Variable and command names are the ones orders 1, 3 and 5 settle; `docs/setup.md` is the authority, this list is the shape:

```powershell
git clone https://github.com/Aliquanto3/wave_local_ai_v2.git; cd wave_local_ai_v2
# follow docs/setup.md sections 1 to 4 exactly, noting every step it did not name
# in .env: the tower's machine id, compute mode gpu, the 0.6B roster entry
uv run wave-local-ai-v2          # run 1, gpu
uv run wave-local-ai-v2          # run 2, gpu, against run 1
# in .env: compute mode cpu_only
uv run wave-local-ai-v2          # run 1, cpu_only
uv run wave-local-ai-v2          # run 2, cpu_only, against run 1
<promote command from order 5> <the four run ids>
git switch -c results/<tower machine id>; git add aidd_docs/results; git commit; git push -u origin results/<tower machine id>
gh pr create --draft
```

Report back: the four `run_id`s, any command that failed with its shortest decisive error line, and every step the doc did not name. The agent writes the README section and fixes the doc from that report.

## Cancellation

n/a — not cancelled.
