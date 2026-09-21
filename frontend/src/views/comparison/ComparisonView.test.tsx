import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { ComparisonView } from './ComparisonView'
import { comparisonViewFixture } from './fixtures/comparisonView.fixture'

function renderWithGate() {
  return render(
    <KeyGate>
      <ComparisonView />
    </KeyGate>,
  )
}

describe('ComparisonView', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders one column per model, each naming its architecture and quant', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    expect(await screen.findByText('qwen3-0.6b-q8')).toBeInTheDocument()
    expect(screen.getByText('qwen3-1.7b-q8')).toBeInTheDocument()
    expect(screen.getByText('qwen3-4b-q4km')).toBeInTheDocument()
    expect(screen.getByText('qwen3.6-35b-a3b-ud-iq4xs')).toBeInTheDocument()
    expect(screen.getAllByText(/"kind":"dense"/).length).toBe(3)
    expect(screen.getByText(/"kind":"moe"/)).toBeInTheDocument()
    expect(screen.getAllByText('Q8_0').length).toBe(2)
    expect(screen.getByText('UD-IQ4_XS')).toBeInTheDocument()
  })

  it('renders a not-compared cell as its own label, never blank or "0"', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    const { container } = renderWithGate()

    const notCompared = await screen.findByText('not compared')
    expect(notCompared).toBeInTheDocument()
    expect(container.textContent).not.toMatch(/not compared0/)
    const cell = notCompared.closest('td')
    expect(cell?.textContent).toBe('not compared')
  })

  it('keeps the IndicativeLabel mark on a per-language cell backed by n below the floor', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/indicative/)).length).toBeGreaterThan(0)
  })

  it('names both suite_versions in the caveat line when columns differ', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    const caveat = await screen.findByText(/suite_version "2", "3"/)
    expect(caveat).toBeInTheDocument()
  })

  it('reaches the not-compared and scored cells for the same item across columns', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/exact-match:/)).length).toBeGreaterThan(0)
  })
})
