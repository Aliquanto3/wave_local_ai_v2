import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'
import type { FailureCounts } from './types'

interface FailureCountsCellProps {
  failureCounts: Maybe<FailureCounts>
}

const REASON_LABELS: Record<keyof FailureCounts, string> = {
  empty: 'empty',
  unparseable: 'unparseable',
  truncated_max_tokens: 'truncated (max tokens)',
  truncated_context: 'truncated (context)',
}

function renderCount(label: string, value: Maybe<number>) {
  if (isAbsent(value)) {
    return (
      <span key={label} className="failure-count">
        {label}: <Absent reason={value.reason} detail={value.detail} />
      </span>
    )
  }
  return (
    <span key={label} className="failure-count">
      {label}: {value}
    </span>
  )
}

/** The four failure-count reasons, individually labelled -- never summed. */
export function FailureCountsCell({ failureCounts }: FailureCountsCellProps) {
  if (isAbsent(failureCounts)) {
    return <Absent reason={failureCounts.reason} detail={failureCounts.detail} />
  }

  return (
    <span className="failure-counts-cell">
      {(Object.keys(REASON_LABELS) as (keyof FailureCounts)[]).map((key) =>
        renderCount(REASON_LABELS[key], failureCounts[key]),
      )}
    </span>
  )
}
