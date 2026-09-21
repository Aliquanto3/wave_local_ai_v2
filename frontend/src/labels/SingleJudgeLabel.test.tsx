import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { SingleJudgeLabel } from './SingleJudgeLabel'

describe('SingleJudgeLabel', () => {
  it('renders a visible flag naming the reason when true', () => {
    render(<SingleJudgeLabel singleJudge reason="second_judge_unavailable" />)

    expect(screen.getByText(/single judge/)).toBeInTheDocument()
    expect(screen.getByText(/second_judge_unavailable/)).toBeInTheDocument()
  })

  it('renders nothing when false', () => {
    const { container } = render(
      <SingleJudgeLabel singleJudge={false} reason="second_judge_unavailable" />,
    )

    expect(container.textContent).toBe('')
  })

  it('routes through Absent when Absent', () => {
    render(
      <SingleJudgeLabel
        singleJudge={{ absent: true, reason: 'null_in_row', detail: {} }}
        reason="second_judge_unavailable"
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
