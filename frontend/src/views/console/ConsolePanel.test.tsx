import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../api/client'
import { setKey } from '../../api/keyStore'
import { KeyGate } from '../../components/KeyGate'
import { ConsolePanel } from './ConsolePanel'
import type { ConsoleFinal, ConsoleOptions, RunHolder, RunProfileOption } from './types'

// The two view components fetch their own run; the panel's job is only to
// hand them the announced run_id.
vi.mock('../runtime/RuntimeView', () => ({
  RuntimeView: ({ runId }: { runId: string }) => <p>runtime view of {runId}</p>,
}))
vi.mock('../quality/QualityView', () => ({
  QualityView: ({ runId }: { runId: string }) => <p>quality view of {runId}</p>,
}))

const HOLDER: RunHolder = {
  kind: 'quality',
  suite: 'translation',
  roster_entry_id: 'entry-a',
  profile_id: 'entry-a@laptop/gpu',
  started_at: '2026-09-24T10:00:00+00:00',
  run_id: 'abc123',
}

function profilesOf(entry: string): RunProfileOption[] {
  return ['cpu_only', 'gpu'].map((mode) => ({
    profile_id: `${entry}@laptop/${mode}`,
    machine_id: 'laptop',
    compute_mode: mode,
  }))
}

function options(holder: RunHolder | null = null): ConsoleOptions {
  return {
    kinds: ['runtime', 'quality'],
    suites: ['classification', 'translation'],
    roster_entries: ['entry-a', 'entry-b'],
    machine_id: 'laptop',
    machine_absence: null,
    profiles: { 'entry-a': profilesOf('entry-a'), 'entry-b': profilesOf('entry-b') },
    holder,
  }
}

function final(overrides: Partial<ConsoleFinal>): ConsoleFinal {
  return {
    ok: true,
    kind: 'runtime',
    profile_id: 'entry-a@laptop/cpu_only',
    run_id: 'run-1',
    exit_code: 0,
    error_line: null,
    view: {},
    missing: null,
    ...overrides,
  }
}

function renderPanel() {
  return render(
    <KeyGate>
      <ConsolePanel />
    </KeyGate>,
  )
}

describe('ConsolePanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('states that demo mode is off rather than showing a broken control', async () => {
    vi.spyOn(client, 'apiFetch').mockRejectedValue(
      new client.ApiError(403, '{"detail": "SERVICE_DEMO_MODE"}'),
    )

    renderPanel()

    expect(
      await screen.findByText('Demo mode is off on this machine.'),
    ).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /Start run/ })).not.toBeInTheDocument()
  })

  it('offers only selects bound to the declared sets, no free text', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    const user = userEvent.setup()

    const { container } = renderPanel()
    await screen.findByRole('button', { name: 'Start run' })
    await user.selectOptions(screen.getByLabelText(/kind/), 'quality')

    expect(container.querySelectorAll('input, textarea')).toHaveLength(0)
    const values = (label: RegExp) =>
      Array.from(
        (screen.getByLabelText(label) as HTMLSelectElement).options,
        (option) => option.value,
      )
    expect(values(/kind/)).toEqual(['runtime', 'quality'])
    expect(values(/suite/)).toEqual(['classification', 'translation'])
    expect(values(/roster entry/)).toEqual(['entry-a', 'entry-b'])
    expect(values(/run profile/)).toEqual([
      'entry-a@laptop/cpu_only',
      'entry-a@laptop/gpu',
    ])
  })

  it('names why no profile is offered and refuses to start', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue({
      ...options(),
      machine_id: null,
      machine_absence: 'MACHINE_ID is not set on the service',
      profiles: { 'entry-a': [], 'entry-b': [] },
    })

    renderPanel()

    expect(
      await screen.findByText(/MACHINE_ID is not set on the service/),
    ).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Start run' })).toBeDisabled()
  })

  it('disables the start and names the holder when a run is in progress', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options(HOLDER))

    renderPanel()

    const start = await screen.findByRole('button', { name: /Run in progress/ })
    expect(start).toBeDisabled()
    expect(start.textContent).toContain('quality translation under entry-a@laptop/gpu')
    expect(start.textContent).toContain('2026-09-24T10:00:00+00:00')
    expect(start.textContent).toContain('abc123')
  })

  it('re-enables the start once the holding run has ended', async () => {
    // The poll's answer is released only once the held state has been seen,
    // so the assertion order does not depend on timing.
    let releasePoll!: (value: ConsoleOptions) => void
    const poll = new Promise<ConsoleOptions>((resolve) => {
      releasePoll = resolve
    })
    const fetch = vi
      .spyOn(client, 'apiFetch')
      .mockResolvedValueOnce(options())
      .mockReturnValue(poll)
    vi.spyOn(client, 'postConsoleRun').mockRejectedValue(
      new client.ApiError(
        409,
        JSON.stringify({ detail: { message: 'a run is in progress', holder: HOLDER } }),
      ),
    )
    const user = userEvent.setup()

    render(
      <KeyGate>
        <ConsolePanel holderPollMs={20} />
      </KeyGate>,
    )
    await user.click(await screen.findByRole('button', { name: 'Start run' }))
    expect(
      await screen.findByRole('button', { name: /Run in progress/ }),
    ).toBeDisabled()
    await waitFor(() => expect(fetch.mock.calls.length).toBeGreaterThanOrEqual(2))

    releasePoll(options(null))

    expect(await screen.findByRole('button', { name: 'Start run' })).toBeEnabled()
  })

  it('names the holder when the service refuses a start with a 409', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    vi.spyOn(client, 'postConsoleRun').mockRejectedValue(
      new client.ApiError(
        409,
        JSON.stringify({ detail: { message: 'a run is in progress', holder: HOLDER } }),
      ),
    )
    const stream = vi.spyOn(client, 'streamConsoleRun')
    const user = userEvent.setup()

    renderPanel()
    await user.click(await screen.findByRole('button', { name: 'Start run' }))

    expect(
      await screen.findByRole('button', { name: /Run in progress/ }),
    ).toBeDisabled()
    expect(stream).not.toHaveBeenCalled()
  })

  it('streams lines, then renders the row through the existing view', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    const post = vi
      .spyOn(client, 'postConsoleRun')
      .mockResolvedValue({ launch_id: 'L1', profile_id: 'entry-a@laptop/cpu_only' })
    let emit!: (line: string) => void
    let finish!: (event: ConsoleFinal) => void
    let resolveStream!: () => void
    vi.spyOn(client, 'streamConsoleRun').mockImplementation(
      (_launchId, onLine, onFinal) =>
        new Promise<void>((resolve) => {
          emit = onLine
          finish = onFinal as (event: ConsoleFinal) => void
          resolveStream = resolve
        }),
    )
    const user = userEvent.setup()

    renderPanel()
    await user.selectOptions(await screen.findByLabelText(/roster entry/), 'entry-b')
    await user.selectOptions(screen.getByLabelText(/run profile/), 'entry-b@laptop/gpu')
    await user.click(screen.getByRole('button', { name: 'Start run' }))

    expect(post).toHaveBeenCalledWith({
      kind: 'runtime',
      roster_entry_id: 'entry-b',
      machine_id: 'laptop',
      compute_mode: 'gpu',
    })
    emit('run-1')
    expect(await screen.findByText('run-1')).toBeInTheDocument()
    expect(screen.queryByText('warming up')).not.toBeInTheDocument()
    emit('warming up')
    expect(await screen.findByText('warming up')).toBeInTheDocument()

    finish(final({}))
    resolveStream()

    expect(await screen.findByText('runtime view of run-1')).toBeInTheDocument()
  })

  it('shows the exit status and the error line of a failed run, no row', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    vi.spyOn(client, 'postConsoleRun').mockResolvedValue({
      launch_id: 'L1',
      profile_id: 'entry-a@laptop/cpu_only',
    })
    vi.spyOn(client, 'streamConsoleRun').mockImplementation(
      async (_launchId, onLine, onFinal) => {
        onLine('error: disk full')
        ;(onFinal as (event: ConsoleFinal) => void)(
          final({
            ok: false,
            exit_code: 3,
            error_line: 'error: disk full',
            view: null,
          }),
        )
      },
    )
    const user = userEvent.setup()

    renderPanel()
    await user.click(await screen.findByRole('button', { name: 'Start run' }))

    expect(await screen.findByText('Run failed: exit status 3')).toBeInTheDocument()
    expect(screen.getAllByText('error: disk full')).toHaveLength(2)
    expect(screen.queryByText(/runtime view of/)).not.toBeInTheDocument()
  })

  it('posts the chosen suite for a quality run', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValue(options())
    const post = vi.spyOn(client, 'postConsoleRun').mockResolvedValue({
      launch_id: 'L1',
      profile_id: 'entry-a@laptop/cpu_only',
    })
    vi.spyOn(client, 'streamConsoleRun').mockImplementation(
      async (_launchId, _onLine, onFinal) => {
        ;(onFinal as (event: ConsoleFinal) => void)(final({ kind: 'quality' }))
      },
    )
    const user = userEvent.setup()

    renderPanel()
    await user.selectOptions(await screen.findByLabelText(/kind/), 'quality')
    await user.selectOptions(screen.getByLabelText(/suite/), 'translation')
    await user.click(screen.getByRole('button', { name: 'Start run' }))

    expect(post).toHaveBeenCalledWith({
      kind: 'quality',
      suite: 'translation',
      roster_entry_id: 'entry-a',
      machine_id: 'laptop',
      compute_mode: 'cpu_only',
    })
    expect(await screen.findByText('quality view of run-1')).toBeInTheDocument()
  })
})
