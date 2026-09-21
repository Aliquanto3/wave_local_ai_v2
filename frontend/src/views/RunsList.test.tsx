import { render, screen } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../api/client'
import { KeyGate } from '../components/KeyGate'
import { setKey } from '../api/keyStore'
import { EMPTY_RUNS_VIEW_FIXTURE, RUNS_VIEW_FIXTURE } from './fixtures/runsView.fixture'
import { RunsList } from './RunsList'

function renderWithGate(
  onSelectRun: (runId: string, kind: 'runtime' | 'quality') => void = () => {},
) {
  return render(
    <KeyGate>
      <RunsList onSelectRun={onSelectRun} />
    </KeyGate>,
  )
}

describe('RunsList', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders every real value from the fixture', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(RUNS_VIEW_FIXTURE)

    renderWithGate()

    expect(await screen.findByText('runtime-run-1')).toBeInTheDocument()
    expect(screen.getByText('quality-run-1')).toBeInTheDocument()
    expect(screen.getAllByText('Qwen3.6-35B-A3B').length).toBeGreaterThan(0)
    expect(screen.getByText(/classification-support-routing/)).toBeInTheDocument()
    expect(screen.getAllByText('1.2.3').length).toBeGreaterThan(0)
    expect(screen.getByText('deadbeef')).toBeInTheDocument()
  })

  it('renders an absent field via the shared component', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(RUNS_VIEW_FIXTURE)

    renderWithGate()

    expect(await screen.findAllByText(/not reported/i)).not.toHaveLength(0)
  })

  it('renders a visible dirty tag for a run with tree_dirty true', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(RUNS_VIEW_FIXTURE)

    renderWithGate()

    expect(await screen.findByText('dirty tree')).toBeInTheDocument()
  })

  it('renders a named empty state when both collections are empty', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(EMPTY_RUNS_VIEW_FIXTURE)

    renderWithGate()

    expect(await screen.findAllByText('no runs recorded')).toHaveLength(2)
  })

  it('calls onSelectRun with the run_id and its kind when a run row is clicked', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(RUNS_VIEW_FIXTURE)
    const onSelectRun = vi.fn()

    renderWithGate(onSelectRun)

    const cell = await screen.findByText('runtime-run-1')
    cell.closest('tr')?.dispatchEvent(new MouseEvent('click', { bubbles: true }))

    expect(onSelectRun).toHaveBeenCalledWith('runtime-run-1', 'runtime')
  })

  it('renders a named unreachable message on a rejected fetch', async () => {
    vi.spyOn(client, 'apiFetch').mockRejectedValueOnce(
      new client.NetworkError(new TypeError('down')),
    )

    renderWithGate()

    expect(await screen.findByText(/could not reach the service/i)).toBeInTheDocument()
  })
})
