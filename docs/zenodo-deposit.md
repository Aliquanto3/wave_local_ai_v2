# Depositing a release archive on Zenodo (optional, manual)

A release does not need a DOI. Its archive on the GitHub Release page is the
distribution point, and nothing in the release flow waits for, calls or
checks Zenodo. This page is for the day a venue asks for an archival DOI: it
turns one release archive into one Zenodo record by hand, in about ten
minutes, and records the returned DOI back into `CITATION.cff` and
`README.md`.

Status of this page: written from Zenodo's public documentation (sources in
`aidd_docs/tasks/2026_10/2026_10_02_zenodo-procedure/evidence/sources.md`),
not yet walked. It becomes proven once the owner performs it on the Zenodo
sandbox and corrects every step the form did not ask as written here (see
[Proving walk](#proving-walk-on-the-sandbox)). A label marked *confirm on
the walk* is one no documentation page showed.

## Why nothing here is automated

- **No token in CI.** A Zenodo token is a write credential to a permanent
  public archive. The release jobs run project and dependency code; none of
  them holds such a token, and `tests/test_zenodo_deposit_procedure.py` fails
  if any workflow names Zenodo.
- **The GitHub-to-Zenodo integration stays disabled.** Once a repository's
  slider is on in Zenodo's GitHub settings, "new releases from the repository
  will be automatically ingested and archived" as a Software record with a
  DOI. Every `v*` tag creates a GitHub Release here (the `release-publish`
  job), so the integration would make every tag a permanent public archival
  act, of the GitHub release rather than of the verified results archive,
  with metadata Zenodo infers rather than the values below. A published
  record's files cannot be changed, and its owner can delete it only within
  30 days.
- **No release is blocked on a deposit.** The PRD keeps an archival DOI
  "deliberately optional for this release, and not an acceptance criterion".
  A deposit happens after a release exists, never as part of it.

Check the integration is off before each deposit: in Zenodo (production and
sandbox alike), open your account's GitHub page from the profile menu and
confirm the slider for `Aliquanto3/wave_local_ai_v2` is off. An account never
connected to GitHub has nothing to check.

## What to upload

One file: the release asset `wave-local-ai-v2-<version>.zip` from the
release's GitHub Release page, **unchanged**. Do not unpack, rename, re-zip
or add to it. It is the archive `release-build` built and verified, with
`CITATION.cff` stamped with the release's commit and a README naming the
release; any edit makes the deposit a different object from the one the
release published.

Before uploading, compute its SHA-256 (`sha256sum`, or
`Get-FileHash -Algorithm SHA256` in PowerShell) and compare it with the
`archive sha256:` line in the release run's `Record the archive digest` step.
They must be equal.

The deposited archive never names its own DOI: it was built before the
deposit. Do not reserve a DOI ("Get a DOI now!") for that reason; there is
nothing to write it into.

## Metadata to enter

Take every value from the `CITATION.cff` **inside the archive** (the
release's own copy), not from the repository's current one. Use
`zenodo.org/` for a real deposit and `sandbox.zenodo.org/` for the proving
walk. Start with the plus icon in the header, then **New upload**, then
**Upload files** (or drag the zip onto the drop zone).

| Form field | Value | From `CITATION.cff` |
| ---------- | ----- | ------------------- |
| Digital Object Identifier: "Do you already have a DOI for this upload?" | No. Zenodo registers one on publish. | none |
| Resource type | Dataset | none: the archive holds tables, the bundle, licences and the citation, and no code. `type: software` in `CITATION.cff` cites the repository, not this deposit. |
| Title | `wave-local-ai-v2 <version>: published results` (the archive README's first heading) | `title`, `version` |
| Publication date | The release date, `YYYY-MM-DD`. Zenodo defaults to the draft's creation date; for content first published elsewhere it asks for the first publication date. | `date-released` |
| Creators | One entry per author, in `authors` order. An author with `family-names` is a **Person**: family name, given names, affiliations, and the ORCID under name identifiers when present. An author given as `name` is an **Organization**. An author given only as `alias` (a pseudonym, which `CITATION.cff` and `tests/test_citation.py` accept) has no documented Zenodo field: enter the alias as a **Person**'s family name with given names empty (*confirm on the walk* that the form accepts it, and correct this row if it does not). | `authors[].family-names`, `given-names`, `affiliation`, `orcid`; `authors[].name`; `authors[].alias` |
| Description | The text under [Description](#description-the-archives-mixed-terms) below, filled in. | `title`, `version`, `commit`, `repository-code` |
| Licenses and rights | Creative Commons Attribution 4.0 International (the form's default). *Confirm on the walk* whether to declare more than one: Zenodo accepts several licences for mixed content, and `LICENSE-DATA` 1.1 does not license the archive's `README.md`, its `NOTICE.md` files or the `LICENSE` and `LICENSE-DATA` texts themselves; the description states that either way. | `license` lists `CC-BY-4.0` for the data; its `MIT` entry covers the repository's code, none of which is in the deposit. |
| Version (*confirm on the walk*: the deposit API documents a `version` key; no help page shows the form label) | `<version>` | `version` |
| Keywords and subjects (optional) | `small language models`, `benchmark`, `llama.cpp`, `on-premises`, `LLM evaluation` | none |
| Related works (*confirm on the walk*: the API documents `related_identifiers` with relations `isIdenticalTo` and `isSupplementTo`; no help page shows the form label) | The release asset's download URL, `<repository-code>/releases/download/v<version>/wave-local-ai-v2-<version>.zip`, relation `isIdenticalTo`; `repository-code`, relation `isSupplementTo` | `repository-code` |
| Access (*confirm on the walk*: the API's `access_right` defaults to `open`) | Open: files and metadata public. | none |
| Contributors, Publisher, Funding | Leave as the form proposes. | none |

A `PLACEHOLDER-` value in `authors` means the owner's identity is not yet
stated. A real release archive cannot hold one: a build on a `v*` tag fails
while any remains (`tests/test_citation.py`). An on-demand archive used for
the sandbox walk may; type it as it stands there.

Click **Save draft** (it validates the fields), then **Preview**, then
**Publish** and confirm. After publishing, metadata stays editable; the file
does not.

### Description: the archive's mixed terms

The licence field names CC-BY 4.0, but not every part of the archive is
CC-BY 4.0. The description states the rest part by part, taken from the
archive's own `LICENSE-DATA` (section numbers as of this writing). Fill the
angle brackets from the archive and paste:

```text
Published results of wave-local-ai-v2 release <version>, commit <commit>:
flat CSV tables (with typed Parquet copies) of every published runtime and
quality result, their column dictionary, and the reference bundle they were
derived from. This deposit is the asset of the GitHub Release
<repository-code>/releases/tag/v<version>, uploaded unchanged; its
README.md names the release and the commit and describes each file.

Terms. The data parts LICENSE-DATA section 1.1 lists are licensed under
CC-BY 4.0. LICENSE-DATA grants nothing over the parts it names as not
covered: model weights (not in this deposit); the third-party licences the
model roster records, which it records but does not grant; and the
model-generated content in the rows (the predicted_label field today),
redistributed on the author's declaration that this is permitted,
unverified against each model's and provider's terms. <Drawn items: quote
the archive's LICENSE-DATA section 2 verbatim. As of this writing its
decisive sentences read: "The bundle holds no item drawn from a public
benchmark today." and "An item drawn from a public benchmark is not
covered by CC-BY 4.0 through this file. It carries its source's licence,
recorded per item in its `licence`, `source` and `source_revision` fields,
and this section names each drawn source and its terms once the first
drawn item is published."> LICENSE-DATA does not license the archive's
README.md, its NOTICE.md files, or the LICENSE and LICENSE-DATA texts.
LICENSE (MIT) ships because the citation also names the repository's code;
no code is in this deposit.

Cite as: <the line under "How to cite this release" in the archive's
README.md>
```

## Recording the DOI back

Zenodo registers two DOIs on a first publication: one for this version and
a concept DOI for all versions. Record the **version DOI** (the one on the
record's page for this release); the concept DOI resolves to whichever
version is latest, which is not the release cited.

Never record a sandbox DOI (prefix `10.5072/`): it names a test record that
"can be cleaned at anytime". `tests/test_zenodo_deposit_procedure.py` fails
when `CITATION.cff` or `README.md` holds one.

On a new branch from `main` (the release is already tagged, so this is a
normal change):

1. In `CITATION.cff`, add an `identifiers` entry after `repository-code`
   (create the list the first time):

   ```yaml
   identifiers:
     - type: doi
       value: 10.5281/zenodo.<record>
       description: >-
         Zenodo deposit of the release archive of version <version>
         (wave-local-ai-v2-<version>.zip).
   ```

   Use `identifiers`, not the top-level `doi`: CFF reads `doi` as the DOI of
   the work, with no version, so once `version` moves to the next release
   it would present this release's deposit as the next one's DOI. Each later
   deposit adds one entry naming its own version.
2. In `README.md`'s "Attribution and citation" section, below the
   `<!-- attribution:end -->` marker, the paragraph starting "No release has
   a DOI yet." holds the place of the DOI list. The first time, replace that
   whole paragraph with the heading line and the first entry below; each
   later deposit adds one entry to the list. Never write a DOI between the
   markers:

   ```markdown
   Releases deposited on Zenodo (each DOI names that release's archive; it
   is also recorded in `CITATION.cff` under `identifiers`):

   - <version>: https://doi.org/10.5281/zenodo.<record>
   ```

   The marked string is derived from `CITATION.cff` by
   `tests/test_citation.py`, and the derivation reads no DOI, so a DOI
   between the markers fails that test.
3. Check, then open the pull request:

   ```sh
   uv run pytest tests/test_citation.py tests/test_zenodo_deposit_procedure.py --no-cov
   uvx cffconvert --validate
   ```

   The `CITATION.cff` version check still holds: the edit adds a key and
   changes neither `version` nor `date-released`, so the citation still
   names the packaged version and its `CHANGELOG.md` date. The archive build
   still stamps the commit after `version` (`stamp_citation` reads no other
   key). The next release's archive carries the entry, naming the earlier
   release it belongs to.
4. Fill in the [deposit log](#deposit-log) row for the release.

## Proving walk on the sandbox

Performed once by the owner (owner answer Q40 (a)), before the story
`the-zenodo-deposit-is-a-written-optional-procedure-proven-once` closes. No
real deposit is part of it.

1. Get a release archive: the asset of the latest GitHub Release that has
   one, or a rehearsal from **Actions → CI → Run workflow** on `main`, whose
   `release-build` job uploads the `release-archive` artifact (the downloaded
   artifact is a zip holding `wave-local-ai-v2-<version>.zip`; extract that
   one file and upload it unchanged).
2. Register on https://sandbox.zenodo.org (a separate account from
   zenodo.org) and check its GitHub page as above.
3. Follow [What to upload](#what-to-upload) and
   [Metadata to enter](#metadata-to-enter) on the sandbox, up to and
   including **Publish**.
4. Record the sandbox DOI only in the corrections log below, never in
   `CITATION.cff` or `README.md`.
5. Dry-run [Recording the DOI back](#recording-the-doi-back) on a scratch
   branch with the sandbox DOI in `CITATION.cff` only: `tests/test_citation.py`
   passes and `tests/test_zenodo_deposit_procedure.py` refuses the
   `10.5072/` value, as it should. Delete the branch.
6. For every step where the form asked something this page does not say
   (a label, a required field, a vocabulary, an order), correct this page and
   add a row below.

The sandbox is not production: the first real deposit may still need one
correction where zenodo.org differs from the sandbox (the DOI prefix, for
one: `10.5281` instead of `10.5072`). Correct this page then too.

### Corrections log

| Date | Where (sandbox or real) | Step | What the form asked | Correction made |
| ---- | ----------------------- | ---- | ------------------- | --------------- |
| pending | sandbox | the whole walk | not yet performed | none yet |

Sandbox record of the walk: pending (record URL and `10.5072/` DOI go here,
and nowhere else).

## Deposit log

Whether each release took a real DOI, and why.

| Release | Real DOI | Why |
| ------- | -------- | --- |
| first release carrying the archive (not yet cut, 2026-10-03) | skipped unless a venue asks before it is cut | No venue has asked for a DOI. Update this row when that release is cut. |
