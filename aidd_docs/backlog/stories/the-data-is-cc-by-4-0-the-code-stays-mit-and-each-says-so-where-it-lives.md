---
type: story
status: done
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
order: 1
---

# Story: The data is CC-BY 4.0, the code stays MIT, and each says so where it lives

**As** a third-party researcher who found the published results
**I want** a licence statement that names exactly which parts of the repository's data I may reuse under CC-BY 4.0, which parts it does not grant, and why
**So that** I can republish or re-analyse the results without asking anyone, and without relying on a grant the owner could not make

Maps to: PRD User Story "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself"; PRD AC "Given a published release, its suite items and reference result bundle carry CC-BY 4.0 while the code stays MIT" (the licence half); Methodology 5 (redistribution terms attach to the item); epic Boundaries "the licence split, declared where each side lives" and "mixed terms inside one download, stated part by part"; epic decision "The licence file names what it covers, item by item where it must"; epic success check 3 (terms for every part), and the epic's falsification clause.

Needs: none. Files and a test only; no model run, API key, hardware or operator is required.

Current state: `LICENSE` is MIT and names the code. Nothing states terms for `aidd_docs/results/`, `aidd_docs/roster/models.json` or the suite definitions; `README.md` has no licence section.

## Acceptance

- `LICENSE` is unchanged: MIT, naming the code.
- `LICENSE-DATA` at the repository root carries the CC-BY 4.0 licence text in full and a scope section naming exactly what it covers: the repository's hand-written suite items as published in `aidd_docs/results/suite-definitions/` and in the rows' item fields, the reference bundle's rows (the current `*-reference.jsonl` files and the superseded ones retained beside them), `aidd_docs/results/fiches/`, `aidd_docs/roster/models.json` and `aidd_docs/results/suite-definitions/`. The untracked per-machine `runtime.jsonl` and `quality.jsonl` are named as not published and not covered.
- The scope section names what the repository does not own and does not grant: model weights, the third-party licences the roster records, and the model-output fields the rows carry (`predicted_label` today). The output fields are named as a separate part, redistributed on the author's declaration that this is permitted, stated as unverified against each model's and provider's terms until `aidd_docs/backlog/spikes/may-the-model-outputs-in-the-published-rows-be-redistributed-and-on-what-terms.md` concludes. Nothing in the file implies CC-BY 4.0 over a part it names as not granted.
- A drawn-items section exists from the start: it states that the bundle holds no item drawn from a public benchmark today, and that a drawn item carries its source's licence, recorded per item, rather than CC-BY 4.0. Filling it is order 7's, not this story's.
- The two assumptions the epic names are disclosed in the file, not buried: the hand-written items are stated to be the owner's to license, unverified against any employment or client agreement, and the output declaration above is stated as unverified.
- A short notice sits in each covered directory (`aidd_docs/results/`, `aidd_docs/results/fiches/`, `aidd_docs/results/suite-definitions/`, `aidd_docs/roster/`) stating the terms and pointing to `LICENSE-DATA`, so a directory copied out of a clone carries its terms with it.
- `README.md` gains a licence section stating the split in plain words (code MIT, data CC-BY 4.0 with the named exclusions) and linking both files. The attribution string a reuser reproduces lands in that section with order 2; until then the section says where it will be.
- Each module in `src/wave_local_ai_v2/` that holds hand-written item literals (`judge_probe.py` since the suites moved to `suite_data/`) carries a header notice stating that its item literals are CC-BY 4.0 under `LICENSE-DATA` while the surrounding code is MIT, and `LICENSE-DATA`'s scope section names those modules (owner answer to Q43, option a).

## Code it changes

- `LICENSE-DATA` (new), one notice file per covered directory (new), `README.md` (licence section), and a header notice in each suite module holding item literals. No behaviour change.

## Tests it needs

- A test that every covered path named in `LICENSE-DATA` exists, every covered directory holds its notice, and `LICENSE` still names MIT, so a covered directory added later without a notice, or a renamed path, fails.

## Evidence it publishes

- `LICENSE-DATA` itself, and the README section, read by someone who did not write them: for each part of the repository's data they can say under which terms it may be reused.

## Cancellation

n/a: not cancelled.
