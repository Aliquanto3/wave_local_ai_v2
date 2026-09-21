import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { VerdictLabel } from './VerdictLabel'

describe('VerdictLabel', () => {
  it('renders reproduced distinctly', () => {
    render(<VerdictLabel verdict="reproduced" referenceRunId="run-1" />)

    expect(screen.getByText(/reproduced/)).toBeInTheDocument()
    expect(screen.getByText(/run-1/)).toBeInTheDocument()
  })

  it('renders not_reproduced distinctly', () => {
    render(<VerdictLabel verdict="not_reproduced" referenceRunId="run-1" />)

    expect(screen.getByText(/not reproduced/)).toBeInTheDocument()
  })

  it('renders not_comparable distinctly with differing fields', () => {
    render(
      <VerdictLabel
        verdict="not_comparable"
        differingFields={['sampling', 'endpoint']}
      />
    )

    expect(screen.getByText(/not comparable/)).toBeInTheDocument()
    expect(screen.getByText(/sampling/)).toBeInTheDocument()
    expect(screen.getByText(/endpoint/)).toBeInTheDocument()
  })

  it('routes through Absent when Absent', () => {
    render(
      <VerdictLabel verdict={{ absent: true, reason: 'null_in_row', detail: {} }} />
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })

  it('renders an unrecognised verdict string rather than throwing', () => {
    render(<VerdictLabel verdict="some_future_verdict" />)

    expect(screen.getByText('some_future_verdict')).toBeInTheDocument()
  })
})
