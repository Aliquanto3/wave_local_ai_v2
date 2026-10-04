// Response shapes of the playground routes (`service.py`'s `/api/playground`).

import type { Holder } from '../console/types'

export interface LoadedModel {
  roster_entry_id: string
  profile_id: string
}

/** The cloud subject selected in place of a local model. */
export interface LoadedCloudSubject {
  provider: string
  model: string
}

/** What the playground holds: a local roster model or its cloud subject. */
export type LoadedSubject = LoadedModel | LoadedCloudSubject

/** The operator-configured cloud subject; `null` on the options when unset. */
export interface CloudSubjectOption {
  provider: string
  /** How the screen names the provider, e.g. `Mistral`. */
  label: string
  model: string
}

export interface PlaygroundOptions {
  roster_entries: string[]
  cloud_subject: CloudSubjectOption | null
  thinking_policies: string[]
  max_prompt_chars: number
  max_tokens: number
  loaded: LoadedSubject | null
  holder: Holder | null
}

/** The 409 body: who holds the one llama-server, or `null` with no model loaded. */
export interface PlaygroundOccupied {
  detail: { message: string; holder: Holder | null }
}

export interface PlaygroundFinal {
  thinking_policy: string
  finish_reason: string | null
  error: string | null
}

/** One NDJSON event of an exchange: answer text, reasoning text, or the end. */
export type PlaygroundEvent =
  { delta: string } | { reasoning: string } | { final: PlaygroundFinal }
