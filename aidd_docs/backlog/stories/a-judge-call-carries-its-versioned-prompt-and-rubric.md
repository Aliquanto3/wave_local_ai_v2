---
type: story
status: ready
source: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
parent: aidd_docs/backlog/epics/any-open-ended-output-carries-two-judges-or-an-honest-flag.md
depends_on: aidd_docs/backlog/stories/a-second-cloud-provider-answers-suite-items-as-a-subject.md
order: 3
---

# Story: A judge call carries its versioned prompt and rubric

**As** a client-side engineer auditing a judged score
**I want** every judge call to name the prompt it issued, in the item's own language, and the rubric version it applied, both re-renderable from the row
**So that** a judged score can be re-derived from the row alone rather than taken on trust

## Acceptance

- Methodology 10: a judged row records each judge's dated model id, the judge prompt id, that prompt template's content hash, and the rubric version.
- Methodology 10: the judge prompt is issued in the item's own language. EN, FR and DE each have their own template variant, and the row names which variant the call used.
- The judge prompt id and content hash re-render the exact prompt that was sent. Editing a template changes its hash, and rows written before the edit stay attributable to the text they actually used — the hash comes from `prompt_provenance.template_hash` over the template, not over the filled prompt, so a per-item substitution does not move it.
- An item whose language has no template variant is refused, naming the language. It is never silently judged in English.
- The rubric is versioned independently of the prompt template: the same template under a revised rubric writes a different rubric version, and a row states both.
- One judge call runs through either provider's client behind one interface. The judge module never imports a single provider's error type directly, so adding or swapping a provider does not reopen it.
- Each judge call records its raw returned text on the row beside the parsed score. `aidd_docs/results/README.md` records that Mistral at `temperature=0` with a pinned `random_seed` did not reproduce one item across two runs, so a judge call is not assumed reproducible and the row carries what was actually returned.
- A judge response that cannot be parsed into the rubric's scale fails that judge call with a named reason. It is never scored as zero — a zero is a judgement, an unparseable response is a missing one.
- Judge fields extend the quality row's required-field list additively, under a `SCHEMA_VERSION` bump: an existing deterministic row keeps validating unchanged, and a judged row missing any judge field cannot be written.
- Every judge call records that the item and the subject's output left the machine, and to which provider — the PRD's egress criterion applied to the calls this story introduces.

## Code it changes

- `src/wave_local_ai_v2/judge_protocol.py` (new) — the versioned judge prompt templates, one variant per language, their ids and hashes, and the versioned rubrics. Templates live in code beside `classification_suite.py`'s items, not in a data file, so a template edit is a reviewable diff.
- `src/wave_local_ai_v2/judge.py` (new) — the provider-agnostic judge-call interface, the parse of a judge response into the rubric's scale, and the per-call record (raw text, parsed score, judge model id, failure reason).
- `src/wave_local_ai_v2/prompt_provenance.py` — the judge template ids reuse `template_hash`; no second hashing rule is introduced.
- `src/wave_local_ai_v2/row_contract.py` — the judge fields added to the `quality` kind, and `SCHEMA_VERSION` bumped with the reason recorded in the version comment block, as every prior bump is.

## Tests it needs

- `tests/test_judge_protocol.py` (new) — an FR item renders the FR variant and a DE item the DE one; an item in a language with no variant raises naming that language; editing a template's text changes its hash; a rubric revision changes the rubric version and leaves the template hash alone.
- `tests/test_judge.py` (new, HTTP stubbed) — a stubbed judge response parses to a score on the rubric's scale; a response outside the scale and an unparseable one each fail the call with a reason and are not scored zero; the same call runs through both provider clients through one interface with only their HTTP stubbed.
- `tests/test_row_contract.py` — a judged row missing any one judge field is refused with that field named; an existing deterministic quality row still validates under the bumped schema version.

## Evidence it publishes

- A judged row whose prompt id and hash re-render the prompt that was sent, shown by rendering from the row rather than from the template source.
- The FR and DE variants shown as they were issued, read off a row — the epic's third success check.

## Cancellation

n/a — not cancelled.
