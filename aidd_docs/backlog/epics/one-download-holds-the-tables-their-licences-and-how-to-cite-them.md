---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
depends_on:
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
---

# Epic: One download holds the tables, their licences and how to cite them

Given one release asset and no clone, a third party opens flat tables of every published result, reads under which terms each part of that download may be reused, recomputes the headline numbers from the per-item rows, and cites the exact release in a form the repository states.

## Context and Value

The audience is the third one the PRD adds for the publication, in its own user story: "As a third-party researcher, I want the suite items and the result bundle under an open licence and in a tabular export, so that I can re-analyse the published results without cloning and running the project myself." Acceptance criterion 138 states it as a release property: "its suite items and reference result bundle carry CC-BY 4.0 while the code stays MIT, and the published results are also available as a tabular export readable outside the repo without running it." The gap brief's gap 8 says the same from the owner's side, and the 2026-09-06 decision settles the split: code MIT, suite items and reference bundle CC-BY 4.0.

Gap 8 is the one item the brief's priority order marks "continuous" rather than queued behind the run campaign, and the reason is visible in the current state: the licensing half costs no bench time and blocks every downstream reuse until it exists.

Verified current state, at `0f849c8`:

- **The data is published under a licence that does not describe it.** `LICENSE` is MIT and names the code, "Copyright (c) 2026 Aliquanto3". Nothing states terms for `aidd_docs/results/`, `aidd_docs/roster/models.json` or the suite definitions. The 82 published rows, the five fiches, the four suite-definition files and the roster therefore sit in a public repository with a software licence beside them and no permission statement about them. `README.md` has no licence section at all: its headings run Who this is for, Hardware, Setup, Results layout, Energy caveat, Pull and run, Project status.
- **There is no `CITATION.cff` and no attribution string anywhere.** A reuser who wants to comply with an open licence has nothing to reproduce, and a reviewer who wants to cite the work has nothing to copy.
- **Nothing is readable without following pointers.** `aidd_docs/results/README.md` states the bundle's whole property: five parts, "No one file in this set is self-sufficient" — `fiche_hash` resolves only against `fiches/`, `roster_entry_id` only against `aidd_docs/roster/models.json`, `suite_id`/`suite_version` only against `suite-definitions/`. That is correct for an auditor holding the repository, and it is exactly what stops a third party opening the results in a spreadsheet.
- **The tag flow ends at an image.** `.github/workflows/ci.yml` runs `verify-tag` and `publish` on `v*`; `publish` pushes `ghcr.io/aliquanto3/wave_local_ai_v2:<tag>` and `:latest`. No GitHub Release object is created and no asset is uploaded — there is currently nothing for an export to be attached to.
- **There is no data stack.** Runtime dependencies are `codecarbon`, `fastapi`, `nvidia-ml-py`, `psutil`, `python-dotenv`, `requests`, `uvicorn`. No pandas, no pyarrow. This is why the export's file format is a boundary decision rather than a detail.
- **The roster records no licence.** `grep -c licen aidd_docs/roster/models.json` returns 0; the PRD's Dependencies already ask for one and the size-class epic already claims the field.

The value is the difference between a repository someone may inspect and a dataset someone may use and credit. The numbers already exist and are already public; what is missing is permission, portability and a citation, and none of the three needs a benchmark run to ship.

## Boundaries

- Includes: **the licence split, declared where each side lives.** `LICENSE` stays MIT and keeps naming the code. A `LICENSE-DATA` file carries CC-BY 4.0 in full and names exactly what it covers — the repository's own suite items, the reference bundle's rows, the fiches, the roster file, the suite definitions. A short notice sits in each covered directory so a file copied out of `aidd_docs/results/` carries its terms with it, and `README.md` states the split plus the attribution string a reuser must reproduce.
- Includes: **mixed terms inside one download, stated part by part rather than averaged.** The repository's hand-written items are the owner's to license and are CC-BY 4.0. Items drawn from public benchmarks are not: they carry their source's terms, recorded per item, and where a source forbids redistribution the statistics epic's manifest-plus-fetch-script fallback means the item text is not in the download at all. The licence file and the export both express that: a covered part says CC-BY 4.0, a drawn part names its source and that source's licence, an absent part is a visible absence with a fetch instruction. Which items are drawn and on what terms is consumed from that epic, never reopened here.
- Includes: **a tabular export command over the published bundle.** Four flat tables — quality per item, runtime aggregates, fiches, roster — one row per thing, with every pointer the JSONL carries resolved into columns, so reading one table needs no join across files and no code that follows a hash. It reads the published bundle and nothing else: it runs no benchmark, it does not read the untracked per-machine `runtime.jsonl` / `quality.jsonl` by default, and it computes no number the rows do not already carry.
- Includes: **CSV as the contract, Parquet as a release-time convenience.** The packaged command emits CSV with the standard library alone, adding no runtime dependency to a harness whose target machines include one with 16 GB and no GPU and whose published image carries the same dependency set. Parquet is produced in the release job by a step that installs `pyarrow` for itself and ships beside the CSV. Where the two ever disagree, the CSV is right.
- Includes: **a documented, versioned table schema.** A column dictionary inside the download: every column, its meaning, its unit, and the row field it came from. The export declares the bundle `schema_version` it read — the published bundle is `"7"` while `row_contract.SCHEMA_VERSION` is `"11"`, and an export silent about that would be claiming a bundle it did not read. Absence stays absence, under the discipline the row epic and the results service already hold: a field a row does not carry is an empty cell with a documented meaning, never a zero, never a back-fill.
- Includes: **`CITATION.cff` at the repository root**, machine-readable by GitHub and Zenodo, naming the work, the release version and the commit, kept in step with the tag by the same style of check that already refuses a tag whose name and packaged version disagree.
- Includes: **one asset per release.** On a `v*` tag, CI builds the export, assembles one archive — the four tables, the column dictionary, the reference bundle they were derived from, `LICENSE`, `LICENSE-DATA`, `CITATION.cff`, and a README naming which release and which commit produced it — creates the GitHub Release the workflow does not create today, and attaches it. The archive is self-describing: nothing inside it points at a path that only exists in a clone.
- Includes: **a Zenodo deposit written as a manual, optional procedure** — what to upload, what metadata to enter, which licence to select, how to record the returned DOI back into `CITATION.cff` and `README.md`. No token in CI, no automated deposit, no release blocked on it.
- Excludes: **the article itself.** Its text, its figures, its venue and its submission are out of this repository (gap brief, Context).
- Excludes: **which public benchmarks seed the publication suites, whether their terms permit redistribution, and the manifest fallback.** `a-score-is-published-with-its-interval-a-difference-with-its-test` owns that spike and that decision. This epic consumes whatever it returns.
- Excludes: **the statistical columns themselves.** The interval, its resample count and seed, the paired test and the comparison record are computed there and land on the rows there; this export carries whichever of them the bundle holds and names the ones it does not. **Overlap named rather than resolved by silence:** that epic's Boundaries include "the tabular export carrying the interval and the comparison record". One export, two owners of different halves — its mechanism, schema, licences and release asset are here; the existence and correctness of those columns are there.
- Excludes: **the bundle contract.** The row schema, the pointers, which files constitute the bundle, and the supersede-don't-back-fill discipline belong to `every-published-row-explains-and-reproduces-itself`. The export flattens that bundle and changes none of it. In particular it does not back-fill the `"7"` rows on their way into a table.
- Excludes: **the roster's licence block.** `every-size-class-spans-two-families-or-says-it-does-not` adds the licence id, the commercial-use flag and the date the terms were read. The roster table exports those columns; it does not create them.
- Excludes: **every human-readable view.** Dashboards, the results service, charts, anything read at pitch distance belong to `the-pitch-runs-from-a-browser-and-only-with-the-key`. This epic produces machine-readable tables for someone who will analyse them elsewhere, and renders nothing.
- Excludes: **licensing anything the repository does not own** — model weights, provider outputs, third-party benchmark corpora. The roster names third-party licences; it grants none of them.
- Excludes: **the tag, the CHANGELOG, `verify-tag` and the image publish.** `clean-machine-runs-it-and-nothing-reaches-main-unchecked` owns the release flow, and `a-release-tag-names-the-code-a-row-can-cite` already shipped the tag, the packaged version and the readable sha. The seam is single and named: this epic adds the Release object and one asset to that flow, and touches neither the tag check nor the image.
- Excludes: **hosting the download anywhere else.** No mirror, no bucket, no website. The release is the distribution point, and Zenodo is the optional archival copy.

### Decisions this epic takes

| Subject | Decision taken here |
| --- | --- |
| CSV is normative, Parquet is built only in the release job | Taken with the owner. `pyarrow` is a ~40 MB wheel for a feature used once per release, in a dependency set that today holds no data stack at all, on a project whose most important target machine has 16 GB and no GPU. CSV read by a spreadsheet, R or DuckDB already satisfies "consumable without Python or the repo". Cost accepted and stated: the Parquet path is exercised only on a tag, so it is the half that can rot unnoticed, and float formatting in the CSV is pinned explicitly rather than left to a default. |
| One asset, not several | A researcher who must download four files and guess how they relate has not been handed a dataset. The archive holds the tables, their dictionary, the bundle they came from, both licences and the citation; the outcome is "download one thing", so it is one thing. |
| The export is derived, never authoritative | The bundle stays the source of truth and the tables are a projection of it. A CI check regenerates the tables from the published bundle and compares them to the shipped asset, so a hand-edited table is a build failure rather than a second, divergent set of published numbers. |
| The licence file names what it covers, item by item where it must | A blanket "the data is CC-BY 4.0" would be a claim about items the repository does not own the moment the first public-benchmark subset lands. The declaration is scoped from the start, so the publication suites arrive into a licence statement that already has a place for them instead of forcing it to be rewritten. |
| Attribution and citation are one string, stated once | The CC-BY attribution form and the `CITATION.cff` entry name the same work in the same way. Two independently maintained descriptions of the same authorship drift, and a reviewer who finds two forms does not know which one to use. |
| A DOI is optional and manual for this release | The PRD's own position: "Whether each release also receives an archival DOI (Zenodo or equivalent). Desirable for citation, deliberately optional for this release, and not an acceptance criterion." An automated deposit needs a token in CI and makes every tag a permanent public archival act; a documented manual step costs ten minutes when it is actually wanted. Revisited only if a venue requires a DOI. |
| An unredistributable item is a visible hole | Where the manifest fallback applies, the export carries the item id, its source and its fetch instruction, and the item text is absent and marked absent. A row silently missing its prompt looks like a bug; a row that names why the text is not there is evidence. |
| The export declares the schema it read | Not the schema the code implements. The published bundle sitting behind the contract is a documented, deliberate state, and an export reporting the live constant because the code says so would be the first thing in this project to misreport a row's provenance. |

## Success Evidence

Hand someone a machine with no clone, no Python and no access to this repository, and one URL: the latest release asset.

- They unpack it and read the four tables in a spreadsheet, R or DuckDB with nothing installed.
- From the per-item quality table alone they recompute each published run's headline accuracy and get the number the published table states; where an interval is published they recompute it from the same per-item rows using the recorded seed, method and resample count and land on the same interval.
- For every part of the download they can say under what terms they may republish it, and reproduce the attribution string without asking anyone.
- They produce a citation for that exact release — version, commit, author, year — without visiting the repository.
- An item whose source forbids redistribution is visibly absent with its source and a fetch instruction, not quietly missing.
- A CI check proves the asset is derived: tables regenerated from the published bundle equal the ones in the archive, every column in the dictionary exists in the tables, and every column in the tables exists in the dictionary.
- The tag, the packaged version, the `CITATION.cff` version and the asset's README name the same release; a disagreement fails the build.

Falsification the epic accepts in advance: if reading the terms shows that some part of what the repository calls its own cannot in fact carry CC-BY 4.0 — items derived from client material, or completions from a provider whose terms restrict republication — that part leaves the declaration and is named as excluded rather than quietly covered. A licence file that overclaims is worse than no licence file, because it invites a reuse the owner cannot authorise.

Once `done`, record here what the licence review actually found it could and could not cover, which format the third-party reader reached for, whether the recomputation matched, and whether a DOI was taken for the first release or deliberately skipped.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| The reference bundle's composition and its pointer contract | dependency | `every-published-row-explains-and-reproduces-itself` owns the row schema, the five bundle parts and the pointers between them. The export flattens what that epic defines and modifies none of it. |
| The tag, the CHANGELOG and the CI release flow | dependency | `clean-machine-runs-it-and-nothing-reaches-main-unchecked`, with `a-release-tag-names-the-code-a-row-can-cite` already `done`. Today's `publish` job pushes an image and creates no Release; this epic adds the Release object and its asset to that flow. |
| Per-item licence, per-item source, and the redistribute-or-manifest decision | dependency | `a-score-is-published-with-its-interval-a-difference-with-its-test` owns the licence spike over candidate public benchmarks and the fallback it settles. Consumed as given. Until it lands, the export covers only hand-written items and says so. |
| The roster's licence id, commercial-use flag and date read | dependency | `every-size-class-spans-two-families-or-says-it-does-not`. The roster table exports the columns; the file today has none. |
| Interval, seed, resample count, and the comparison record as columns | dependency | Same statistics epic. The export names them absent until they exist rather than waiting for them; the licensing and citation half of this epic depends on none of them, which is what lets gap 8 stay "continuous" instead of queueing behind the run campaign. |
| The attribution string and the `CITATION.cff` author identity | decision, deferred | Pseudonym, real name, ORCID, affiliation — decided when the first tag is cut, not written into a backlog file now. Taken with the owner. The epic ships the files, the split and the mechanism; the string is filled at release, and the deferral is why the outcome above says "a form the repository states" rather than naming one. |
| Whether generated completions may be redistributed under the bundle's terms | assumption | Quality rows already carry the rendered `prompt`; the open-ended suites will carry model output beside it. The assumption is that outputs of models this repository runs may be redistributed with the rows. It is an author declaration, unverified against any provider's terms, and it is the most likely thing the falsification above fires on. Named so it is disclosed rather than discovered. |
| The repository's hand-written items are the owner's to license | assumption | The existing suites' items are `provenance: hand_written`, so CC-BY 4.0 is the owner's grant to make. Stated, not verified against any employment or client agreement, and it is the second thing the falsification fires on. |
| The published bundle's schema lag persists into the export, and is wider than its own README says | assumption | The bundle is `"7"` (`tests/test_reference_bundle.py:48`); `row_contract.SCHEMA_VERSION` is `"11"`. `aidd_docs/results/README.md` still describes the gap as one version and names `"8"` — stale, and the row epic's to correct, not this one's. The export declares the version it actually read and reconciles nothing; the regeneration that closes the lag is a bench-time job already filed in `aidd_docs/backlog/tech-debt.md`. If it lands first, the export's declaration follows the bytes with no code change. |
| The Parquet half is only exercised on a tag | assumption | Accepted as the price of keeping `pyarrow` out of the runtime dependency set. Bounded by making the release job's export step runnable on demand rather than only on a tag, so the path can be proved without cutting a version. |
| A GitHub Release with an attached asset needs a permission the workflow does not hold | dependency | `ci.yml` declares `permissions: contents: read` at the top and grants `packages: write` only inside `publish`. Creating a Release needs `contents: write` on that job — a scoped, reviewable change to a workflow another epic owns, coordinated at story level rather than assumed. |
| Zenodo's own metadata and licence vocabulary | unknown | Not knowable from this repository and subject to change. Resolved when the procedure is written, by performing the deposit once against a real release rather than describing it from memory. The DOI stays optional, so a surprise here delays a nice-to-have and blocks nothing. |

## Cancellation

n/a — not cancelled.
