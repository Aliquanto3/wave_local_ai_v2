import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { getKey, setKey } from '../api/keyStore'
import { KeyGate, useKeyGate } from './KeyGate'

function ChildThatReportsUnauthorized() {
  const { reportUnauthorized } = useKeyGate()
  return (
    <button type="button" onClick={reportUnauthorized}>
      simulate a 401
    </button>
  )
}

describe('KeyGate', () => {
  beforeEach(() => {
    sessionStorage.clear()
  })

  it('renders children with no prompt when a key is already stored', () => {
    setKey('a-key')

    render(
      <KeyGate>
        <p>protected content</p>
      </KeyGate>,
    )

    expect(screen.getByText('protected content')).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('withholds children and shows the prompt when no key is stored', () => {
    render(
      <KeyGate>
        <p>protected content</p>
      </KeyGate>,
    )

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.queryByText('protected content')).not.toBeInTheDocument()
  })

  it('stores a submitted key and renders children', async () => {
    const user = userEvent.setup()
    render(
      <KeyGate>
        <p>protected content</p>
      </KeyGate>,
    )

    await user.type(screen.getByLabelText('Key'), 'the-real-key')
    await user.click(screen.getByRole('button', { name: 'Continue' }))

    expect(screen.getByText('protected content')).toBeInTheDocument()
    expect(getKey()).toBe('the-real-key')
  })

  it('re-shows the prompt with a refusal on a reported 401, clearing the key', async () => {
    const user = userEvent.setup()
    setKey('a-key')

    render(
      <KeyGate>
        <ChildThatReportsUnauthorized />
      </KeyGate>,
    )

    await user.click(screen.getByRole('button', { name: 'simulate a 401' }))

    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByRole('alert').textContent).not.toBe('')
    expect(getKey()).toBeNull()
  })
})
