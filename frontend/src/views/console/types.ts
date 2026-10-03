// Response shapes of the demo console routes (`service.py`'s `/api/console`).

export type ConsoleKind = 'runtime' | 'quality'

/** Who holds the console: the choices of the one run in flight. */
export interface RunHolder {
  session: 'run'
  kind: ConsoleKind
  suite: string | null
  roster_entry_id: string
  profile_id: string
  started_at: string
  run_id: string | null
}

/** Who holds the console: the playground, with one roster model loaded. */
export interface PlaygroundHolder {
  session: 'playground'
  roster_entry_id: string
  profile_id: string
  started_at: string
}

/** Who holds the console: the playground, with its cloud subject selected. */
export interface CloudPlaygroundHolder {
  session: 'playground'
  provider: string
  model: string
  started_at: string
}

/** The one occupancy owner: a console run or the playground. */
export type Holder = RunHolder | PlaygroundHolder | CloudPlaygroundHolder

export interface ConsoleOptions {
  kinds: ConsoleKind[]
  suites: string[]
  roster_entries: string[]
  /** The machine this service runs on, or null with `machine_absence` naming why. */
  machine_id: string | null
  machine_absence: string | null
  /** Per roster entry, the declared run profiles of this machine. */
  profiles: Record<string, RunProfileOption[]>
  holder: Holder | null
}

/** One declared run profile: `<entry>@<machine>/<mode>`, and its two parts. */
export interface RunProfileOption {
  profile_id: string
  machine_id: string
  compute_mode: string
}

export interface ConsoleLaunch {
  launch_id: string
  profile_id: string
}

/** The 409 body when a run or the playground already holds the console. */
export interface ConsoleOccupied {
  detail: { message: string; holder: Holder }
}

/** The stream's last event: the run's row as read back, or its failure. */
export interface ConsoleFinal {
  ok: boolean
  kind: ConsoleKind
  profile_id: string
  run_id: string | null
  exit_code: number | null
  error_line: string | null
  view: unknown
  missing: string | null
}
