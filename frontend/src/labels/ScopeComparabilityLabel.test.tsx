import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ScopeComparabilityLabel } from './ScopeComparabilityLabel'

describe('ScopeComparabilityLabel', () => {
  it('renders the text visibly in the DOM text content', () => {
    render(
      <ScopeComparabilityLabel text="cpu/ram are Scope-2 local, gpu is Scope-3 cloud" />
    )

    const label = screen.getByText(/Scope-2 local/)
    expect(label.textContent).toContain('Scope-3 cloud')
  })

  it('routes through Absent when Absent', () => {
    render(
      <ScopeComparabilityLabel
        text={{ absent: true, reason: 'null_in_row', detail: {} }}
      />
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
