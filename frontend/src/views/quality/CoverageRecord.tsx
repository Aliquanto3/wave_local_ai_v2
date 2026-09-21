import { DeclaredAbsenceLabel } from '../../labels/DeclaredAbsenceLabel'

/**
 * No store, route, or `read_model` field carries a coverage record today --
 * it is owned and built by a sibling epic (see plan.md's Decisions). A
 * static absence, wired to no API field, rather than fabricating an entry.
 */
export function CoverageRecord() {
  return (
    <section className="coverage-record">
      <DeclaredAbsenceLabel
        reason="no-use-case-is-silently-absent"
        detail="the coverage record is built by a sibling epic, not this one"
      />
    </section>
  )
}
