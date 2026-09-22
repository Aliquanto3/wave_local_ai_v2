import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../../../api/client'
import type { Maybe } from '../../../api/types'
import { isAbsent } from '../../../api/types'
import { Absent } from '../../../components/Absent'
import { useKeyGate } from '../../../components/KeyGate'
import { DeclaredAbsenceLabel } from '../../../labels/DeclaredAbsenceLabel'
import { EnergyMethodLabel } from '../../../labels/EnergyMethodLabel'
import { isWithheldHeadline } from './types'
import type { EnergyChannelName, EnergyHeadline, OverviewRuntimeView } from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: OverviewRuntimeView }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

const CHANNELS: EnergyChannelName[] = ['cpu', 'gpu', 'ram']

function renderMachine(machine: Maybe<Record<string, unknown>>): ReactNode {
  if (isAbsent(machine)) {
    return <Absent reason={machine.reason} detail={machine.detail} />
  }
  const gpuName = machine.gpu_name
  return (
    <span className="overview-machine">
      {typeof gpuName === 'string' ? (
        gpuName
      ) : (
        <DeclaredAbsenceLabel reason="cpu-only fiche" detail="no gpu_name on this machine" />
      )}
    </span>
  )
}

// Mirrors `EnergyView.tsx`'s own `HeadlineBlock` for the same reason
// `overview/runtime/types.ts` mirrors `views/energy/types.ts`: this module
// imports no view directory other than `labels/`.
function EnergyHeadlineBlock({ headline }: { headline: EnergyHeadline }) {
  if (isWithheldHeadline(headline)) {
    return (
      <div className="energy-headline energy-headline-withheld">
        {headline.missing_labels.map((missing) => (
          <DeclaredAbsenceLabel
            key={missing.field}
            reason="energy-headline-withheld"
            detail={`missing ${missing.field}`}
          />
        ))}
      </div>
    )
  }

  return (
    <div className="energy-headline">
      <span className="energy-headline-figures">
        {renderMaybe(headline.energy_kwh)} kWh / {renderMaybe(headline.emissions_kg)} kg
        CO2e
      </span>
      {CHANNELS.map((channel) => (
        <Fragment key={channel}>
          {' · '}
          <EnergyMethodLabel channel={channel} method={headline.methods[channel]} />
        </Fragment>
      ))}
    </div>
  )
}

export function RuntimeEnergyPanel({
  leaderRosterEntryIds,
}: {
  leaderRosterEntryIds: string[] | 'unpublished'
}) {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<OverviewRuntimeView>('/api/overview/runtime')
      .then((view) => {
        if (!cancelled) {
          setState({ status: 'loaded', view })
        }
      })
      .catch((error: unknown) => {
        if (cancelled) {
          return
        }
        if (error instanceof UnauthorizedError) {
          reportUnauthorized()
          return
        }
        const message = error instanceof Error ? error.message : String(error)
        setState({ status: 'unreachable', message })
      })

    return () => {
      cancelled = true
    }
  }, [reportUnauthorized])

  if (state.status === 'loading') {
    return <p>Loading runtime…</p>
  }
  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  if (leaderRosterEntryIds === 'unpublished') {
    return (
      <section className="overview-runtime-panel">
        <DeclaredAbsenceLabel
          reason="no model to take a headline from"
          detail="no leader set published for this suite and machine class"
        />
      </section>
    )
  }

  if (leaderRosterEntryIds.length === 0) {
    return (
      <section className="overview-runtime-panel">
        <DeclaredAbsenceLabel
          reason="no model to take a headline from"
          detail="leader set published, no member"
        />
      </section>
    )
  }

  return (
    <section className="overview-runtime-panel">
      {leaderRosterEntryIds.map((id) => {
        const entry = state.view.entries.find(
          (candidate) => String(candidate.roster_entry_id) === id,
        )
        if (entry === undefined) {
          return (
            <DeclaredAbsenceLabel
              key={id}
              reason="no runtime row for this leader"
              detail={id}
            />
          )
        }
        return (
          <div key={id} className="overview-runtime-entry">
            <span className="overview-runtime-headline">
              {renderMaybe(entry.runtime_headline.median_gen_tok_per_s)} tok/s ·{' '}
              {renderMachine(entry.runtime_headline.machine)} · run{' '}
              {renderMaybe(entry.runtime_headline.run_id)} · fiche{' '}
              {renderMaybe(entry.runtime_headline.fiche_hash)}
            </span>
            <EnergyHeadlineBlock headline={entry.energy_headline} />
          </div>
        )
      })}
    </section>
  )
}
