---
type: story
status: ready
source: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
parent: aidd_docs/backlog/epics/the-same-suite-runs-on-three-machines-or-names-why-it-cannot.md
depends_on:
  - aidd_docs/backlog/stories/the-laptop-proves-both-modes-and-republishes-the-bundle-once.md
  - aidd_docs/backlog/stories/the-tower-walks-the-fresh-clone-and-returns-both-modes.md
order: 8
---

# Story: The no-GPU professional PC publishes rows and refusals beside the GPU machines

**As** someone planning local AI on a standard 16 GB office PC with no GPU
**I want** that machine set up from the repo alone, the model that fits it published as an ordinary row and the model that does not fit refused with its reason published, all merged beside the two GPU machines
**So that** I can anticipate what a professional workstation will actually do, and a machine that cannot run a model is no longer indistinguishable from one that runs it

Maps to: PRD AC "Given the no-GPU professional-PC configuration, it is a declared machine with its own run profiles, and its rows appear in the published tables as ordinary rows distinguished by machine rather than marked as degraded"; PRD AC "given a combination below the model's declared minimum for that mode, the run refuses..."; PRD AC "Given the repo cloned fresh onto a different machine..."; Methodology 21; epic success checks 5, 6 and 7.

The pro-PC walk can run in parallel with order 7; only the final three-machine merge waits for the tower.

## Acceptance

- **`docs/setup.md` gains the no-GPU path before the walk**, written from order 0's record: the CPU build of `llama-server` `b10537` instead of the CUDA asset, no NVML, no CUDA ceiling, the proxy setting if order 0 needed one, the `cpu_only`-only profile, and which roster entries this machine class can and cannot hold. `README.md`'s hardware section names the three machine classes instead of one. [epic Boundaries "the professional PC's own setup path"]
- The professional PC, from a fresh clone, following that path alone, runs `Qwen3-0.6B` under its `cpu_only` profile twice, the second against the first. The rows are ordinary rows: named by machine, mode and profile, VRAM not applicable, no degraded marker, and the second run receives a real `reproduced` or `not_reproduced` against the first, not a permanent `not_comparable`. [PRD AC no-GPU PC; order 1's declared-absent GPU]
- **The flagship refuses** on the same machine in the same session: before `llama-server` starts and before its 18 GB of weights are looked for, naming the RAM requirement, `cpu_only`, the declared minimum and the observed RAM; non-zero exit; no row; one refusal record. [epic success check 5]
- The two dense entries between the two ends (`Qwen3-1.7B`, `Qwen3-4B`) are each either run once under `cpu_only` or refused with a record, so the machine's column in the table is complete: every declared (entry x this machine x `cpu_only`) is a row or a named refusal, never a blank.
- The rows and refusal records reach `main` through the pro PC's own pull request, or through the operator-carried fallback order 0 selected, recorded as operator-carried with source and carrying machine named.
- **The three-machine bundle passes the epic's last two checks**: every pointer resolves, every row's machine id resolves to a declared entry, no two machines' rows share a fiche hash (success check 6); and handed the bundle alone, without `context_input/hardware.md`, a reader can name for any row its machine, its compute mode and that machine's memory generation (success check 7, performed by reading the bundle's files, with the reading recorded).
- **The epic's post-`done` record is filled in**: what the professional PC needed that the README did not say, which (model x machine x mode) combinations refused and on which requirement, and the laptop-versus-tower `cpu_only` result from order 7, including whether the CPU-generation confound turned out to be the larger term.

## Code it changes

- `docs/setup.md` (the no-GPU path), `README.md` (hardware section).
- `aidd_docs/results/`: the pro PC's tracked location, fiches, refusal records, the merged three-machine bundle.
- `aidd_docs/results/README.md`: a dated section for the pro-PC pass.
- The epic file's Success Evidence block, completed (the one write to the parent this epic's close requires).

## Tests it needs

- None new unless the walk uncovers a regression; the three-machine bundle is asserted by `tests/test_reference_bundle.py`.

## Evidence it publishes

- The pro PC's rows and refusal records in the bundle.
- The results README section: rows cited by `run_id`, the refusals with their requirement, the setup gaps.
- The epic's completed post-`done` record.

## Plan shape

1. The no-GPU setup path written from order 0's record.
2. The operator walks it on the pro PC and runs the session.
3. Transport by pull request or operator-carried fallback; three-machine merge; bundle assertions green.
4. The bundle-only reading check, the results README section, the epic's post-`done` record.

## What the operator runs by hand

On the professional PC, in PowerShell. Names are the ones orders 1, 3, 4 and 5 settle; `docs/setup.md` is the authority:

```powershell
git clone https://github.com/Aliquanto3/wave_local_ai_v2.git; cd wave_local_ai_v2
# follow the no-GPU path in docs/setup.md exactly, noting every step it did not name
# in .env: the pro PC's machine id, compute mode cpu_only, the 0.6B entry
uv run wave-local-ai-v2          # run 1
uv run wave-local-ai-v2          # run 2, against run 1
# in .env: the flagship entry (do not download its weights)
uv run wave-local-ai-v2          # must refuse on RAM before starting; copy the refusal line
# in .env: Qwen3-1.7B, then Qwen3-4B, one run each (download each only if the doc says it fits)
<promote command from order 5> <every run id>
# if order 0 recorded push rights:
git switch -c results/<pro-pc machine id>; git add aidd_docs/results; git commit; git push -u origin results/<pro-pc machine id>
# if not: copy the machine's results location and the new fiche files to a USB key,
# and hand them over for the operator-carried commit from the laptop
```

Report back: every `run_id`, the refusal lines verbatim, any failed step with its shortest decisive error line, and every step the doc did not name.

## Cancellation

n/a — not cancelled.
