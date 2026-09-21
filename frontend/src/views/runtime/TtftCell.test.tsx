import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { TtftCell } from './TtftCell'

describe('TtftCell', () => {
  it('renders ttft_ms beside ttft_source', () => {
    render(<TtftCell ttftMs={5465.025} ttftSource="server_reported" />)

    expect(screen.getByText(/5465/)).toBeInTheDocument()
    expect(screen.getByText(/server_reported/)).toBeInTheDocument()
  })

  it('routes through Absent when ttft_ms is Absent', () => {
    render(
      <TtftCell
        ttftMs={{ absent: true, reason: 'null_in_row', detail: {} }}
        ttftSource="server_reported"
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })

  it('routes through Absent when ttft_source is Absent', () => {
    render(
      <TtftCell
        ttftMs={5465.025}
        ttftSource={{ absent: true, reason: 'null_in_row', detail: {} }}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
