// Mirrors `read_model.comparison_view`'s JSON shape exactly, the same
// discipline `views/quality/types.ts` holds -- deliberately does not import
// `views/quality/types.ts` or `views/runtime/types.ts` (see
// `views/boundary.test.ts`'s third check), so the identity/score fields a
// "compared" cell carries are restated here rather than shared.

import type { Maybe, RosterEntry } from '../../api/types'

export interface ComparisonVerdictBlock {
  verdict: Maybe<string>
  reference_run_id: Maybe<string> | null
  differing_fields: Maybe<string[]>
  reason?: Maybe<string> | null
}

export interface ComparisonFailureCounts {
  empty: Maybe<number>
  unparseable: Maybe<number>
  truncated_max_tokens: Maybe<number>
  truncated_context: Maybe<number>
}

export interface ComparisonSuiteDefinition {
  snapshot_filename: string
  suite_id: Maybe<string>
  suite_version: Maybe<string>
  prompt_set_hash: Maybe<string>
  max_output_tokens: Maybe<number>
  stop_sequences: Maybe<string[]>
  thinking_policy?: Maybe<string>
  context_length: Maybe<number>
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

export interface ComparisonJudgeBlock {
  judge_prompt_id: Maybe<string>
  judge_prompt_template_hash: Maybe<string>
  judge_prompt_language: Maybe<string>
  rubric_id: Maybe<string>
  rubric_version: Maybe<string>
  rubric_kind: Maybe<string>
  judges: Maybe<unknown>
  single_judge: Maybe<boolean>
  single_judge_reason: Maybe<string>
  agreement: Maybe<number>
  agreement_statistic: Maybe<string>
  contested: Maybe<boolean>
  contested_reason: Maybe<string>
  contested_threshold: Maybe<number>
  judged_headline_score: Maybe<number>
  judged_headline_excluded_n: Maybe<number>
  judge_egress: Maybe<unknown>
  judge_cost: Maybe<unknown>
}

// The fields a "compared" cell carries: `_quality_entry`'s own output,
// exactly as `QualityEntry` mirrors it -- restated here rather than shared,
// per this module's own boundary.
export interface ComparedCellFields {
  // RUNS_VIEW_FIELDS: the identity block every view carries.
  run_id: Maybe<string>
  captured_at: Maybe<string>
  schema_version: Maybe<string>
  roster_entry_id: Maybe<string>
  release_version: Maybe<string>
  commit_sha: Maybe<string>
  tree_dirty: Maybe<boolean>

  // QUALITY_VIEW_FIELDS.
  roster_version: Maybe<number>
  endpoint: Maybe<string>
  prompt_template_id: Maybe<string>
  prompt_template_hash: Maybe<string>
  prompt_capture: Maybe<string>
  model_id: Maybe<string>
  provider: Maybe<string>
  fiche_hash: Maybe<string>
  verdict: Maybe<ComparisonVerdictBlock>
  task_suite: Maybe<string>
  item_id: Maybe<string>
  expected_label: Maybe<string>
  predicted_label: Maybe<string>
  sampling: Maybe<Record<string, unknown>>
  max_output_tokens: Maybe<number>
  stop_sequences: Maybe<string[]>
  thinking_policy: Maybe<string>
  context_length: Maybe<number>
  suite_id: Maybe<string>
  suite_version: Maybe<string>
  prompt_set_hash: Maybe<string>
  language: Maybe<string>
  provenance: Maybe<string>
  contamination_risk: Maybe<boolean>
  indicative: Maybe<boolean>
  indicative_reasons: Maybe<string[]>
  failure_reason: Maybe<string>
  failure_counts: Maybe<ComparisonFailureCounts>
  retries: Maybe<number>
  resumed: Maybe<boolean>
  tokens_in_total: Maybe<number>
  tokens_out_total: Maybe<number>
  cost_total: Maybe<number>
  cost_currency: Maybe<string>
  cost_per_million_tokens: Maybe<number>
  normalization_unit: Maybe<string>
  kwh_price_eur: Maybe<number>
  kwh_price_currency: Maybe<string>
  kwh_price_recorded_at: Maybe<string>
  list_price_input_per_million: Maybe<number>
  list_price_output_per_million: Maybe<number>
  list_price_per_million_tokens: Maybe<number>
  list_price_currency: Maybe<string>
  list_price_retrieved_at: Maybe<string>

  score_shape: 'exact_match' | 'graded'
  roster_entry: Maybe<RosterEntry>
  fiche: Maybe<Record<string, unknown>>
  suite_definition: Maybe<ComparisonSuiteDefinition>
  judge: ComparisonJudgeBlock

  // QUALITY_EXACT_MATCH_FIELDS: present only when score_shape is 'exact_match'.
  correct?: Maybe<boolean>
  suite_accuracy?: Maybe<number>
  language_breakdown?: Maybe<Record<string, ComparisonExactMatchLanguageCell>>

  // QUALITY_GRADED_FIELDS: present only when score_shape is 'graded'.
  metric_id?: Maybe<string>
  metric_version?: Maybe<string>
  metric_params?: Maybe<Record<string, unknown>>
  item_score?: Maybe<number>
  suite_score?: Maybe<number>
  reference_output?: Maybe<string>
  score_breakdown?: Maybe<Record<string, ComparisonGradedLanguageCell>>
}

// A discriminated union on `status`: the third cell shape decision.md
// mandates -- never a `null` and never a blank that reads like a zero.
export type ComparisonCell =
  | ({ status: 'compared' } & ComparedCellFields)
  | { status: 'not_compared'; item_id: Maybe<string> }

export interface ComparisonColumn {
  roster_entry_id: Maybe<string>
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
