import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface ContestedLabelProps {
  contested: Maybe<boolean>
  reason: Maybe<string>
  threshold: Maybe<number>
}

/**
 * The judge-contested mark. `reason` and `threshold` are resolved
 * independently of `contested` itself: an unjudged row can carry a
 * non-`Absent` `contested: false` beside an `Absent` `threshold`.
 */
export function ContestedLabel({ contested, reason, threshold }: ContestedLabelProps) {
  if (isAbsent(contested)) {
    return <Absent reason={contested.reason} detail={contested.detail} />
  }
  if (!contested) {
    return null
  }
  if (isAbsent(reason)) {
    return <Absent reason={reason.reason} detail={reason.detail} />
  }
  if (isAbsent(threshold)) {
    return <Absent reason={threshold.reason} detail={threshold.detail} />
  }

  return (
    <span className="contested-label">
      contested ({reason}, threshold {threshold})
    </span>
  )
}
