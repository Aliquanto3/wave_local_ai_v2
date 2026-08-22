---
type: story
status: ready
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/a-versioned-roster-pins-every-model.md
order: 13
---

# Story: Flags, model file and build come from the roster, not from source

**As** a consultant running the benchmark on a second machine
**I want** the server flags, the model file and the llama.cpp build to come from the roster and the environment rather than from constants in the code
**So that** a row reports the build the running binary reported instead of one the code asserts, and a new machine needs configuration rather than a source edit

## Acceptance

- Methodology 13: the flag set a run launches with is the flag set its roster entry pins; `N_CPU_MOE`, `THREADS` and the other per-model flag constants stop being source constants.
- Methodology 13: the model file and quant come from the roster entry, resolved under the configured models directory.
- Methodology 14: `llama_cpp_build` is read from the running llama-server binary at launch and recorded from that reading; the `LLAMA_CPP_BUILD = "b10537"` constant in `src/wave_local_ai_v2/__init__.py:25` is removed. A build that cannot be read is an explicit null, never an assumed value.
- A run whose resolved flag set does not match its roster entry cannot start.
- Machine-independent behaviour is preserved: with the first roster entry selected and the same models directory, the launched command is byte-identical to today's validated baseline.

## Code it changes

- `src/wave_local_ai_v2/server.py` — `build_flags` takes a roster entry rather than reading module constants; host and port stay local settings.
- `src/wave_local_ai_v2/__init__.py`, `src/wave_local_ai_v2/quality_cli.py` — model path, quant and flag set resolve through `roster.py`; the run-specific constants are deleted.
- `src/wave_local_ai_v2/settings.py` — roster entry id for the run.
- `src/wave_local_ai_v2/build_probe.py` (new) — reads the build identifier the llama-server binary reports.

## Tests it needs

- `tests/test_server.py` — a roster entry produces the exact validated flag list; a mismatched entry refuses to launch.
- `tests/test_build_probe.py` (new) — with the subprocess stubbed, a version banner is parsed into a build id, an unparseable banner yields null, and a failed invocation never raises. No test starts a real llama-server.
- `tests/test_cli.py` — the row's build, model file and quant come from the probe and the roster, not from constants.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` (order 19): `llama_cpp_build` is a reading rather than the asserted `b10537` the two current tracked rows carry.

## Cancellation

n/a — not cancelled.
