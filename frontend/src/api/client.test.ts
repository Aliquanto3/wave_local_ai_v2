import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { getKey, setKey } from './keyStore'
import {
  ApiError,
  NetworkError,
  UnauthorizedError,
  apiFetch,
  postConsoleRun,
  streamConsoleRun,
} from './client'

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

/** A response whose body the test feeds chunk by chunk. */
function controlledStream(): {
  response: Response
  push: (text: string) => void
  close: () => void
} {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({
    start(c) {
      controller = c
    },
  })
  const encoder = new TextEncoder()
  return {
    response: new Response(body, { status: 200 }),
    push: (text) => controller.enqueue(encoder.encode(text)),
    close: () => controller.close(),
  }
}

describe('console client', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
    vi.stubGlobal('fetch', vi.fn())
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('posts a run with the key and a JSON body', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(200, { launch_id: 'L1' }))

    const launch = await postConsoleRun<{ launch_id: string }>({ kind: 'runtime' })

    expect(launch.launch_id).toBe('L1')
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/console/runs')
    expect(init?.method).toBe('POST')
    expect(new Headers(init?.headers).get('X-API-Key')).toBe('a-key')
    expect(init?.body).toBe('{"kind":"runtime"}')
  })

  it('treats a 401 on the post like apiFetch does', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(401, { detail: 'no' }))

    await expect(postConsoleRun({ kind: 'runtime' })).rejects.toBeInstanceOf(
      UnauthorizedError,
    )
    expect(getKey()).toBeNull()
  })

  it('treats a 401 on the stream like apiFetch does', async () => {
    vi.mocked(fetch).mockResolvedValueOnce(jsonResponse(401, { detail: 'no' }))

    await expect(streamConsoleRun('L1', vi.fn(), vi.fn())).rejects.toBeInstanceOf(
      UnauthorizedError,
    )
    expect(getKey()).toBeNull()
  })

  it('delivers each line as its chunk arrives, then the final event', async () => {
    const stream = controlledStream()
    vi.mocked(fetch).mockResolvedValueOnce(stream.response)
    const onLine = vi.fn()
    const onFinal = vi.fn()

    const done = streamConsoleRun('L1', onLine, onFinal)
    stream.push('{"line": "first"}\n{"line": "sec')
    await vi.waitFor(() => expect(onLine).toHaveBeenCalledTimes(1))
    expect(onLine).toHaveBeenLastCalledWith('first')

    stream.push('ond"}\n{"final": {"ok": true}}\n')
    stream.close()
    await done

    expect(onLine).toHaveBeenCalledTimes(2)
    expect(onLine).toHaveBeenLastCalledWith('second')
    expect(onFinal).toHaveBeenCalledWith({ ok: true })
    const [path, init] = vi.mocked(fetch).mock.calls[0]
    expect(path).toBe('/api/console/runs/L1/stream')
    expect(new Headers(init?.headers).get('X-API-Key')).toBe('a-key')
  })
})
