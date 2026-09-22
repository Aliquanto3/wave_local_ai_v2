// Mirrors `read_model.overview_quality_view`'s JSON shape exactly (every
// field this module cannot compute is `Maybe<T>`), the same discipline
// `views/quality/types.ts` holds for `QualityView`. A `use_cases[].leader`
// member and every `cloud_comparators[]` entry are rendered through the same
// `_quality_entry` shape the quality detail route already sends, so
// `OverviewQualityEntry` below is deliberately a full mirror of
// `views/quality/types.ts`'s own `QualityEntry` rather than a narrower type
// -- imported from nowhere else, though: this module imports only
// `api/types`, never `views/quality/types.ts` or `views/runtime/types.ts`,
// so the overview's quality slice stays self-contained (see
// `views/boundary.test.ts`).

import type { Absent, Maybe, RosterEntry, UnreadableRows } from '../../../api/types'

export interface VerdictBlock {
  verdict: Maybe<string>
  reference_run_id: Maybe<string> | null
  differing_fields: Maybe<string[]>
  reason?: Maybe<string> | null
}

export interface FailureCounts {
  empty: Maybe<number>
  unparseable: Maybe<number>
  truncated_max_tokens: Maybe<number>
  truncated_context: Maybe<number>
}

export interface SuiteDefinition {
  snapshot_filename: string
  suite_id: Maybe<string>
  suite_version: Maybe<string>
  prompt_set_hash: Maybe<string>
  max_output_tokens: Maybe<number>
  stop_sequences: Maybe<string[]>
  thinking_policy?: Maybe<string>
  context_length: Maybe<number>
}

export interface ExactMatchLanguageCell {
  accuracy: Maybe<number>
  n: Maybe<number>
  indicative: Maybe<boolean>
}

export interface GradedLanguageCell {
  score: Maybe<number>
  n: Maybe<number>
  indicative: Maybe<boolean>
}

export interface JudgeBlock {
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

export interface OverviewQualityEntry {
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
  verdict: Maybe<VerdictBlock>
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
  failure_counts: Maybe<FailureCounts>
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
  suite_definition: Maybe<SuiteDefinition>
  judge: JudgeBlock

  // QUALITY_EXACT_MATCH_FIELDS: present only when score_shape is 'exact_match'.
  correct?: Maybe<boolean>
  suite_accuracy?: Maybe<number>
  language_breakdown?: Maybe<Record<string, ExactMatchLanguageCell>>

  // QUALITY_GRADED_FIELDS: present only when score_shape is 'graded'.
  metric_id?: Maybe<string>
  metric_version?: Maybe<string>
  metric_params?: Maybe<Record<string, unknown>>
  item_score?: Maybe<number>
  suite_score?: Maybe<number>
  reference_output?: Maybe<string>
  score_breakdown?: Maybe<Record<string, GradedLanguageCell>>
}

export interface LeaderSet {
  members: OverviewQualityEntry[]
}

// Absent when the leader set is unowned (predates_schema, today's live
// path): no derivation writes `leader_set_member` yet.
export type Leader = Absent | LeaderSet

export interface UseCase {
  task_suite: Maybe<string>
  leader: Leader
  cloud_comparators: OverviewQualityEntry[]
}

export interface OverviewQualityView {
  store: 'quality'
  schema_floor: string
  use_cases: UseCase[]
  unreadable: UnreadableRows[]
}
