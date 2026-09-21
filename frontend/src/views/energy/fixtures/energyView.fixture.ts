// Real rows from `aidd_docs/results/runtime-reference.jsonl`, read through
// `read_model.energy_view` over the committed reference bundle (floor "7",
// run `f5f78c795eaa4175ac506440e597ee3e`) and hand-transcribed here -- not
// invented values. `WITHHELD_HEADLINE_ENTRY` is a hand-built edge case per
// phase-3's task 2: the real bundle carries no row with a missing channel
// method, so this is a copy of the real entry with `gpu_energy_method` set
// to `Absent`, documented here.

import type { Absent } from '../../../api/types'
import type { EnergyEntry, EnergyView } from '../types'

function absent(reason: string, detail: Record<string, unknown> = {}): Absent {
  return { absent: true, reason, detail }
}

const IDENTITY = {
  run_id: 'f5f78c795eaa4175ac506440e597ee3e',
  captured_at: '2026-08-27T04:57:27.124220+00:00',
  schema_version: '7',
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  release_version: '0.1.0+untagged',
  commit_sha: '9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7', // pragma: allowlist secret
  tree_dirty: true,
}

// Real values (see plan.md Decisions for why `scope_comparability` is
// `null_in_row` on this bundle -- hand-edited to a real string below to
// exercise ScopeComparabilityLabel, since no row in the bundle carries one).
const FULLY_LABELLED_ENTRY: EnergyEntry = {
  ...IDENTITY,
  channels: {
    cpu: { energy_kwh: 0.0009217651125, energy_method: 'estimated_tdp' },
    gpu: { energy_kwh: 0.001168761490564, energy_method: 'measured_nvml' },
    ram: { energy_kwh: 0.000513982856666654, energy_method: 'estimated_constant' },
  },
  energy_kwh: 0.002604509459730654,
  emissions_kg: 0.0001459541056138461,
  emission_factor_kg_per_kwh: 0.056039,
  emission_region: 'FR',
  emissions_scope: 'scope_2',
  emissions_scope_formula_id: absent('null_in_row'),
  // Hand-edited from the real Absent -- see the comment above.
  scope_comparability:
    'cpu/ram are Scope-2 local (grid-drawn), gpu is measured on-device: not comparable to a cloud provider’s Scope-3 published figure',
  energy_headline: {
    energy_kwh: 0.002604509459730654,
    emissions_kg: 0.0001459541056138461,
    methods: {
      cpu: 'estimated_tdp',
      gpu: 'measured_nvml',
      ram: 'estimated_constant',
    },
  },
}

// Hand-edited copy: gpu_energy_method turned Absent, withholding the
// headline per `read_model._energy_entry`'s own rule.
const WITHHELD_HEADLINE_ENTRY: EnergyEntry = {
  ...IDENTITY,
  channels: {
    cpu: { energy_kwh: 0.0009217651125, energy_method: 'estimated_tdp' },
    gpu: {
      energy_kwh: 0.001168761490564,
      energy_method: absent('null_in_row'),
    },
    ram: { energy_kwh: 0.000513982856666654, energy_method: 'estimated_constant' },
  },
  energy_kwh: 0.002604509459730654,
  emissions_kg: 0.0001459541056138461,
  emission_factor_kg_per_kwh: 0.056039,
  emission_region: 'FR',
  emissions_scope: 'scope_2',
  emissions_scope_formula_id: absent('null_in_row'),
  scope_comparability: absent('null_in_row'),
  energy_headline: {
    withheld: true,
    missing_labels: [{ field: 'gpu_energy_method', absence: absent('null_in_row') }],
  },
}

export const energyViewFixture: EnergyView = {
  store: 'runtime',
  run_id: 'f5f78c795eaa4175ac506440e597ee3e',
  schema_floor: '7',
  entries: [FULLY_LABELLED_ENTRY, WITHHELD_HEADLINE_ENTRY],
  unreadable: [],
}
