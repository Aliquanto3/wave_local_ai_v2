import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { runtimeViewFixture } from './fixtures/runtimeView.fixture'
import { RuntimeView } from './RuntimeView'

const RUN_ID = 'f5f78c795eaa4175ac506440e597ee3e' // pragma: allowlist secret

function renderWithGate() {
  return render(
    <KeyGate>
      <RuntimeView runId={RUN_ID} />
    </KeyGate>,
  )
}

describe('RuntimeView', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders the fiche unconditionally for every row', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/RTX 3060/)).length).toBeGreaterThan(0)
  })

  it('renders ttft_source beside ttft_ms', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    expect(
      (await screen.findAllByText(/5465.*server_reported/)).length,
    ).toBeGreaterThan(0)
  })

  it('renders process_rss_bytes and vram_used_mib with distinct unit suffixes', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/MB$/)).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/MiB$/).length).toBeGreaterThan(0)
  })

  it('flags the unreliable entry with its spread', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/unreliable/)).length).toBeGreaterThan(0)
    expect(
      screen.getByText(/unreliable \(gen_tok_per_s spread 0\.18\)/),
    ).toBeInTheDocument()
  })

  it('shows the unreliable label on gen_tok_per_s only, the metric it was computed on', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    const labels = await screen.findAllByText(/^unreliable \(/)
    expect(labels).toHaveLength(1)
    expect(labels[0].textContent).toMatch(/gen_tok_per_s/)
    expect(screen.queryByText(/unreliable \(prompt_tok_per_s/)).toBeNull()
    expect(screen.getAllByText(/spread 0\.0109387/).length).toBeGreaterThan(0)
  })

  it('shows each throughput spread even on a row that is not flagged unreliable', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    expect((await screen.findAllByText(/spread 0\.00818/)).length).toBeGreaterThan(0)
  })

  it('renders the entry fiche_hash under the fiche_hash label, not the roster entry id', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    const hashes = await screen.findAllByText(/^b9d1af56db2b6a26/)
    expect(hashes.length).toBeGreaterThan(0)
    expect(
      hashes.every((node) => node.previousElementSibling?.textContent === 'fiche_hash'),
    ).toBe(true)
  })

  it('routes an unresolved fiche through Absent, naming the hash', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    const absences = await screen.findAllByText(/not reported/i)
    expect(absences.length).toBeGreaterThan(0)
    expect(absences.some((node) => node.title.includes('cccccccc'))).toBe(true)
  })
})
