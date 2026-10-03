import { act, render, screen, waitFor } from '@testing-library/react'
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
function mockEveryRoute({ demoMode = false }: { demoMode?: boolean } = {}) {
  vi.spyOn(client, 'apiFetch').mockImplementation((path: unknown) => {
    const url = String(path)
    if (url.includes('/api/console/options')) {
      return demoMode
        ? Promise.resolve({
            kinds: ['runtime', 'quality'],
            suites: ['classification'],
            roster_entries: ['entry-a'],
            machine_id: 'laptop',
            machine_absence: null,
            profiles: {},
            holder: null,
          })
        : Promise.reject(new client.ApiError(403, '{"detail": "SERVICE_DEMO_MODE"}'))
    }
    if (url.includes('/api/playground/options')) {
      return demoMode
        ? Promise.resolve({
            roster_entries: ['entry-a'],
            cloud_subject: null,
            thinking_policies: ['allowed', 'disabled'],
            max_prompt_chars: 4000,
            max_tokens: 512,
            loaded: null,
            holder: null,
          })
        : Promise.reject(new client.ApiError(403, '{"detail": "SERVICE_DEMO_MODE"}'))
    }
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

  it('shows no console entry when demo mode is off', async () => {
    mockEveryRoute()

    render(<App />)

    await screen.findByText(/no-use-case-is-silently-absent/)
    // Settled, not merely not-yet-answered: the refusal has been handled.
    await waitFor(() =>
      expect(client.apiFetch).toHaveBeenCalledWith('/api/console/options'),
    )
    await act(async () => {})
    expect(screen.queryByText('Console →')).not.toBeInTheDocument()
    expect(screen.queryByText('Playground →')).not.toBeInTheDocument()
  })

  it('shows the console entry when demo mode is on, routing to the panel', async () => {
    mockEveryRoute({ demoMode: true })
    const user = userEvent.setup()

    render(<App />)

    await user.click(await screen.findByText('Console →'))

    expect(await screen.findByRole('button', { name: 'Start run' })).toBeInTheDocument()
  })

  it('shows the playground entry when demo mode is on, routing to its labelled panel', async () => {
    mockEveryRoute({ demoMode: true })
    const user = userEvent.setup()

    render(<App />)

    await user.click(await screen.findByText('Playground →'))

    expect(
      await screen.findByText('playground — nothing here is a benchmark row'),
    ).toBeInTheDocument()
    expect(await screen.findByRole('button', { name: 'Start' })).toBeInTheDocument()
  })
})
