---
type: story
status: proposed
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
depends_on:
  - aidd_docs/backlog/stories/the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one.md
  - aidd_docs/backlog/stories/a-candidate-model-enters-the-roster-only-through-the-verification-gate-or-leaves-a-recorded-refusal.md
order: 7
---

# Story: The ~4B class spans two families, or is published as a searched single-family ladder

**As** a consultant recommending a small dense model for a client's classification or translation work
**I want** the ~4B class to hold a second family beside `Qwen3-4B`, scored on the same classification and translation items, or to be labelled a single-family ladder with every refused candidate's record behind the label
**So that** the class the project's own candidate notes single out for classification ("a small dense classifier, 3-4B class") is a comparison of vendors, not a recommendation of the only one measured

Maps to: PRD AC "Given the published roster, each size class it publishes spans at least two model families, with dense and MoE both present where the class has both, and any single-family size class is labelled as such in the table"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side, and each of them cites its entry in the versioned roster file"; PRD User Story "As a consultant, I want tiny dense models compared alongside MoE models on each use case"; Methodology 3, 4, 13; epic Boundaries "candidate coverage across the gap brief's families" (Ministral, Phi), "a recorded refusal for every candidate that does not enter", "the existing suites re-run on the dev machine as each addition's acceptance", "the roster version bump and the `docs/setup.md` download section per model added"; epic decisions "Where the class has them", "Unsupported architecture: defer by default", "EN/FR/DE capability is a claim, not a measurement"; epic Dependencies "Whether any MoE candidate exists in GGUF below the top class"; epic success check 6.

Needs: a real local model run on the dev machine (gate downloads of roughly 2 to 3 GB per candidate, one load each, then both suites per entry). No API key; an operator only if a candidate is refused for its architecture, since the build-upgrade tradeoff is the owner's.

Blocked: by the spike `aidd_docs/backlog/spikes/which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them.md`, which establishes which of this class's shortlisted GGUFs exist, at which quants, and whether the pinned build loads them.

## Acceptance

- The class's shortlist, as Q12 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles it, is Ministral 3B and the Phi mini model, plus any MoE GGUF the spike finds at this class, all restricted to the epic's families. The candidates go through the gate (order 4) one at a time, smallest download first. Each candidate is taken at the quant of the class's Qwen entry (`Q4_K_M`) where its publisher ships it, otherwise at the nearest quant shipped, with the difference stated in the candidate record and on the README's composition section, so a family comparison is not read as a quant comparison. The search stops when one non-Qwen family passes (which suffices; the class does not seek a third) and the MoE question below is answered. Every refusal on the way stays in the candidate record.
- Each passing candidate enters `aidd_docs/roster/models.json` from its pass record: a commit-sha revision, the sha256 read off the file, quant, architecture, `family` declared in the file, `size_class` (the band its total parameters fall in) with its two figures, total parameters and bytes on disk, licence block, language claim and thinking control. `roster_version` moves under the existing rule, and `docs/setup.md` gains its download section on the pattern step 3.1 set: `hf download <repo> <file> --revision <sha>`, then `Get-FileHash -Algorithm SHA256 ... .ToLower()`.
- Each new entry runs the classification and translation suites to completion through the local chat path on the dev machine, launched with the flags its entry declares; where the declared offload does not fit, the value that launched is recorded rather than the one hoped for. Its rows carry its `roster_entry_id`, a `family` other than `qwen`, its `size_class`, and the `thinking_policy` its verified control applied. They join the published store as new rows; nothing published is edited.
- Where the spike found a MoE GGUF at this class, it is taken through the gate like any candidate; where it found none, the class records that a MoE was sought and the search that came back empty, so "dense-only by nature" is distinguishable from "not looked at".
- The class's declaration states two families, or carries the single-family-ladder label citing the refused candidates.
- The composition check (order 3) passes for this class, and the README's composition section is regenerated from it.
- A candidate refused because the pinned build does not load its architecture is deferred and recorded. The story raises the build-upgrade tradeoff to the owner and never changes the pinned build itself.
- Where an entry's suite rows contradict its EN/FR/DE claim, the claim stays and the README names the contradiction as a finding.

## Code it changes

- `aidd_docs/roster/models.json`, the candidate record, `docs/setup.md`, `aidd_docs/results/` (new rows, the regenerated composition section). No `src/` change is expected; one that proves necessary is a finding to name in the story's evidence.

## Tests it needs

- `tests/test_roster.py`: the new entries load, resolve their family and follow the version bump; the composition check's test over the shipped file is updated to the new composition of this class.

## Evidence it publishes

- The new entries' classification and translation rows, the candidate record's passes and refusals for this class, and the composition section showing the class's state.

## Cancellation

n/a: not cancelled.
