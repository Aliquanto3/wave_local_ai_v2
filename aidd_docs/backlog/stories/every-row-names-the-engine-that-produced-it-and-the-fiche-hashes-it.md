---
type: story
status: ready
source: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
parent: aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md
order: 1
---

# Story: Every row names the engine that produced it, and the fiche hashes it

**As** an academic or technical reviewer reading a runtime or quality number
**I want** every local row to name the inference engine that produced it, with its live-probed build and the configuration defaults it applied, and the fiche's hashed identity to include that engine
**So that** "these are llama.cpp numbers" is a field I can select on rather than an assumption the repository never states, and two engines on one machine can never hash to one identity

Maps to: PRD AC "Given a campaign, every row records its engine (with build identifier and configuration defaults) and its prompt variant..."; PRD User Story "As a consultant, I want the inference engine, the agentic harness and the prompt variant compared as dimensions..."; Methodology 8, 14, 19, 22; epic Boundaries "an engine registry, one tracked entry per engine", "the fiche generalised from one engine to any engine"; epic decisions "Fiche identity", "Engine configuration in the hash", "Thinking control is per engine as well as per model"; epic success check 1 (the registry half: a row naming an engine absent from the registry is refused).

Needs: a real local model run (llama.cpp, `qwen3-0.6b-q8` on the laptop) for the published evidence only; the code and its tests need none.

Current state: `server.py` pins `HOST` and `PORT = 8080` (`server.py:28-29`) and emits llama.cpp's own flag spellings; `llama_cpp_build` is a member of `_NORMALISED_KEYS` (`hardware.py:44-55`); `verdict._RUNTIME_BLOCKING_FIELDS` is `("llama_cpp_build", "quant", "gpu_name", "flags")`; `row_contract.py` is at `SCHEMA_VERSION = "12"` and no row field names an engine; the thinking switch is hardcoded as `chat_template_kwargs.enable_thinking` in `local_client._thinking_kwargs`.

## Acceptance

- A tracked engine registry holds one entry, `llama.cpp`, declared as the reference engine. The entry carries its stable `engine_id`; how its build identifier is read at run time (the live probe `build_probe.py` already performs, never a constant); its endpoint set (chat, health, prompt rendering, template source); its lifecycle, `spawned`; its default port; and its configuration defaults, each marked `declared` by this project or `engine_reported` by the running server. A registry entry missing any of these refuses to load, naming the field, the way `roster.load_roster` refuses an incomplete entry.
- The thinking switch's spelling moves into the engine entry beside the roster entry's declared control: `local_client` reads it from the registry instead of hardcoding it. The llama.cpp entry's switch is verified by rendering one item through `/apply-template` with and without it and recording that the two prompts differ; a declared switch that renders no difference refuses the batch before any generation (as `a-thinking-switch-the-template-ignores-is-refused-never-published-as-disabled` does); an engine that offers no switch declares `none`, checked by the candidate gate.
- The fiche carries `engine_id` and `engine_build` (generalising `llama_cpp_build`) and an engine configuration hash computed over a path-free normalisation: for llama.cpp, the launch flag list with the absolute model path replaced by the roster entry reference. All three are inside the hashed projection; the raw `flags` stay outside it as evidence (Methodology 14). Whether llama.cpp's configuration hash enters the projection is Q20 (`aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md`); this bullet is written to its recommended default and a different answer changes this bullet only.
- `engine_id` and `engine_build` replace `llama_cpp_build` among the runtime verdict's blocking fields. Two constructed fiches identical except for `engine_id` hash differently, and a reproduction verdict between their rows returns `not comparable` naming `engine_id`, never `not reproduced`.
- Every runtime row and every local quality row carries `engine_id` and `engine_build`. The writer gate refuses a local row missing either, and a row whose `engine_id` is not a registry entry, naming the id. A row no local engine produced (a cloud subject's quality row, a judge row) states that the engine does not apply, on the precedent the machine epic sets for `compute_mode`, and never carries `llama.cpp`.
- The port guard at `server.py:155` stays as it is for a `spawned` engine: an occupied port refuses the launch. The host and port a run uses are read from the engine entry rather than module constants, and stay outside the hashed projection as Methodology 14 requires.
- The MoE flagship's launch stays byte-identical (`tests/test_launch_byte_identical.py` unedited and green).
- The schema version is bumped with its history comment. The committed bundle still verifies with no file edited: which projection a stored fiche is verified under is decided by the citing row's `schema_version` (the `FICHE_HASH_SCHEMA_VERSION` precedent), never by a field being absent. The bundle is not regenerated here: the campaign (order 12) republishes under this epic's final schema, superseding rather than back-filling.

## Code it changes

- New tracked engine registry (proposed `aidd_docs/roster/engines.json`) and its loader.
- `hardware.py` (`Fiche` fields, `_NORMALISED_KEYS`, legacy projection), `fiche_registry.py` / `fiche_validator.py`, `verdict.py`, `row_contract.py`.
- `server.py` (host, port and lifecycle from the entry), `local_client.py` (thinking switch from the entry), `build_probe.py` (called through the entry).
- The row and fiche writers (`__init__.py`, `quality_cli.py`, `judge_probe.py`); `CHANGELOG.md`; `aidd_docs/memory/architecture.md` where the fiche is described.

## Tests it needs

- Registry loader: complete entry loads; each missing field refused by name; a default lacking its `declared` / `engine_reported` mark refused.
- `tests/test_hardware.py`: engine fields change the hash; the path-free configuration hash is identical for two model directories; key order irrelevant.
- `tests/test_verdict.py`: engine mismatch is `not comparable` naming `engine_id`.
- `tests/test_row_contract.py`: unregistered engine refused through the gate; cloud row states not applicable; schema-12 bundle still verifies.
- Thinking switch: verified render difference recorded; a no-op switch refuses the batch.

## Evidence it publishes

- One llama.cpp runtime run of `qwen3-0.6b-q8` on the laptop showing `engine_id`, the live-probed `engine_build`, the engine configuration hash and the new `fiche_hash`, and the gate's refusal of a constructed row naming an unregistered engine, recorded in the plan's evidence file.

## Cancellation

n/a: not cancelled.
