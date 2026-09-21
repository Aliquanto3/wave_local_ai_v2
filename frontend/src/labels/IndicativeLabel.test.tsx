import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { IndicativeLabel } from './IndicativeLabel'

describe('IndicativeLabel', () => {
  it('renders the tag and every reason when indicative is true', () => {
    render(<IndicativeLabel indicative reasons={['low_n', 'near_context_cap']} />)

    expect(screen.getByText(/indicative/)).toBeInTheDocument()
    expect(screen.getByText(/low_n/)).toBeInTheDocument()
    expect(screen.getByText(/near_context_cap/)).toBeInTheDocument()
  })

  it('renders n beside the tag when it is passed', () => {
    render(<IndicativeLabel indicative reasons={['low_n']} n={5} />)

    expect(screen.getByText(/n=5/)).toBeInTheDocument()
  })

  it('renders nothing when indicative is false', () => {
    const { container } = render(
      <IndicativeLabel indicative={false} reasons={['low_n']} />,
    )

    expect(container.textContent).toBe('')
  })

  it('routes through Absent when indicative is Absent', () => {
    render(
      <IndicativeLabel
        indicative={{ absent: true, reason: 'null_in_row', detail: {} }}
        reasons={['low_n']}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })

  it('routes through Absent when reasons is Absent', () => {
    render(
      <IndicativeLabel
        indicative
        reasons={{ absent: true, reason: 'null_in_row', detail: {} }}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
