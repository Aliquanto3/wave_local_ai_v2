// Real rows from `aidd_docs/results/quality-reference.jsonl`, read through
// `read_model.quality_view` over the committed reference bundle (floor "7",
// run `5e13166da0654390a7d63f346ea5d4f1` and
// `d20afbda710c40378e6ad5ca8d9b6558`) and hand-transcribed here -- not
// invented values. `PREDATES_SCHEMA_JUDGE` mirrors every real entry's own
// judge block: no store holds a judged row at this bundle's floor, so every
// judge field is `Absent(predates_schema)`.
//
// The bundle carries no judged, contested, or graded row and every real
// `contamination_risk`/`indicative` (suite-level) is `false`/`[]` -- so
// `HAND_EDITED_EDGE_CASE_ENTRY` below is a copy of a real row with exactly
// those marks turned on, documented field by field, per plan.md's Decisions
// and phase-3's task 2.

import type { Absent } from '../../../api/types'
import type { JudgeBlock, QualityEntry, QualityView } from '../types'

function absent(reason: string, detail: Record<string, unknown> = {}): Absent {
  return { absent: true, reason, detail }
}

const PREDATES_SCHEMA = () => absent('predates_schema', { row_schema_version: '7' })

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

const NULL_ABSENT = absent('null_in_row')

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

const FICHE = {
  cpu: 'AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD',
  cuda_ceiling: '12.8',
  flags: [
    '-m',
    'D:\\ia\\models\\Qwen3.6-35B-A3B\\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf',
    '-ngl',
    '99',
    '--n-cpu-moe',
    '37',
    '-c',
    '32768',
    '-fa',
    'on',
    '-t',
    '8',
    '--jinja',
    '-np',
    '1',
    '--load-mode',
    'none',
    '--temp',
    '1.0',
    '--top-p',
    '0.95',
    '--top-k',
    '20',
    '--min-p',
    '0',
    '--presence-penalty',
    '1.5',
    '--host',
    '127.0.0.1',
    '--port',
    '8080',
  ],
  gpu_driver_version: '572.70',
  gpu_name: 'NVIDIA GeForce RTX 3060 Laptop GPU',
  llama_cpp_build: 'b10537',
  model_sha256: '649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3', // pragma: allowlist secret
  os: 'Windows 11',
  quant: 'UD-IQ4_XS',
  ram_gb: 31.4,
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
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

const IDENTITY_5E1 = {
  run_id: '5e13166da0654390a7d63f346ea5d4f1',
  captured_at: '2026-08-27T05:08:19.554454+00:00',
  schema_version: '7',
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  release_version: '0.1.0+untagged',
  commit_sha: '9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7', // pragma: allowlist secret
  tree_dirty: true,
}

const SHARED_FIELDS = {
  roster_version: 1,
  endpoint: '/completion',
  prompt_template_id: 'none',
  prompt_template_hash: NULL_ABSENT,
  prompt_capture: 'captured',
  model_id: 'Qwen3.6-35B-A3B',
  provider: 'local',
  fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a', // pragma: allowlist secret
  task_suite: 'classification',
  expected_label: 'billing',
  predicted_label: 'billing',
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
  failure_reason: NULL_ABSENT,
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
  fiche: FICHE,
  suite_definition: SUITE_DEFINITION,
  judge: PREDATES_SCHEMA_JUDGE,
}

// billing-01, run 5e13166...: no reference run exists yet, so the verdict is
// not_comparable. Real per-language indicative marks (fr/de: true, en: false).
const NOT_COMPARABLE_ENTRY: QualityEntry = {
  ...IDENTITY_5E1,
  ...SHARED_FIELDS,
  item_id: 'billing-01',
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
  score_shape: 'exact_match',
  correct: true,
  suite_accuracy: 0.8,
  language_breakdown: {
    en: { accuracy: 0.6, indicative: false, n: 10 },
    fr: { accuracy: 1.0, indicative: true, n: 5 },
    de: { accuracy: 1.0, indicative: true, n: 5 },
  },
}

const IDENTITY_D20 = {
  run_id: 'd20afbda710c40378e6ad5ca8d9b6558',
  captured_at: '2026-08-27T05:09:41.477962+00:00',
  schema_version: '7',
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  release_version: '0.1.0+untagged',
  commit_sha: '9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7', // pragma: allowlist secret
  tree_dirty: true,
}

// billing-01, run d20afbda...: reproduced against 5e13166 (real second run).
const REPRODUCED_ENTRY: QualityEntry = {
  ...IDENTITY_D20,
  ...SHARED_FIELDS,
  item_id: 'billing-01',
  language: 'en',
  contamination_risk: false,
  indicative: false,
  indicative_reasons: [],
  cost_total: 0.0002967923135196749,
  verdict: {
    verdict: 'reproduced',
    reference_run_id: '5e13166da0654390a7d63f346ea5d4f1',
    differing_fields: [],
    reason: null,
  },
  score_shape: 'exact_match',
  correct: true,
  suite_accuracy: 0.8,
  language_breakdown: {
    en: { accuracy: 0.6, indicative: false, n: 10 },
    fr: { accuracy: 1.0, indicative: true, n: 5 },
    de: { accuracy: 1.0, indicative: true, n: 5 },
  },
}

// billing-01, run d20afbda...: not_reproduced against 5e13166 (real second
// run), differing_fields non-empty.
const NOT_REPRODUCED_ENTRY: QualityEntry = {
  ...IDENTITY_D20,
  ...SHARED_FIELDS,
  item_id: 'billing-01',
  language: 'en',
  contamination_risk: false,
  indicative: false,
  indicative_reasons: [],
  cost_total: 0.0002967923135196749,
  verdict: {
    verdict: 'not_reproduced',
    reference_run_id: '5e13166da0654390a7d63f346ea5d4f1',
    differing_fields: ['other-de-01'],
    reason: null,
  },
  score_shape: 'exact_match',
  correct: true,
  suite_accuracy: 0.8,
  language_breakdown: {
    en: { accuracy: 0.6, indicative: false, n: 10 },
    fr: { accuracy: 1.0, indicative: true, n: 5 },
    de: { accuracy: 1.0, indicative: true, n: 5 },
  },
}

// Hand-edited copy of NOT_COMPARABLE_ENTRY: the reference bundle carries no
// judged, contested, or graded row, and no top-level (suite-level)
// contamination_risk/indicative true row exists at this floor. Turned on
// here, documented, per plan.md's "editing a copy of a real row rather than
// fabricating one from nothing."
const HAND_EDITED_EDGE_CASE_ENTRY: QualityEntry = {
  ...IDENTITY_D20,
  ...SHARED_FIELDS,
  item_id: 'billing-02',
  language: 'fr',
  // Hand-edited from the real `false`/`[]`.
  contamination_risk: true,
  indicative: true,
  indicative_reasons: ['low_n'],
  verdict: {
    verdict: 'not_comparable',
    reference_run_id: null,
    differing_fields: [],
    reason: 'hand-edited edge case, not a real reference row',
  },
  // Hand-edited from the real all-absent judge block: a two-judge contested
  // call with an agreement figure, no single-judge fallback.
  judge: {
    ...PREDATES_SCHEMA_JUDGE,
    single_judge: false,
    single_judge_reason: NULL_ABSENT,
    agreement: 0.42,
    agreement_statistic: 'cohens_kappa',
    contested: true,
    contested_reason: 'agreement below threshold',
    contested_threshold: 0.6,
    judged_headline_score: 0.55,
    judged_headline_excluded_n: 3,
  },
  // Hand-edited to the graded shape: the real bundle carries exact_match
  // rows only.
  score_shape: 'graded',
  metric_id: 'chrf',
  metric_version: '1',
  metric_params: { char_order: 6 },
  item_score: 0.62,
  suite_score: 0.58,
  reference_output: 'une reference',
  score_breakdown: {
    en: { score: 0.62, n: 1, indicative: true },
    fr: { score: 0.71, n: 5, indicative: true },
    de: { score: 0.0, n: 0, indicative: true },
  },
}

export const qualityViewFixture: QualityView = {
  store: 'quality',
  run_id: 'd20afbda710c40378e6ad5ca8d9b6558',
  schema_floor: '7',
  score_shapes: ['exact_match', 'graded'],
  entries: [
    NOT_COMPARABLE_ENTRY,
    REPRODUCED_ENTRY,
    NOT_REPRODUCED_ENTRY,
    HAND_EDITED_EDGE_CASE_ENTRY,
  ],
  unreadable: [],
}
