import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { DeclaredAbsenceLabel } from './DeclaredAbsenceLabel'

describe('DeclaredAbsenceLabel', () => {
  it('renders its own distinct text for two different reasons', () => {
    const { unmount } = render(
      <DeclaredAbsenceLabel reason="no-use-case-is-silently-absent" />
    )
    expect(
      screen.getByText(/no-use-case-is-silently-absent/)
    ).toBeInTheDocument()
    unmount()

    render(<DeclaredAbsenceLabel reason="judged-score-withheld" detail="no store holds a judged row" />)
    expect(screen.getByText(/judged-score-withheld/)).toBeInTheDocument()
    expect(screen.getByText(/no store holds a judged row/)).toBeInTheDocument()
  })

  it('never renders a shared generic "absent" string', () => {
    render(<DeclaredAbsenceLabel reason="energy-headline-withheld" />)

    expect(screen.queryByText(/^absent$/i)).not.toBeInTheDocument()
  })
})
