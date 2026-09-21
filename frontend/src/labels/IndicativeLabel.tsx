import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface IndicativeLabelProps {
  indicative: Maybe<boolean>
  reasons: Maybe<string[]>
  n?: Maybe<number>
}

/**
 * Methodology 4's indicative mark, shared by a suite-level score and a
 * per-language cell (which additionally carries the cell's own `n`).
 */
export function IndicativeLabel({ indicative, reasons, n }: IndicativeLabelProps) {
  if (isAbsent(indicative)) {
    return <Absent reason={indicative.reason} detail={indicative.detail} />
  }
  if (!indicative) {
    return null
  }
  if (isAbsent(reasons)) {
    return <Absent reason={reasons.reason} detail={reasons.detail} />
  }

  return (
    <span className="indicative-label">
      indicative ({reasons.join(', ')})
      {n !== undefined && !isAbsent(n) && <span className="indicative-n"> n={n}</span>}
    </span>
  )
}
