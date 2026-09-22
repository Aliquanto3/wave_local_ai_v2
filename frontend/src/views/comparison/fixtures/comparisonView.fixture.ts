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

import type {
  ComparedCellFields,
  ComparisonCell,
  ComparisonColumn,
  ComparisonView,
} from '../types'

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

const COLUMNS: ComparisonColumn[] = [
  {
    roster_entry_id: 'qwen3-0.6b-q8',
    provider: 'local',
    model_id: 'Qwen3-0.6B',
    fiche_hash: 'f804bee0d215c89c05289907fd2573fa722d290896775749f3c6d16329efca18', // pragma: allowlist secret
    run_id: 'e716ce86ddc7448b8583e0d24387649a',
    suite_version: '3',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: DENSE_0_6B_ROSTER_ENTRY,
    dimensions: { architecture: DENSE_0_6B_ROSTER_ENTRY.architecture },
  },
  {
    roster_entry_id: 'qwen3-1.7b-q8',
    provider: 'local',
    model_id: 'Qwen3-1.7B',
    fiche_hash: '067530efd6944e8bb09ddc91e61ce45364fcd6261bd22edeed9d33a82276a2f4', // pragma: allowlist secret
    run_id: '91ee67b104db49f89ef73c75dd0f9bd9',
    suite_version: '3',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: DENSE_1_7B_ROSTER_ENTRY,
    dimensions: { architecture: DENSE_1_7B_ROSTER_ENTRY.architecture },
  },
  {
    roster_entry_id: 'qwen3-4b-q4km',
    provider: 'local',
    model_id: 'Qwen3-4B',
    fiche_hash: 'dfd5a5eaa441cff2f7aee55b6d2206561eb9d19cb955bddc566d3e9d7fcb2ab2', // pragma: allowlist secret
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
    provider: 'local',
    model_id: 'Qwen3.6-35B-A3B',
    fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a', // pragma: allowlist secret
    run_id: 'd4d2e0d5d9a94aa98d7c2eb1569fd60c',
    suite_version: '2',
    prompt_set_hash: 'd41a2134274cf1c8036022d2b68396d04bfd14ff263d2f8699dbefd7a2e4596a', // pragma: allowlist secret
    thinking_policy: 'disabled',
    roster_entry: MOE_ROSTER_ENTRY,
    dimensions: { architecture: MOE_ROSTER_ENTRY.architecture },
  },
]

function comparedCell(
  fields: Pick<
    ComparedCellFields,
    'run_id' | 'item_id' | 'correct' | 'suite_accuracy' | 'language_breakdown'
  >,
): ComparisonCell & { status: 'compared' } {
  return {
    status: 'compared',
    score_shape: 'exact_match',
    contamination_risk: false,
    verdict: {
      verdict: 'not_comparable',
      reference_run_id: null,
      differing_fields: [],
      reason:
        "no reference row shares this batch's task_suite/model_id/suite_version/seed",
    },
    ...fields,
  }
}

// account-01: present in every column. Real per-column suite_accuracy
// (0.45 / 0.60 / 0.70 / 1.00) matches `aidd_docs/results/README.md`'s
// "The same eight batches, chat-templated" table exactly.
const ACCOUNT_01_CELLS: ComparisonCell[] = [
  comparedCell({
    run_id: 'e716ce86ddc7448b8583e0d24387649a',
    item_id: 'account-01',
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
    item_id: 'account-01',
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
    item_id: 'account-01',
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
    item_id: 'account-01',
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
    item_id: 'account-02',
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
    item_id: 'account-02',
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
    item_id: 'account-02',
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
