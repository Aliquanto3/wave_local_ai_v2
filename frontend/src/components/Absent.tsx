import type { Absent as AbsentShape } from '../api/types'

const REASON_LABELS: Record<string, string> = {
  predates_schema: 'predates this field',
  null_in_row: 'not captured on this row',
  pointer_unresolved: 'reference could not be resolved',
}

interface AbsentProps {
  reason: AbsentShape['reason']
  detail: AbsentShape['detail']
}

/**
 * The shared "not reported" marker every view routes an absent field
 * through, so a cell is never blank, a dash, `0`, or an em-dash with
 * nothing behind it -- it always names why the value is not there.
 */
export function Absent({ reason, detail }: AbsentProps) {
  const label = REASON_LABELS[reason] ?? reason
  const detailText = Object.entries(detail)
    .filter(([, value]) => value !== null && value !== undefined)
    .map(([key, value]) => `${key}: ${String(value)}`)
    .join(', ')

  return (
    <span className="absent" title={detailText === '' ? reason : detailText}>
      not reported ({label})
    </span>
  )
}
