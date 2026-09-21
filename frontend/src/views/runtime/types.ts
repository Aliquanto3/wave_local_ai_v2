// Mirrors `read_model.runtime_view`'s JSON shape exactly, matching
// `read_model.RUNTIME_VIEW_FIELDS`. Deliberately does not import
// `views/quality/types.ts` or `views/energy/types.ts` -- see
// `views/boundary.test.ts`.

import type { Maybe, RosterEntry } from '../../api/types'

export interface VerdictBlock {
  verdict: Maybe<string>
  reference_run_id: Maybe<string> | null
  differing_fields: Maybe<string[]>
  reason?: Maybe<string> | null
}

export type Fiche = Record<string, unknown>

export interface RuntimeEntry {
  // RUNS_VIEW_FIELDS: the identity block every view carries.
  run_id: Maybe<string>
  captured_at: Maybe<string>
  schema_version: Maybe<string>
  roster_entry_id: Maybe<string>
  release_version: Maybe<string>
  commit_sha: Maybe<string>
  tree_dirty: Maybe<boolean>

  // RUNTIME_VIEW_FIELDS.
  roster_version: Maybe<number>
  endpoint: Maybe<string>
  prompt_template_id: Maybe<string>
  prompt_template_hash: Maybe<string>
  prompt_capture: Maybe<string>
  fiche_hash: Maybe<string>
  verdict: Maybe<VerdictBlock>
  max_tokens: Maybe<number>
  wall_clock_s: Maybe<number>
  ttft_ms: Maybe<number>
  prompt_tok_per_s: Maybe<number>
  gen_tok_per_s: Maybe<number>
  ttft_source: Maybe<string>
  vram_used_mib: Maybe<number>
  gpu_draw_w: Maybe<number>
  process_rss_bytes: Maybe<number>
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
  sampling: Maybe<Record<string, unknown>>
  seed_pinned: Maybe<boolean>
  warmup_count: Maybe<number>
  warmup_repetitions: Maybe<unknown[]>
  restart_between_repetitions: Maybe<boolean>
  cooldown_s: Maybe<number>
  repetitions_n: Maybe<number>
  slot_reset_method: Maybe<string>
  aggregation: Maybe<Record<string, string>>
  ttft_ms_mean: Maybe<number>
  ttft_ms_sd: Maybe<number>
  ttft_ms_spread: Maybe<number>
  prompt_tok_per_s_mean: Maybe<number>
  prompt_tok_per_s_sd: Maybe<number>
  prompt_tok_per_s_spread: Maybe<number>
  gen_tok_per_s_mean: Maybe<number>
  gen_tok_per_s_sd: Maybe<number>
  gen_tok_per_s_spread: Maybe<number>
  unreliable: Maybe<boolean>
  thermal_posture: Maybe<string>

  roster_entry: Maybe<RosterEntry>
  fiche: Maybe<Fiche>
}

export interface RuntimeView {
  store: 'runtime'
  run_id: string
  schema_floor: string
  entries: RuntimeEntry[]
  unreadable: { schema_version: string; count: number; reason: string }[]
}
