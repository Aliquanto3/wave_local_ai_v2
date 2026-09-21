import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FailureCountsCell } from './FailureCountsCell'

describe('FailureCountsCell', () => {
  it('renders all four reasons as individually labelled counts', () => {
    render(
      <FailureCountsCell
        failureCounts={{
          empty: 0,
          unparseable: 4,
          truncated_max_tokens: 1,
          truncated_context: 2,
        }}
      />
    )

    expect(screen.getByText(/empty: 0/)).toBeInTheDocument()
    expect(screen.getByText(/unparseable: 4/)).toBeInTheDocument()
    expect(screen.getByText(/truncated \(max tokens\): 1/)).toBeInTheDocument()
    expect(screen.getByText(/truncated \(context\): 2/)).toBeInTheDocument()
  })

  it('routes through Absent when the whole block is Absent', () => {
    render(
      <FailureCountsCell
        failureCounts={{ absent: true, reason: 'null_in_row', detail: {} }}
      />
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
