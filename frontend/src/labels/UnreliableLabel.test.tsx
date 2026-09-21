import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { UnreliableLabel } from './UnreliableLabel'

describe('UnreliableLabel', () => {
  it('renders the flag with its spread and metric name when true', () => {
    render(<UnreliableLabel unreliable spread={0.42} metric="ttft_ms" />)

    expect(screen.getByText(/unreliable/)).toBeInTheDocument()
    expect(screen.getByText(/ttft_ms/)).toBeInTheDocument()
    expect(screen.getByText(/0\.42/)).toBeInTheDocument()
  })

  it('renders nothing from this component when false', () => {
    const { container } = render(
      <UnreliableLabel unreliable={false} spread={0.42} metric="ttft_ms" />,
    )

    expect(container.textContent).toBe('')
  })

  it('routes through Absent when Absent', () => {
    render(
      <UnreliableLabel
        unreliable={{ absent: true, reason: 'null_in_row', detail: {} }}
        spread={0.42}
        metric="ttft_ms"
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
