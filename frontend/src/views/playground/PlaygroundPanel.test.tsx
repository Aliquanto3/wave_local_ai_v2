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
    cloud_subject: null,
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

describe('PlaygroundPanel cloud subject', () => {
  const MISTRAL = { provider: 'mistral', label: 'Mistral', model: 'mistral-small-2603' }
  const CLOUD_SEND = 'Send to Mistral: the text leaves this machine'
  const answered: PlaygroundEvent[] = [
    { delta: 'Tides follow the moon.' },
    { final: { thinking_policy: 'not_sent', finish_reason: 'stop', error: null } },
  ]

  beforeEach(() => {
    sessionStorage.clear()
    localStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('is absent from the selector while unconfigured', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())

    renderPanel()

    await screen.findByRole('button', { name: 'Start' })
    expect(screen.queryByRole('option', { name: /cloud/ })).not.toBeInTheDocument()
    expect(screen.queryByText(/leaves this machine/)).not.toBeInTheDocument()
  })

  it('sits in the same selector under the same label, and starts by provider', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options({ cloud_subject: MISTRAL }))
    const start = vi
      .spyOn(client, 'postJson')
      .mockResolvedValue({ provider: 'mistral', model: 'mistral-small-2603' })
    const user = userEvent.setup()

    renderPanel()
    await user.selectOptions(
      await screen.findByLabelText(/Model/),
      'Mistral mistral-small-2603 (cloud)',
    )
    await user.click(screen.getByRole('button', { name: 'Start' }))

    expect(start).toHaveBeenCalledWith('/api/playground/session', {
      cloud_subject: 'mistral',
    })
    expect(
      await screen.findByText(/Selected: Mistral mistral-small-2603 \(cloud\)/),
    ).toBeInTheDocument()
    expect(label()).toBeInTheDocument()
  })

  it('names the provider on the send control before every send', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(
      options({
        cloud_subject: MISTRAL,
        loaded: { provider: 'mistral', model: 'mistral-small-2603' },
      }),
    )
    const chat = vi
      .spyOn(client, 'streamPlaygroundChat')
      .mockImplementation(async (_body, onEvent) => {
        answered.forEach((event) => (onEvent as (e: PlaygroundEvent) => void)(event))
      })
    const user = userEvent.setup()

    renderPanel()
    for (const sent of [1, 2]) {
      await user.type(await screen.findByLabelText('Prompt'), `${PROMPT} ${sent}`)
      const send = await screen.findByRole('button', { name: CLOUD_SEND })
      expect(send).toBeEnabled()
      await user.click(send)
      await waitFor(() => expect(chat).toHaveBeenCalledTimes(sent))
    }

    expect(await screen.findAllByText(/Tides follow the moon\./)).toHaveLength(2)
    expect(screen.getByRole('button', { name: CLOUD_SEND })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Send' })).not.toBeInTheDocument()
  })

  it('carries no statement on the send control for a local subject', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(
      options({
        cloud_subject: MISTRAL,
        loaded: {
          roster_entry_id: 'qwen3-0.6b-q8',
          profile_id: 'qwen3-0.6b-q8@laptop-mobile-gpu/gpu',
        },
      }),
    )

    renderPanel()

    expect(await screen.findByRole('button', { name: 'Send' })).toBeInTheDocument()
    expect(screen.queryByText(/leaves this machine/)).not.toBeInTheDocument()
    expect(screen.getByLabelText(/Thinking/)).toBeEnabled()
  })

  it('disables the thinking policy while the cloud subject is selected', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(
      options({
        cloud_subject: MISTRAL,
        loaded: { provider: 'mistral', model: 'mistral-small-2603' },
      }),
    )

    renderPanel()

    await screen.findByRole('button', { name: CLOUD_SEND })
    expect(screen.getByLabelText(/Thinking/)).toBeDisabled()
    expect(screen.getByText(/no thinking control/)).toBeInTheDocument()
  })

  it('shows a provider refusal as an error, never as an empty answer', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(
      options({
        cloud_subject: MISTRAL,
        loaded: { provider: 'mistral', model: 'mistral-small-2603' },
      }),
    )
    const refusal =
      'refused by Mistral: it answered 429 (rate limit or provider failure) through 4 retries'
    vi.spyOn(client, 'streamPlaygroundChat').mockImplementation(
      async (_body, onEvent) => {
        ;(onEvent as (e: PlaygroundEvent) => void)({
          final: { thinking_policy: 'not_sent', finish_reason: null, error: refusal },
        })
      },
    )
    const user = userEvent.setup()

    renderPanel()
    await user.type(await screen.findByLabelText('Prompt'), PROMPT)
    await user.click(screen.getByRole('button', { name: CLOUD_SEND }))

    expect(await screen.findByText(refusal)).toBeInTheDocument()
  })

  it('names a cloud holder in a refusal', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    vi.spyOn(client, 'postJson').mockRejectedValue(
      new client.ApiError(
        409,
        JSON.stringify({
          detail: {
            message: 'the playground holds its mistral cloud subject',
            holder: {
              session: 'playground',
              provider: 'mistral',
              model: 'mistral-small-2603',
              started_at: '2026-10-02T22:00:00+00:00',
            },
          },
        }),
      ),
    )
    const user = userEvent.setup()

    renderPanel()
    await user.click(await screen.findByRole('button', { name: 'Start' }))

    expect(
      await screen.findByText(/the mistral cloud subject mistral-small-2603/),
    ).toBeInTheDocument()
  })
})
