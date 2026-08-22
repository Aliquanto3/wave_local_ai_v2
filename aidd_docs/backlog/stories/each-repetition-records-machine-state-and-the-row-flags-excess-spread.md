---
type: story
status: done
source: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
parent: aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
depends_on: aidd_docs/backlog/stories/runtime-rows-publish-aggregates-and-peak-memory.md
order: 10
---

# Story: Each repetition records machine state and the row flags excess spread

**As** a client-side engineer deciding whether to trust a throughput figure
**I want** each counted repetition to record the machine state it ran in, and the row to flag itself unreliable when its repetitions disagree
**So that** a number measured on a throttling machine says so instead of being averaged into respectability

## Acceptance

- Methodology 7: each counted repetition records GPU temperature and the NVML throttle reasons in force at that repetition.
- Methodology 7: each counted repetition records CPU package temperature where a reader exists on the platform, and an explicit `unavailable` where none does — the same honesty discipline the energy method labels carry.
- Methodology 7: system load is not recorded on any row. `psutil.getloadavg()` on this platform is an emulation that returned `(0.0, 0.0, 0.0)` against a real 2-3% CPU; a fabricated number is worse than a declared absence.
- Methodology 7: spread is the sample standard deviation of `gen_tok_per_s` over the counted repetitions divided by their median; a row whose spread exceeds 10% (configurable) carries `unreliable` true, with the computed spread recorded whether or not it fires.
- Methodology 7: `ttft_ms` and `prompt_tok_per_s` carry the same spread statistic, reported for interpretation and never raising the flag.
- The inter-repetition thermal posture is declared on the row, so a reader can tell a cold machine from a saturated one.

## Code it changes

- `src/wave_local_ai_v2/machine_state.py` (new) — the per-repetition reader: GPU temperature and throttle reasons through the repo's existing NVML path, CPU package temperature or `unavailable`.
- `src/wave_local_ai_v2/nvml.py` — the throttle-reason and temperature queries.
- `src/wave_local_ai_v2/repetitions.py` — samples machine state per counted repetition.
- `src/wave_local_ai_v2/aggregation.py` — the spread statistic and the flag.
- `src/wave_local_ai_v2/settings.py` — the spread threshold as a configured value defaulting to 10%.

## Tests it needs

- `tests/test_machine_state.py` (new) — with `pynvml` stubbed: temperature and throttle reasons are read and decoded; every NVML failure degrades to explicit nulls without raising; a platform with no CPU temperature reader yields `unavailable` rather than a number or a missing key.
- `tests/test_aggregation.py` — a constructed repetition set at 5.4% spread does not flag, one at 12% flags, and the recorded spread is present in both cases.
- `tests/test_cli.py` — every counted repetition in the written row carries a machine-state block.

## Spike inside this story

Which thermal signals actually explain observed runtime variance on this platform, at ordinary privilege. Bounded, and it does not block the story: the expected answer is the NVML path this repo already owns (GPU temperature and clock event reasons). `psutil.sensors_temperatures` does not exist on Windows at all — `hasattr` is `False` on psutil 7.2.2 — so the documented degrade path for CPU package temperature is the declared `unavailable` state above, and the story ships whether or not a reader is found. What the spike may change is which signals are added beside the GPU pair, never whether the story lands.

## Evidence it publishes

- The regenerated `aidd_docs/results/runtime-reference.jsonl` (order 19), each repetition carrying its machine state, with the observed spread recorded in `aidd_docs/results/README.md` against the 10% threshold rather than assumed to fit it.

## Cancellation

n/a — not cancelled.
