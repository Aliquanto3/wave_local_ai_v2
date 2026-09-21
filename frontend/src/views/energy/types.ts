// Mirrors `read_model.energy_view`'s JSON shape exactly, matching
// `read_model.ENERGY_VIEW_FIELDS` and `read_model._energy_entry`'s own
// channel/composite/headline split. Deliberately does not import
// `views/quality/types.ts` or `views/runtime/types.ts` -- see
// `views/boundary.test.ts`.

import type { Absent, Maybe } from '../../api/types'

export type EnergyChannelName = 'cpu' | 'gpu' | 'ram'

export interface EnergyChannel {
  energy_kwh: Maybe<number>
  energy_method: Maybe<string>
}

export type EnergyChannels = Record<EnergyChannelName, EnergyChannel>

export interface MissingLabel {
  field: string
  absence: Absent
}

export interface EnergyHeadlineWithheld {
  withheld: true
  missing_labels: MissingLabel[]
}

export interface EnergyHeadlineComposite {
  energy_kwh: Maybe<number>
  emissions_kg: Maybe<number>
  methods: Record<EnergyChannelName, Maybe<string>>
}

export type EnergyHeadline = EnergyHeadlineWithheld | EnergyHeadlineComposite

export function isWithheldHeadline(
  headline: EnergyHeadline,
): headline is EnergyHeadlineWithheld {
  return (headline as EnergyHeadlineWithheld).withheld === true
}

export interface EnergyEntry {
  // RUNS_VIEW_FIELDS: the identity block every view carries.
  run_id: Maybe<string>
  captured_at: Maybe<string>
  schema_version: Maybe<string>
  roster_entry_id: Maybe<string>
  release_version: Maybe<string>
  commit_sha: Maybe<string>
  tree_dirty: Maybe<boolean>

  channels: EnergyChannels

  // ENERGY_VIEW_FIELDS minus the per-channel energy/method fields, which
  // live under `channels` above.
  energy_kwh: Maybe<number>
  emissions_kg: Maybe<number>
  emission_factor_kg_per_kwh: Maybe<number>
  emission_region: Maybe<string>
  emissions_scope: Maybe<string>
  emissions_scope_formula_id: Maybe<string>
  scope_comparability: Maybe<string>

  energy_headline: EnergyHeadline
}

export interface EnergyView {
  store: 'runtime' | 'quality'
  run_id: string
  schema_floor: string
  entries: EnergyEntry[]
  unreadable: { schema_version: string; count: number; reason: string }[]
}
