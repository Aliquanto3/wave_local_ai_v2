# Sources the Zenodo procedure relies on

Read over HTTPS on 2026-10-03, read-only: no account, no login, no token, no
upload. Each row names what `docs/zenodo-deposit.md` takes from the page. A
form label the procedure needs but no page below shows is marked there as
"confirm on the walk", never guessed.

| Source | What the procedure takes from it |
| ------ | -------------------------------- |
| https://developers.zenodo.org/ | The sandbox is https://sandbox.zenodo.org, needs its own registration and token, "can be cleaned at anytime", and issues test DOIs under prefix `10.5072` instead of `10.5281`. The deposit metadata keys `upload_type` (`dataset`, `software`, ...), `access_right` (default `open`), `license` (required when open), `creators` (`name` as "Family name, Given names", `affiliation`, `orcid`), `description` (required), `version` (optional), `related_identifiers` (relations including `isIdenticalTo`, `isSupplementTo`), `keywords`, `publication_date`, `prereserve_doi`. |
| https://help.zenodo.org/docs/deposit/create-new-upload/ | The form flow: plus icon then "New upload"; "Upload files" or drag and drop (up to 100 files, 50 GB); required fields under "Basic information" marked with a red star; "Save draft", "Preview", "Publish"; the publish confirmation says metadata stays editable and files are editable only within a limited window. |
| https://help.zenodo.org/docs/deposit/describe-records/ | The form's field list: DOI, Resource types, Titles, Publication date, Creators, Descriptions, Licenses and rights, Keywords and subjects, Contributors, Publisher, Funding information. |
| https://help.zenodo.org/docs/deposit/describe-records/reserve-doi/ | The question "Do you already have a DOI for this upload?" and the "Get a DOI now!" reservation; Zenodo registers a DOI for every upload when published. |
| https://help.zenodo.org/docs/deposit/describe-records/resource-type/ | Resource type is required, chosen from a drop-down based on DataCite's vocabulary; with mixed content, choose the type that best describes the most significant part. |
| https://help.zenodo.org/docs/deposit/describe-records/titles/ | Title is required. |
| https://help.zenodo.org/docs/deposit/describe-records/publication-date/ | Publication date is required, defaults to the draft's creation date, takes YYYY-MM-DD, and for content published elsewhere first should be the date of first publication. |
| https://help.zenodo.org/docs/deposit/describe-records/creators/ | Creators is required; a creator is a Person (family name, given names) or an Organization; name identifiers (ORCID among them), affiliations, an optional role. |
| https://help.zenodo.org/docs/deposit/describe-records/descriptions/ | Description is the record's abstract; additional descriptions can be added. |
| https://help.zenodo.org/docs/deposit/describe-records/licenses/ | Licence is required and defaults to "Creative Commons Attribution 4.0 International"; "Edit" to choose another; several licences can be declared for mixed content; custom licences are possible. |
| https://help.zenodo.org/docs/deposit/about-records/ | Once published, "Files and the persistent identifier CANNOT be modified"; metadata can; an update is a new version, a new record with its own identifier. |
| https://help.zenodo.org/docs/deposit/manage-records/ | Metadata editable at any time; files only through support after publication; deletion by the owner within 30 days, later only with a documented reason through support. |
| https://help.zenodo.org/docs/deposit/manage-versions/ | The "New version" button on the record page creates a new record linked to the previous ones; "Import files" brings files forward. |
| https://zenodo.org/help/versioning (via search result summary of the Zenodo versioning FAQ) | The first publication registers two DOIs: one for the version and one, the concept DOI, for all versions, which resolves to the latest version. |
| https://help.zenodo.org/docs/github/enable-repository/ | The GitHub integration is enabled per repository by toggling its slider in the Zenodo account's GitHub page; once enabled, "new releases from the repository will be automatically ingested and archived". |
| https://help.zenodo.org/docs/github/archive-software/github-upload/ | A release of an enabled repository becomes a Software record with a DOI. |
| https://help.zenodo.org/docs/github/archive-software/manual-upload/ | A Software record with a single compressed file is sent to Software Heritage; this is a Software-type behaviour, not used here (the deposit is a Dataset). |
| https://support.zenodo.org/help/en-gb/24-github-integration/96-how-does-a-citation-cff-file-affect-metadata-of-my-github-release | With the integration, Zenodo parses `CITATION.cff` unless a `.zenodo.json` exists. Not used: the integration stays off and the metadata is typed by hand. |
| https://raw.githubusercontent.com/citation-file-format/citation-file-format/1.2.0/schema-guide.md | CFF 1.2.0 `doi` ("most useful when there is just one DOI") and `identifiers` (objects with `type: doi`, `value`, optional `description`). |

## Gaps the documentation left open

- The pages disagree on the file edit window: `create-new-upload` quotes a
  confirmation allowing file edits for a limited period, `manage-records`
  says files change after publication only through support. The procedure
  treats files as frozen at publish.
- No page fetched names the form labels for the version, access, related
  works or publisher fields. The procedure names the API key and asks the
  walk to record the label.
- No page fetched states how to turn the GitHub integration off or which
  files it archives. The procedure only asks that the repository's slider
  stay off and that this be checked on the walk.
