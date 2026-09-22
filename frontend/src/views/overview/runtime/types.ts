// Mirrors `read_model.overview_runtime_view`'s JSON shape exactly, the same
// discipline `views/energy/types.ts` holds for its own headline/channel
// split. Imports only `api/types` -- never `views/quality/types.ts` or
// `views/runtime/types.ts`, and deliberately not `views/energy/types.ts`
// either, so the overview's runtime slice stays self-contained (see
// `views/boundary.test.ts`).

import type { Absent, Maybe, UnreadableRows } from '../../../api/types'

export type EnergyChannelName = 'cpu' | 'gpu' | 'ram'

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

export interface RuntimeHeadline {
  median_gen_tok_per_s: Maybe<number>
  machine: Maybe<Record<string, unknown>>
}

export interface OverviewRuntimeEntry {
  roster_entry_id: Maybe<string>
  runtime_headline: RuntimeHeadline
  energy_headline: EnergyHeadline
}

export interface OverviewRuntimeView {
  store: 'runtime'
  schema_floor: string
  entries: OverviewRuntimeEntry[]
  unreadable: UnreadableRows[]
}
