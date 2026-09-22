// The cheap automated half of the 1280x800 no-horizontal-scroll check (see
// plan.md's Decisions): jsdom performs no real layout, so this cannot prove
// the page fits at 1280px -- only that no element declares an inline width
// wider than it. The primary evidence is the manual 1280x800 screenshot walk
// filed under this phase's evidence/ (see phase-3.md task 8 and phase-4).

import { render } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../api/client'
import { setKey } from '../api/keyStore'
import { KeyGate } from '../components/KeyGate'
import { qualityViewFixture } from './quality/fixtures/qualityView.fixture'
import { QualityView } from './quality/QualityView'
import { runtimeViewFixture } from './runtime/fixtures/runtimeView.fixture'
import { RuntimeView } from './runtime/RuntimeView'
import { comparisonViewFixture } from './comparison/fixtures/comparisonView.fixture'
import { ComparisonView } from './comparison/ComparisonView'
import { energyViewFixture } from './energy/fixtures/energyView.fixture'
import { EnergyView } from './energy/EnergyView'

const MAX_WIDTH_PX = 1280
const RUN_ID = 'f5f78c795eaa4175ac506440e597ee3e' // pragma: allowlist secret
const QUALITY_RUN_ID = 'd20afbda710c40378e6ad5ca8d9b6558' // pragma: allowlist secret

function assertNoElementExceedsWidth(container: HTMLElement) {
  for (const element of Array.from(container.querySelectorAll<HTMLElement>('*'))) {
    const width = element.style.width
    const minWidth = element.style.minWidth
    for (const declared of [width, minWidth]) {
      if (declared.endsWith('px')) {
        const value = Number.parseFloat(declared)
        expect(value).toBeLessThanOrEqual(MAX_WIDTH_PX)
      }
    }
  }
}

describe('no screen declares an element wider than 1280px', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('QualityView', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(qualityViewFixture)
    const { container, findByText } = render(
      <KeyGate>
        <QualityView runId={QUALITY_RUN_ID} />
      </KeyGate>,
    )
    await findByText(/no-use-case-is-silently-absent/)

    assertNoElementExceedsWidth(container)
  })

  it('RuntimeView', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(runtimeViewFixture)
    const { container, findAllByText } = render(
      <KeyGate>
        <RuntimeView runId={RUN_ID} />
      </KeyGate>,
    )
    await findAllByText(/RTX 3060/)

    assertNoElementExceedsWidth(container)
  })

  it('EnergyView', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(energyViewFixture)
    const { container, findByText } = render(
      <KeyGate>
        <EnergyView runId={RUN_ID} />
      </KeyGate>,
    )
    await findByText(/kWh \/.*kg CO2e/)

    assertNoElementExceedsWidth(container)
  })

  it('ComparisonView', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(comparisonViewFixture)
    const { container, findByText } = render(
      <KeyGate>
        <ComparisonView />
      </KeyGate>,
    )
    await findByText('Suite score')

    assertNoElementExceedsWidth(container)
  })
})
