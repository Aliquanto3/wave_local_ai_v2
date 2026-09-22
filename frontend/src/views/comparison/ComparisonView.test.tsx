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
    expect(screen.getAllByText(/^dense, /).length).toBe(3)
    expect(screen.getByText('MoE, 40 experts, 3.1B active')).toBeInTheDocument()
    expect(screen.getAllByText(/^local \/ Qwen3/).length).toBe(4)
    expect(screen.getAllByText('Q8_0').length).toBe(2)
    expect(screen.getByText('UD-IQ4_XS')).toBeInTheDocument()
  })

  it('names each column machine and backing run, so a number traces to its run', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    const moeFichePrefix = 'b9d1af56db2b' // pragma: allowlist secret
    const fiche = await screen.findByText(moeFichePrefix)
    expect(fiche.getAttribute('title')?.startsWith(moeFichePrefix)).toBe(true)
    expect(screen.getByText('run d4d2e0d5d9a94aa98d7c2eb1569fd60c')).toBeInTheDocument()
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

  it('states each column suite score once, at the published precision', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    const suiteRow = (await screen.findByText('Suite score')).closest('tr')
    expect(suiteRow?.textContent).toMatch(/0\.45.*0\.60.*0\.70.*1\.00/)
    expect(screen.getAllByText('0.45').length).toBe(1)
  })

  it('reads an exact-match item as correct or wrong', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)

    renderWithGate()

    expect((await screen.findAllByText('wrong')).length).toBe(3)
    expect(screen.getAllByText('correct').length).toBe(4)
  })
})
