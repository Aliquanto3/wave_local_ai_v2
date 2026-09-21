import { useState } from 'react'
import { KeyGate } from './components/KeyGate'
import { EnergyView } from './views/energy/EnergyView'
import { QualityView } from './views/quality/QualityView'
import { RuntimeView } from './views/runtime/RuntimeView'
import { RunsList } from './views/RunsList'

type Screen = 'runs' | 'quality' | 'runtime' | 'energy'

interface Selection {
  runId: string | null
  screen: Screen
}

const TABS: { screen: Screen; label: string }[] = [
  { screen: 'quality', label: 'Quality' },
  { screen: 'runtime', label: 'Runtime' },
  { screen: 'energy', label: 'Energy' },
]

function TabStrip({
  runId,
  screen,
  onSelectScreen,
  onBackToRuns,
}: {
  runId: string
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
      {TABS.map((tab) => (
        <button
          key={tab.screen}
          type="button"
          aria-pressed={screen === tab.screen}
          disabled={screen === tab.screen}
          onClick={() => onSelectScreen(tab.screen)}
        >
          {tab.label}
        </button>
      ))}
    </nav>
  )
}

function App() {
  const [selection, setSelection] = useState<Selection>({ runId: null, screen: 'runs' })

  return (
    <KeyGate>
      <header>
        <h1>wave-local-ai-v2</h1>
      </header>
      {selection.runId === null ? (
        <RunsList onSelectRun={(runId) => setSelection({ runId, screen: 'quality' })} />
      ) : (
        <>
          <TabStrip
            runId={selection.runId}
            screen={selection.screen}
            onSelectScreen={(screen) => setSelection((s) => ({ ...s, screen }))}
            onBackToRuns={() => setSelection({ runId: null, screen: 'runs' })}
          />
          {selection.screen === 'quality' && <QualityView runId={selection.runId} />}
          {selection.screen === 'runtime' && <RuntimeView runId={selection.runId} />}
          {selection.screen === 'energy' && <EnergyView runId={selection.runId} />}
        </>
      )}
    </KeyGate>
  )
}

export default App
