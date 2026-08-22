---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/flags-model-and-build-come-from-the-roster-not-from-source.md
order: 14
---

# Story: The fiche carries a normalised hash every row cites

**As** a client-side engineer checking whether two rows describe the same machine
**I want** the hardware fiche to be a stored artifact with a SHA-256 identity computed over a normalised projection, cited by hash from every row
**So that** the same configuration hashes identically on my machine and yours, and two rows from different machines are distinguishable by value rather than by eye

## Acceptance

- Methodology 14: a fiche carries CPU, RAM, GPU, driver, llama.cpp build, quant and flags, and is written once as an addressable artifact in a fiche registry rather than flattened inline into every row.
- Methodology 14: its SHA-256 is computed over a normalised projection — the model identified by roster entry id and checksum instead of a filesystem path, host and port excluded — so a moved models directory does not move the hash and a second machine with the same configuration matches it.
- Methodology 14: the raw flag list stays on the fiche as evidence and is not part of the hashed projection.
- Every runtime and quality row cites its fiche by hash; the inline fiche fields leave the row.
- Hashing is order- and formatting-stable: the same projection hashes identically across processes and across key insertion orders.
- Today's flag list opening with an absolute `D:\ia\models\...` path produces the same hash after `SLM_MODELS_DIR` moves, demonstrated by a test that moves it.

## Code it changes

- `src/wave_local_ai_v2/hardware.py` — the fiche gains the run-specific fields it currently refuses, and a normalised projection beside the captured one.
- `src/wave_local_ai_v2/fiche_registry.py` (new) — hash, write-once storage under `aidd_docs/results/fiches/<hash>.json`, and lookup by hash.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — write the fiche, cite the hash, drop the inline flattening.
- `src/wave_local_ai_v2/row_contract.py` — `fiche_hash` becomes required on both row kinds; the flattened fiche fields leave the contract.

## Tests it needs

- `tests/test_fiche_registry.py` (new) — the projection excludes host, port and the model path; two captures differing only by models directory hash identically; two differing by GPU do not; key order does not change the hash; writing the same fiche twice does not duplicate the artifact.
- `tests/test_hardware.py` — the projection carries roster entry id and checksum in place of the path, and the raw flag list survives on the stored fiche.
- `tests/test_cli.py` — the written row cites a hash that resolves to a stored fiche.

## Evidence it publishes

- `aidd_docs/results/fiches/<hash>.json` and the `fiche_hash` on every regenerated row (order 19) — the pointer that replaces the six inline fiche fields the current tracked rows flatten.

## Cancellation

n/a — not cancelled.
