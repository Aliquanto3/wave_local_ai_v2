import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { setKey } from '../../../api/keyStore'
import { KeyGate } from '../../../components/KeyGate'
import { overviewRuntimeFixture } from '../fixtures/overviewRuntime.fixture'
import { RuntimeEnergyPanel } from './RuntimeEnergyPanel'

function renderWithGate(leaderRosterEntryIds: string[]) {
  return render(
    <KeyGate>
      <RuntimeEnergyPanel leaderRosterEntryIds={leaderRosterEntryIds} />
    </KeyGate>,
  )
}

describe('RuntimeEnergyPanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("renders the leader's headline traced to the fixture's own values", async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)
    const [leader] = overviewRuntimeFixture.entries

    renderWithGate(['qwen3.6-35b-a3b-ud-iq4xs'])

    expect(
      await screen.findByText(
        new RegExp(String(leader.runtime_headline.median_gen_tok_per_s)),
      ),
    ).toBeInTheDocument()
    expect(screen.getByText(/RTX 3060/)).toBeInTheDocument()
  })

  it('renders the same class of absence as the quality panel when no leader exists', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)

    renderWithGate([])

    expect(
      await screen.findByText(/no model to take a headline from/),
    ).toBeInTheDocument()
  })

  it('renders missing-label absences instead of a bare figure on a withheld headline', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)

    renderWithGate(['phi-4-14b-q4-k-m'])

    expect(await screen.findByText(/missing gpu_energy_method/)).toBeInTheDocument()
    expect(screen.queryByText(/kg CO2e/)).not.toBeInTheDocument()
  })

  it('renders a named unreachable message on a rejected fetch', async () => {
    vi.spyOn(client, 'apiFetch').mockRejectedValueOnce(
      new client.NetworkError(new TypeError('down')),
    )

    renderWithGate(['qwen3.6-35b-a3b-ud-iq4xs'])

    expect(await screen.findByText(/could not reach the service/i)).toBeInTheDocument()
  })
})
