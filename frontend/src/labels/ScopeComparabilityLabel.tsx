import type { Maybe } from '../api/types'
import { isAbsent } from '../api/types'
import { Absent } from '../components/Absent'

interface ScopeComparabilityLabelProps {
  text: Maybe<string>
}

/**
 * Methodology 15's scope-comparability caveat, rendered inline in the DOM
 * text -- never in a `title` attribute or a footnote-style aside.
 */
export function ScopeComparabilityLabel({ text }: ScopeComparabilityLabelProps) {
  if (isAbsent(text)) {
    return <Absent reason={text.reason} detail={text.detail} />
  }
  return <span className="scope-comparability-label">{text}</span>
}
