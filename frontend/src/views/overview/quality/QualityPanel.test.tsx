import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { setKey } from '../../../api/keyStore'
import { KeyGate } from '../../../components/KeyGate'
import { overviewQualityFixture } from '../fixtures/overviewQuality.fixture'
import { QualityPanel } from './QualityPanel'

function renderWithGate(suite: string) {
  return render(
    <KeyGate>
      <QualityPanel suite={suite} />
    </KeyGate>,
  )
}

describe('QualityPanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders every leader member of a two-entry leader set, each with its own score', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('classification')

    await screen.findByText(/Cloud comparators/)
    expect(
      container.querySelectorAll('.overview-leader-members .overview-quality-entry'),
    ).toHaveLength(2)
    expect(
      screen.getByText('d20afbda710c40378e6ad5ca8d9b6558'), // pragma: allowlist secret
    ).toBeInTheDocument()
    expect(screen.getAllByText(/exact-match:/)).toHaveLength(3)
  })

  it('renders the cloud comparator with its own run_id, not ranked against the leader', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('classification')

    await screen.findByText(/Cloud comparators/)
    expect(
      container.querySelectorAll('.overview-cloud-comparators .overview-quality-entry'),
    ).toHaveLength(1)
  })

  it('renders DeclaredAbsenceLabel and no model when no leader set is published', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('translation')

    expect(
      await screen.findByText(
        /no leader set published for this suite and machine class/,
      ),
    ).toBeInTheDocument()
    expect(container.querySelectorAll('.overview-leader-members')).toHaveLength(0)
  })
})
