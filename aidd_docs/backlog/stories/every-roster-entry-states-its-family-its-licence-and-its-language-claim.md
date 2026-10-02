---
type: story
status: done
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
order: 1
---

# Story: Every roster entry states its family, its licence and its language claim

**As** an academic or technical reviewer judging whether the roster's results may be cited and reused
**I want** every roster entry to name its model family, the licence its weights ship under with whether client-side commercial use is permitted and the date those terms were read, and the EN/FR/DE capability its vendor claims with the source of that claim
**So that** I can tell which rows I may act on, and a non-Qwen model can enter the roster without its family being refused by the code that resolves families

Maps to: PRD Dependencies "Licence terms of each roster model permitting the client-side use the reproduction story asks for; a roster entry records the licence and whether client-side commercial use is permitted"; PRD AC "Given the published roster, each size class it publishes spans at least two model families" (the family half); Methodology 11 (family is what judge independence reads), Methodology 13; epic Boundaries "the roster fields the rule needs" (family and licence block), "a verification step per candidate model" (the EN/FR/DE capability recorded as a sourced claim); epic decisions "Licence policy", "EN/FR/DE capability is a claim, not a measurement", "Family resolution for the flagship"; epic Dependencies "`roster.KNOWN_FAMILIES` refuses every candidate family"; epic success check 3 (licence half).

Needs: none. The licence and language terms are read from each shipped entry's model card at its pinned revision; no model run, API key, hardware or operator is required.

Current state: `aidd_docs/roster/models.json` is at `roster_version` 2 with four Qwen entries. The three dense entries carry `family: "qwen"`; the flagship carries none and resolves through `roster.MODEL_FAMILIES`. `roster.KNOWN_FAMILIES` is `{"qwen", "mistral", "google"}`, so `family_of` refuses every other family. No entry records a licence or a language claim.

## Acceptance

- `roster.KNOWN_FAMILIES` grows, additively, to hold the families of the epic's candidate set (Gemma, Granite, Ministral, LFM2, Phi), spelled as Q11 in `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` settles (written to its recommended default: vendor lineage, so Gemma resolves to `google` and Ministral to `mistral`, and `ibm`, `liquid` and `microsoft` are added). No existing value is removed. The judge families (`glm`, `deepseek`) and any subject-only marking are left to the judge epic's stories, which touch the same set.
- A roster entry declaring a family outside `KNOWN_FAMILIES` is refused at load, naming the entry and the value. The flagship still resolves through `MODEL_FAMILIES`, `REQUIRED_FIELDS` does not gain `family`, and `tests/test_roster.py::test_the_shipped_moe_entry_still_loads_with_no_family_of_its_own` keeps passing unchanged.
- Each entry can carry a licence block: the licence id, whether client-side commercial use is permitted (a boolean), the date the terms were read (ISO 8601), and the URL the terms were read from at the entry's revision. The loader refuses a malformed block naming the entry and the field: a non-boolean commercial flag, an unparseable date, an empty id.
- Each entry can carry a language claim: which of EN, FR and DE the vendor states the model supports, and the source of that statement (model card URL at the revision, read date). It is a claim, never a score: no suite result writes to it, and a later suite row contradicting it leaves the claim in place.
- All four shipped entries carry both blocks, read off each repository's own licence and model card at its pinned revision (the flagship at `main`, its read date standing in for the missing sha, as the tech-debt row already records). A test over the shipped file asserts every entry carries both.
- `roster_version` moves, `tests/test_roster.py`'s shipped-version assertion follows the file as it did for version 2, and no published row is edited: rows already published keep the version they were produced under. The fiche hash does not move, since Methodology 14 identifies the model by entry id and checksum only.

## Code it changes

- `src/wave_local_ai_v2/roster.py`: the grown `KNOWN_FAMILIES`, the family check at load, the licence and language-claim blocks on `RosterEntry` and their shape validation.
- `aidd_docs/roster/models.json`: both blocks on the four entries, the version bump.

## Tests it needs

- `tests/test_roster.py`: a constructed entry with each new family loads and `family_of` resolves it; an unknown family is refused naming it; each malformed licence field is refused naming it; the shipped file's four entries all carry both blocks; the flagship still resolves with no `family` of its own.
- `tests/test_reference_bundle.py` passes unchanged.

## Evidence it publishes

- The roster file itself, with the four licences, their read dates and source URLs.

## Cancellation

n/a: not cancelled.
