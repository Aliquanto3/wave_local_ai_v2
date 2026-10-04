import { useEffect, useState } from 'react'
import { apiFetch, UnauthorizedError } from './api/client'
import { KeyGate, useKeyGate } from './components/KeyGate'
import { ComparisonView } from './views/comparison/ComparisonView'
import { ConsolePanel } from './views/console/ConsolePanel'
import { EnergyView } from './views/energy/EnergyView'
import { OverviewView } from './views/overview/OverviewView'
import { PlaygroundPanel } from './views/playground/PlaygroundPanel'
import { QualityView } from './views/quality/QualityView'
import { RuntimeView } from './views/runtime/RuntimeView'
import { RunsList } from './views/RunsList'

type RunKind = 'quality' | 'runtime'
type Screen = 'primary' | 'energy'

type Selection =
  | { status: 'overview' }
  | { status: 'runs' }
  | { status: 'selected'; runId: string; kind: RunKind; screen: Screen }
  | { status: 'comparison' }
  | { status: 'console' }
  | { status: 'playground' }

// A quality run_id and a runtime run_id are minted by two separate CLIs over
// two separate stores (see read_model.runs_view's own docstring) -- there is
// no run whose id resolves against both. The tab strip therefore only ever
// offers the screen matching the selected run's own kind, plus Energy (which
// reads over that same store by construction), never a screen that names the
// other store's route.
const PRIMARY_LABEL: Record<RunKind, string> = {
  quality: 'Quality',
  runtime: 'Runtime',
}

function TabStrip({
  runId,
  kind,
  screen,
  onSelectScreen,
  onBackToRuns,
}: {
  runId: string
  kind: RunKind
  screen: Screen
  onSelectScreen: (screen: Screen) => void
  onBackToRuns: () => void
}) {
  return (
    <nav className="tab-strip">
      <button type="button" className="back-to-runs" onClick={onBackToRuns}>
        ← Runs
      </button>
      <span className="tab-strip-run-id">{runId}</span>
      <button
        type="button"
        aria-pressed={screen === 'primary'}
        disabled={screen === 'primary'}
        onClick={() => onSelectScreen('primary')}
      >
        {PRIMARY_LABEL[kind]}
      </button>
      <button
        type="button"
        aria-pressed={screen === 'energy'}
        disabled={screen === 'energy'}
        onClick={() => onSelectScreen('energy')}
      >
        Energy
      </button>
    </nav>
  )
}

/**
 * A demo surface's entry ("Console →", "Playground →"), shown only when this
 * machine's service answers that surface's options route: demo mode off
 * (403), or any other refusal, shows nothing.
 */
function DemoEntry({
  optionsPath,
  label,
  onOpen,
}: {
  optionsPath: string
  label: string
  onOpen: () => void
}) {
  const { reportUnauthorized } = useKeyGate()
  const [available, setAvailable] = useState(false)

  useEffect(() => {
    let cancelled = false
    apiFetch(optionsPath)
      .then(() => {
        if (!cancelled) {
          setAvailable(true)
        }
      })
      .catch((error: unknown) => {
        if (!cancelled && error instanceof UnauthorizedError) {
          reportUnauthorized()
        }
      })
    return () => {
      cancelled = true
    }
  }, [optionsPath, reportUnauthorized])

  if (!available) {
    return null
  }
  return (
    <button type="button" onClick={onOpen}>
      {label}
    </button>
  )
}

function App() {
  const [selection, setSelection] = useState<Selection>({ status: 'overview' })

  return (
    <KeyGate>
      <header>
        <h1>wave-local-ai-v2</h1>
      </header>
      {selection.status === 'overview' && (
        <>
          <nav className="top-nav">
            <button type="button" onClick={() => setSelection({ status: 'runs' })}>
              Runs →
            </button>
            <DemoEntry
              optionsPath="/api/console/options"
              label="Console →"
              onOpen={() => setSelection({ status: 'console' })}
            />
            <DemoEntry
              optionsPath="/api/playground/options"
              label="Playground →"
              onOpen={() => setSelection({ status: 'playground' })}
            />
          </nav>
          <OverviewView />
        </>
      )}
      {selection.status === 'runs' && (
        <>
          <nav className="top-nav">
            <button
              type="button"
              onClick={() => setSelection({ status: 'comparison' })}
            >
              Compare dense and MoE
            </button>
          </nav>
          <RunsList
            onSelectRun={(runId, kind) =>
              setSelection({ status: 'selected', runId, kind, screen: 'primary' })
            }
          />
        </>
      )}
      {selection.status === 'comparison' && (
        <>
          <nav className="top-nav">
            <button type="button" onClick={() => setSelection({ status: 'runs' })}>
              ← Runs
            </button>
          </nav>
          <ComparisonView />
        </>
      )}
      {selection.status === 'console' && (
        <>
          <nav className="top-nav">
            <button type="button" onClick={() => setSelection({ status: 'overview' })}>
              ← Overview
            </button>
          </nav>
          <ConsolePanel />
        </>
      )}
      {selection.status === 'playground' && (
        <>
          <nav className="top-nav">
            <button type="button" onClick={() => setSelection({ status: 'overview' })}>
              ← Overview
            </button>
          </nav>
          <PlaygroundPanel />
        </>
      )}
      {selection.status === 'selected' && (
        <>
          <TabStrip
            runId={selection.runId}
            kind={selection.kind}
            screen={selection.screen}
            onSelectScreen={(screen) => setSelection((s) => ({ ...s, screen }))}
            onBackToRuns={() => setSelection({ status: 'runs' })}
          />
          {selection.screen === 'primary' && selection.kind === 'quality' && (
            <QualityView runId={selection.runId} />
          )}
          {selection.screen === 'primary' && selection.kind === 'runtime' && (
            <RuntimeView runId={selection.runId} />
          )}
          {selection.screen === 'energy' && (
            <EnergyView runId={selection.runId} initialStore={selection.kind} />
          )}
        </>
      )}
    </KeyGate>
  )
}

export default App
