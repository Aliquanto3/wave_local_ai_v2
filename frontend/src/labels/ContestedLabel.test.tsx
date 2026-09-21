import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ContestedLabel } from './ContestedLabel'

describe('ContestedLabel', () => {
  it('renders a visible tag naming the reason and threshold when contested', () => {
    render(<ContestedLabel contested reason="split_verdict" threshold={0.2} />)

    expect(screen.getByText(/contested/)).toBeInTheDocument()
    expect(screen.getByText(/split_verdict/)).toBeInTheDocument()
    expect(screen.getByText(/0\.2/)).toBeInTheDocument()
  })

  it('renders nothing when not contested', () => {
    const { container } = render(
      <ContestedLabel contested={false} reason="split_verdict" threshold={0.2} />,
    )

    expect(container.textContent).toBe('')
  })

  it('routes through Absent when contested is Absent', () => {
    render(
      <ContestedLabel
        contested={{ absent: true, reason: 'null_in_row', detail: {} }}
        reason="split_verdict"
        threshold={0.2}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })

  it('routes through Absent when threshold is Absent on an otherwise contested row', () => {
    render(
      <ContestedLabel
        contested
        reason="split_verdict"
        threshold={{ absent: true, reason: 'predates_schema', detail: {} }}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
