---
type: story
status: proposed
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
depends_on:
  - aidd_docs/backlog/stories/every-row-names-the-engine-that-produced-it-and-the-fiche-hashes-it.md
  - aidd_docs/backlog/stories/a-campaign-is-declared-as-data-and-an-empty-cell-fails-it.md
order: 6
---

# Story: Ollama runtime rows stand beside llama.cpp rows on the same artifact

**As** a client-side engineer asking whether Ollama would give different numbers
**I want** Ollama registered as the attached comparator engine, checked before every run, pointed at the roster entry's own GGUF, and run under the unchanged runtime protocol
**So that** an Ollama row and a llama.cpp row of the same model on the same machine are two honestly separate measurements of one artifact, never a hash collision and never a comparison confounded by the file each engine loaded

Maps to: PRD AC "Given a campaign, every row records its engine (with build identifier and configuration defaults)..."; PRD Dependency "Availability of a second inference engine (Ollama) as a pinned, installable build alongside llama.cpp"; Methodology 3, 6, 7, 8, 14, 15, 20, 22; epic Boundaries "two declared engines ... and the lifecycle difference between them made explicit", "the same-artifact rule and its record on the row", "the runtime protocol and the quality path both run per engine, unchanged in shape"; epic decisions "Attached engines", "Fiche identity"; epic success check 2.

Needs: a real local model run on the reference machine with a pinned Ollama build installed beside llama.cpp (an operator installs it once). No API key.

Blocked: none by a spike. Spike `aidd_docs/backlog/spikes/can-a-pinned-ollama-build-serve-the-roster-gguf-under-the-runtime-protocol.md` is `resolved` (live session on Ollama v0.35.1, 2026-10-04: `same_gguf` reached by import, the model held loaded across a warm-up and five counted repetitions with no reload, the over-long prompt refused with HTTP 400, a second client not observable through any endpoint). Both `depends_on` are `done`. Readiness is the owner's to reassess against that spike's remaining uncertainty: every counted repetition on Ollama reused 60 of its 61 prompt tokens from the runner's prompt cache and no captured request field disables it, while this story runs the runtime protocol exactly as written (a full prefill per repetition, `cache_prompt: false`).

Current state (verified on `main` at `c68b23e`, 2026-10-03):

- `aidd_docs/roster/engines.json` registers one engine, `llama.cpp` (`reference: true`, `lifecycle: spawned`, `default_port` 8080, `thinking_switch.request_field` `chat_template_kwargs`); there is no `ollama` entry.
- `engines.LIFECYCLES` accepts `attached` at load, but nothing serves it: `server.start_server` refuses any engine not `spawned`, and its port guard (`server._port_is_open`) is the spawned rule only. No pre-run attachment, keep-alive or context check exists.
- `engines.REQUIRED_FIELDS` requires `config_normalisation.model_path_flag` and `location_flags`, and `engines.normalise_config` raises when the launch flags carry no model path flag: the configuration hash is defined over a launch flag list only. An attached engine has none, so the Ollama entry needs the epic's comparator normalisation ("its model definition plus the resolved options the server reports").
- Fiche projection `"2"` (`hardware.FICHE_PROJECTIONS`, `CURRENT_FICHE_PROJECTION`) hashes `engine_id`, `engine_build` and `engine_config_hash`, and `verdict._RUNTIME_BLOCKING_FIELDS` is `("engine_id", "engine_build", "quant", "gpu_name", "flags")`: two engines already hash and verdict apart once a second entry exists.
- `row_contract.SCHEMA_VERSION` is `"22"`; no row carries `artifact_parity` or an attachment-check record. `ttft_source` takes `timings.TTFT_SOURCE_SERVER_REPORTED` or `TTFT_SOURCE_CLIENT_MEASURED`.
- `comparison.DIMENSIONS` holds `model` and `prompt_variant` only; no comparison runs along an engine axis.
- Spike desk findings the entry can be drafted from, unverified until the live session: version probe `GET /api/version`, health `GET /`, chat `POST /api/chat`, default port 11434; `same_gguf` reachable by `FROM <roster file>` (the model layer digest is the file's SHA-256); `/api/ps` `context_length` is the engine-reported effective context; concurrent clients are not observable through any endpoint; keep-alive pinned per request with `keep_alive: -1`; `prompt_eval_duration` is a server-reported TTFT on the llama.cpp rows' definition; Ollama v0.35.1 runs a bundled, patched llama-server `b11232`, not the reference's `b10537`.

## Acceptance

- The engine registry gains `ollama` as the comparator, complete under order 1's rule: its pinned version and the live probe that reads it, its endpoint set, its default port, its configuration defaults each marked `declared` or `engine_reported`, and its lifecycle, `attached`.
- The port rule holds for both lifecycles without weakening either: a `spawned` engine refuses an occupied port (unchanged); an `attached` engine refuses when nothing answers on its declared port, naming the engine and port.
- Before every run on an `attached` engine, the harness reads what the engine has loaded. A model other than the run's own, or a second client where the engine makes one observable, refuses the run naming what was found. Where concurrent clients are not observable on this engine, the row records that the check could not be made.
- The engine's model lifetime is pinned for the run so that weights stay loaded across the warm-up, the counted repetitions and the recorded cooldowns. A reload detected during a counted repetition fails the row under Methodology 6, naming the repetition index and the reload as its reason.
- The effective context the engine reports is read back before the run and asserted against the run's declared context length; a mismatch refuses the run naming both values.
- Every Ollama row carries `artifact_parity`: `same_gguf` when the loaded file's checksum matches the roster entry's `sha256`, or `engine_supplied` naming what the engine loaded and the quant it chose. A comparison between two engines where either side is not `same_gguf` is published as an observation, never as a paired engine comparison.
- The runtime protocol runs on Ollama exactly as written (warm-up excluded, at least 5 counted repetitions, the recorded cooldown, machine state per repetition, the spread flag), and `ttft_source` names whether Ollama's first-token time was server-reported or client-measured.
- Two runtime rows on one machine, one model and one variant, one per engine, carry different `fiche_hash` values, and a reproduction verdict between them returns `not comparable` naming the engine fields (epic success check 2).

## Code it changes

- The `ollama` registry entry; an attached-engine lifecycle beside `server.running_server`; an Ollama chat and timing client beside `local_client`; the pre-run attachment, keep-alive and context checks.
- `engines.py`: a configuration normalisation for an attached engine, which has no launch flag list; `comparison.py`: an engine axis that reads `artifact_parity`.
- `row_contract.py`: `artifact_parity` and its detail, the attachment-check record, `SCHEMA_VERSION` bumped; `docs/setup.md`: installing the pinned Ollama build.

## Tests it needs

- Port rule per lifecycle; foreign loaded model refused; context mismatch refused; a simulated reload mid-repetition fails the row with its index.
- `artifact_parity` set from a checksum match and from a mismatch; a cross-engine comparison with `engine_supplied` on one side is an observation.
- Two-engine fiches hash differently; the verdict names the engine fields.

## Evidence it publishes

- One runtime row per engine for `qwen3-0.6b-q8` on the reference machine, both `same_gguf` if the spike shows it reachable, their two fiche hashes and the `not comparable` verdict between them, recorded in `aidd_docs/results/README.md`.

## Cancellation

n/a: not cancelled.
