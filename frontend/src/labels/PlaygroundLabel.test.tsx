import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { PlaygroundLabel } from './PlaygroundLabel'

describe('PlaygroundLabel', () => {
  it('renders the PRD string exactly', () => {
    render(<PlaygroundLabel />)

    expect(screen.getByRole('note').textContent).toBe(
      'playground — nothing here is a benchmark row',
    )
  })
})
