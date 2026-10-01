---
type: story
status: ready
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parent: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
depends_on:
  - aidd_docs/backlog/stories/each-release-attaches-one-archive-that-needs-no-clone.md
order: 5
---

# Story: Parquet copies ship beside the CSV and never disagree with it

**As** a third-party researcher loading the tables into a dataframe or a columnar engine
**I want** typed Parquet copies of the four tables in the release archive, proven equal to the CSV
**So that** I load the results with their types intact, and never have to wonder which of two formats is right

Maps to: PRD AC "the published results are also available as a tabular export readable outside the repo without running it"; epic Boundaries "CSV as the contract, Parquet as a release-time convenience"; epic decision "CSV is normative, Parquet is built only in the release job"; epic Dependencies row "The Parquet half is only exercised on a tag".

Needs: an operator, to trigger the on-demand release-build run on GitHub. No model run, API key or hardware is required.

## Acceptance

- The release job installs `pyarrow` for itself, at a pinned version, and writes one Parquet file per CSV table into the archive. `pyarrow` enters neither the runtime dependency set in `pyproject.toml` nor the published image.
- A check reads each Parquet file back and compares it to its CSV cell by cell under the column dictionary's types, empty cells included; any disagreement fails the build. The archive README states that the CSV is right wherever the two could disagree, and names the `pyarrow` version used.
- The build can be run on demand without cutting a tag and without creating a Release, so the Parquet path is proven between releases instead of rotting unnoticed. One on-demand run is performed and its result kept.

## Code it changes

- `.github/workflows/ci.yml`: the Parquet step and the on-demand trigger on the release job of order 4.
- A script under `scripts/` that writes and checks the Parquet files, run only by that job.

## Tests it needs

- `tests/test_ci_workflow.py`: the on-demand trigger creates no Release, `pyarrow` is installed only inside the release job, and `pyproject.toml` runtime dependencies do not include it.
- The check itself, run where `pyarrow` is available: a Parquet file with one altered cell fails it.

## Evidence it publishes

- The on-demand run's log showing every table compared and equal, filed with the delivery.

## Cancellation

n/a: not cancelled.
