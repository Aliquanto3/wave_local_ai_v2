---
type: story
status: proposed
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
depends_on:
  - aidd_docs/backlog/stories/the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one.md
  - aidd_docs/backlog/stories/a-candidate-model-enters-the-roster-only-through-the-verification-gate-or-leaves-a-recorded-refusal.md
order: 8
---

# Story: The top class spans two families with dense and MoE, or says why not

**As** a client decision-maker weighing the largest model a consumer machine can hold against a cloud model
**I want** the ~8B-and-up class to hold a second family beside the `Qwen3.6-35B-A3B` flagship, and a dense model beside the MoE ones, all scored on the same classification and translation items, or to say which of the two requirements it misses and why
**So that** the headline local model is compared against a rival, not only against its own vendor's smaller siblings, and a MoE win is read against a dense model of the same footprint class

Maps to: PRD AC "Given the published roster, each size class it publishes spans at least two model families, with dense and MoE both present where the class has both, and any single-family size class is labelled as such in the table"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side, and each of them cites its entry in the versioned roster file"; Methodology 3, 4, 13; epic Boundaries "candidate coverage across the gap brief's families" (Gemma 4 including the 26B-A4B MoE), "a recorded refusal for every candidate that does not enter", "the existing suites re-run on the dev machine as each addition's acceptance", "the roster version bump and the `docs/setup.md` download section per model added"; epic decisions "Where the class has them", "Unsupported architecture: defer by default", "EN/FR/DE capability is a claim, not a measurement"; epic Dependencies "Whether the tower ... holds a Gemma-4-class 26B-A4B MoE at a usable quant", "Bench cost" (disk headroom checked before a download); epic success check 6.

Needs: a real local model run on the dev machine (gate downloads in the order of 7 GB for a dense candidate and 16 GB for a MoE one, one load each with CPU expert offload as the flagship runs, then both suites per entry). No API key; an operator only if a candidate is refused for its architecture, since the build-upgrade tradeoff is the owner's.

Blocked: by the spike `aidd_docs/backlog/spikes/which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them.md`, which establishes which of this class's shortlisted GGUFs exist, at which quants, and whether the pinned build loads them.

Current state: the class holds one entry, the MoE flagship, so it has no second family and no dense model.

## Acceptance

- The class's shortlist, as Q12 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles it, is Gemma 4 26B-A4B (MoE) and Gemma 4 12B (dense); GPT-OSS 20B, Qwen3-Coder-30B-A3B and Mellum2-12B-A2.5B stay out, being outside the epic's families. The candidates go through the gate (order 4) one at a time, smallest download first, with free disk checked before each download. Each candidate is taken at the quant of the class's Qwen entry (`UD-IQ4_XS`) where its publisher ships it, otherwise at the nearest quant shipped, with the difference stated in the candidate record and on the README's composition section, so a family comparison is not read as a quant comparison. The search stops when one non-Qwen family passes (which suffices; the class does not seek a third) and both a dense and a MoE entry are represented, or when the shortlist is exhausted. Every refusal on the way stays in the candidate record.
- Each passing candidate enters `aidd_docs/roster/models.json` from its pass record: a commit-sha revision, the sha256 read off the file, quant, architecture (a MoE with its expert count and active-parameter figure), `family` declared in the file, `size_class` (the band its total parameters fall in) with its two figures, total parameters and bytes on disk, licence block, language claim and thinking control. `roster_version` moves under the existing rule, and `docs/setup.md` gains its download section on the pattern step 3.1 set: `hf download <repo> <file> --revision <sha>`, then `Get-FileHash -Algorithm SHA256 ... .ToLower()`.
- Each new entry runs the classification and translation suites to completion through the local chat path on the dev machine, launched with the flags its entry declares; a MoE entry declares its host expert offload and is refused by `validate_host_fit` if it exceeds its expert count, and where the declared offload does not fit, the value that launched is recorded rather than the one hoped for. Its rows carry its `roster_entry_id`, its `family`, its `size_class`, and the `thinking_policy` its verified control applied. They join the published store as new rows; nothing published is edited.
- The class's declaration states two families, or carries the single-family-ladder label citing the refused candidates; and states dense and MoE both represented, or which is missing with the reason recorded (for example, a candidate that would not load on the dev machine is named with the load failure, not left blank).
- The flagship keeps its `revision: "main"` pin and its byte-identical launch: the tech-debt row owns that fix, and this story does not retro-fit it.
- The composition check (order 3) passes for this class, and the README's composition section is regenerated from it.
- A candidate refused because the pinned build does not load its architecture is deferred and recorded. The story raises the build-upgrade tradeoff to the owner and never changes the pinned build itself.
- Where an entry's suite rows contradict its EN/FR/DE claim, the claim stays and the README names the contradiction as a finding.

## Code it changes

- `aidd_docs/roster/models.json`, the candidate record, `docs/setup.md`, `aidd_docs/results/` (new rows, the regenerated composition section). No `src/` change is expected; one that proves necessary is a finding to name in the story's evidence.

## Tests it needs

- `tests/test_roster.py`: the new entries load, resolve their family and follow the version bump, and a new MoE entry passes `validate_host_fit` with its declared offload; the composition check's test over the shipped file is updated to the new composition of this class.

## Evidence it publishes

- The new entries' classification and translation rows, the candidate record's passes and refusals for this class, and the composition section showing the class's state. Once this story is done, the epic's closing record (which candidates were refused and on what, which classes stayed labelled ladders, whether the pinned build held, whether the four class boundaries survived) can be written from the candidate record.

## Cancellation

n/a: not cancelled.
