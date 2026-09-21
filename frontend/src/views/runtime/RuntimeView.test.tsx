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
    </KeyGate>
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

    expect((await screen.findAllByText(/5465.*server_reported/)).length).toBeGreaterThan(0)
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
    expect(screen.getByText(/0\.18/)).toBeInTheDocument()
  })

  it('routes an unresolved fiche through Absent, naming the hash', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)

    renderWithGate()

    const absences = await screen.findAllByText(/not reported/i)
    expect(absences.length).toBeGreaterThan(0)
    expect(absences.some((node) => node.title.includes('cccccccc'))).toBe(true)
  })
})
