---
type: story
status: done
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
order: 7
---

# Story: The pitch opens on one card per use case, read from published rows

**As** a client decision-maker who has a few minutes of attention before the detail
**I want** the pitch to open on one card per use case naming the best local model, its cloud comparator and the runtime and energy headlines, with every label its detail view carries
**So that** I get the answer before the detail without losing the caveats

## Acceptance

- PRD AC "Given the pitch overview, it shows one card per use case": opening the service's root shows the overview; the runs list stays one navigation step away. This replaces order 2's "root opens on the list of runs" as the landing screen, and changes nothing else order 2 established.
- **The use-case set is read, never assumed.** A card exists for each suite present in the quality store. A use case out of scope for the release appears as a labelled empty card when the coverage record names it. While no coverage record exists, the overview states that absence once, naming its owning epic (`no-use-case-is-silently-absent`), and lists no guessed use case — the same rule order 3 applies to the quality view.
- **The best local model is the published leader set, and only the leader set.** Every member is shown when the set holds several. When no leader set is published for that suite and machine class, the card states that absence and shows no model in its place: the highest local score is never substituted for it. Nothing in the repo produces a leader set today (the stats epic records its derivation as unowned), so the shipped behaviour on day one is the stated absence on every card. Relaxing that is the PRD's open question, a product decision, and not this story's to take.
- **Label parity with the detail view.** The leader's score renders through the same label components the quality view uses — indicative, single-judge, contested, contamination-risk, caps and `thinking_policy` — imported from `frontend/src/labels/`, never re-implemented. A score the quality view would withhold is withheld here and its absence stated the same way.
- **The cloud comparator is every cloud subject the store holds for that suite**, each with its own labels and `run_id`. The overview does not pick a best cloud model: that would be a ranking no published row states.
- **Runtime and energy headlines** are those of the leader's `roster_entry_id`, each carrying its fiche reference and its `energy_method` labels through `EnergyMethodLabel`. A headline lacking a label the energy view requires is withheld and its absence stated. With no leader set, there is no model to take a headline from, and the card says so.
- **No figure on the overview is absent from the rows it reads.** The overview scores, ranks, averages and derives nothing; every figure on a card names the `run_id` and field it was read from.
- **Quality and runtime still never arrive in one response.** The overview is served by two routes, one per store (for example `GET /api/overview/quality` and `GET /api/overview/runtime`), and neither returns a figure from the other. A card is one visual unit made of two panels: the quality panel reads only the quality overview, the runtime-and-energy panel reads only the runtime overview, and the card shell that places them side by side reads neither. This is the narrowest reading of the epic's "no response that returns both" rule under which the PRD's card can exist; the epic's Boundaries are amended to say so (see the handoff below).
- The overview routes are `GET`-only, sit behind the same key gate as the four views, answer 405 to every other method, and open no file for writing.
- Readable at pitch distance: the overview renders without horizontal scrolling at 1280×800, and every label is legible without a hover.

## Code it changes

- `src/wave_local_ai_v2/read_model.py` — two selection functions, one per store, returning per-suite leader membership (or its absence), the comparator rows and the leader's runtime and energy headline fields with their labels. Selection only: they filter and resolve, they compute no figure.
- `src/wave_local_ai_v2/service.py` — the two `GET` routes on the existing gated `api` router.
- `frontend/src/views/overview/` (new) — `OverviewView`, the card shell, the quality panel and the runtime-and-energy panel, their types and fixtures.
- `frontend/src/App.tsx` — the overview becomes the landing screen; the runs list is reached from it.
- `frontend/src/api/types.ts` — the two response shapes.

## Tests it needs

- `tests/test_read_model.py` — each selection over the committed reference bundle (every card an honest absence: no leader set, no coverage record) and over a fixture carrying a leader set with two members; a fixture whose leader row lacks `energy_method` yields a withheld headline, never a bare figure.
- `tests/test_service.py` — both routes answer under the key gate off loopback and refuse without it; every non-`GET` method answers 405; neither response carries a key from the other store.
- `frontend/src/views/overview/*.test.tsx` (vitest) — a leader set of two renders both; an absent leader set renders the absence and no model; a withheld score and a withheld energy headline render as absences; an out-of-scope use case renders a labelled empty card; every rendered number is present in the fixture payload it came from.
- `frontend/src/views/boundary.test.ts` — extended: the overview's quality panel imports no runtime or energy type, the runtime-and-energy panel imports no quality type, and the card shell imports neither view model.
- `frontend/src/views/widthGuard.test.tsx` — the overview is added to the 1280×800 guard.

## Plan shape

At most four phases: (1) the two read-model selections and their tests; (2) the two routes and their service tests; (3) the overview panels, card shell and label reuse; (4) landing wiring, the boundary and width guards, and the evidence.

## Evidence it publishes

- Screenshots of the overview over the committed reference bundle (a screen of stated absences, no leader set anywhere) and over a fixture carrying a leader set, filed with the delivery task.
- A dated note in `aidd_docs/results/README.md` recording what the overview withholds on day one and why.

## Cancellation

n/a — not cancelled.
