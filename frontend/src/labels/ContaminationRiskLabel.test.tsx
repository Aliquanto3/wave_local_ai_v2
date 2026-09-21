import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { ContaminationRiskLabel } from './ContaminationRiskLabel'

describe('ContaminationRiskLabel', () => {
  it('renders a visible tag when true', () => {
    render(<ContaminationRiskLabel contaminationRisk />)

    expect(screen.getByText(/contamination risk/i)).toBeInTheDocument()
  })

  it('renders nothing when false', () => {
    const { container } = render(<ContaminationRiskLabel contaminationRisk={false} />)

    expect(container.textContent).toBe('')
  })

  it('routes through Absent when Absent', () => {
    render(
      <ContaminationRiskLabel
        contaminationRisk={{ absent: true, reason: 'null_in_row', detail: {} }}
      />
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
