// The TypeScript shapes for `/api/runs`'s response, mirroring
// `read_model.Absent.as_json()` and `read_model.runs_view` exactly. Nothing
// here is inferred beyond what the read model actually sends: a field the
// read model can report absent is typed `Maybe<T>`, never defaulted away.

export interface Absent {
  absent: true
  reason: string
  detail: Record<string, unknown>
}

export type Maybe<T> = T | Absent

export function isAbsent(value: unknown): value is Absent {
  return (
    typeof value === 'object' &&
    value !== null &&
    (value as { absent?: unknown }).absent === true
  )
}

export interface RosterEntryArchitecture {
  kind: string
  expert_count: number | null
  active_params_b: number | null
}

export interface RosterEntry {
  entry_id: string
  display_id: string
  repo: string
  revision: string
  file: string
  quant: string
  sha256: string
  family: string | null
  architecture: RosterEntryArchitecture
  roster_version: number
}

export interface UnreadableRows {
  schema_version: string
  count: number
  reason: string
}

export interface RunEntry {
  run_id: Maybe<string>
  captured_at: Maybe<string>
  schema_version: Maybe<string>
  roster_entry_id: Maybe<string>
  release_version: Maybe<string>
  commit_sha: Maybe<string>
  tree_dirty: Maybe<boolean>
  row_count: number
  roster_entry: Maybe<RosterEntry>
  models: Maybe<RosterEntry>[]
  // Quality-only: a runtime entry carries no `suites` key at all, matching
  // `read_model.runs_view`'s "a key that is always absent is worse than a
  // key that doesn't exist."
  suites?: Maybe<string>[]
}

export interface RunsCollection {
  schema_floor: string
  runs: RunEntry[]
  unreadable: UnreadableRows[]
}

export interface RunsView {
  runtime_runs: RunsCollection
  quality_runs: RunsCollection
}
