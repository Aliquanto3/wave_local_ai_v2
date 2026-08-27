---
objective: "Every runtime and quality row carries per-channel energy with per-channel method labels, an emissions figure with its factor/region/scope boundary, and a derived cost with its normalization unit and derivation inputs — never a single mislabeled composite, never a cost without what produced it."
status: implemented
---

<!-- Fill or omit these sections; never add, rename, or reorder one. -->

# Plan: Per-channel energy, emissions scope and cost

## Overview

| Field      | Value                   |
| ---------- | ----------------------- |
| **Goal**   | Ship Methodology 15 (Story: rows-carry-per-channel-energy-emissions-and-their-scope-boundary, order 17) and Methodology 16 (Story: rows-carry-a-cost-and-what-it-was-derived-from, order 18) as one increment, energy/emissions first since cost's local half is derived from `energy_kwh`. |
| **Source** | `aidd_docs/backlog/stories/rows-carry-per-channel-energy-emissions-and-their-scope-boundary.md` (order 17), `aidd_docs/backlog/stories/rows-carry-a-cost-and-what-it-was-derived-from.md` (order 18), PRD `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` (Methodology 15, 16), epic `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md` |

## Phases

| #   | Phase                                                       | File                          |
| --- | ------------------------------------------------------------ | ---------------------------- |
| 1   | Per-channel energy + emissions module + contract              | [`phase-1.md`](./phase-1.md) |
| 2   | Cost module + Mistral token usage + contract                  | [`phase-2.md`](./phase-2.md) |
| 3   | CLI wiring, live runs, docs and memory                        | [`phase-3.md`](./phase-3.md) |

## Resources

| Source | Verified |
| ------ | -------- |
| `.venv/Lib/site-packages/codecarbon/output_methods/emissions_data.py` (installed codecarbon 3.3.0) | `EmissionsData` field names and units: `cpu_energy`, `gpu_energy`, `ram_energy`, `energy_consumed` are all kWh floats (never `None`, never absent — a channel with no hardware reads `0.0`, not a missing key); `emissions` is kg CO2eq; `gpu_count` tells whether NVML found a GPU, independent of the energy magnitude. |
| `.venv/Lib/site-packages/codecarbon/emissions_tracker.py` (`OfflineEmissionsTracker.__init__` docstring) | `country_iso_code` (3-letter, e.g. `"FRA"`) selects the static grid mix with no live geolocation call; `region` is documented as supported for US states and Canadian provinces only — not usable for France, so the row's published "region" is the configured `country_iso_code`/its 2-letter form, not codecarbon's `region` kwarg. |
| `.venv/Lib/site-packages/codecarbon/external/ram.py` (`RAM.total_power`) | RAM power is always a fixed-constant estimate (`RAM_SLOT_POWER_X86` / a W-per-8GB rule), on every platform — never a measured channel, so `ram_energy_method` is unconditionally `"estimated_constant"`, not derived from a live introspection. |
| `.venv/Lib/site-packages/codecarbon/data/private_infra/global_energy_mix.json` (`"FRA"` entry) | France's `carbon_intensity` is `56.039` (gCO2eq/kWh, year 2023) — the source for the default `EMISSION_FACTOR_KG_PER_KWH = 0.056039`, cited in `emissions.py` with this file path and year. |
| `aidd_docs/memory/architecture.md` Gotchas | "On Windows, CodeCarbon has no RAPL access and falls back to TDP-based estimation" — confirms `cpu_energy_method` stays unconditionally `"estimated_tdp"` on this project's target platform; a future non-Windows run is out of scope for this increment. |

## Decisions

<!-- Architecture-magnitude only, one you'd regret reversing. Omit if none qualify. -->

| Decision | Why |
| -------- | --- |
| A channel's method label is derived from what CodeCarbon can structurally report, not from the channel's own magnitude (today's `gpu_energy > 0` heuristic is kept only for GPU, and only as an *availability* check via `gpu_count > 0`, not a value check). `cpu_energy_method` is always `"estimated_tdp"`, `ram_energy_method` is always `"estimated_constant"`, `gpu_energy_method` is `"measured_nvml"` when `gpu_count > 0` else `null` + `"unavailable"`. This is what makes "a channel that genuinely drew ~0W in a short run" distinguishable from "no GPU present" — the bug the story's last acceptance line names. |
| `measure_energy` switches from `codecarbon.EmissionsTracker` (which attempts a live IP-geolocation lookup for its country/region) to `codecarbon.OfflineEmissionsTracker(country_iso_code=..., output_methods=[], log_level="error")`. This is the story's explicit instruction ("declared for CodeCarbon offline mode ... rather than looked up live") and removes an implicit network dependency the current code carries. |
| `emissions_kg` is computed by this project (`energy_kwh * emission_factor_kg_per_kwh`), not read off `tracker.final_emissions_data.emissions`. Keeping one arithmetic source makes the story's own acceptance test ("`energy_kwh` times the configured factor equals `emissions_kg`") a direct assertion on `emissions.py` rather than an indirect check on CodeCarbon's internal math, and keeps the Scope-3 cloud path (which CodeCarbon never touches at all) on the same formula shape. |
| The per-channel energy fields (`cpu_energy_kwh`, `gpu_energy_kwh`, `ram_energy_kwh`) join `aggregation.AGGREGATION_LABELS` with the same `"total_over_counted_repetitions_including_cooldowns"` label `energy_kwh` already carries — they are measured by the same tracker over the same span. `emissions_kg` does **not** join it: it is a downstream computation of `energy_kwh`, in the same category as `verdict` or `fiche_hash`, not an independent thing the tracker measured. |
| Quality rows get the *same* per-channel/emissions/cost field set as runtime rows (one `REQUIRED_FIELDS` shape per kind, per the row-contract convention this project already established), populated differently per provider: a `local` quality row wraps its whole suite loop in one `measure_energy` call (Scope 2, CodeCarbon channels populated, mirroring how `suite_accuracy` is already one batch-level number repeated on every item row); a `mistral` quality row's three CodeCarbon channels are `null`/`"unavailable"` (no on-machine energy to attribute to a network call) and its `energy_kwh`/`emissions_kg` instead come from the Scope-3 Wh-per-token formula, keyed to that batch's total tokens. |
| Cost is **batch-level**, not per-item, for quality rows — same repeated-value pattern as `suite_accuracy` and (for local) the Scope-2 energy above. Splitting a batch's real cost evenly across items would fabricate a per-item figure this project has no way to measure. |
| The row contract carries every cost-derivation field for both bases (`kwh_price*` and `list_price*`) on every row of both kinds; the inapplicable half is `null`, the same pattern `prompt_template_hash` already uses for the raw local path. This keeps `REQUIRED_FIELDS` one flat set per kind rather than a per-provider union, consistent with today's contract shape. |
| `tokens_in_total` on a **runtime** row is `null` until a live `/completion` response confirms which field (`tokens_evaluated` at top level, or `timings.prompt_n`) carries the prompt-token count on build `b10537` — the harness does not synthesize a token count it never asked the server for. `tokens_out_total` is `sum(tokens_predicted)` over the counted repetitions, already captured. `cost_per_million_tokens` is `null` when its denominator is unknown or zero, the same "undefined, not fabricated" rule `aggregation.spread` already applies to a zero median. |
| Normalization unit is fixed at `"cost_per_million_total_tokens"` (`total_tokens = tokens_in_total + tokens_out_total` when both are known), a named constant in `cost.py`, per the story's "chosen once for the project." |
