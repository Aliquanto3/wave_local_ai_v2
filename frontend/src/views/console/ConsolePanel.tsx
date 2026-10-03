import { useEffect, useState, type FormEvent } from 'react'
import {
  apiFetch,
  ApiError,
  postConsoleRun,
  streamConsoleRun,
  UnauthorizedError,
} from '../../api/client'
import { useKeyGate } from '../../components/KeyGate'
import { QualityView } from '../quality/QualityView'
import { RuntimeView } from '../runtime/RuntimeView'
import { LiveOutput } from './LiveOutput'
import type {
  ConsoleFinal,
  ConsoleKind,
  ConsoleLaunch,
  ConsoleOccupied,
  ConsoleOptions,
  RunHolder,
} from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'off' }
  | { status: 'unreachable'; message: string }
  | { status: 'loaded'; options: ConsoleOptions }

type RunState =
  | { status: 'idle' }
  | { status: 'running'; lines: string[] }
  | { status: 'finished'; lines: string[]; final: ConsoleFinal }
  | { status: 'failed-to-start'; message: string }

/** How often a held console re-reads its holder, in milliseconds. */
export const HOLDER_POLL_MS = 3000

function describeHolder(holder: RunHolder): string {
  const suite = holder.suite === null ? '' : ` ${holder.suite}`
  const runId = holder.run_id ?? 'run_id not yet announced'
  return `${holder.kind}${suite} under ${holder.profile_id}, started ${holder.started_at} (${runId})`
}

function Outcome({ final }: { final: ConsoleFinal }) {
  if (final.ok && final.run_id !== null) {
    return (
      <section className="console-outcome" aria-label="Outcome">
        {final.kind === 'quality' ? (
          <QualityView runId={final.run_id} />
        ) : (
          <RuntimeView runId={final.run_id} />
        )}
      </section>
    )
  }
  return (
    <section className="console-outcome" aria-label="Outcome">
      <p>Run failed: exit status {String(final.exit_code)}</p>
      {final.error_line !== null && <p className="console-error">{final.error_line}</p>}
      {final.missing !== null && <p className="console-error">{final.missing}</p>}
    </section>
  )
}

/**
 * Start one runtime or quality run from the declared choices and watch it.
 *
 * Every control is a select bound to the options route's declared sets: no
 * free text reaches the service.
 */
export function ConsolePanel({
  holderPollMs = HOLDER_POLL_MS,
}: { holderPollMs?: number } = {}) {
  const { reportUnauthorized } = useKeyGate()
  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
  const [holder, setHolder] = useState<RunHolder | null>(null)
  const [kind, setKind] = useState<ConsoleKind>('runtime')
  const [suite, setSuite] = useState('')
  const [rosterEntry, setRosterEntry] = useState('')
  const [profileId, setProfileId] = useState('')
  const [run, setRun] = useState<RunState>({ status: 'idle' })

  useEffect(() => {
    let cancelled = false
    apiFetch<ConsoleOptions>('/api/console/options')
      .then((options) => {
        if (cancelled) {
          return
        }
        setLoad({ status: 'loaded', options })
        setHolder(options.holder)
        setSuite(options.suites[0] ?? '')
        setRosterEntry(options.roster_entries[0] ?? '')
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        if (error instanceof UnauthorizedError) {
          reportUnauthorized()
          return
        }
        if (error instanceof ApiError && error.status === 403) {
          setLoad({ status: 'off' })
          return
        }
        setLoad({ status: 'unreachable', message: String(error) })
      })
    return () => {
      cancelled = true
    }
  }, [reportUnauthorized])

  // While another run holds the console, re-read who holds it until it is
  // free, so Start re-enables when that run ends rather than on a reload.
  const held = holder !== null
  useEffect(() => {
    if (!held) {
      return
    }
    const timer = setInterval(() => {
      apiFetch<ConsoleOptions>('/api/console/options')
        .then((options) => setHolder(options.holder))
        .catch(() => {
          // A failed poll leaves the holder shown; the next one retries.
        })
    }, holderPollMs)
    return () => clearInterval(timer)
  }, [held, holderPollMs])

  if (load.status === 'loading') {
    return <p>Loading the console…</p>
  }
  if (load.status === 'off') {
    return <p>Demo mode is off on this machine.</p>
  }
  if (load.status === 'unreachable') {
    return <p>The console could not be loaded: {load.message}</p>
  }
  const { options } = load
  // The declared profiles of the chosen entry on this machine; the first is
  // the default until another is picked.
  const entryProfiles = options.profiles[rosterEntry] ?? []
  const profile =
    entryProfiles.find((option) => option.profile_id === profileId) ?? entryProfiles[0]

  const handleStart = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (profile === undefined) {
      return
    }
    const body: Record<string, string> = {
      kind,
      roster_entry_id: rosterEntry,
      machine_id: profile.machine_id,
      compute_mode: profile.compute_mode,
    }
    if (kind === 'quality') {
      body.suite = suite
    }
    let launch: ConsoleLaunch
    try {
      launch = await postConsoleRun<ConsoleLaunch>(body)
    } catch (error: unknown) {
      if (error instanceof UnauthorizedError) {
        reportUnauthorized()
        return
      }
      if (error instanceof ApiError && error.status === 409) {
        setHolder((JSON.parse(error.body) as ConsoleOccupied).detail.holder)
        return
      }
      setRun({ status: 'failed-to-start', message: String(error) })
      return
    }

    let lines: string[] = []
    setRun({ status: 'running', lines })
    try {
      await streamConsoleRun<ConsoleFinal>(
        launch.launch_id,
        (line) => {
          lines = [...lines, line]
          setRun({ status: 'running', lines })
        },
        (final) => setRun({ status: 'finished', lines, final }),
      )
    } catch (error: unknown) {
      if (error instanceof UnauthorizedError) {
        reportUnauthorized()
        return
      }
      setRun({ status: 'failed-to-start', message: String(error) })
    }
  }

  const running = run.status === 'running'

  return (
    <section className="console-panel" aria-label="Console">
      <form onSubmit={(event) => void handleStart(event)}>
        <label>
          kind{' '}
          <select
            value={kind}
            onChange={(event) => setKind(event.target.value as ConsoleKind)}
          >
            {options.kinds.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>{' '}
        {kind === 'quality' && (
          <label>
            suite{' '}
            <select value={suite} onChange={(event) => setSuite(event.target.value)}>
              {options.suites.map((value) => (
                <option key={value} value={value}>
                  {value}
                </option>
              ))}
            </select>
          </label>
        )}{' '}
        <label>
          roster entry{' '}
          <select
            value={rosterEntry}
            onChange={(event) => setRosterEntry(event.target.value)}
          >
            {options.roster_entries.map((value) => (
              <option key={value} value={value}>
                {value}
              </option>
            ))}
          </select>
        </label>
        {profile === undefined ? (
          <p className="console-profile">
            no run profile on this machine:{' '}
            {options.machine_absence ?? 'none declared for this roster entry'}
          </p>
        ) : (
          <label>
            run profile{' '}
            <select
              value={profile.profile_id}
              onChange={(event) => setProfileId(event.target.value)}
            >
              {entryProfiles.map((option) => (
                <option key={option.profile_id} value={option.profile_id}>
                  {option.profile_id}
                </option>
              ))}
            </select>
          </label>
        )}{' '}
        <button
          type="submit"
          disabled={holder !== null || running || profile === undefined}
        >
          {holder === null ? 'Start run' : `Run in progress: ${describeHolder(holder)}`}
        </button>
      </form>
      {run.status === 'failed-to-start' && (
        <p className="console-error">The run could not be started: {run.message}</p>
      )}
      {(run.status === 'running' || run.status === 'finished') && (
        <LiveOutput lines={run.lines} />
      )}
      {run.status === 'finished' && <Outcome final={run.final} />}
    </section>
  )
}
