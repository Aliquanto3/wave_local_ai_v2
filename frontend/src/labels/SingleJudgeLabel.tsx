import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface SingleJudgeLabelProps {
  singleJudge: Maybe<boolean>
  reason: Maybe<string>
}

/** The single-judge (no second opinion) flag. */
export function SingleJudgeLabel({ singleJudge, reason }: SingleJudgeLabelProps) {
  if (isAbsent(singleJudge)) {
    return <Absent reason={singleJudge.reason} detail={singleJudge.detail} />
  }
  if (!singleJudge) {
    return null
  }
  if (isAbsent(reason)) {
    return <Absent reason={reason.reason} detail={reason.detail} />
  }

  return <span className="single-judge-label">single judge ({reason})</span>
}
