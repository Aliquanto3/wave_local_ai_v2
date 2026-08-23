---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
order: 12
---

# Story: A versioned roster pins every model

**As** a client-side engineer reproducing a published row
**I want** a versioned roster file pinning each model's revision, file, quant, checksum, architecture and its own server flag set
**So that** I can obtain the exact weights a row was produced with, and a flag set can be checked against the architecture it claims to serve

## Acceptance

- Methodology 13: a tracked, versioned roster file holds one entry per roster model, pinning repo revision, file name, quant, checksum, architecture (dense or MoE, and for MoE the expert count and active-parameter figure) and that model's own server flag set.
- Methodology 13: every row cites its roster entry by id, and the roster version it was read from.
- Methodology 13: a dense entry carrying MoE-offload flags is refused by a named validation, and an MoE entry whose offload flag exceeds its declared expert count is refused — the architecture field is what makes the rule checkable rather than a convention.
- The first entry reproduces the validated baseline flag set for `Qwen3.6-35B-A3B-UD-IQ4_XS` byte for byte, so the rows republished under it stay comparable to the two carrying the project's headline throughput.
- Which models populate the roster is not decided here: this story ships the file, its fields, its validation and the citation. The roster's model set belongs to `quality-scored-comparison-first-three-use-cases`.

## Code it changes

- `aidd_docs/roster/models.json` (new, tracked) — the roster file, carrying its own `roster_version`.
- `src/wave_local_ai_v2/roster.py` (new) — load, validate, resolve an entry by id; the dense-versus-MoE flag rule.
- `src/wave_local_ai_v2/settings.py` — the roster file path as a configured value with the tracked file as default.
- `src/wave_local_ai_v2/row_contract.py` — roster entry id and roster version become required fields on both row kinds.

## Tests it needs

- `tests/test_roster.py` (new) — a valid entry loads; a dense entry with `--n-cpu-moe` is refused; an MoE entry with `--n-cpu-moe` above its expert count is refused; an unknown entry id raises; a checksum-less entry is refused.
- A test asserting the shipped first entry's flag list equals the flag list `server.build_flags` validated, so the byte-for-byte claim is enforced rather than asserted in prose.

## Evidence it publishes

- `aidd_docs/roster/models.json` itself, published as part of the reference bundle (order 19) — the file every regenerated row cites.

## Cancellation

n/a — not cancelled.
