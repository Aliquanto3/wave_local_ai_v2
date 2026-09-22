// Mirrors `read_model.comparison_view`'s JSON shape exactly, the same
// discipline `views/quality/types.ts` holds -- deliberately imports neither
// `views/quality/types.ts` nor `views/runtime/types.ts`, so the few score
// fields a "compared" cell carries are restated here rather than shared.

import type { Maybe, RosterEntry } from '../../api/types'

export interface ComparisonVerdictBlock {
  verdict: Maybe<string>
  reference_run_id: Maybe<string> | null
  differing_fields: Maybe<string[]>
  reason?: Maybe<string> | null
}

export interface ComparisonExactMatchLanguageCell {
  accuracy: Maybe<number>
  n: Maybe<number>
  indicative: Maybe<boolean>
}

export interface ComparisonGradedLanguageCell {
  score: Maybe<number>
  n: Maybe<number>
  indicative: Maybe<boolean>
}

// The fields a "compared" cell carries: `read_model.COMPARISON_CELL_FIELDS`,
// a quality-only projection of `_quality_entry` -- no cost, pricing, token
// total or energy field reaches this route.
export interface ComparedCellFields {
  run_id: Maybe<string>
  item_id: Maybe<string>
  score_shape: 'exact_match' | 'graded'
  contamination_risk: Maybe<boolean>
  verdict: Maybe<ComparisonVerdictBlock>

  // Present only when score_shape is 'exact_match'.
  correct?: Maybe<boolean>
  suite_accuracy?: Maybe<number>
  language_breakdown?: Maybe<Record<string, ComparisonExactMatchLanguageCell>>

  // Present only when score_shape is 'graded'.
  metric_id?: Maybe<string>
  item_score?: Maybe<number>
  suite_score?: Maybe<number>
  score_breakdown?: Maybe<Record<string, ComparisonGradedLanguageCell>>
}

// A discriminated union on `status`: the third cell shape decision.md
// mandates -- never a `null` and never a blank that reads like a zero.
export type ComparisonCell =
  | ({ status: 'compared' } & ComparedCellFields)
  | { status: 'not_compared'; item_id: Maybe<string> }

export interface ComparisonColumn {
  roster_entry_id: Maybe<string>
  // With roster_entry_id, the column's model identity: a cited comparator
  // shares its subject's roster_entry_id, so these tell the two apart.
  provider: Maybe<string>
  model_id: Maybe<string>
  // The machine (whole-setup fingerprint): one column per host, so a later
  // host's run never hides an earlier one's.
  fiche_hash: Maybe<string>
  run_id: Maybe<string>
  suite_version: Maybe<string>
  prompt_set_hash: Maybe<string>
  thinking_policy: Maybe<string>
  roster_entry: Maybe<RosterEntry>
  // COMPARISON_DIMENSIONS, resolved. Iterated with `Object.entries` by the
  // view, never hand-listed -- a future dimension needs no new branch here.
  dimensions: Record<string, Maybe<unknown>>
}

export interface ComparisonItem {
  item_id: Maybe<string>
  cells: ComparisonCell[]
}

export interface ComparisonSuite {
  suite_id: Maybe<string>
  columns: ComparisonColumn[]
  items: ComparisonItem[]
}

export interface ComparisonView {
  store: 'quality'
  schema_floor: string
  suites: ComparisonSuite[]
  unreadable: { schema_version: string; count: number; reason: string }[]
}
