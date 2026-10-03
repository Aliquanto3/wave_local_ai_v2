import type { Holder } from './types'

/** Who holds the console, in one line, whichever session it is. */
export function describeHolder(holder: Holder): string {
  if (holder.session === 'playground') {
    return `Playground in use: ${holder.roster_entry_id} under ${holder.profile_id}, started ${holder.started_at}`
  }
  const suite = holder.suite === null ? '' : ` ${holder.suite}`
  const runId = holder.run_id ?? 'run_id not yet announced'
  return `Run in progress: ${holder.kind}${suite} under ${holder.profile_id}, started ${holder.started_at} (${runId})`
}
