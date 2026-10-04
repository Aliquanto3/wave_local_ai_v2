/** The PRD's exact playground label, character for character. */
export const PLAYGROUND_LABEL_TEXT = 'playground — nothing here is a benchmark row'

/**
 * The one label every playground screen carries, in every state, so an
 * exchange on screen is never read as a benchmark result.
 */
export function PlaygroundLabel() {
  return (
    <p className="playground-label" role="note">
      {PLAYGROUND_LABEL_TEXT}
    </p>
  )
}
