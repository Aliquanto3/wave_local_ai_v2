// Real field values transcribed from `aidd_docs/results/quality-reference.jsonl`
// (floor "7", run `5e13166da0654390a7d63f346ea5d4f1`), the same source
// `views/quality/fixtures/qualityView.fixture.ts` draws from -- not invented
// values. `leader_set_member` is unowned today (see plan.md's Decisions), so
// `TRANSLATION_USE_CASE` below states that as `Absent(predates_schema)`,
// matching every real row; `CLASSIFICATION_USE_CASE`'s two leader members
// are a hand-edited copy of a real row with `leader_set_member: true` turned
// on, since no store carries the field yet, documented per the same
// discipline `qualityView.fixture.ts`'s own header uses for its edge case.

import type { Absent } from '../../../api/types'
import type {
  JudgeBlock,
  OverviewQualityEntry,
  OverviewQualityView,
} from '../quality/types'

function absent(reason: string, detail: Record<string, unknown> = {}): Absent {
  return { absent: true, reason, detail }
}

const PREDATES_SCHEMA = () => absent('predates_schema', { row_schema_version: '7' })
const NULL_ABSENT = absent('null_in_row')

const PREDATES_SCHEMA_JUDGE: JudgeBlock = {
  judge_prompt_id: PREDATES_SCHEMA(),
  judge_prompt_template_hash: PREDATES_SCHEMA(),
  judge_prompt_language: PREDATES_SCHEMA(),
  rubric_id: PREDATES_SCHEMA(),
  rubric_version: PREDATES_SCHEMA(),
  rubric_kind: PREDATES_SCHEMA(),
  judges: PREDATES_SCHEMA(),
  single_judge: PREDATES_SCHEMA(),
  single_judge_reason: PREDATES_SCHEMA(),
  agreement: PREDATES_SCHEMA(),
  agreement_statistic: PREDATES_SCHEMA(),
  contested: PREDATES_SCHEMA(),
  contested_reason: PREDATES_SCHEMA(),
  contested_threshold: PREDATES_SCHEMA(),
  judged_headline_score: PREDATES_SCHEMA(),
  judged_headline_excluded_n: PREDATES_SCHEMA(),
  judge_egress: PREDATES_SCHEMA(),
  judge_cost: PREDATES_SCHEMA(),
}

const ROSTER_ENTRY = {
  entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  display_id: 'Qwen3.6-35B-A3B',
  repo: 'unsloth/Qwen3.6-35B-A3B-GGUF',
  revision: 'main',
  file: 'Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf',
  quant: 'UD-IQ4_XS',
  sha256: '649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3', // pragma: allowlist secret
  family: null,
  architecture: { kind: 'moe', expert_count: 40, active_params_b: 3.1 },
  roster_version: 2,
}

const SUITE_DEFINITION = {
  snapshot_filename: 'classification-support-routing@2.json',
  context_length: 32768,
  max_output_tokens: 32,
  prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
  stop_sequences: [],
  suite_id: 'classification-support-routing',
  suite_version: '2',
}

const SHARED_FIELDS = {
  run_id: '5e13166da0654390a7d63f346ea5d4f1',
  captured_at: '2026-08-27T05:08:19.554454+00:00',
  schema_version: '7',
  release_version: '0.1.0+untagged',
  commit_sha: '9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7', // pragma: allowlist secret
  tree_dirty: true,
  roster_version: 1,
  endpoint: '/completion',
  prompt_template_id: 'none',
  prompt_template_hash: NULL_ABSENT,
  prompt_capture: 'captured',
  fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a', // pragma: allowlist secret
  task_suite: 'classification',
  sampling: {
    seed: 20260821,
    temperature: 0,
    top_k: 0,
    top_p: 1.0,
    presence_penalty: 0,
  },
  max_output_tokens: 32,
  stop_sequences: [],
  thinking_policy: PREDATES_SCHEMA(),
  context_length: 32768,
  suite_id: 'classification-support-routing',
  suite_version: '2',
  prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
  provenance: 'hand_written',
  failure_counts: {
    empty: 0,
    unparseable: 4,
    truncated_max_tokens: 0,
    truncated_context: 0,
  },
  retries: PREDATES_SCHEMA(),
  resumed: PREDATES_SCHEMA(),
  tokens_in_total: NULL_ABSENT,
  tokens_out_total: 240,
  cost_total: 0.0002960961888663049,
  cost_currency: 'EUR',
  cost_per_million_tokens: NULL_ABSENT,
  normalization_unit: 'cost_per_million_total_tokens',
  kwh_price_eur: 0.194,
  kwh_price_currency: 'EUR',
  kwh_price_recorded_at: '2026-02-01',
  list_price_input_per_million: NULL_ABSENT,
  list_price_output_per_million: NULL_ABSENT,
  list_price_per_million_tokens: NULL_ABSENT,
  list_price_currency: NULL_ABSENT,
  list_price_retrieved_at: NULL_ABSENT,
  roster_entry: ROSTER_ENTRY,
  suite_definition: SUITE_DEFINITION,
  judge: PREDATES_SCHEMA_JUDGE,
  score_shape: 'exact_match' as const,
  correct: true,
  suite_accuracy: 0.8,
  language_breakdown: {
    en: { accuracy: 0.6, indicative: false, n: 10 },
    fr: { accuracy: 1.0, indicative: true, n: 5 },
    de: { accuracy: 1.0, indicative: true, n: 5 },
  },
}

const LOCAL_FICHE = {
  cpu: 'AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD',
  gpu_name: 'NVIDIA GeForce RTX 3060 Laptop GPU',
}

// Hand-edited leader member 1: real row, `leader_set_member: true` set by
// hand (no store carries the field yet).
const LEADER_MEMBER_ONE: OverviewQualityEntry = {
  ...SHARED_FIELDS,
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  model_id: 'Qwen3.6-35B-A3B',
  provider: 'local',
  fiche: LOCAL_FICHE,
  language: 'en',
  contamination_risk: false,
  indicative: false,
  indicative_reasons: [],
  verdict: {
    verdict: 'not_comparable',
    reference_run_id: null,
    differing_fields: [],
    reason: "no reference row shares this batch's model_id/suite_version/seed",
  },
}

// Hand-edited leader member 2: a second real row of the same suite, also
// hand-marked as a leader member.
const LEADER_MEMBER_TWO: OverviewQualityEntry = {
  ...SHARED_FIELDS,
  run_id: 'd20afbda710c40378e6ad5ca8d9b6558',
  captured_at: '2026-08-27T05:09:41.477962+00:00',
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  model_id: 'Qwen3.6-35B-A3B',
  provider: 'local',
  fiche: LOCAL_FICHE,
  language: 'fr',
  contamination_risk: false,
  indicative: true,
  indicative_reasons: ['low_n'],
  verdict: {
    verdict: 'reproduced',
    reference_run_id: '5e13166da0654390a7d63f346ea5d4f1',
    differing_fields: [],
    reason: null,
  },
}

// Real mistral row from the same bundle: a cloud comparator, never ranked
// against the leader.
const CLOUD_COMPARATOR: OverviewQualityEntry = {
  ...SHARED_FIELDS,
  run_id: '5e13166da0654390a7d63f346ea5d4f1',
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  model_id: 'mistral-medium',
  provider: 'mistral',
  fiche: PREDATES_SCHEMA(),
  language: 'en',
  contamination_risk: false,
  indicative: false,
  indicative_reasons: [],
  verdict: {
    verdict: 'not_comparable',
    reference_run_id: null,
    differing_fields: [],
    reason: "no reference row shares this batch's model_id/suite_version/seed",
  },
}

const CLASSIFICATION_USE_CASE = {
  task_suite: 'classification',
  leader: { members: [LEADER_MEMBER_ONE, LEADER_MEMBER_TWO] },
  cloud_comparators: [CLOUD_COMPARATOR],
}

// No store writes `leader_set_member` for this suite either -- the real,
// unedited absence every row of the reference bundle carries.
const TRANSLATION_USE_CASE = {
  task_suite: 'translation',
  leader: PREDATES_SCHEMA(),
  cloud_comparators: [],
}

// A suite whose leader set is published (not `Absent`) but whose every row
// resolved `leader_set_member` to `false` -- a real "evaluated, none
// qualified" fact, distinct from `TRANSLATION_USE_CASE`'s "field unowned".
const EMPTY_LEADER_USE_CASE = {
  task_suite: 'summarization',
  leader: { members: [] },
  cloud_comparators: [CLOUD_COMPARATOR],
}

export const overviewQualityFixture: OverviewQualityView = {
  store: 'quality',
  schema_floor: '7',
  use_cases: [CLASSIFICATION_USE_CASE, TRANSLATION_USE_CASE, EMPTY_LEADER_USE_CASE],
  unreadable: [],
}
