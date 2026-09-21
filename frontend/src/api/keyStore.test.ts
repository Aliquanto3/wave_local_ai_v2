import { beforeEach, describe, expect, it } from 'vitest'
import { clearKey, getKey, setKey } from './keyStore'

describe('keyStore', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
  })

  it('round-trips a key through sessionStorage only', () => {
    setKey('a-key')

    expect(getKey()).toBe('a-key')
    expect(sessionStorage.getItem('wave-local-ai-v2:api-key')).toBe('a-key')
  })

  it('never touches localStorage on setKey, for every key it holds', () => {
    setKey('a-key')

    expect(localStorage.length).toBe(0)
    expect(localStorage.getItem('wave-local-ai-v2:api-key')).toBeNull()
  })

  it('clearKey removes the key from sessionStorage', () => {
    setKey('a-key')

    clearKey()

    expect(getKey()).toBeNull()
    expect(sessionStorage.getItem('wave-local-ai-v2:api-key')).toBeNull()
  })
})
