import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { EnergyMethodLabel } from './EnergyMethodLabel'

describe('EnergyMethodLabel', () => {
  it.each([
    ['cpu', 'estimated_tdp'],
    ['gpu', 'nvml_sampled'],
    ['ram', 'estimated_constant'],
  ] as const)('renders the %s channel beside its method string', (channel, method) => {
    render(<EnergyMethodLabel channel={channel} method={method} />)

    expect(screen.getByText(new RegExp(channel))).toBeInTheDocument()
    expect(screen.getByText(new RegExp(method))).toBeInTheDocument()
  })

  it('routes through Absent when the method is Absent', () => {
    render(
      <EnergyMethodLabel
        channel="gpu"
        method={{ absent: true, reason: 'null_in_row', detail: {} }}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
