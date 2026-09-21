interface DeclaredAbsenceLabelProps {
  reason: string
  detail?: string
}

/**
 * The generic "this whole construct is not here" marker for a design-time
 * absence `components/Absent` cannot express -- nothing on the row names
 * this field as missing because the construct itself is not built yet
 * (a judged score, the coverage record, an energy headline withheld for
 * missing labels). Visibly distinct from `components/Absent`'s "not
 * reported (...)" text so a reader can tell the two apart.
 */
export function DeclaredAbsenceLabel({ reason, detail }: DeclaredAbsenceLabelProps) {
  return (
    <span className="declared-absence-label">
      not yet available: {reason}
      {detail !== undefined && <span className="declared-absence-detail"> ({detail})</span>}
    </span>
  )
}
