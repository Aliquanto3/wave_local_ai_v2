import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { setKey } from '../../../api/keyStore'
import { KeyGate } from '../../../components/KeyGate'
import { overviewRuntimeFixture } from '../fixtures/overviewRuntime.fixture'
import { RuntimeEnergyPanel } from './RuntimeEnergyPanel'

function renderWithGate(leaderRosterEntryIds: string[] | 'unpublished') {
  return render(
    <KeyGate>
      <RuntimeEnergyPanel leaderRosterEntryIds={leaderRosterEntryIds} />
    </KeyGate>,
  )
}

const [LEADER_ENTRY, WITHHELD_ENTRY] = overviewRuntimeFixture.entries
const LEADER_MACHINE = LEADER_ENTRY.runtime_headline.machine as Record<string, unknown>

// Every numeric text node the panel renders must trace back to a number the
// fixture itself carries.
function assertEveryRenderedNumberIsInFixture(
  container: HTMLElement,
  entries: unknown,
) {
  const fixtureText = JSON.stringify(entries)
  const numbers = container.textContent?.match(/-?\d+(\.\d+)?/g) ?? []
  for (const number of numbers) {
    expect(fixtureText.includes(number), `${number} is not in the fixture`).toBe(true)
  }
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

    const { container } = renderWithGate([String(LEADER_ENTRY.roster_entry_id)])

    expect(
      await screen.findByText(
        new RegExp(String(LEADER_ENTRY.runtime_headline.median_gen_tok_per_s)),
      ),
    ).toBeInTheDocument()
    expect(
      screen.getByText(new RegExp(String(LEADER_MACHINE.gpu_name))),
    ).toBeInTheDocument()
    expect(
      screen.getByText(new RegExp(String(LEADER_ENTRY.runtime_headline.run_id))),
    ).toBeInTheDocument()
    expect(
      screen.getByText(new RegExp(String(LEADER_ENTRY.runtime_headline.fiche_hash))),
    ).toBeInTheDocument()
    assertEveryRenderedNumberIsInFixture(container, LEADER_ENTRY)
  })

  it('renders "no leader set published" when the leader field is unowned', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)

    renderWithGate('unpublished')

    expect(
      await screen.findByText(
        /no leader set published for this suite and machine class/,
      ),
    ).toBeInTheDocument()
  })

  it('renders a distinct absence for a published leader set with no member', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)

    renderWithGate([])

    expect(
      await screen.findByText(/leader set published, no member/),
    ).toBeInTheDocument()
    expect(
      screen.queryByText(/no leader set published for this suite and machine class/),
    ).not.toBeInTheDocument()
  })

  it('renders a per-id absence when a leader has no matching runtime row', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)

    renderWithGate(['no-such-roster-entry'])

    expect(
      await screen.findByText(/no runtime row for this leader/),
    ).toBeInTheDocument()
    expect(screen.getByText(/no-such-roster-entry/)).toBeInTheDocument()
  })

  it('renders missing-label absences instead of a bare figure on a withheld headline', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewRuntimeFixture)

    renderWithGate([String(WITHHELD_ENTRY.roster_entry_id)])

    expect(await screen.findByText(/missing gpu_energy_method/)).toBeInTheDocument()
    expect(screen.queryByText(/kg CO2e/)).not.toBeInTheDocument()
  })

  it('renders a named unreachable message on a rejected fetch', async () => {
    vi.spyOn(client, 'apiFetch').mockRejectedValueOnce(
      new client.NetworkError(new TypeError('down')),
    )

    renderWithGate([String(LEADER_ENTRY.roster_entry_id)])

    expect(await screen.findByText(/could not reach the service/i)).toBeInTheDocument()
  })
})
