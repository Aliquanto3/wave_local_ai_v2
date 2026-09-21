import { KeyGate } from './components/KeyGate'
import { RunsList } from './views/RunsList'

function App() {
  return (
    <KeyGate>
      <header>
        <h1>wave-local-ai-v2</h1>
      </header>
      <RunsList />
    </KeyGate>
  )
}

export default App
