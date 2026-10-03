---
type: story
status: proposed
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
depends_on:
  - aidd_docs/backlog/stories/the-composition-check-names-every-size-class-and-refuses-an-unlabelled-single-family-one.md
  - aidd_docs/backlog/stories/a-candidate-model-enters-the-roster-only-through-the-verification-gate-or-leaves-a-recorded-refusal.md
order: 6
---

# Story: The ~2B class spans two families, or is published as a searched single-family ladder

**As** an academic or technical reviewer reading the ~2B row of the published table
**I want** the class to hold a second family beside `Qwen3-1.7B`, scored on the same classification and translation items, or to be labelled a single-family ladder with every refused candidate's record behind the label
**So that** a difference I read at this size is a difference between models, not between quants of one vendor's line

Maps to: PRD AC "Given the published roster, each size class it publishes spans at least two model families, with dense and MoE both present where the class has both, and any single-family size class is labelled as such in the table"; PRD AC "Given the model roster, for each in-scope use case it includes at least one MoE candidate and at least one tiny dense candidate, run over the same items with results shown side by side, and each of them cites its entry in the versioned roster file"; Methodology 3, 4, 13; epic Boundaries "candidate coverage across the gap brief's families" (Granite 1B), "a recorded refusal for every candidate that does not enter", "the existing suites re-run on the dev machine as each addition's acceptance", "the roster version bump and the `docs/setup.md` download section per model added"; epic decisions "Where the class has them", "Unsupported architecture: defer by default", "EN/FR/DE capability is a claim, not a measurement"; epic Dependencies "Whether any MoE candidate exists in GGUF below the top class"; epic success check 6.

Needs: a real local model run on the dev machine (gate downloads of roughly 1 to 2 GB per candidate, one load each, then both suites per entry). No API key; an operator only if a candidate is refused for its architecture, since the build-upgrade tradeoff is the owner's.

Blocked: by the spike `aidd_docs/backlog/spikes/which-candidate-ggufs-exist-per-size-class-and-does-the-pinned-build-load-them.md` (`blocked`), which still needs the live gate runs under b10537 of this class's candidates, each with its `/props` template: the LFM2 candidate Q107 picks (`lfm2`), Granite 3.1 1B-A400M (MoE, `granitemoe`), Granite 4.0 H 1B (`granitehybrid`) and Granite 4.0 1B (`granite`); by Q107 (which LFM2 model stands for the line at ~2B: `LFM2.5-1.2B-Instruct` under options (a) and (b), `LFM2-1.2B` under (c)) and by Q108 (whether those loads are this story's own first gate runs, which drops the spike from this line), both in `aidd_docs/tasks/2026_10/2026_10_02_backlog-refinement/owner-questions.md`. Both `depends_on` targets are `done`.

Current state (verified on `main` at `c68b23e`, 2026-10-03): the class holds one entry, `qwen3-1.7b-q8` (`Q8_0`, 1,720,574,976 total params, 1,834,426,016 bytes on disk), and its `size_classes` declaration in `aidd_docs/roster/models.json` (`roster_version` 4) is `single_family_ladder: false`, `moe_sought: false`, `moe_entry: null`, `moe_absent_reason: null`, so the README's composition block names two failures for it ("spans one family (qwen) without the single-family-ladder label", "has no MoE represented and no reason recorded"). `roster.KNOWN_FAMILIES` already holds `ibm` and `liquid`. `candidate_gate.run_gate` writes a pass record whose `entry` block carries `size_class` (`roster.size_class_for`), `bytes_on_disk`, `architecture.total_params`, `kind` and `expert_count` read off the GGUF header (`<arch>.expert_count`, so a `granitemoe` file enters as `moe`), so an entry is a copy of that block. `composition_check._class_failures` names a class whose MoE entry its declaration's `moe_entry` does not name, so a MoE that enters moves `moe_sought` and `moe_entry` with it. The candidate record file `candidate_gate.DEFAULT_RECORDS_PATH` (`aidd_docs/roster/candidate-records.jsonl`) does not exist yet. `roster.SizeClassDeclaration` has four fields only: the ladder label is a boolean with no field naming refused candidates, so the refusals behind a label are read from the candidate record and named in the README's composition section.

## Acceptance

- The class's shortlist, as Q12 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles it, is Granite 1B and the LFM2 model of this class, plus any MoE GGUF the spike finds at this class, all restricted to the epic's families. The candidates go through the gate (order 4) one at a time, smallest download first. Each candidate is taken at the quant of the class's Qwen entry (`Q8_0`) where its publisher ships it, otherwise at the nearest quant shipped, with the difference stated in the candidate record and on the README's composition section, so a family comparison is not read as a quant comparison. The search stops when one non-Qwen family passes (which suffices; the class does not seek a third) and the MoE question below is answered. Every refusal on the way stays in the candidate record.
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

- `tests/test_roster.py`: the new entries load, resolve their family and follow the version bump; the composition check's tests over the shipped file and its README block (`tests/test_composition_check.py`, `test_the_shipped_roster_reports_four_single_family_classes_and_fails`, `test_the_readme_quotes_the_check_output_on_the_shipped_roster`) are updated to the new composition of this class.

## Evidence it publishes

- The new entries' classification and translation rows, the candidate record's passes and refusals for this class, and the composition section showing the class's state.

## Cancellation

n/a: not cancelled.
