import { DeclaredAbsenceLabel } from '../../labels/DeclaredAbsenceLabel'

/**
 * No store, route, or `read_model` field carries a coverage record today --
 * it is owned and built by a sibling epic (see plan.md's Decisions).
 * Structurally identical to `views/quality/CoverageRecord.tsx` but a
 * separate file, not a shared import: this one renders once at the overview
 * page level, not once per run.
 */
export function CoverageAbsence() {
  return (
    <section className="coverage-absence">
      <DeclaredAbsenceLabel
        reason="no-use-case-is-silently-absent"
        detail="the coverage record is built by a sibling epic, not this one"
      />
    </section>
  )
}
