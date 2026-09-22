import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import * as client from './api/client'
import { setKey } from './api/keyStore'
import { RUNS_VIEW_FIXTURE } from './views/fixtures/runsView.fixture'
import { overviewQualityFixture } from './views/overview/fixtures/overviewQuality.fixture'
import { overviewRuntimeFixture } from './views/overview/fixtures/overviewRuntime.fixture'

// Keyed by path, not queued: `RunsList`, `QualityPanel` and
// `RuntimeEnergyPanel` all call `apiFetch` on their own mount/unmount timing,
// so a `mockResolvedValueOnce` queued ahead of the click could be consumed by
// whichever component's fetch happens to run next, not necessarily the one
// the test intends -- a real race the previous version of this test hit
// intermittently under the full suite's parallel load.
function mockEveryRoute() {
  vi.spyOn(client, 'apiFetch').mockImplementation((path: unknown) => {
    const url = String(path)
    if (url.includes('/api/overview/runtime')) {
      return Promise.resolve(overviewRuntimeFixture)
    }
    if (url.includes('/api/overview/quality')) {
      return Promise.resolve(overviewQualityFixture)
    }
    return Promise.resolve(RUNS_VIEW_FIXTURE)
  })
}

describe('App', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('opens on the overview, and one click reaches the unchanged runs list', async () => {
    mockEveryRoute()
    const user = userEvent.setup()

    render(<App />)

    await screen.findByText(/no-use-case-is-silently-absent/)
    expect(screen.getByText('classification')).toBeInTheDocument()

    await user.click(screen.getByText('Runs →'))

    expect(await screen.findByText('runtime-run-1')).toBeInTheDocument()
    expect(screen.queryByText('classification')).not.toBeInTheDocument()
  })
})
