# Evidence: the four views over two stores, from one unchanged service

Eight response bodies, captured over HTTP from `wave-local-ai-v2-serve`. The
first four answer over the committed reference bundle, whose rows sit at
`schema_version` `"7"`; the second four answer over the live per-machine
stores, whose newest quality rows sit at `"11"`. There is no code difference
between the two runs — only four `SERVICE_*` / `*_RESULTS_PATH` values.

That is the point of filing them together. The same service, pointed at a
store one generation behind, returns a *mostly-absent* shape rather than a
failure, a zero, or a quietly dropped column.

## What the two shapes show

| | bundle (`"7"`) | live (`"11"`) |
| --- | --- | --- |
| quality entries captured | 40 | 21 |
| score shape declared | `exact_match` | `graded` |
| `predates_schema` absences in the quality body | 840 (21 per entry) | 378 (18 per entry) |
| `null_in_row` absences in the quality body | 260 | 168 |

The 21-per-entry figure on the bundle is the 18-field judge block plus
`thinking_policy` (introduced at `"11"`), `retries` and `resumed` (at `"8"`).
The live run, being at `"11"`, carries those three and is left with the judge
block alone — no store holds a judged row today, so those 18 absences are the
live path this story ships, not a branch reserved for later.

`unreadable` is empty in all eight bodies: both configurations point at stores
whose every row is at or above the floor in force. The non-empty case — every
row of a superseded `*.schema-1.jsonl` file landing in `unreadable` at floor
`"7"`, none of them rendered — is asserted in
`tests/test_reference_bundle.py::test_every_row_of_a_superseded_file_lands_in_unreadable`.

## How they were captured

`SERVICE_API_KEY` is required to start the service even on a loopback bind, so
the captures were run with a throwaway value. It is not in this repository and
is not needed to read these files; a loopback client is answered without an
`X-API-Key` header, which is why the `curl` calls below carry none.

The bundle four (schema floor `"7"`, both store paths moved to the reference
files):

```sh
SERVICE_API_KEY=<throwaway> \
SERVICE_PORT=8123 \
SERVICE_SCHEMA_FLOOR=7 \
RUNTIME_RESULTS_PATH=aidd_docs/results/runtime-reference.jsonl \
QUALITY_RESULTS_PATH=aidd_docs/results/quality-reference.jsonl \
uv run wave-local-ai-v2-serve

curl -sS http://127.0.0.1:8123/api/runs                             -o bundle-runs.json
curl -sS http://127.0.0.1:8123/api/runs/5e13166d.../quality         -o bundle-quality.json
curl -sS http://127.0.0.1:8123/api/runs/f5f78c79.../runtime         -o bundle-runtime.json
curl -sS 'http://127.0.0.1:8123/api/runs/f5f78c79.../energy?store=runtime' -o bundle-energy.json
```

The live four, at every default (`SERVICE_SCHEMA_FLOOR` unset resolves to
`"7"`, the store paths to the live per-machine files):

```sh
SERVICE_API_KEY=<throwaway> SERVICE_PORT=8124 uv run wave-local-ai-v2-serve

curl -sS http://127.0.0.1:8124/api/runs                             -o live-runs.json
curl -sS http://127.0.0.1:8124/api/runs/79e95271.../quality         -o live-quality.json
curl -sS http://127.0.0.1:8124/api/runs/68a5e1df.../runtime         -o live-runtime.json
curl -sS 'http://127.0.0.1:8124/api/runs/79e95271.../energy?store=quality' -o live-energy.json
```

## The runs each body covers

| file | `run_id` | store | `schema_version` of its rows |
| --- | --- | --- | --- |
| `bundle-quality.json` | `5e13166da0654390a7d63f346ea5d4f1` | quality | `"7"` |
| `bundle-runtime.json` | `f5f78c795eaa4175ac506440e597ee3e` | runtime | `"7"` |
| `bundle-energy.json` | `f5f78c795eaa4175ac506440e597ee3e` | runtime | `"7"` |
| `live-quality.json` | `79e95271e6714f7d8ba78da787e35698` | quality | `"11"` |
| `live-runtime.json` | `68a5e1df18d540008eb8f19ac6efa2a9` | runtime | `"10"` |
| `live-energy.json` | `79e95271e6714f7d8ba78da787e35698` | quality | `"11"` |

`live-runtime.json` sits at `"10"`, not `"11"`: `"11"` added
`thinking_policy` to the *quality* row only, and the live runtime store's
newest generation is `"10"`. Recorded here rather than smoothed over — the
claim this evidence supports is about one service reading two stores as they
actually stand, and this is how they stand.

The energy view is captured over `runtime` on the bundle side and `quality` on
the live side, so the required `store` parameter is exercised in both of its
accepted values across the eight bodies.

## What this story wrote

No results row. Neither `aidd_docs/results/runtime.jsonl` nor
`aidd_docs/results/quality.jsonl` gained a line during capture, and neither
file's bytes changed — the service opens every store for reading, and these
eight responses are this story's own output rather than a benchmark artifact.

Nothing in the bodies is redacted or defaulted. A mostly-absent response *is*
the evidence.
