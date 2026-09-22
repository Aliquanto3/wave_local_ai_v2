import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { overviewQualityFixture } from './fixtures/overviewQuality.fixture'
import { overviewRuntimeFixture } from './fixtures/overviewRuntime.fixture'
import { OverviewView } from './OverviewView'

function mockBothRoutes() {
  vi.spyOn(client, 'apiFetch').mockImplementation((path: unknown) =>
    String(path).includes('runtime')
      ? Promise.resolve(overviewRuntimeFixture)
      : Promise.resolve(overviewQualityFixture),
  )
}

function renderWithGate() {
  return render(
    <KeyGate>
      <OverviewView />
    </KeyGate>,
  )
}

describe('OverviewView', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders one card per use_cases entry and the coverage absence exactly once', async () => {
    mockBothRoutes()

    const { container } = renderWithGate()

    await screen.findByText(/no-use-case-is-silently-absent/)
    expect(container.querySelectorAll('.coverage-absence')).toHaveLength(1)
    expect(container.querySelectorAll('.overview-card')).toHaveLength(
      overviewQualityFixture.use_cases.length,
    )
    expect(screen.getByText('classification')).toBeInTheDocument()
    expect(screen.getByText('translation')).toBeInTheDocument()
  })

  it('never renders a card for a use case with no task_suite', async () => {
    vi.spyOn(client, 'apiFetch').mockImplementation((path: unknown) => {
      if (String(path).includes('runtime')) {
        return Promise.resolve(overviewRuntimeFixture)
      }
      return Promise.resolve({
        ...overviewQualityFixture,
        use_cases: [
          ...overviewQualityFixture.use_cases,
          {
            task_suite: { absent: true, reason: 'null_in_row', detail: {} },
            leader: { absent: true, reason: 'predates_schema', detail: {} },
            cloud_comparators: [],
          },
        ],
      })
    })

    const { container } = renderWithGate()

    await screen.findByText(/no-use-case-is-silently-absent/)
    expect(container.querySelectorAll('.overview-card')).toHaveLength(
      overviewQualityFixture.use_cases.length,
    )
  })
})
