import type { Absent as AbsentShape } from '../api/types'

const REASON_LABELS: Record<string, string> = {
  predates_schema: 'predates this field',
  null_in_row: 'not captured on this row',
  pointer_unresolved: 'reference could not be resolved',
}

// A reason that is a statement, not a missing value: a `cpu_only` row has no
// VRAM figure. Rendered as its own text so it never reads as "not reported".
const NOT_APPLICABLE = 'not_applicable'

interface AbsentProps {
  reason: AbsentShape['reason']
  detail: AbsentShape['detail']
}

/**
 * The shared "not reported" marker every view routes an absent field
 * through, so a cell is never blank, a dash, `0`, or an em-dash with
 * nothing behind it -- it always names why the value is not there. A
 * `not_applicable` absence reads "not applicable" instead: the row states
 * the field does not apply, which is not a value that went unreported.
 */
export function Absent({ reason, detail }: AbsentProps) {
  const label = REASON_LABELS[reason] ?? reason
  const detailText = Object.entries(detail)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(', ')

  const title = detailText === '' ? reason : detailText

  if (reason === NOT_APPLICABLE) {
    return (
      <span className="absent not-applicable" title={title}>
        not applicable
      </span>
    )
  }
  return (
    <span className="absent" title={title}>
      not reported ({label})
    </span>
  )
}
