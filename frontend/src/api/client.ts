import { clearKey, getKey } from './keyStore'

const API_KEY_HEADER = 'X-API-Key' // pragma: allowlist secret

/** The service rejected the stored key (or none was stored). */
export class UnauthorizedError extends Error {
  constructor() {
    super('the service refused the stored API key')
    this.name = 'UnauthorizedError'
  }
}

/** The underlying `fetch` itself rejected -- the service is unreachable. */
export class NetworkError extends Error {
  constructor(cause: unknown) {
    super('the service could not be reached')
    this.name = 'NetworkError'
    this.cause = cause
  }
}

/** Any other non-2xx response, carrying the response's own status and body. */
export class ApiError extends Error {
  readonly status: number
  readonly body: string

  constructor(status: number, body: string) {
    super(`the service answered ${status}`)
    this.name = 'ApiError'
    this.status = status
    this.body = body
  }
}

function keyHeaders(): Record<string, string> {
  const key = getKey()
  return key === null ? {} : { [API_KEY_HEADER]: key }
}

/**
 * `fetch`, then the triage every call shares: a 401 clears the stored key and
 * throws `UnauthorizedError`, distinct from a `NetworkError` (the fetch itself
 * rejected) and an `ApiError` (any other non-2xx) -- so a caller can tell
 * "needs a key" from every other failure.
 */
async function send(path: string, init: RequestInit): Promise<Response> {
  let response: Response
  try {
    response = await fetch(path, init)
  } catch (cause) {
    throw new NetworkError(cause)
  }

  if (response.status === 401) {
    clearKey()
    throw new UnauthorizedError()
  }
  if (!response.ok) {
    throw new ApiError(response.status, await response.text())
  }
  return response
}

/** `GET path`, attaching the stored key when there is one. */
export async function apiFetch<T>(path: string): Promise<T> {
  const response = await send(path, { headers: keyHeaders() })
  return (await response.json()) as T
}

/** `POST /api/console/runs` with the chosen, declared-set values. */
export async function postConsoleRun<T>(body: Record<string, string>): Promise<T> {
  const response = await send('/api/console/runs', {
    method: 'POST',
    headers: { ...keyHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return (await response.json()) as T
}

/**
 * Follow a console run's NDJSON stream: `onLine` once per output line as it
 * arrives, then `onFinal` once with the final event.
 *
 * `fetch` plus a manual `ReadableStream` read, never `EventSource` or
 * `WebSocket`: neither can send the `X-API-Key` header, and a key in the
 * query string would land in the service's access log.
 */
export async function streamConsoleRun<F>(
  launchId: string,
  onLine: (line: string) => void,
  onFinal: (final: F) => void,
): Promise<void> {
  const response = await send(`/api/console/runs/${launchId}/stream`, {
    headers: keyHeaders(),
  })
  if (response.body === null) {
    return
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffered = ''

  const dispatch = (text: string) => {
    if (text.trim() === '') {
      return
    }
    const event = JSON.parse(text) as { line?: string; final?: F }
    if (event.line !== undefined) {
      onLine(event.line)
    } else if (event.final !== undefined) {
      onFinal(event.final)
    }
  }

  for (;;) {
    const { done, value } = await reader.read()
    if (done) {
      break
    }
    buffered += decoder.decode(value, { stream: true })
    const complete = buffered.split('\n')
    buffered = complete.pop() ?? ''
    complete.forEach(dispatch)
  }
  dispatch(buffered + decoder.decode())
}
