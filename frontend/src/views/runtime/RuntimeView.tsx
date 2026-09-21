import { useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../../api/client'
import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'
import { useKeyGate } from '../../components/KeyGate'
import { UnreliableLabel } from '../../labels/UnreliableLabel'
import { VerdictLabel } from '../../labels/VerdictLabel'
import { TtftCell } from './TtftCell'
import type { RuntimeEntry, RuntimeView as RuntimeViewShape } from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: RuntimeViewShape }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

/** `bytes` in decimal MB -- never sharing a unit label with `vram_used_mib`. */
function formatMB(bytes: number): string {
  return `${(bytes / 1_000_000).toFixed(1)} MB`
}

function formatMiB(mib: number): string {
  return `${mib.toFixed(1)} MiB`
}

function FicheBlock({ fiche }: { fiche: Maybe<Record<string, unknown>> }) {
  if (isAbsent(fiche)) {
    return <Absent reason={fiche.reason} detail={fiche.detail} />
  }
  const flags = fiche.flags
  return (
    <dl className="fiche-block">
      <dt>CPU</dt>
      <dd>{String(fiche.cpu)}</dd>
      <dt>RAM</dt>
      <dd>{String(fiche.ram_gb)} GB</dd>
      <dt>GPU</dt>
      <dd>{String(fiche.gpu_name)}</dd>
      <dt>GPU driver</dt>
      <dd>{String(fiche.gpu_driver_version)}</dd>
      <dt>llama.cpp build</dt>
      <dd>{String(fiche.llama_cpp_build)}</dd>
      <dt>Quant</dt>
      <dd>{String(fiche.quant)}</dd>
      <dt>Flags</dt>
      <dd>{Array.isArray(flags) ? flags.join(' ') : String(flags)}</dd>
      <dt>fiche_hash</dt>
      <dd>{String(fiche.roster_entry_id)}</dd>
    </dl>
  )
}

function RuntimeRow({ entry }: { entry: RuntimeEntry }) {
  return (
    <tr>
      <td>
        {isAbsent(entry.roster_entry) ? (
          <Absent reason={entry.roster_entry.reason} detail={entry.roster_entry.detail} />
        ) : (
          entry.roster_entry.display_id
        )}
      </td>
      <td>
        <TtftCell ttftMs={entry.ttft_ms} ttftSource={entry.ttft_source} />
      </td>
      <td>
        {renderMaybe(entry.prompt_tok_per_s)}
        {!isAbsent(entry.unreliable) && entry.unreliable && (
          <UnreliableLabel
            unreliable={entry.unreliable}
            spread={entry.prompt_tok_per_s_spread}
            metric="prompt_tok_per_s"
          />
        )}
      </td>
      <td>
        {renderMaybe(entry.gen_tok_per_s)}
        {!isAbsent(entry.unreliable) && entry.unreliable && (
          <UnreliableLabel
            unreliable={entry.unreliable}
            spread={entry.gen_tok_per_s_spread}
            metric="gen_tok_per_s"
          />
        )}
      </td>
      <td>
        {isAbsent(entry.process_rss_bytes)
          ? renderMaybe(entry.process_rss_bytes)
          : formatMB(entry.process_rss_bytes)}
      </td>
      <td>
        {isAbsent(entry.vram_used_mib)
          ? renderMaybe(entry.vram_used_mib)
          : formatMiB(entry.vram_used_mib)}
      </td>
      <td>{renderMaybe(entry.wall_clock_s)}</td>
      <td>
        {isAbsent(entry.verdict) ? (
          <Absent reason={entry.verdict.reason} detail={entry.verdict.detail} />
        ) : (
          <VerdictLabel
            verdict={entry.verdict.verdict}
            referenceRunId={entry.verdict.reference_run_id}
            differingFields={entry.verdict.differing_fields}
          />
        )}
      </td>
      <td>
        <FicheBlock fiche={entry.fiche} />
      </td>
    </tr>
  )
}

export function RuntimeView({ runId }: { runId: string }) {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<RuntimeViewShape>(`/api/runs/${runId}/runtime`)
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
  }, [runId, reportUnauthorized])

  if (state.status === 'loading') {
    return <p>Loading runtime…</p>
  }
  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  return (
    <div className="runtime-view">
      <table>
        <thead>
          <tr>
            <th>Model</th>
            <th>TTFT</th>
            <th>Prompt tok/s</th>
            <th>Gen tok/s</th>
            <th>RSS</th>
            <th>VRAM</th>
            <th>Wall clock (s)</th>
            <th>Verdict</th>
            <th>Fiche</th>
          </tr>
        </thead>
        <tbody>
          {state.view.entries.map((entry, index) => (
            <RuntimeRow key={index} entry={entry} />
          ))}
        </tbody>
      </table>
    </div>
  )
}
