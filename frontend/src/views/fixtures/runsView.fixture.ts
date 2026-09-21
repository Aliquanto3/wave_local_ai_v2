import type { RunsView } from '../../api/types'

const ROSTER_ENTRY = {
  entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
  display_id: 'Qwen3.6-35B-A3B',
  repo: 'unsloth/Qwen3.6-35B-A3B-GGUF',
  revision: 'main',
  file: 'model.gguf',
  quant: 'UD-IQ4_XS',
  sha256: 'c'.repeat(64),
  family: 'qwen',
  architecture: { kind: 'moe', expert_count: 48, active_params_b: 3.0 },
  roster_version: 3,
}

/** A fixture matching `/api/runs`'s real shape (see `read_model.runs_view`). */
export const RUNS_VIEW_FIXTURE: RunsView = {
  runtime_runs: {
    schema_floor: '7',
    runs: [
      {
        run_id: 'runtime-run-1',
        captured_at: '2026-09-01T00:00:00+00:00',
        schema_version: '11',
        roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
        release_version: '1.2.3',
        commit_sha: 'deadbeef',
        tree_dirty: true,
        row_count: 5,
        roster_entry: ROSTER_ENTRY,
        models: [ROSTER_ENTRY],
      },
    ],
    unreadable: [],
  },
  quality_runs: {
    schema_floor: '7',
    runs: [
      {
        run_id: 'quality-run-1',
        captured_at: '2026-09-02T00:00:00+00:00',
        schema_version: '4',
        roster_entry_id: 'qwen3.6-35b-a3b-ud-iq4xs',
        release_version: '1.2.3',
        // Predates the field's relocation into RUNS_VIEW_FIELDS: the row's
        // own schema_version is below the version that started carrying it.
        commit_sha: {
          absent: true,
          reason: 'predates_schema',
          detail: { row_schema_version: '4' },
        },
        tree_dirty: false,
        row_count: 12,
        roster_entry: ROSTER_ENTRY,
        models: [ROSTER_ENTRY],
        suites: ['classification-support-routing', 'translation-fr-en'],
      },
    ],
    unreadable: [],
  },
}

/** A fixture with both collections empty, for the "no runs recorded" state. */
export const EMPTY_RUNS_VIEW_FIXTURE: RunsView = {
  runtime_runs: { schema_floor: '7', runs: [], unreadable: [] },
  quality_runs: { schema_floor: '7', runs: [], unreadable: [] },
}
