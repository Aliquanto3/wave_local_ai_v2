import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { Absent } from './Absent'

describe('Absent', () => {
  it.each([
    ['predates_schema', { row_schema_version: '4' }],
    ['null_in_row', {}],
    ['pointer_unresolved', { pointer: 'roster_entry_id', value: 'abc123' }],
  ])('renders visible, non-empty text for reason %s', (reason, detail) => {
    render(<Absent reason={reason} detail={detail} />)

    const marker = screen.getByText(/not reported/i)
    expect(marker.textContent).not.toBe('')
    expect(marker.textContent).not.toBe('-')
    expect(marker.textContent).not.toBe('0')
    expect(marker.textContent).not.toBe('—')
  })
})
