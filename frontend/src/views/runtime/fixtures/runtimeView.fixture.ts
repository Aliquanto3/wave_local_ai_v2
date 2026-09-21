// Real rows from `aidd_docs/results/runtime-reference.jsonl`, read through
// `read_model.runtime_view` over the committed reference bundle (floor "7",
// run `f5f78c795eaa4175ac506440e597ee3e`) and hand-transcribed here -- not
// invented values. The bundle's own `unreliable` is `false` on every row, so
// `UNRELIABLE_ENTRY` below is a hand-edited copy of the real row with that
// flag (and the spread it names) turned on, documented per plan.md's
// Decisions and phase-3's task 2.

import type { Absent } from '../../../api/types'
import type { RuntimeEntry, RuntimeView } from '../types'

function absent(reason: string, detail: Record<string, unknown> = {}): Absent {
  return { absent: true, reason, detail }
}

const NULL_ABSENT = absent('null_in_row')

const IDENTITY = {
  run_id: 'f5f78c795eaa4175ac506440e597ee3e',
  captured_at: '2026-08-27T04:57:27.124220+00:00',
  schema_version: '7',
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  release_version: '0.1.0+untagged',
  commit_sha: '9bc9da88cf6c450e8f9d086d853b5ee73f55cbd7',  // pragma: allowlist secret
  tree_dirty: true,
}

const ROSTER_ENTRY = {
  entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  display_id: 'Qwen3.6-35B-A3B',
  repo: 'unsloth/Qwen3.6-35B-A3B-GGUF',
  revision: 'main',
  file: 'Qwen3.6-35B-A3B/Qwen3.6-35B-A3B-UD-IQ4_XS.gguf',
  quant: 'UD-IQ4_XS',
  sha256: '649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3',  // pragma: allowlist secret
  family: null,
  architecture: { kind: 'moe', expert_count: 40, active_params_b: 3.1 },
  roster_version: 2,
}

const FICHE = {
  cpu: 'AMD64 Family 25 Model 80 Stepping 0, AuthenticAMD',
  cuda_ceiling: '12.8',
  flags: [
    '-m', 'D:\\ia\\models\\Qwen3.6-35B-A3B\\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf',
    '-ngl', '99', '--n-cpu-moe', '37', '-c', '32768', '-fa', 'on', '-t', '8',
    '--jinja', '-np', '1', '--load-mode', 'none', '--temp', '1.0',
    '--top-p', '0.95', '--top-k', '20', '--min-p', '0', '--presence-penalty', '1.5',
    '--host', '127.0.0.1', '--port', '8080',
  ],
  gpu_driver_version: '572.70',
  gpu_name: 'NVIDIA GeForce RTX 3060 Laptop GPU',
  llama_cpp_build: 'b10537',
  model_sha256: '649d7508507b84638732c4f52c24c8b15843c6dca2f3ff793ae07c14a67ebbb3',  // pragma: allowlist secret
  os: 'Windows 11',
  quant: 'UD-IQ4_XS',
  ram_gb: 31.4,
  roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
}

const SHARED_FIELDS = {
  roster_version: 1,
  endpoint: '/completion',
  prompt_template_id: 'none',
  prompt_template_hash: NULL_ABSENT,
  prompt_capture: 'captured',
  fiche_hash: 'b9d1af56db2b6a26bfb265842bfd757dc78ed2d95e4ad3fce0088b8396d9003a',  // pragma: allowlist secret
  verdict: {
    verdict: 'not_comparable',
    reference_run_id: null,
    differing_fields: [],
    reason: 'no reference rows configured or matched',
  },
  max_tokens: 128,
  wall_clock_s: 52.5,
  cost_currency: 'EUR',
  cost_total: 0.0005052748351877469,
  cost_per_million_tokens: 0.06245671633964733,
  normalization_unit: 'cost_per_million_total_tokens',
  kwh_price_eur: 0.194,
  kwh_price_currency: 'EUR',
  kwh_price_recorded_at: '2026-02-01',
  list_price_input_per_million: NULL_ABSENT,
  list_price_output_per_million: NULL_ABSENT,
  list_price_per_million_tokens: NULL_ABSENT,
  list_price_currency: NULL_ABSENT,
  list_price_retrieved_at: NULL_ABSENT,
  sampling: { seed: 20260822, temperature: 1.0, top_p: 0.95, top_k: 20, min_p: 0, presence_penalty: 1.5 },
  seed_pinned: true,
  warmup_count: 1,
  warmup_repetitions: [
    {
      index: 0,
      ttft_ms: 5598.029,
      ttft_source: 'server_reported',
      prompt_tok_per_s: 266.16510918396455,
      gen_tok_per_s: 25.457993308757352,
      vram_used_mib: 4548.67578125,
      gpu_draw_w: 39.206,
      process_rss_bytes: 15225393152,
      wall_clock_s: 10.609000000000378,
      stop_type: 'limit',
      tokens_predicted: 128,
      tokens_evaluated: 1490,
    },
  ],
  restart_between_repetitions: false,
  cooldown_s: 10.0,
  repetitions_n: 5,
  slot_reset_method: 'cache_prompt_false',
  aggregation: {
    ttft_ms: 'median',
    prompt_tok_per_s: 'median',
    gen_tok_per_s: 'median',
    ttft_ms_spread: 'sample_sd_over_median',
    prompt_tok_per_s_spread: 'sample_sd_over_median',
    gen_tok_per_s_spread: 'sample_sd_over_median',
    vram_used_mib: 'peak_over_counted_repetitions',
    process_rss_bytes: 'peak_over_counted_repetitions',
    gpu_draw_w: 'max_post_completion_sample_over_counted_repetitions',
    wall_clock_s: 'total_over_counted_repetitions',
    energy_kwh: 'total_over_counted_repetitions_including_cooldowns',
    cpu_energy_kwh: 'total_over_counted_repetitions_including_cooldowns',
    gpu_energy_kwh: 'total_over_counted_repetitions_including_cooldowns',
    ram_energy_kwh: 'total_over_counted_repetitions_including_cooldowns',
  },
  thermal_posture: 'fixed_cooldown',
  tokens_in_total: 7450,
  tokens_out_total: 640,
  ttft_ms: 5465.025,
  ttft_ms_mean: 5473.9876,
  ttft_ms_sd: 60.18608226409156,
  ttft_ms_spread: 0.011012956439191323,
  ttft_source: 'server_reported',
  prompt_tok_per_s: 272.64285158805313,
  prompt_tok_per_s_mean: 272.2226836496228,
  prompt_tok_per_s_sd: 2.9823805854326326,
  prompt_tok_per_s_spread: 0.010938781516042934,
  gen_tok_per_s: 25.408247517144066,
  gen_tok_per_s_mean: 25.32852579747163,
  gen_tok_per_s_sd: 0.20793190115776303,
  gen_tok_per_s_spread: 0.00818363804971052,
  gpu_draw_w: 40.259,
  vram_used_mib: 4548.67578125,
  process_rss_bytes: 15225516032,
  roster_entry: ROSTER_ENTRY,
  fiche: FICHE,
}

// Real, reliable row.
const RELIABLE_ENTRY: RuntimeEntry = {
  ...IDENTITY,
  ...SHARED_FIELDS,
  unreliable: false,
}

// Hand-edited copy: the real row's `unreliable` is `false` and its
// `gen_tok_per_s_spread` is 0.008 -- turned on here with a spread the
// unreliable threshold would actually flag, documented per plan.md's
// Decisions.
const UNRELIABLE_ENTRY: RuntimeEntry = {
  ...IDENTITY,
  ...SHARED_FIELDS,
  unreliable: true,
  gen_tok_per_s_spread: 0.18,
}

// Hand-edited: `fiche_hash` points at a hash the fiche registry does not
// carry, so `entry.fiche` resolves to a pointer_unresolved Absent, exercising
// the unconditional-fiche-block acceptance criterion's absent branch.
const UNRESOLVED_FICHE_ENTRY: RuntimeEntry = {
  ...IDENTITY,
  ...SHARED_FIELDS,
  unreliable: false,
  fiche_hash: 'c'.repeat(64),
  fiche: absent('pointer_unresolved', { pointer: 'fiche_hash', value: 'c'.repeat(64) }),
}

export const runtimeViewFixture: RuntimeView = {
  store: 'runtime',
  run_id: 'f5f78c795eaa4175ac506440e597ee3e',
  schema_floor: '7',
  entries: [RELIABLE_ENTRY, UNRELIABLE_ENTRY, UNRESOLVED_FICHE_ENTRY],
  unreadable: [],
}
