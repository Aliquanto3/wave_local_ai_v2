import { QualityPanel } from './quality/QualityPanel'
import { RuntimeEnergyPanel } from './runtime/RuntimeEnergyPanel'

/**
 * The card shell: the one file allowed to know both `overview/quality` and
 * `overview/runtime` exist, and only through their components -- never their
 * type modules. Props are primitives only (`suite: string`,
 * `leaderRosterEntryIds: string[]`), never a quality or runtime type, so the
 * boundary the two panels keep is not defeated one level up (see
 * `views/boundary.test.ts`).
 */
export function OverviewCard({
  suite,
  leaderRosterEntryIds,
}: {
  suite: string
  leaderRosterEntryIds: string[]
}) {
  return (
    <article className="overview-card">
      <h2>{suite}</h2>
      <QualityPanel suite={suite} />
      <RuntimeEnergyPanel leaderRosterEntryIds={leaderRosterEntryIds} />
    </article>
  )
}
