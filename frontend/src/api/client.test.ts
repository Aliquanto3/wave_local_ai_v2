import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getKey, setKey } from './keyStore'
import { ApiError, NetworkError, UnauthorizedError, apiFetch } from './client'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'content-type': 'application/json' },
  })
}

describe('apiFetch', () => {
  beforeEach(() => {
    sessionStorage.clear()
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('attaches X-API-Key only when a key is stored', async () => {
    setKey('a-key')
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, { ok: true }))

    const result = await apiFetch<{ ok: boolean }>('/api/runs')

    expect(result).toEqual({ ok: true })
    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers).get('X-API-Key')).toBe('a-key')
  })

  it('sends no key header when none is stored', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, {}))

    await apiFetch('/api/runs')

    const [, init] = vi.mocked(fetch).mock.calls[0]
    expect(new Headers(init?.headers).has('X-API-Key')).toBe(false)
  })

  it('throws UnauthorizedError and clears the stored key on a 401', async () => {
    setKey('a-key')
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(401, { detail: 'no' }))

    await expect(apiFetch('/api/runs')).rejects.toBeInstanceOf(UnauthorizedError)
    expect(getKey()).toBeNull()
  })

  it('throws a distinct NetworkError on a rejected fetch', async () => {
    vi.mocked(fetch).mockRejectedValueOnce(new TypeError('network down'))

    const failure = apiFetch('/api/runs')

    await expect(failure).rejects.toBeInstanceOf(NetworkError)
    await expect(failure).rejects.not.toBeInstanceOf(UnauthorizedError)
  })

  it('throws ApiError carrying the status on a non-401 non-2xx response', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(
      new Response('server exploded', { status: 500 }),
    )

    const failure = apiFetch('/api/runs')

    await expect(failure).rejects.toBeInstanceOf(ApiError)
    await failure.catch((error: unknown) => {
      expect((error as ApiError).status).toBe(500)
    })
  })
})
