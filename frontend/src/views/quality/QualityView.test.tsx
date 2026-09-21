import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { qualityViewFixture } from './fixtures/qualityView.fixture'
import { QualityView } from './QualityView'

const RUN_ID = 'd20afbda710c40378e6ad5ca8d9b6558' // pragma: allowlist secret

function renderWithGate() {
  return render(
    <KeyGate>
      <QualityView runId={RUN_ID} />
    </KeyGate>
  )
}

describe('QualityView', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the coverage record as a declared absence', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect(await screen.findByText(/no-use-case-is-silently-absent/)).toBeInTheDocument()
  })

  it('renders every real verdict distinctly', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/not comparable/)).length).toBeGreaterThan(0)
    expect(screen.getByText(/^reproduced$/)).toBeInTheDocument()
    expect(screen.getByText(/not reproduced/)).toBeInTheDocument()
  })

  it('renders a judge-less entry with DeclaredAbsenceLabel and no bare judged score', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect(await screen.findAllByText(/judged-score-withheld/)).toHaveLength(3)
  })

  it('renders the judged headline score only when a judge block backs it', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect(await screen.findByText(/judged score: 0\.55/)).toBeInTheDocument()
    expect(screen.getByText(/agreement: 0\.42/)).toBeInTheDocument()
  })

  it('renders the contamination-risk, contested and indicative marks on the hand-edited entry', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect(await screen.findByText(/contamination risk/)).toBeInTheDocument()
    expect(screen.getByText(/contested/)).toBeInTheDocument()
    expect(screen.getAllByText(/indicative/).length).toBeGreaterThan(0)
  })

  it('renders exact-match and graded scores in the same render without sharing a column', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/exact-match:/)).length).toBeGreaterThan(0)
    expect(screen.getByText(/graded \(chrf\)/)).toBeInTheDocument()
  })

  it('renders the suite-level summary once per suite, not once per item', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    const { container } = renderWithGate()

    expect(await screen.findByText(/indicative \(low_n\)/)).toBeInTheDocument()
    expect(container.querySelectorAll('.quality-suite-summary-row')).toHaveLength(1)
    expect(screen.getAllByText(/excluded from headline: 3/)).toHaveLength(1)
  })

  it('routes a breakdown that is itself absent through Absent, not through its keys', async () => {
    const [entry] = qualityViewFixture.entries
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce({
      ...qualityViewFixture,
      entries: [
        {
          ...entry,
          language_breakdown: {
            absent: true,
            reason: 'predates_schema',
            detail: { row_schema_version: '7' },
          },
        },
      ],
    })

    const { container } = renderWithGate()

    await screen.findByText(/no-use-case-is-silently-absent/)
    const perLanguageCell = container.querySelectorAll('tbody tr td')[3]
    expect(perLanguageCell.querySelector('.absent')).not.toBeNull()
    expect(perLanguageCell.textContent).not.toMatch(/absent:|undefined/)
  })

  it('renders the four failure-count reasons individually', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)

    renderWithGate()

    expect(await screen.findAllByText(/unparseable: 4/)).not.toHaveLength(0)
  })
})
