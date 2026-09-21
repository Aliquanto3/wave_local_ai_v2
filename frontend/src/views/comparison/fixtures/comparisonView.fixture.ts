// Real values from `aidd_docs/results/quality.jsonl`'s
// `classification-support-routing` batches, read through
// `read_model.comparison_view` (floor "7") and hand-transcribed here -- not
// invented values, matching `views/quality/fixtures/qualityView.fixture.ts`'s
// own discipline.
//
// One hand-edit, documented where it happens: the live store's four columns
// all sit at `suite_version` "3" today (the MoE flagship was re-run since
// this story was framed). The MoE column's `suite_version` is turned back to
// "2" here, and `account-02` dropped from its backing rows, to exercise the
// split-version/not-compared edge cases the acceptance names -- the same
// "edit a copy of a real row rather than fabricate one from nothing" the
// quality fixture already does.

import type { Absent, RosterEntry } from '../../../api/types'
import type {
  ComparedCellFields,
  ComparisonCell,
  ComparisonColumn,
  ComparisonJudgeBlock,
  ComparisonSuiteDefinition,
  ComparisonView,
} from '../types'

function absent(reason: string, detail: Record<string, unknown> = {}): Absent {
  return { absent: true, reason, detail }
}

const PREDATES_SCHEMA = () => absent('predates_schema', { row_schema_version: '11' })
const NULL_ABSENT = absent('null_in_row')

const PREDATES_SCHEMA_JUDGE: ComparisonJudgeBlock = {
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

const DENSE_0_6B_ROSTER_ENTRY = {
  entry_id: 'qwen3-0.6b-q8',
  display_id: 'Qwen3-0.6B',
  repo: 'Qwen/Qwen3-0.6B-GGUF',
  revision: '23749fefcc72300e3a2ad315e1317431b06b590a', // pragma: allowlist secret
  file: 'Qwen3-0.6B/Qwen3-0.6B-Q8_0.gguf',
  quant: 'Q8_0',
  sha256: '9465e63a22add5354d9bb4b99e90117043c7124007664907259bd16d043bb031', // pragma: allowlist secret
  family: 'qwen',
  architecture: { kind: 'dense', expert_count: 0, active_params_b: 0.6 },
  roster_version: 2,
}

const DENSE_1_7B_ROSTER_ENTRY = {
  entry_id: 'qwen3-1.7b-q8',
  display_id: 'Qwen3-1.7B',
  repo: 'Qwen/Qwen3-1.7B-GGUF',
  revision: '90862c4b9d2787eaed51d12237eafdfe7c5f6077', // pragma: allowlist secret
  file: 'Qwen3-1.7B/Qwen3-1.7B-Q8_0.gguf',
  quant: 'Q8_0',
  sha256: '061b54daade076b5d3362dac252678d17da8c68f07560be70818cace6590cb1a', // pragma: allowlist secret
  family: 'qwen',
  architecture: { kind: 'dense', expert_count: 0, active_params_b: 1.7 },
  roster_version: 2,
}

const DENSE_4B_ROSTER_ENTRY = {
  entry_id: 'qwen3-4b-q4km',
  display_id: 'Qwen3-4B',
  repo: 'Qwen/Qwen3-4B-GGUF',
  revision: 'bc640142c66e1fdd12af0bd68f40445458f3869b', // pragma: allowlist secret
  file: 'Qwen3-4B/Qwen3-4B-Q4_K_M.gguf',
  quant: 'Q4_K_M',
  sha256: '7485fe6f11af29433bc51cab58009521f205840f5b4ae3a32fa7f92e8534fdf5', // pragma: allowlist secret
  family: 'qwen',
  architecture: { kind: 'dense', expert_count: 0, active_params_b: 4.0 },
  roster_version: 2,
}

const MOE_ROSTER_ENTRY = {
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

const SUITE_DEFINITION_V3 = {
  snapshot_filename: 'classification-support-routing@3.json',
  context_length: 32768,
  max_output_tokens: 32,
  prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
  stop_sequences: [],
  suite_id: 'classification-support-routing',
  suite_version: '3',
  thinking_policy: 'disabled',
}

// Hand-edited: the real snapshot is "@3", turned back to "@2" per this
// fixture's own documented edit above.
const SUITE_DEFINITION_V2 = {
  ...SUITE_DEFINITION_V3,
  snapshot_filename: 'classification-support-routing@2.json',
  suite_version: '2',
}

const FICHE = {
  cpu: 'AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD',
  gpu_name: 'NVIDIA GeForce RTX 3060 Laptop GPU',
  os: 'Windows 11',
}

const COLUMNS: ComparisonColumn[] = [
  {
    roster_entry_id: 'qwen3-0.6b-q8',
    run_id: 'e716ce86ddc7448b8583e0d24387649a',
    suite_version: '3',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: DENSE_0_6B_ROSTER_ENTRY,
    dimensions: { architecture: DENSE_0_6B_ROSTER_ENTRY.architecture },
  },
  {
    roster_entry_id: 'qwen3-1.7b-q8',
    run_id: '91ee67b104db49f89ef73c75dd0f9bd9',
    suite_version: '3',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: DENSE_1_7B_ROSTER_ENTRY,
    dimensions: { architecture: DENSE_1_7B_ROSTER_ENTRY.architecture },
  },
  {
    roster_entry_id: 'qwen3-4b-q4km',
    run_id: 'ebce4da610a04167827ef911d4a60e82',
    suite_version: '3',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: DENSE_4B_ROSTER_ENTRY,
    dimensions: { architecture: DENSE_4B_ROSTER_ENTRY.architecture },
  },
  {
    // Hand-edited suite_version: "2", not the live store's current "3" --
    // see this file's own header.
    roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
    run_id: 'd4d2e0d5d9a94aa98d7c2eb1569fd60c',
    suite_version: '2',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: MOE_ROSTER_ENTRY,
    dimensions: { architecture: MOE_ROSTER_ENTRY.architecture },
  },
]

function comparedCell(
  overrides: Partial<ComparedCellFields> & {
    run_id: string
    roster_entry: RosterEntry
    suite_definition: ComparisonSuiteDefinition
    item_id: string
    correct: boolean
    suite_accuracy: number
    language_breakdown: Record<
      string,
      { accuracy: number; indicative: boolean; n: number }
    >
  },
): ComparisonCell & { status: 'compared' } {
  return {
    status: 'compared',
    captured_at: '2026-09-06T15:03:45.512209+00:00',
    commit_sha: 'f34e5b844099b16a6c856173a7a6a08d1d902693', // pragma: allowlist secret
    release_version: '0.1.0+untagged',
    schema_version: '11',
    tree_dirty: true,
    contamination_risk: false,
    context_length: 32768,
    cost_currency: 'EUR',
    cost_per_million_tokens: 0.178,
    cost_total: 0.000235,
    endpoint: '/v1/chat/completions',
    expected_label: 'account',
    predicted_label: 'account',
    failure_counts: {
      empty: 0,
      unparseable: 0,
      truncated_max_tokens: 0,
      truncated_context: 0,
    },
    failure_reason: NULL_ABSENT,
    fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a', // pragma: allowlist secret
    indicative: false,
    indicative_reasons: [],
    kwh_price_currency: 'EUR',
    kwh_price_eur: 0.194,
    kwh_price_recorded_at: '2026-02-01',
    language: 'en',
    list_price_currency: NULL_ABSENT,
    list_price_input_per_million: NULL_ABSENT,
    list_price_output_per_million: NULL_ABSENT,
    list_price_per_million_tokens: NULL_ABSENT,
    list_price_retrieved_at: NULL_ABSENT,
    max_output_tokens: 32,
    model_id: 'Qwen3.6-35B-A3B',
    normalization_unit: 'cost_per_million_total_tokens',
    prompt_capture: 'reconstructed',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    prompt_template_hash:
      '55d4931433fe502b794226ee7f4d206a6bdd436ac9f80eb7d8ebb4c639f9ea0c', // pragma: allowlist secret
    prompt_template_id: 'llamacpp-model-chat-template',
    provenance: 'hand_written',
    provider: 'local',
    resumed: false,
    retries: 0,
    roster_version: 2,
    sampling: {
      seed: 20260821,
      temperature: 0,
      top_k: 0,
      top_p: 1.0,
      presence_penalty: 0,
    },
    stop_sequences: [],
    suite_id: 'classification-support-routing',
    task_suite: 'classification',
    thinking_policy: 'disabled',
    tokens_in_total: 1279,
    tokens_out_total: 40,
    verdict: {
      verdict: 'not_comparable',
      reference_run_id: null,
      differing_fields: [],
      reason:
        "no reference row shares this batch's task_suite/model_id/suite_version/seed",
    },
    fiche: FICHE,
    judge: PREDATES_SCHEMA_JUDGE,
    score_shape: 'exact_match',
    ...overrides,
    roster_entry_id: overrides.roster_entry.entry_id,
    run_id: overrides.run_id,
    suite_version: overrides.suite_definition.suite_version,
  }
}

// account-01: present in every column. Real per-column suite_accuracy
// (0.45 / 0.60 / 0.70 / 1.00) matches `aidd_docs/results/README.md`'s
// "The same eight batches, chat-templated" table exactly.
const ACCOUNT_01_CELLS: ComparisonCell[] = [
  comparedCell({
    run_id: 'e716ce86ddc7448b8583e0d24387649a',
    roster_entry: DENSE_0_6B_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V3,
    item_id: 'account-01',
    predicted_label: 'technical',
    correct: false,
    suite_accuracy: 0.45,
    language_breakdown: {
      en: { accuracy: 0.5, indicative: false, n: 10 },
      fr: { accuracy: 0.4, indicative: true, n: 5 },
      de: { accuracy: 0.4, indicative: true, n: 5 },
    },
  }),
  comparedCell({
    run_id: '91ee67b104db49f89ef73c75dd0f9bd9',
    roster_entry: DENSE_1_7B_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V3,
    item_id: 'account-01',
    predicted_label: 'other',
    correct: false,
    suite_accuracy: 0.6,
    language_breakdown: {
      en: { accuracy: 0.7, indicative: false, n: 10 },
      fr: { accuracy: 0.4, indicative: true, n: 5 },
      de: { accuracy: 0.6, indicative: true, n: 5 },
    },
  }),
  comparedCell({
    run_id: 'ebce4da610a04167827ef911d4a60e82',
    roster_entry: DENSE_4B_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V3,
    item_id: 'account-01',
    predicted_label: 'other',
    correct: false,
    suite_accuracy: 0.7,
    language_breakdown: {
      en: { accuracy: 0.8, indicative: false, n: 10 },
      fr: { accuracy: 0.6, indicative: true, n: 5 },
      de: { accuracy: 0.6, indicative: true, n: 5 },
    },
  }),
  comparedCell({
    run_id: 'd4d2e0d5d9a94aa98d7c2eb1569fd60c',
    roster_entry: MOE_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V2,
    item_id: 'account-01',
    predicted_label: 'account',
    correct: true,
    suite_accuracy: 1.0,
    language_breakdown: {
      en: { accuracy: 1.0, indicative: false, n: 10 },
      fr: { accuracy: 1.0, indicative: true, n: 5 },
      de: { accuracy: 1.0, indicative: true, n: 5 },
    },
  }),
]

// account-02: present only in the three dense columns, all at the newer
// suite_version "3" -- the MoE column's hand-edited "2" snapshot does not
// carry this item, so its cell is `not_compared`.
const ACCOUNT_02_CELLS: ComparisonCell[] = [
  comparedCell({
    run_id: 'e716ce86ddc7448b8583e0d24387649a',
    roster_entry: DENSE_0_6B_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V3,
    item_id: 'account-02',
    predicted_label: 'account',
    correct: true,
    suite_accuracy: 0.45,
    language_breakdown: {
      en: { accuracy: 0.5, indicative: false, n: 10 },
      fr: { accuracy: 0.4, indicative: true, n: 5 },
      de: { accuracy: 0.4, indicative: true, n: 5 },
    },
  }),
  comparedCell({
    run_id: '91ee67b104db49f89ef73c75dd0f9bd9',
    roster_entry: DENSE_1_7B_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V3,
    item_id: 'account-02',
    predicted_label: 'account',
    correct: true,
    suite_accuracy: 0.6,
    language_breakdown: {
      en: { accuracy: 0.7, indicative: false, n: 10 },
      fr: { accuracy: 0.4, indicative: true, n: 5 },
      de: { accuracy: 0.6, indicative: true, n: 5 },
    },
  }),
  comparedCell({
    run_id: 'ebce4da610a04167827ef911d4a60e82',
    roster_entry: DENSE_4B_ROSTER_ENTRY,
    suite_definition: SUITE_DEFINITION_V3,
    item_id: 'account-02',
    predicted_label: 'account',
    correct: true,
    suite_accuracy: 0.7,
    language_breakdown: {
      en: { accuracy: 0.8, indicative: false, n: 10 },
      fr: { accuracy: 0.6, indicative: true, n: 5 },
      de: { accuracy: 0.6, indicative: true, n: 5 },
    },
  }),
  { status: 'not_compared', item_id: 'account-02' },
]

export const comparisonViewFixture: ComparisonView = {
  store: 'quality',
  schema_floor: '7',
  suites: [
    {
      suite_id: 'classification-support-routing',
      columns: COLUMNS,
      items: [
        { item_id: 'account-01', cells: ACCOUNT_01_CELLS },
        { item_id: 'account-02', cells: ACCOUNT_02_CELLS },
      ],
    },
  ],
  unreadable: [],
}
