import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'

interface TtftCellProps {
  ttftMs: Maybe<number>
  ttftSource: Maybe<string>
}

/**
 * `ttft_ms` beside `ttft_source` as plain text -- a screen-local pair, not a
 * `labels/` component, since it appears on exactly one screen (see plan.md's
 * Decisions).
 */
export function TtftCell({ ttftMs, ttftSource }: TtftCellProps) {
  if (isAbsent(ttftMs)) {
    return <Absent reason={ttftMs.reason} detail={ttftMs.detail} />
  }
  if (isAbsent(ttftSource)) {
    return <Absent reason={ttftSource.reason} detail={ttftSource.detail} />
  }

  return (
    <span className="ttft-cell">
      {ttftMs} ms ({ttftSource})
    </span>
  )
}
