import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'

interface CapsCellProps {
  maxOutputTokens: Maybe<number>
  stopSequences: Maybe<string[]>
  contextLength: Maybe<number>
  thinkingPolicy: Maybe<string>
}

function renderMaybe(value: Maybe<unknown>) {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  if (Array.isArray(value)) {
    return value.length === 0 ? '(none)' : value.join(', ')
  }
  return String(value)
}

/**
 * The suite's own caps, beside the score they qualify. Methodology 3: a
 * `thinking_policy` of `disabled` means `max_output_tokens` is the routing
 * score's own ceiling, not the model's -- stated explicitly rather than left
 * for a reader to infer.
 */
export function CapsCell({
  maxOutputTokens,
  stopSequences,
  contextLength,
  thinkingPolicy,
}: CapsCellProps) {
  return (
    <span className="caps-cell">
      <span>max_output_tokens: {renderMaybe(maxOutputTokens)}</span>
      <span>stop_sequences: {renderMaybe(stopSequences)}</span>
      <span>context_length: {renderMaybe(contextLength)}</span>
      <span>thinking_policy: {renderMaybe(thinkingPolicy)}</span>
      {!isAbsent(thinkingPolicy) && thinkingPolicy === 'disabled' && (
        <span className="caps-cell-note">
          routing score, not the model's ceiling
        </span>
      )}
    </span>
  )
}
