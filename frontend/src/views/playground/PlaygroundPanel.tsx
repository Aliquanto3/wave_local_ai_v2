import { useEffect, useState, type FormEvent } from 'react'
import {
  apiFetch,
  ApiError,
  deleteJson,
  postJson,
  streamPlaygroundChat,
  UnauthorizedError,
} from '../../api/client'
import { useKeyGate } from '../../components/KeyGate'
import { PlaygroundLabel } from '../../labels/PlaygroundLabel'
import { describeHolder } from '../console/holder'
import type {
  LoadedModel,
  PlaygroundEvent,
  PlaygroundOccupied,
  PlaygroundOptions,
} from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'refused'; message: string }
  | { status: 'loaded'; options: PlaygroundOptions }

/**
 * The service sends each prompt alone: the exchanges listed above it are not
 * context the model sees, and a client must not read them as a conversation.
 */
const SINGLE_TURN_NOTE =
  'Each prompt is answered on its own: the model does not see earlier exchanges.'

interface Exchange {
  id: number
  prompt: string
  thinkingPolicy: string
  reasoning: string
  answer: string
  status: 'streaming' | 'done' | 'failed'
  error: string | null
}

/** A refusal's one line: who holds the model, or the service's own detail. */
function refusalMessage(error: unknown): string {
  if (!(error instanceof ApiError)) {
    return 'the service could not be reached'
  }
  try {
    const detail = (JSON.parse(error.body) as PlaygroundOccupied).detail
    if (typeof detail === 'string') {
      return detail
    }
    return detail.holder === null ? detail.message : describeHolder(detail.holder)
  } catch {
    return `the service answered ${error.status}`
  }
}

function ExchangeView({ exchange }: { exchange: Exchange }) {
  return (
    <li className="playground-exchange">
      <p className="playground-prompt">
        <strong>you:</strong> {exchange.prompt}
      </p>
      {exchange.reasoning !== '' && (
        <p className="playground-reasoning">
          <em>reasoning:</em> {exchange.reasoning}
        </p>
      )}
      <p className="playground-answer">
        <strong>model</strong>{' '}
        <span className="playground-policy">(thinking: {exchange.thinkingPolicy})</span>
        : {exchange.answer}
        {exchange.status === 'streaming' && <span aria-label="answering">…</span>}
      </p>
      {exchange.error !== null && <p className="console-error">{exchange.error}</p>}
    </li>
  )
}

/**
 * Type to one local roster model and watch it answer.
 *
 * The conversation lives in this component's state only: never in session or
 * local storage, gone on reload or remount. No speed or latency figure is
 * shown -- any number here would read as a measurement.
 */
export function PlaygroundPanel() {
  const { reportUnauthorized } = useKeyGate()
  const [load, setLoad] = useState<LoadState>({ status: 'loading' })
  const [rosterEntry, setRosterEntry] = useState('')
  const [policy, setPolicy] = useState('')
  const [loaded, setLoaded] = useState<LoadedModel | null>(null)
  const [busy, setBusy] = useState(false)
  const [refusal, setRefusal] = useState<string | null>(null)
  const [prompt, setPrompt] = useState('')
  const [exchanges, setExchanges] = useState<Exchange[]>([])

  useEffect(() => {
    let cancelled = false
    apiFetch<PlaygroundOptions>('/api/playground/options')
      .then((options) => {
        if (cancelled) {
          return
        }
        setLoad({ status: 'loaded', options })
        setRosterEntry(
          options.loaded?.roster_entry_id ?? options.roster_entries[0] ?? '',
        )
        setPolicy(options.thinking_policies[0] ?? '')
        setLoaded(options.loaded)
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        if (error instanceof UnauthorizedError) {
          reportUnauthorized()
          return
        }
        setLoad({ status: 'refused', message: refusalMessage(error) })
      })
    return () => {
      cancelled = true
    }
  }, [reportUnauthorized])

  const handleFailure = (error: unknown) => {
    if (error instanceof UnauthorizedError) {
      reportUnauthorized()
      return
    }
    setRefusal(refusalMessage(error))
  }

  const handleStart = async () => {
    setBusy(true)
    setRefusal(null)
    try {
      setLoaded(
        await postJson<LoadedModel>('/api/playground/session', {
          roster_entry_id: rosterEntry,
        }),
      )
    } catch (error: unknown) {
      handleFailure(error)
    } finally {
      setBusy(false)
    }
  }

  const handleStop = async () => {
    setBusy(true)
    try {
      await deleteJson('/api/playground/session')
      setLoaded(null)
    } catch (error: unknown) {
      handleFailure(error)
    } finally {
      setBusy(false)
    }
  }

  const update = (id: number, change: (exchange: Exchange) => Exchange) =>
    setExchanges((all) => all.map((each) => (each.id === id ? change(each) : each)))

  const handleSend = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const id = exchanges.length
    const sent = prompt
    setPrompt('')
    setExchanges((all) => [
      ...all,
      {
        id,
        prompt: sent,
        thinkingPolicy: policy,
        reasoning: '',
        answer: '',
        status: 'streaming',
        error: null,
      },
    ])
    try {
      await streamPlaygroundChat<PlaygroundEvent>(
        { prompt: sent, thinking_policy: policy },
        (streamed) => {
          if ('delta' in streamed) {
            update(id, (each) => ({ ...each, answer: each.answer + streamed.delta }))
          } else if ('reasoning' in streamed) {
            update(id, (each) => ({
              ...each,
              reasoning: each.reasoning + streamed.reasoning,
            }))
          } else {
            const { final } = streamed
            update(id, (each) => ({
              ...each,
              thinkingPolicy: final.thinking_policy,
              status: final.error === null ? 'done' : 'failed',
              error: final.error,
            }))
          }
        },
      )
    } catch (error: unknown) {
      if (error instanceof UnauthorizedError) {
        reportUnauthorized()
        return
      }
      update(id, (each) => ({
        ...each,
        status: 'failed',
        error: refusalMessage(error),
      }))
    }
  }

  let body
  if (load.status === 'loading') {
    body = <p>Loading playground…</p>
  } else if (load.status === 'refused') {
    body = <p className="console-error">Playground unavailable: {load.message}</p>
  } else {
    const { options } = load
    const streaming = exchanges.some((each) => each.status === 'streaming')
    body = (
      <>
        <div className="playground-model">
          <label>
            Model{' '}
            <select
              value={rosterEntry}
              onChange={(change) => setRosterEntry(change.target.value)}
            >
              {options.roster_entries.map((entry) => (
                <option key={entry} value={entry}>
                  {entry}
                </option>
              ))}
            </select>
          </label>
          <button
            type="button"
            disabled={busy || rosterEntry === ''}
            onClick={handleStart}
          >
            {loaded === null ? 'Start' : 'Switch'}
          </button>
          <button type="button" disabled={busy || loaded === null} onClick={handleStop}>
            Stop
          </button>
          {busy && <span> Loading the model…</span>}
          {loaded !== null && (
            <span className="playground-loaded">
              {' '}
              Loaded: {loaded.roster_entry_id} under {loaded.profile_id}
            </span>
          )}
        </div>
        {refusal !== null && <p className="console-error">Refused: {refusal}</p>}
        <label>
          Thinking{' '}
          <select value={policy} onChange={(change) => setPolicy(change.target.value)}>
            {options.thinking_policies.map((each) => (
              <option key={each} value={each}>
                {each}
              </option>
            ))}
          </select>
        </label>
        <ul className="playground-exchanges" aria-label="Exchanges">
          {exchanges.map((exchange) => (
            <ExchangeView key={exchange.id} exchange={exchange} />
          ))}
        </ul>
        <p className="playground-single-turn">{SINGLE_TURN_NOTE}</p>
        <form onSubmit={handleSend}>
          <textarea
            aria-label="Prompt"
            value={prompt}
            maxLength={options.max_prompt_chars}
            onChange={(change) => setPrompt(change.target.value)}
          />
          <button
            type="submit"
            disabled={loaded === null || streaming || prompt.trim() === ''}
          >
            Send
          </button>
        </form>
      </>
    )
  }

  return (
    <section className="playground-panel" aria-label="Playground">
      <PlaygroundLabel />
      {body}
    </section>
  )
}
