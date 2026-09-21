import {
  createContext,
  useCallback,
  useContext,
  useState,
  type FormEvent,
  type ReactNode,
} from 'react'
import { clearKey, getKey, setKey } from '../api/keyStore'

interface KeyGateContextValue {
  /** Route an `apiFetch` `UnauthorizedError` back to re-showing the prompt. */
  reportUnauthorized: () => void
}

const KeyGateContext = createContext<KeyGateContextValue | null>(null)

/** A descendant of `KeyGate` gets this to report a caught `UnauthorizedError`. */
export function useKeyGate(): KeyGateContextValue {
  const value = useContext(KeyGateContext)
  if (value === null) {
    throw new Error('useKeyGate must be called within a KeyGate')
  }
  return value
}

interface KeyGateProps {
  children: ReactNode
}

/**
 * Renders `children` once a key is present in this tab's `sessionStorage`,
 * a one-time prompt otherwise -- and re-prompts with a stated refusal on a
 * 401, without any child re-implementing that handling itself.
 */
export function KeyGate({ children }: KeyGateProps) {
  const [hasKey, setHasKey] = useState(() => getKey() !== null)
  const [refusal, setRefusal] = useState<string | null>(null)
  const [draft, setDraft] = useState('')

  const reportUnauthorized = useCallback(() => {
    clearKey()
    setHasKey(false)
    setRefusal('The service refused that key. Enter it again.')
  }, [])

  if (!hasKey) {
    const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault()
      const trimmed = draft.trim()
      if (trimmed === '') {
        return
      }
      setKey(trimmed)
      setHasKey(true)
      setRefusal(null)
      setDraft('')
    }

    return (
      <div role="dialog" aria-label="API key required">
        <p>This dashboard needs the service&apos;s API key</p>
        <form onSubmit={handleSubmit}>
          <label htmlFor="api-key-input">Key</label>
          <input
            id="api-key-input"
            type="password"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
          />
          <button type="submit">Continue</button>
        </form>
        {refusal !== null && <p role="alert">{refusal}</p>}
      </div>
    )
  }

  return (
    <KeyGateContext.Provider value={{ reportUnauthorized }}>
      {children}
    </KeyGateContext.Provider>
  )
}
