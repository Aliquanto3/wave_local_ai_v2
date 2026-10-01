---
type: story
status: ready
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
depends_on: aidd_docs/backlog/stories/every-roster-entry-states-its-family-its-licence-and-its-language-claim.md
order: 3
---

# Story: The composition check names every size class and refuses an unlabelled single-family one

**As** an academic or technical reviewer handed a table titled "small language models on ordinary hardware"
**I want** a command that reads the roster and reports, per size class, the families it spans, whether dense and MoE are both present, and whether a single-family class is labelled as a ladder, exiting non-zero when the roster stays silent about any of it
**So that** I can tell a comparison of families from a comparison of quants within one vendor's line, and the composition rule is something that can fail rather than prose

Maps to: PRD AC "Given the published roster, each size class it publishes spans at least two model families, with dense and MoE both present where the class has both, and any single-family size class is labelled as such in the table"; Methodology 13 (the composition rule and the single-family-ladder label); epic Boundaries "the composition rule as an executable check", "the size-class definition itself", "the roster fields the rule needs" (`size_class` and the footprint figures); epic decisions "What a size class is measured in", "The initial boundaries", "What the check refuses", "Where the class has them", "Family resolution for the flagship"; epic success checks 1, 2, 3, 4 and 7 (its composition half).

Needs: none. Constructed rosters exercise every outcome, and the shipped roster is the calibration; no model run, API key, hardware or operator is required.

Current state: `grep -rn "size_class" src/` returns nothing; `architecture.active_params_b` is the only size-shaped field, and no entry records total parameters or bytes on disk. Nothing gates the roster's composition; `suite_gate.py` gates suites only.

## Acceptance

- The size class is a fixed ordered vocabulary of four values (the epic's ~0.5B, ~2B, ~4B and ~8B-and-up), banded on total parameters, as Q10 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles: below 1B is ~0.5B, from 1B to below 3B is ~2B, from 3B to below 6B is ~4B, and 6B and up is ~8B-and-up. The edges are held as configuration beside the vocabulary and stated as revisable after the first full-roster run. Moving an edge is a value change and a re-class, never a rewrite of the check.
- Bytes on disk is the footprint figure: recorded on every entry and published beside its class, never banded and never read by the class-agreement check. Whether an entry fits a given machine stays with the machine epic's profiles, not with the size class.
- Each entry declares `size_class` and the two figures that justify it, total parameters and the GGUF's bytes on disk, beside the existing `active_params_b`. The four shipped entries carry all three, the bytes read off the files (`docs/setup.md` already records them) and the totals off each GGUF's metadata.
- The roster carries one declaration per class: whether it is a single-family ladder, whether a MoE candidate was sought, which entry represents it if one was found, and the reason when none is represented. Where this declaration lives (the roster file or a record beside it) is the implementer's to choose; it is data, never prose in a README.
- The check reports, per class, the families it spans, whether dense and MoE are both present, and its ladder label, and exits non-zero naming the class or entry when: a class spans one family without the single-family-ladder label; an entry has no family `roster.family_of` can resolve, no `size_class`, or no licence block; an entry's declared class disagrees with the band its total parameters fall in; a class has no MoE represented and no reason recorded. A class spanning two families passes; a labelled single-family class passes.
- Calibration, before any new entry is authored: run against the shipped roster, the check reports four classes, each spanning exactly one family (`qwen`), and exits non-zero naming all four as unlabelled. A check that passes on today's roster is a failed acceptance. The shipped roster is not labelled by this story: the search that would justify a label belongs to orders 5 to 8.
- The flagship resolves its family through the in-code fallback; no exception is carved out for it and `REQUIRED_FIELDS` does not gain `family`.
- Every quality row written after this story carries the `family` and `size_class` of the entry it cites, added to the row contract additively under the row epic's writer gate: the schema version moves and no earlier row is back-filled.
- `aidd_docs/results/README.md` gains a roster composition section produced from the check's output: per class, its families, dense and MoE presence, its label or its absence, the MoE reason, and per entry its total parameters, its bytes on disk, its licence id, commercial-use flag and read date. Today it states four unlabelled single-family classes, which is the honest state.
- The check is a documented step before a roster table is published. It is not added to the merge gate while the shipped roster is expected to fail it.

## Code it changes

- `src/wave_local_ai_v2/` (new composition-check module and its command): reads the roster, classes the entries, prints the per-class report, sets the exit code.
- `src/wave_local_ai_v2/roster.py`: `size_class`, total parameters and bytes on disk on an entry, and the per-class declaration, with their shape validation.
- `src/wave_local_ai_v2/row_contract.py`, `quality_cli.py`: `family` and `size_class` on quality rows.
- `aidd_docs/roster/models.json`: the three figures on the four shipped entries, the version bump.
- `aidd_docs/results/README.md`: the composition section.

## Tests it needs

- A new composition-check test module over constructed rosters: one class with two families passes for that class; the same roster with the second family removed and the label added passes as a labelled ladder; removed and unlabelled, it exits non-zero naming the class. A class with no MoE and no reason exits non-zero; with the reason recorded it passes. An entry with no resolvable family, no class or no licence is named, never skipped; an entry whose class disagrees with its total parameters is named, one test per edge (an entry just below and one at each of 1B, 3B and 6B); an entry whose bytes on disk alone would suggest another class is not named.
- The same module run over the shipped file: four classes, one family each, non-zero exit naming four classes.
- `tests/test_row_contract.py`: a quality row without `family` or `size_class` is refused at the new schema version; an earlier-version row still validates.

## Evidence it publishes

- The calibration output on the shipped roster, quoted in the README's composition section.

## Cancellation

n/a: not cancelled.
