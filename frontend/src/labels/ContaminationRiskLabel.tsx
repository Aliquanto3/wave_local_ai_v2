import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface ContaminationRiskLabelProps {
  contaminationRisk: Maybe<boolean>
}

/** Methodology 4's contamination-risk mark: visible when true, silent when false. */
export function ContaminationRiskLabel({
  contaminationRisk,
}: ContaminationRiskLabelProps) {
  if (isAbsent(contaminationRisk)) {
    return <Absent reason={contaminationRisk.reason} detail={contaminationRisk.detail} />
  }
  if (!contaminationRisk) {
    return null
  }
  return <span className="contamination-risk-label">contamination risk</span>
}
