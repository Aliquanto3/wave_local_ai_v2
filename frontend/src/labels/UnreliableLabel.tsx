import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface UnreliableLabelProps {
  unreliable: Maybe<boolean>
  spread: Maybe<number>
  metric: string
}

/**
 * Methodology 7's unreliable flag. This component owns only the flag: the
 * bare spread number is shown by the caller independently of this flag, so
 * the flag and the number stay visibly distinct.
 */
export function UnreliableLabel({ unreliable, spread, metric }: UnreliableLabelProps) {
  if (isAbsent(unreliable)) {
    return <Absent reason={unreliable.reason} detail={unreliable.detail} />
  }
  if (!unreliable) {
    return null
  }
  if (isAbsent(spread)) {
    return <Absent reason={spread.reason} detail={spread.detail} />
  }

  return (
    <span className="unreliable-label">
      unreliable ({metric} spread {spread})
    </span>
  )
}
