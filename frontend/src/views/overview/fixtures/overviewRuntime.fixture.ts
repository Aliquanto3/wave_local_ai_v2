// Real field values transcribed from `aidd_docs/results/runtime-reference.jsonl`
// (floor "7", roster entry `qwen3.6-35b-a3b-ud-iq4xs`), the same source
// `views/runtime/fixtures/runtimeView.fixture.ts` draws from -- not invented
// values. `WITHHELD_ENTRY` is a hand-edited copy with `gpu_energy_method`
// deleted, documented per the same discipline the sibling fixtures use for
// their own edge case.

import type { OverviewRuntimeEntry, OverviewRuntimeView } from '../runtime/types'

const MACHINE = {
  cpu: 'AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD',
  gpu_name: 'NVIDIA GeForce RTX 3060 Laptop GPU',
}

const LEADER_ENTRY: OverviewRuntimeEntry = {
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  runtime_headline: {
    median_gen_tok_per_s: 24.801659953618945,
    run_id: '5e13166da0654390a7d63f346ea5d4f1',
    fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a', // pragma: allowlist secret
    machine: MACHINE,
  },
  energy_headline: {
    energy_kwh: 0.00132,
    emissions_kg: 0.000074,
    methods: {
      cpu: 'estimated_tdp',
      gpu: 'nvml_sampled',
      ram: 'estimated_constant',
    },
  },
}

// A second roster entry, its gpu_energy_method withheld -- a hand-edited
// copy of a real row.
const WITHHELD_ENTRY: OverviewRuntimeEntry = {
  roster_entry_id: 'phi-4-14b-q4-k-m',
  runtime_headline: {
    median_gen_tok_per_s: 18.2,
    run_id: 'd20afbda710c40378e6ad5ca8d9b6558',
    fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a', // pragma: allowlist secret
    machine: MACHINE,
  },
  energy_headline: {
    withheld: true,
    missing_labels: [
      {
        field: 'gpu_energy_method',
        absence: { absent: true, reason: 'null_in_row', detail: {} },
      },
    ],
  },
}

export const overviewRuntimeFixture: OverviewRuntimeView = {
  store: 'runtime',
  schema_floor: '7',
  entries: [LEADER_ENTRY, WITHHELD_ENTRY],
  unreadable: [],
}
