import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { PLAYGROUND_LABEL_TEXT } from '../../labels/PlaygroundLabel'
import { PlaygroundPanel } from './PlaygroundPanel'
import type { PlaygroundEvent, PlaygroundOptions } from './types'

const PROMPT = 'zebra-violet-4419 tell me about tides'
// Any figure that would read as a measurement of speed or latency.
const SPEED_FIGURE = /\d\s*(tok|tokens?\/s|t\/s|ms\b|s\b)|per second|latency/i

function options(overrides: Partial<PlaygroundOptions> = {}): PlaygroundOptions {
  return {
    roster_entries: ['qwen3-0.6b-q8', 'qwen3-1.7b-q8'],
    thinking_policies: ['allowed', 'disabled'],
    max_prompt_chars: 4000,
    max_tokens: 512,
    loaded: null,
    holder: null,
    ...overrides,
  }
}

function renderPanel() {
  return render(
    <KeyGate>
      <PlaygroundPanel />
    </KeyGate>,
  )
}

const label = () => screen.getByText(PLAYGROUND_LABEL_TEXT)

async function startAndAnswer(events: PlaygroundEvent[]) {
  vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
  vi.spyOn(client, 'postJson').mockResolvedValue({
    roster_entry_id: 'qwen3-0.6b-q8',
    profile_id: 'qwen3-0.6b-q8@laptop-mobile-gpu/gpu',
  })
  const chat = vi
    .spyOn(client, 'streamPlaygroundChat')
    .mockImplementation(async (_body, onEvent) => {
      events.forEach((event) => (onEvent as (e: PlaygroundEvent) => void)(event))
    })
  const user = userEvent.setup()
  const view = renderPanel()
  await user.click(await screen.findByRole('button', { name: 'Start' }))
  await screen.findByText(/Loaded: qwen3-0.6b-q8/)
  await user.selectOptions(screen.getByLabelText(/Thinking/), 'disabled')
  await user.type(screen.getByLabelText('Prompt'), PROMPT)
  await user.click(screen.getByRole('button', { name: 'Send' }))
  return { chat, view }
}

describe('PlaygroundPanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('carries the label while loading', () => {
    vi.spyOn(client, 'apiFetch').mockReturnValue(new Promise(() => {}))

    renderPanel()

    expect(label()).toBeInTheDocument()
    expect(screen.getByText(/Loading playground/)).toBeInTheDocument()
  })

  it('carries the label on a refusal', async () => {
    vi.spyOn(client, 'apiFetch').mockRejectedValue(
      new client.ApiError(403, '{"detail": "demo mode is off (SERVICE_DEMO_MODE)"}'),
    )

    renderPanel()

    expect(await screen.findByText(/SERVICE_DEMO_MODE/)).toBeInTheDocument()
    expect(label()).toBeInTheDocument()
  })

  it('carries the label when empty, and names the run that holds the model', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    vi.spyOn(client, 'postJson').mockRejectedValue(
      new client.ApiError(
        409,
        JSON.stringify({
          detail: {
            message: 'a run is in progress',
            holder: {
              session: 'run',
              kind: 'runtime',
              suite: null,
              roster_entry_id: 'qwen3-0.6b-q8',
              profile_id: 'qwen3-0.6b-q8@laptop-mobile-gpu/gpu',
              started_at: '2026-10-02T22:00:00+00:00',
              run_id: null,
            },
          },
        }),
      ),
    )
    const user = userEvent.setup()

    renderPanel()
    await user.click(await screen.findByRole('button', { name: 'Start' }))

    expect(
      await screen.findByText(/Refused: Run in progress: runtime/),
    ).toBeInTheDocument()
    expect(label()).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Send' })).toBeDisabled()
  })

  it('streams an answer with the policy in force beside it and no speed figure', async () => {
    const { chat } = await startAndAnswer([
      { reasoning: 'thinking it over' },
      { delta: 'Tides ' },
      { delta: 'rise.' },
      { final: { thinking_policy: 'disabled', finish_reason: 'stop', error: null } },
    ])

    expect(await screen.findByText(/Tides rise\./)).toBeInTheDocument()
    expect(screen.getByText('(thinking: disabled)')).toBeInTheDocument()
    expect(screen.getByText(/thinking it over/)).toBeInTheDocument()
    expect(label()).toBeInTheDocument()
    expect(chat).toHaveBeenCalledWith(
      { prompt: PROMPT, thinking_policy: 'disabled' },
      expect.any(Function),
    )
    expect(screen.getByLabelText('Exchanges').textContent).not.toMatch(SPEED_FIGURE)
  })

  it('states that each prompt is answered on its own, and sends it alone', async () => {
    const { chat } = await startAndAnswer([
      { delta: 'Tides rise.' },
      { final: { thinking_policy: 'disabled', finish_reason: 'stop', error: null } },
    ])
    await screen.findByText(/Tides rise\./)
    const user = userEvent.setup()

    await user.type(screen.getByLabelText('Prompt'), 'and the moon?')
    await user.click(screen.getByRole('button', { name: 'Send' }))

    expect(
      screen.getByText(
        'Each prompt is answered on its own: the model does not see earlier exchanges.',
      ),
    ).toBeInTheDocument()
    expect(chat).toHaveBeenLastCalledWith(
      { prompt: 'and the moon?', thinking_policy: 'disabled' },
      expect.any(Function),
    )
  })

  it('shows a failed exchange with its error', async () => {
    await startAndAnswer([
      {
        final: {
          thinking_policy: 'disabled',
          finish_reason: null,
          error: 'llama-server answered 500',
        },
      },
    ])

    expect(await screen.findByText('llama-server answered 500')).toBeInTheDocument()
  })

  it('keeps the conversation in memory only: gone after a remount', async () => {
    const { view } = await startAndAnswer([
      { delta: 'Tides rise.' },
      { final: { thinking_policy: 'disabled', finish_reason: 'stop', error: null } },
    ])
    await screen.findByText(/Tides rise\./)
    const stored = JSON.stringify({ ...sessionStorage, ...localStorage })
    view.unmount()

    renderPanel()

    await screen.findByRole('button', { name: 'Start' })
    expect(screen.queryByText(/Tides rise\./)).not.toBeInTheDocument()
    expect(screen.queryByText(PROMPT)).not.toBeInTheDocument()
    expect(stored).not.toContain(PROMPT)
    expect(stored).not.toContain('Tides')
  })

  it('stops the loaded model', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(
      options({
        loaded: {
          roster_entry_id: 'qwen3-1.7b-q8',
          profile_id: 'qwen3-1.7b-q8@laptop-mobile-gpu/gpu',
        },
      }),
    )
    const stop = vi.spyOn(client, 'deleteJson').mockResolvedValue({ stopped: true })
    const user = userEvent.setup()

    renderPanel()
    await user.click(await screen.findByRole('button', { name: 'Stop' }))

    await waitFor(() => expect(stop).toHaveBeenCalledWith('/api/playground/session'))
    expect(screen.queryByText(/Loaded:/)).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start' })).toBeInTheDocument()
  })
})
