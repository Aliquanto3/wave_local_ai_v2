import { useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../../api/client'
import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'
import { useKeyGate } from '../../components/KeyGate'
import { DeclaredAbsenceLabel } from '../../labels/DeclaredAbsenceLabel'
import { EnergyMethodLabel } from '../../labels/EnergyMethodLabel'
import { ScopeComparabilityLabel } from '../../labels/ScopeComparabilityLabel'
import { isWithheldHeadline } from './types'
import type {
  EnergyChannelName,
  EnergyEntry,
  EnergyView as EnergyViewShape,
} from './types'

type Store = 'runtime' | 'quality'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: EnergyViewShape }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

const CHANNELS: EnergyChannelName[] = ['cpu', 'gpu', 'ram']

function HeadlineBlock({ entry }: { entry: EnergyEntry }) {
  const { energy_headline: headline } = entry
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
        {renderMaybe(headline.energy_kwh)} kWh / {renderMaybe(headline.emissions_kg)} kg CO2e
      </span>
      {CHANNELS.map((channel) => (
        <EnergyMethodLabel key={channel} channel={channel} method={headline.methods[channel]} />
      ))}
    </div>
  )
}

function DrillDown({ entry }: { entry: EnergyEntry }) {
  return (
    <table className="energy-drilldown">
      <thead>
        <tr>
          <th>Channel</th>
          <th>Energy (kWh)</th>
          <th>Method</th>
        </tr>
      </thead>
      <tbody>
        {CHANNELS.map((channel) => (
          <tr key={channel}>
            <td>{channel}</td>
            <td>{renderMaybe(entry.channels[channel].energy_kwh)}</td>
            <td>
              <EnergyMethodLabel
                channel={channel}
                method={entry.channels[channel].energy_method}
              />
            </td>
          </tr>
        ))}
      </tbody>
      <tfoot>
        <tr>
          <td colSpan={3}>
            emission_factor_kg_per_kwh: {renderMaybe(entry.emission_factor_kg_per_kwh)} ·
            emission_region: {renderMaybe(entry.emission_region)} · emissions_scope:{' '}
            {renderMaybe(entry.emissions_scope)} · formula_id:{' '}
            {renderMaybe(entry.emissions_scope_formula_id)}
          </td>
        </tr>
        <tr>
          <td colSpan={3}>
            <ScopeComparabilityLabel text={entry.scope_comparability} />
          </td>
        </tr>
      </tfoot>
    </table>
  )
}

export function EnergyView({ runId }: { runId: string }) {
  const { reportUnauthorized } = useKeyGate()
  const [store, setStore] = useState<Store>('runtime')
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<EnergyViewShape>(`/api/runs/${runId}/energy?store=${store}`)
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
  }, [runId, store, reportUnauthorized])

  return (
    <div className="energy-view">
      <div className="energy-store-selector" role="group" aria-label="Store">
        <button
          type="button"
          aria-pressed={store === 'runtime'}
          disabled={store === 'runtime'}
          onClick={() => {
            setStore('runtime')
            setState({ status: 'loading' })
          }}
        >
          runtime
        </button>
        <button
          type="button"
          aria-pressed={store === 'quality'}
          disabled={store === 'quality'}
          onClick={() => {
            setStore('quality')
            setState({ status: 'loading' })
          }}
        >
          quality
        </button>
      </div>
      {state.status === 'loading' && <p>Loading energy…</p>}
      {state.status === 'unreachable' && (
        <p className="error-state">could not reach the service: {state.message}</p>
      )}
      {state.status === 'loaded' &&
        state.view.entries.map((entry, index) => (
          <section key={index} className="energy-entry">
            <HeadlineBlock entry={entry} />
            <DrillDown entry={entry} />
          </section>
        ))}
    </div>
  )
}
