import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { LiveOutput } from './LiveOutput'

describe('LiveOutput', () => {
  it('appends new lines to the ones already shown', () => {
    const { rerender } = render(<LiveOutput lines={['first']} />)
    expect(screen.getByText('first')).toBeInTheDocument()

    rerender(<LiveOutput lines={['first', 'second']} />)

    const output = screen.getByLabelText('Live output')
    expect(output.textContent).toBe('firstsecond')
  })
})
