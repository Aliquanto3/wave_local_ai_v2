---
status: done
---

# Instruction: The real hub, download and GGUF seams

## Architecture projection

> Tree of the final files. ✅ create · ✏️ modify · ❌ delete

```txt
.
├── src/wave_local_ai_v2/candidate_gate.py   ✏️ HubClient over requests, stream_download, read_gguf_facts
└── tests/test_candidate_gate.py             ✏️ requests stubbed, a synthetic GGUF written in tmp_path
```

## User Journey

```mermaid
flowchart TD
  A[api/models/repo/revision/sha?blobs=true] --> B[files + sizes + licence id]
  B --> C[resolve/sha/LICENSE text]
  D[resolve/sha/file stream] --> E[.part then replace]
  E --> F[GGUF header: architecture, expert_count, tensor dims]
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    synthetic GGUF in tmp_path, stubbed requests => fixtures ready: 5: system
  section Happy path
    read listing, licence text, download, GGUF facts => values match the fixtures: 5: system
  section Edge case - unknown revision
    hub 404 => listing => revision not found error: 1: system
  section Edge case - not a GGUF
    bad magic => read facts => refused naming the magic: 1: system
```

## Tasks to do

### `1)` Hub client

> Read-only listing, licence id, text file at a revision.

1. `GET /api/models/<repo>/revision/<sha>?blobs=true`; `resolve/<sha>/<path>` for text.

### `2)` Downloader

> Stream to `<dest>.part`, replace on completion.

### `3)` GGUF reader

> Architecture, expert count, total parameters, without loading tensors.

## Test acceptance criteria

| Task | Acceptance criteria              |
| ---- | -------------------------------- |
| 1 | Listing yields file sizes and licence id; a 404 is a not-found error |
| 2 | A download leaves the file and no `.part` |
| 3 | A synthetic GGUF reports its architecture, expert count and dim-sum parameter count |
