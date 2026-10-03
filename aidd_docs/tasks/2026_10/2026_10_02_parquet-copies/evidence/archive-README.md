# wave-local-ai-v2 0.2.0: published results

- Release: `v0.2.0` (packaged version 0.2.0)
- Commit: `aa3b104cc7eb61b138eca88a1cb742da831fe886`
- Source at this commit: https://github.com/Aliquanto3/wave_local_ai_v2/tree/aa3b104cc7eb61b138eca88a1cb742da831fe886
- Bundle schema version read: runtime rows 7, quality rows 7 (from `bundle_manifest.csv`)

Everything needed to read the tables is in this archive. They open
in any spreadsheet; each row resolves its pointers into its own
columns, so no join is needed. The tables are derived from the bundle
beside them, never edited by hand: the release build regenerates them
from the bundle at this commit and fails if any byte differs.

## What each file is

| File | What it is |
| ---- | ---------- |
| `bundle_manifest.csv` | Each bundle part read, its path in this archive, entries read and the versions it declares. |
| `column_dictionary.csv` | Every column of every table: meaning, unit, what an empty cell means. |
| `comparison_records.csv` | One row per comparison-family record, comparison, leader-set record and leader-set subject, named by record_kind. |
| `fiches.csv` | One row per stored hardware fiche. |
| `quality_items.csv` | One row per quality row, every pointer resolved into columns (fiche, roster entry, suite definition). |
| `roster.csv` | One row per roster entry. |
| `runtime_aggregates.csv` | One row per runtime row, fiche and roster entry resolved into columns. |
| `comparison_records.parquet` | Typed Parquet copy of `comparison_records.csv`; the CSV is right wherever the two could disagree. |
| `fiches.parquet` | Typed Parquet copy of `fiches.csv`; the CSV is right wherever the two could disagree. |
| `quality_items.parquet` | Typed Parquet copy of `quality_items.csv`; the CSV is right wherever the two could disagree. |
| `roster.parquet` | Typed Parquet copy of `roster.csv`; the CSV is right wherever the two could disagree. |
| `runtime_aggregates.parquet` | Typed Parquet copy of `runtime_aggregates.csv`; the CSV is right wherever the two could disagree. |
| `aidd_docs/results/NOTICE.md` | The licence notice for the directory it sits in. |
| `aidd_docs/results/comparisons/NOTICE.md` | The licence notice for the directory it sits in. |
| `aidd_docs/results/comparisons/classification-support-routing@2.model.1e1658cbe073.json` | A paired-comparison family record. |
| `aidd_docs/results/comparisons/classification-support-routing@2.model.2ef9fd3581d2.json` | A paired-comparison family record. |
| `aidd_docs/results/comparisons/classification-support-routing@2.model.837e5355b954.json` | A paired-comparison family record. |
| `aidd_docs/results/comparisons/classification-support-routing@2.model.d4641d06a525.json` | A paired-comparison family record. |
| `aidd_docs/results/fiches/067530efd6944e8bb09ddc91e61ce45364fcd6261bd22edeed9d33a82276a2f4.json` | A hardware fiche the rows cite by fiche_hash. |
| `aidd_docs/results/fiches/197d2732769ec3056776fa671bfd77e059f61147ac42488d83b44f3aa97a87f8.json` | A hardware fiche the rows cite by fiche_hash. |
| `aidd_docs/results/fiches/NOTICE.md` | The licence notice for the directory it sits in. |
| `aidd_docs/results/fiches/b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a.json` | A hardware fiche the rows cite by fiche_hash. |
| `aidd_docs/results/fiches/dfd5a5eaa441cff2f7aee55b6d2206561eb9d19cb955bddc566d3e9d7fcb2ab2.json` | A hardware fiche the rows cite by fiche_hash. |
| `aidd_docs/results/fiches/f804bee0d215c89c05289907fd2573fa722d290896775749f3c6d16329efca18.json` | A hardware fiche the rows cite by fiche_hash. |
| `aidd_docs/results/leader-sets/NOTICE.md` | The licence notice for the directory it sits in. |
| `aidd_docs/results/leader-sets/classification-support-routing@2.053c65354ff8.json` | A leader-set record. |
| `aidd_docs/results/quality-reference.jsonl` | The quality rows, one JSON object per line. |
| `aidd_docs/results/runtime-reference.jsonl` | The runtime rows, one JSON object per line. |
| `aidd_docs/results/suite-definitions/NOTICE.md` | The licence notice for the directory it sits in. |
| `aidd_docs/results/suite-definitions/classification-support-routing@2.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/classification-support-routing@3.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/classification-support-routing@4.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/classification-support-routing@5.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/code-generation-python-javascript@1.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/translation-business-short-form@1.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/translation-business-short-form@2.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/translation-business-short-form@3.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/results/suite-definitions/translation-business-short-form@4.json` | A suite definition the rows cite by suite_id and suite_version. |
| `aidd_docs/roster/NOTICE.md` | The licence notice for the directory it sits in. |
| `aidd_docs/roster/models.json` | The model roster the rows cite by roster_entry_id. |
| `CITATION.cff` | How to cite this release, with its commit. |
| `LICENSE` | The MIT License, covering the code. |
| `LICENSE-DATA` | CC-BY 4.0 and the parts it covers, by path. |
| `README.md` | This file. |

## Parquet copies

Each table also ships as a Parquet file of the same name, typed from
the unit `column_dictionary.csv` gives each column; an empty CSV cell
is a Parquet null. The release build reads every copy back and fails
unless it equals its CSV cell by cell under those types. The CSV is
the contract: wherever the two could disagree, the CSV is right.
The copies were written with pyarrow 25.0.1.

## How to cite this release

PLACEHOLDER-OWNER-FAMILY-NAMES, PLACEHOLDER-OWNER-GIVEN-NAMES (2026). wave-local-ai-v2, version 0.2.0. https://github.com/Aliquanto3/wave_local_ai_v2. Licences: code: MIT; data: CC-BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Commit aa3b104cc7eb61b138eca88a1cb742da831fe886.

`CITATION.cff` holds the same citation for citation managers. If
you changed the data, say so after the string.

## Licences

The code is MIT (`LICENSE`); the data is CC-BY 4.0 (`LICENSE-DATA`).
`LICENSE-DATA` names the parts it covers by repository path; the ones
this archive holds sit at those same paths.

## Repository paths named here but not shipped

A file in this archive names each path below; none is needed to read
the tables. Each link opens it at this commit:

- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/aidd_docs/results/runtime-reference.schema-1.jsonl: superseded runtime rows, retained in the repository; no table reads them.
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/aidd_docs/results/quality-reference.schema-1.jsonl: superseded quality rows, retained in the repository; no table reads them.
- https://github.com/Aliquanto3/wave_local_ai_v2/tree/aa3b104cc7eb61b138eca88a1cb742da831fe886/src/wave_local_ai_v2/suite_data/: the hand-written suite items as stored in the source tree; their published snapshots are aidd_docs/results/suite-definitions/.
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/src/wave_local_ai_v2/use_case_coverage.json: the declared use-case coverage record.
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/src/wave_local_ai_v2/judge_probe.py: the judge probe, whose hand-written items LICENSE-DATA covers.
- `runtime.jsonl` in aidd_docs/results/: an untracked per-machine live store, never published; no commit holds it, so there is no link.
- `quality.jsonl` in aidd_docs/results/: an untracked per-machine live store, never published; no commit holds it, so there is no link.
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/aidd_docs/backlog/spikes/may-the-model-outputs-in-the-published-rows-be-redistributed-and-on-what-terms.md: the open question on redistributing model output (LICENSE-DATA 1.3).
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/aidd_docs/results/README.md: the repository's results guide, whose runtime table a roster minimum was read from.
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/aidd_docs/tasks/2026_10/2026_10_02_gpu-cpu-never-share-a-fiche/evidence/runtime.jsonl: unpublished run evidence a roster minimum was read from.
- https://github.com/Aliquanto3/wave_local_ai_v2/blob/aa3b104cc7eb61b138eca88a1cb742da831fe886/aidd_docs/tasks/2026_10/2026_10_02_named-run-profiles/evidence/runtime.jsonl: unpublished run evidence a roster minimum was read from.
