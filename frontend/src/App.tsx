import { useState } from 'react'
import { KeyGate } from './components/KeyGate'
import { ComparisonView } from './views/comparison/ComparisonView'
import { EnergyView } from './views/energy/EnergyView'
import { OverviewView } from './views/overview/OverviewView'
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
