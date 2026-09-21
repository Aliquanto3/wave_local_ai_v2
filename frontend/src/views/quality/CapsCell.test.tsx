import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { CapsCell } from './CapsCell'

describe('CapsCell', () => {
  it('renders max_output_tokens, stop_sequences, context_length and thinking_policy together', () => {
    render(
      <CapsCell
        maxOutputTokens={32}
        stopSequences={[]}
        contextLength={32768}
        thinkingPolicy="disabled"
      />,
    )

    expect(screen.getByText(/max_output_tokens: 32/)).toBeInTheDocument()
    expect(screen.getByText(/context_length: 32768/)).toBeInTheDocument()
    expect(screen.getByText(/thinking_policy: disabled/)).toBeInTheDocument()
  })

  it('states the routing-score caveat when thinking_policy is disabled', () => {
    render(
      <CapsCell
        maxOutputTokens={32}
        stopSequences={[]}
        contextLength={32768}
        thinkingPolicy="disabled"
      />,
    )

    expect(
      screen.getByText(/routing score, not the model's ceiling/),
    ).toBeInTheDocument()
  })

  it('omits the caveat when thinking_policy is not disabled', () => {
    render(
      <CapsCell
        maxOutputTokens={32}
        stopSequences={[]}
        contextLength={32768}
        thinkingPolicy="enabled"
      />,
    )

    expect(screen.queryByText(/routing score/)).not.toBeInTheDocument()
  })

  it('routes an absent thinking_policy through Absent', () => {
    render(
      <CapsCell
        maxOutputTokens={32}
        stopSequences={[]}
        contextLength={32768}
        thinkingPolicy={{ absent: true, reason: 'predates_schema', detail: {} }}
      />,
    )

    expect(screen.getByText(/not reported/i)).toBeInTheDocument()
  })
})
