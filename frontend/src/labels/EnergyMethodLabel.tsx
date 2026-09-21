import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface EnergyMethodLabelProps {
  channel: 'cpu' | 'gpu' | 'ram'
  method: Maybe<string>
}

/**
 * Methodology 15's per-channel energy method label: never a shared
 * composite across channels, each channel keeps its own.
 */
export function EnergyMethodLabel({ channel, method }: EnergyMethodLabelProps) {
  if (isAbsent(method)) {
    return <Absent reason={method.reason} detail={method.detail} />
  }
  return (
    <span className="energy-method-label">
      {channel}: {method}
    </span>
  )
}
