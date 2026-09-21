// The one place this app touches storage for the service's API key.
// `sessionStorage`, never `localStorage`: the key must not outlive the tab
// session (epic: "the browser holds the key for the session only").
const STORAGE_KEY = 'wave-local-ai-v2:api-key'

export function getKey(): string | null {
  return sessionStorage.getItem(STORAGE_KEY)
}

export function setKey(key: string): void {
  sessionStorage.setItem(STORAGE_KEY, key)
}

export function clearKey(): void {
  sessionStorage.removeItem(STORAGE_KEY)
}
