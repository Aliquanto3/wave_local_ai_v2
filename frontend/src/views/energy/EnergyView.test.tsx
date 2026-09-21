import { render, screen, waitFor } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { energyViewFixture } from './fixtures/energyView.fixture'
import { EnergyView } from './EnergyView'

const RUN_ID = 'f5f78c795eaa4175ac506440e597ee3e' // pragma: allowlist secret

function renderWithGate() {
  return render(
    <KeyGate>
      <EnergyView runId={RUN_ID} />
    </KeyGate>
  )
}

describe('EnergyView', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('shows the composite headline and all three per-channel methods for a fully-labelled entry', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(energyViewFixture)

    renderWithGate()

    expect(await screen.findByText(/kWh \/.*kg CO2e/)).toBeInTheDocument()
    expect(screen.getAllByText(/estimated_tdp/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/measured_nvml/).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/estimated_constant/).length).toBeGreaterThan(0)
  })

  it('shows no headline and names the missing channel for the withheld entry', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(energyViewFixture)

    renderWithGate()

    const withheld = (await screen.findAllByText(/energy-headline-withheld/)).map(
      (node) => node.closest('.energy-headline')
    )
    expect(withheld.some(Boolean)).toBe(true)
    expect(screen.getAllByText(/gpu_energy_method/).length).toBeGreaterThan(0)
  })

  it('renders ScopeComparabilityLabel inline beside the figure it explains', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(energyViewFixture)

    renderWithGate()

    expect(await screen.findByText(/Scope-2 local/)).toBeInTheDocument()
  })

  it('toggles the store selector between runtime and quality', async () => {
    const spy = vi.spyOn(client, 'apiFetch').mockResolvedValue(energyViewFixture)

    renderWithGate()
    await screen.findByText(/kWh \/.*kg CO2e/)

    screen.getByRole('button', { name: 'quality' }).click()

    await waitFor(() => {
      expect(spy).toHaveBeenLastCalledWith(expect.stringContaining('store=quality'))
    })
  })
})
