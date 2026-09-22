import { useEffect, useState } from 'react'
import { apiFetch, UnauthorizedError } from '../../api/client'
import { isAbsent } from '../../api/types'
import { useKeyGate } from '../../components/KeyGate'
import { CoverageAbsence } from './CoverageAbsence'
import { OverviewCard } from './OverviewCard'
import type { OverviewQualityView } from './quality/types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: OverviewQualityView }
  | { status: 'unreachable'; message: string }

/**
 * The one file in the overview tree allowed to know both stores exist --
 * neither `the quality panel`, `the runtime-and-energy panel`, nor `the
 * card shell`, the three pieces the epic's boundary bullet names (see
 * plan.md's Decisions). It fetches `/api/overview/quality` once to build the
 * suite list, the per-suite leader `roster_entry_id`s (bare strings, not
 * typed quality entries) and the single coverage-absence banner, then hands
 * `OverviewCard` two primitives -- never a quality or runtime type.
 */
export function OverviewView() {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<OverviewQualityView>('/api/overview/quality')
      .then((view) => {
        if (!cancelled) {
          setState({ status: 'loaded', view })
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        if (error instanceof UnauthorizedError) {
          reportUnauthorized()
          return
        }
        const message = error instanceof Error ? error.message : String(error)
        setState({ status: 'unreachable', message })
      })

    return () => {
      cancelled = true
    }
  }, [reportUnauthorized])

  if (state.status === 'loading') {
    return <p>Loading overview…</p>
  }
  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  // An `Absent` task_suite is skipped, not rendered as a card with no name.
  const cards = state.view.use_cases
    .filter(
      (useCase): useCase is typeof useCase & { task_suite: string } =>
        !isAbsent(useCase.task_suite),
    )
    .map((useCase) => ({
      suite: useCase.task_suite,
      // `'unpublished'` (the leader set field is unowned) and `[]` (published,
      // but every row was excluded) are different facts -- collapsing them
      // would make the runtime panel say "no leader set published" for a
      // suite that published one with zero members.
      leaderRosterEntryIds: isAbsent(useCase.leader)
        ? ('unpublished' as const)
        : useCase.leader.members
            .map((entry) => entry.roster_entry_id)
            .filter((id): id is string => !isAbsent(id)),
    }))

  return (
    <div className="overview-view">
      <CoverageAbsence />
      <div className="overview-card-grid">
        {cards.map((card) => (
          <OverviewCard
            key={card.suite}
            suite={card.suite}
            leaderRosterEntryIds={card.leaderRosterEntryIds}
          />
        ))}
      </div>
    </div>
  )
}
