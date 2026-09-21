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

/**
 * `GET path`, attaching the stored key when there is one.
 *
 * A 401 clears the stored key and throws `UnauthorizedError`, distinct from
 * a `NetworkError` (the fetch itself rejected) and an `ApiError` (any other
 * non-2xx) -- so a caller can tell "needs a key" from every other failure.
 */
export async function apiFetch<T>(path: string): Promise<T> {
  const key = getKey()
  const headers: HeadersInit = key === null ? {} : { [API_KEY_HEADER]: key }

  let response: Response
  try {
    response = await fetch(path, { headers })
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
  return (await response.json()) as T
}
