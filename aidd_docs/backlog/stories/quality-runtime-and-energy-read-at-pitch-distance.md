---
type: story
status: ready
source: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on: aidd_docs/backlog/stories/the-browser-opens-on-the-list-of-runs-behind-its-own-gate.md
order: 3
---

# Story: Quality, runtime and energy read at pitch distance, every caveat on screen

**As** a client decision-maker judging the on-prem-versus-cloud question at a glance
**I want** the quality table, the runtime table with its fiche, and the energy detail each on their own screen, with every mark the methodology puts on a number carried onto that screen
**So that** I can read the comparison without reading the repo, and cannot read a number that is more confident than the row behind it

## Acceptance

- PRD AC "a dashboard presents those four views without the viewer touching a terminal": the quality table, the runtime table with its fiche, and the per-run energy detail each render as their own screen, over the read-model's four routes and nothing else.
- **Quality and runtime never arrive together.** No screen shows a quality figure and a runtime figure, no component reads both view models, and no navigation composes them. This is the epic's fifth success check, and it is enforced by the component boundary rather than by page layout.
- Methodology 14 and PRD AC "it always references a hardware fiche": the fiche is on every runtime view, not behind a toggle — CPU, RAM, GPU, driver, llama.cpp build, quant, the launched flag list, and the hash the row cites. A hash the service could not resolve is shown as that absence, naming the hash.
- Methodology 15 and PRD AC "a single headline number in kg CO2e is displayed together with its energy_method label": the headline is one `emissions_kg` figure carrying its three per-channel labels, with a drill-down to per-channel energy, the emission factor, the region, the scope and the Scope-3 formula id. A run whose three channels are not all labelled shows **no** headline and states which label is missing. Wherever a Scope-2 local figure appears beside a Scope-3 cloud one, that row's own `scope_comparability` sentence is on the screen, not in a footnote elsewhere.
- Methodology 11 and PRD AC "never presented without both judges' scores and their agreement level": a judged score renders only with two judges and an agreement figure, or with the single-judge flag visible. A row carrying neither is rendered as a declared absence and never as a plain score. Neither store holds a judged row today, so the shipped behaviour on day one is the absence, honestly stated — the surface does not wait for the quality epic to become correct.
- PRD AC "the item is published as contested and excluded from that suite's headline score": a contested item is marked contested and the headline states how many items it excluded.
- Methodology 8 and PRD AC "an explicit verdict of reproduced, not reproduced, or not comparable": each row's verdict is on screen as one of the three, with the reference run id it was compared against or the fiche fields that differ.
- Methodology 7: a runtime row flagged `unreliable` says so beside its throughput, with the spread figure that raised the flag. The `ttft_ms` and `prompt_tok_per_s` spreads are shown for interpretation and are visibly not the flag.
- Methodology 20: `ttft_source` is on the runtime view beside the TTFT it qualifies, so a server-reported figure and a client-measured one are never read as the same measurement.
- Methodology 4: every per-language cell carries its `n` and its indicative mark, and a suite-level indicative mark carries its `indicative_reasons`. The two score shapes stay visually separate: an exact-match accuracy and a graded chrF mean never share a column.
- Methodology 5: an item declaring public provenance is marked contamination-risk in the table.
- Methodology 9: failure counts are on the row with the four reasons distinguished, so an empty generation, an unparseable one, a suite-cap truncation and a context-limit truncation are four visible states rather than one.
- Methodology 3: the caps the score was produced under — `max_output_tokens`, `stop_sequences`, `context_length` and `thinking_policy` — are readable beside it. A routing score produced under `thinking_policy: disabled` is a routing score, never the model's ceiling, and the screen says which was measured.
- PRD AC "each of the nine task use cases ... or is marked out of scope for this release as a labelled empty row": the coverage record renders when the store carries one, and is a declared absence naming its owning epic (`no-use-case-is-silently-absent`) when it does not. That epic's Boundaries assign the rendering here and the record itself there; this story builds the surface and fabricates no entry.
- Readable at pitch distance, made checkable rather than asserted: every table renders without horizontal scrolling at 1280×800, every number carries its unit (the runtime view carries two memory units that are genuinely different — `process_rss_bytes` in decimal MB and `vram_used_mib` in MiB — and labels them as such), and every mark above is legible without a hover.

## Code it changes

- `frontend/src/views/quality/`, `frontend/src/views/runtime/`, `frontend/src/views/energy/` (new) — the three screens.
- `frontend/src/labels/` (new) — the shared label components each methodology mark renders through: indicative, contamination-risk, contested, single-judge, unreliable, verdict, per-channel energy method, scope comparability, declared absence. One component per mark, so a mark cannot be rendered in two ways on two screens.
- `src/wave_local_ai_v2/read_model.py` — the fields these screens name that the four routes did not yet carry: the suite's caps and `thinking_policy`, `contamination_risk`, `indicative_reasons`, the failure-count breakdown, `ttft_source` and the three spread figures.
- `frontend/src/api-client.ts` — no change beyond the routes it already calls; the screens fetch through it and nowhere else.

## Tests it needs

- `frontend/src/**/*.test.tsx` (vitest) — one test per refusal, each able to fail: a run missing one energy channel label renders no headline and names the missing label; a quality row with no judge block renders the absence and no score; a judged fixture with neither agreement nor the single-judge flag renders no plain score; a contested item is excluded from the headline and the exclusion count is shown; an `unreliable` row is flagged; a suite-level and a per-language indicative mark both render; a contamination-risk item is marked; a `not_comparable` verdict names the differing fiche fields.
- A structural test that no quality component imports the runtime or energy view model and no runtime component imports the quality one — the epic's fifth check asserted at the boundary rather than by inspecting a rendered page.
- `tests/test_read_model.py` — the added fields carry their absences under the committed bundle's `"7"` rows, which predate several of them.

## Evidence it publishes

- Screenshots of the three screens over the committed reference bundle and over the live stores, filed with the delivery task: the bundle at `schema_version` `"7"` shows a screen full of honest absences, the live store at `"11"` shows the same screens populated, and neither required a code change.
- A section in `aidd_docs/results/README.md` recording what the dashboard withholds and why — the judged score with no judged row behind it, the energy headline with an unlabelled channel, the coverage record that does not exist yet — so the withholding is documented evidence rather than an apparent gap.

## Cancellation

n/a — not cancelled.
