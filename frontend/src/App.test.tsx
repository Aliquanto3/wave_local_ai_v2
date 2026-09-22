import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'
import * as client from './api/client'
import { setKey } from './api/keyStore'
import { RUNS_VIEW_FIXTURE } from './views/fixtures/runsView.fixture'
import { overviewQualityFixture } from './views/overview/fixtures/overviewQuality.fixture'
import { overviewRuntimeFixture } from './views/overview/fixtures/overviewRuntime.fixture'

function mockOverviewRoutes() {
  vi.spyOn(client, 'apiFetch').mockImplementation((path: unknown) =>
    String(path).includes('runtime')
      ? Promise.resolve(overviewRuntimeFixture)
      : Promise.resolve(overviewQualityFixture),
  )
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
    mockOverviewRoutes()
    const user = userEvent.setup()

    render(<App />)

    await screen.findByText(/no-use-case-is-silently-absent/)
    expect(screen.getByText('classification')).toBeInTheDocument()

    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(RUNS_VIEW_FIXTURE)
    await user.click(screen.getByText('Runs →'))

    expect(await screen.findByText('runtime-run-1')).toBeInTheDocument()
    expect(screen.queryByText('classification')).not.toBeInTheDocument()
  })
})
