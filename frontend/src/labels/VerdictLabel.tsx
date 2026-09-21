import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

// Mirrors verdict.VERDICT_REPRODUCED / VERDICT_NOT_REPRODUCED /
// VERDICT_NOT_COMPARABLE as string literals: the frontend has no Python
// import, so the three values are restated here rather than inferred.
const VERDICT_REPRODUCED = 'reproduced'
const VERDICT_NOT_REPRODUCED = 'not_reproduced'
const VERDICT_NOT_COMPARABLE = 'not_comparable'

interface VerdictLabelProps {
  verdict: Maybe<string>
  referenceRunId?: Maybe<string> | null
  differingFields?: Maybe<string[]>
}

function renderReferenceRunId(referenceRunId: VerdictLabelProps['referenceRunId']) {
  if (referenceRunId === undefined) {
    return null
  }
  if (isAbsent(referenceRunId)) {
    return <Absent reason={referenceRunId.reason} detail={referenceRunId.detail} />
  }
  if (referenceRunId === null) {
    return null
  }
  return <span className="verdict-reference-run"> vs {referenceRunId}</span>
}

function renderDifferingFields(differingFields: VerdictLabelProps['differingFields']) {
  if (differingFields === undefined) {
    return null
  }
  if (isAbsent(differingFields)) {
    return <Absent reason={differingFields.reason} detail={differingFields.detail} />
  }
  if (differingFields.length === 0) {
    return null
  }
  return (
    <span className="verdict-differing-fields"> differing: {differingFields.join(', ')}</span>
  )
}

/** The reproducibility verdict, one of three visibly distinct renders. */
export function VerdictLabel({
  verdict,
  referenceRunId,
  differingFields,
}: VerdictLabelProps) {
  if (isAbsent(verdict)) {
    return <Absent reason={verdict.reason} detail={verdict.detail} />
  }

  if (verdict === VERDICT_NOT_COMPARABLE) {
    return (
      <span className="verdict-label verdict-not-comparable">
        not comparable
        {renderDifferingFields(differingFields)}
      </span>
    )
  }

  if (verdict === VERDICT_REPRODUCED) {
    return (
      <span className="verdict-label verdict-reproduced">
        reproduced
        {renderReferenceRunId(referenceRunId)}
      </span>
    )
  }

  if (verdict === VERDICT_NOT_REPRODUCED) {
    return (
      <span className="verdict-label verdict-not-reproduced">
        not reproduced
        {renderReferenceRunId(referenceRunId)}
      </span>
    )
  }

  // An unrecognised string is not thrown on: Maybe<string> comes from JSON,
  // not a closed union, so the raw value renders as-is.
  return <span className="verdict-label verdict-unrecognised">{verdict}</span>
}
