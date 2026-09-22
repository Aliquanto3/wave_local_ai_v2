import { render, screen, waitFor, within } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import * as client from '../../../api/client'
import { setKey } from '../../../api/keyStore'
import { KeyGate } from '../../../components/KeyGate'
import { overviewQualityFixture } from '../fixtures/overviewQuality.fixture'
import { QualityPanel } from './QualityPanel'

function renderWithGate(suite: string) {
  return render(
    <KeyGate>
      <QualityPanel suite={suite} />
    </KeyGate>,
  )
}

const CLASSIFICATION_USE_CASE = overviewQualityFixture.use_cases.find(
  (useCase) => useCase.task_suite === 'classification',
)!
const CLASSIFICATION_MEMBERS =
  'members' in CLASSIFICATION_USE_CASE.leader
    ? CLASSIFICATION_USE_CASE.leader.members
    : []
const [CLASSIFICATION_LEADER_ONE, CLASSIFICATION_LEADER_TWO] = CLASSIFICATION_MEMBERS
const [CLASSIFICATION_COMPARATOR] = CLASSIFICATION_USE_CASE.cloud_comparators

// Every numeric text node the panel renders must trace back to a number the
// fixture itself carries -- proving a figure not present in the fixture
// would fail this test rather than pass silently.
function assertEveryRenderedNumberIsInFixture(
  container: HTMLElement,
  useCase: unknown,
) {
  const fixtureText = JSON.stringify(useCase)
  const numbers = container.textContent?.match(/-?\d+(\.\d+)?/g) ?? []
  for (const number of numbers) {
    expect(fixtureText.includes(number), `${number} is not in the fixture`).toBe(true)
  }
}

describe('QualityPanel', () => {
  beforeEach(() => {
    sessionStorage.clear()
    setKey('a-key')
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('renders every leader member of a two-entry leader set, each with its own score', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('classification')

    await screen.findByText(/Cloud comparators/)
    expect(
      container.querySelectorAll('.overview-leader-members .overview-quality-entry'),
    ).toHaveLength(CLASSIFICATION_MEMBERS.length)
    expect(
      screen.getByText(String(CLASSIFICATION_LEADER_TWO.run_id)),
    ).toBeInTheDocument()
    expect(screen.getAllByText(/exact-match, suite accuracy:/)).toHaveLength(
      CLASSIFICATION_MEMBERS.length + CLASSIFICATION_USE_CASE.cloud_comparators.length,
    )
    expect(
      screen.getAllByText(
        new RegExp(`suite accuracy: ${CLASSIFICATION_LEADER_ONE.suite_accuracy}`),
      ),
    ).toHaveLength(
      CLASSIFICATION_MEMBERS.length + CLASSIFICATION_USE_CASE.cloud_comparators.length,
    )
    assertEveryRenderedNumberIsInFixture(container, CLASSIFICATION_USE_CASE)
  })

  it('renders the caps and thinking_policy for every entry', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    renderWithGate('classification')

    await screen.findByText(/Cloud comparators/)
    expect(
      screen.getAllByText(
        new RegExp(`max_output_tokens: ${CLASSIFICATION_LEADER_ONE.max_output_tokens}`),
      ),
    ).toHaveLength(CLASSIFICATION_MEMBERS.length + 1)
    expect(screen.getAllByText(/thinking_policy:/)).toHaveLength(
      CLASSIFICATION_MEMBERS.length + 1,
    )
  })

  it('renders the cloud comparator with its own run_id, not ranked against the leader', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('classification')

    await screen.findByText(/Cloud comparators/)
    const comparators = container.querySelectorAll(
      '.overview-cloud-comparators .overview-quality-entry',
    )
    expect(comparators).toHaveLength(1)
    expect(
      within(comparators[0] as HTMLElement).getByText(
        String(CLASSIFICATION_COMPARATOR.run_id),
      ),
    ).toBeInTheDocument()
  })

  it('renders DeclaredAbsenceLabel and no model when no leader set is published', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('translation')

    expect(
      await screen.findByText(
        /no leader set published for this suite and machine class/,
      ),
    ).toBeInTheDocument()
    expect(container.querySelectorAll('.overview-leader-members')).toHaveLength(0)
    // translation's cloud_comparators is [] -- a declared absence, not a
    // bare heading with nothing under it.
    expect(
      screen.getByText(/no cloud subject in the store for this suite/),
    ).toBeInTheDocument()
  })

  it('renders a distinct absence for a published leader set with no member', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('summarization')

    expect(
      await screen.findByText(/leader set published, no member/),
    ).toBeInTheDocument()
    // Never the "unowned field" wording -- a published-but-empty set is a
    // different fact from an unpublished one.
    expect(
      screen.queryByText(/no leader set published for this suite and machine class/),
    ).not.toBeInTheDocument()
    expect(container.querySelectorAll('.overview-leader-members')).toHaveLength(0)
  })

  it('renders nothing when the fetched view carries no use case for this suite', async () => {
    vi.spyOn(client, 'apiFetch').mockResolvedValueOnce(overviewQualityFixture)

    const { container } = renderWithGate('no-such-suite')
    await waitFor(() =>
      expect(screen.queryByText(/Loading quality/)).not.toBeInTheDocument(),
    )

    expect(container.querySelector('.overview-quality-panel')).toBeNull()
  })

  it('renders a named unreachable message on a rejected fetch', async () => {
    vi.spyOn(client, 'apiFetch').mockRejectedValueOnce(
      new client.NetworkError(new TypeError('down')),
    )

    renderWithGate('classification')

    expect(await screen.findByText(/could not reach the service/i)).toBeInTheDocument()
  })
})
