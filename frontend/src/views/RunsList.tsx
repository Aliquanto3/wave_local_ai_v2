import { useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../api/client'
import type {
  Maybe,
  RosterEntry,
  RunEntry,
  RunsCollection,
  RunsView,
} from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'
import { useKeyGate } from '../components/KeyGate'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: RunsView }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<string>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return value
}

/** A short joined list, each item routed through `Absent` when it is one. */
function renderJoinedList(items: Maybe<string>[] | Maybe<RosterEntry>[]): ReactNode {
  const nodes = items.map((item, index): ReactNode => {
    if (isAbsent(item)) {
      return <Absent key={index} reason={item.reason} detail={item.detail} />
    }
    const text = typeof item === 'string' ? item : item.display_id
    return <span key={index}>{text}</span>
  })

  return nodes.flatMap((node, index) => (index === 0 ? [node] : [', ', node]))
}

function RunRow({ run, kind }: { run: RunEntry; kind: 'runtime' | 'quality' }) {
  return (
    <tr>
      <td>{renderMaybe(run.run_id)}</td>
      <td>{renderMaybe(run.captured_at)}</td>
      <td>{renderJoinedList(run.models)}</td>
      {kind === 'quality' && (
        <td>{run.suites === undefined ? null : renderJoinedList(run.suites)}</td>
      )}
      <td>{renderMaybe(run.release_version)}</td>
      <td>{renderMaybe(run.commit_sha)}</td>
      <td>
        {isAbsent(run.tree_dirty) ? (
          <Absent reason={run.tree_dirty.reason} detail={run.tree_dirty.detail} />
        ) : (
          run.tree_dirty && <span className="dirty-tag">dirty tree</span>
        )}
      </td>
    </tr>
  )
}

function RunsSection({
  title,
  collection,
  kind,
}: {
  title: string
  collection: RunsCollection
  kind: 'runtime' | 'quality'
}) {
  return (
    <section>
      <h2>{title}</h2>
      {collection.runs.length === 0 ? (
        <p className="empty-state">no runs recorded</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Run</th>
              <th>Captured</th>
              <th>Models</th>
              {kind === 'quality' && <th>Suites</th>}
              <th>Release</th>
              <th>Commit</th>
              <th>Tree</th>
            </tr>
          </thead>
          <tbody>
            {collection.runs.map((run, index) => (
              <RunRow key={index} run={run} kind={kind} />
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export function RunsList() {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<RunsView>('/api/runs')
      .then((view) => {
        if (!cancelled) {
          setState({ status: 'loaded', view })
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        if (error instanceof UnauthorizedError) {
          reportUnauthorized()
          return
        }
        const message = error instanceof Error ? error.message : String(error)
        setState({ status: 'unreachable', message })
      })

    return () => {
      cancelled = true
    }
  }, [reportUnauthorized])

  if (state.status === 'loading') {
    return <p>Loading runs…</p>
  }

  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  return (
    <>
      <RunsSection
        title="Runtime runs"
        collection={state.view.runtime_runs}
        kind="runtime"
      />
      <RunsSection
        title="Quality runs"
        collection={state.view.quality_runs}
        kind="quality"
      />
    </>
  )
}
