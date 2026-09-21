import { useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../../api/client'
import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'
import { useKeyGate } from '../../components/KeyGate'
import { ContaminationRiskLabel } from '../../labels/ContaminationRiskLabel'
import { IndicativeLabel } from '../../labels/IndicativeLabel'
import { VerdictLabel } from '../../labels/VerdictLabel'
import type {
  ComparisonCell,
  ComparisonColumn,
  ComparisonView as ComparisonViewShape,
} from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: ComparisonViewShape }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

function renderScore(cell: ComparisonCell & { status: 'compared' }): ReactNode {
  if (cell.score_shape === 'exact_match') {
    return (
      <span className="quality-score">
        exact-match: {renderMaybe(cell.correct)} (suite{' '}
        {renderMaybe(cell.suite_accuracy)})
      </span>
    )
  }
  return (
    <span className="quality-score">
      graded ({renderMaybe(cell.metric_id)}): {renderMaybe(cell.item_score)} (suite{' '}
      {renderMaybe(cell.suite_score)})
    </span>
  )
}

// The breakdown itself can be an absence (a row predating the field), not
// only one of its cells -- mirrors `QualityView.tsx`'s own
// `renderLanguageBreakdown`, restated per this module's boundary.
function renderLanguageBreakdown(
  cell: ComparisonCell & { status: 'compared' },
): ReactNode {
  const breakdown =
    cell.score_shape === 'exact_match' ? cell.language_breakdown : cell.score_breakdown
  if (breakdown === undefined) {
    return null
  }
  if (isAbsent(breakdown)) {
    return <Absent reason={breakdown.reason} detail={breakdown.detail} />
  }
  return Object.entries(breakdown).map(([lang, langCell]) =>
    isAbsent(langCell) ? (
      <Absent key={lang} reason={langCell.reason} detail={langCell.detail} />
    ) : (
      <span key={lang} className="language-cell">
        {lang}:{' '}
        {renderMaybe('accuracy' in langCell ? langCell.accuracy : langCell.score)}{' '}
        <IndicativeLabel indicative={langCell.indicative} reasons={[]} n={langCell.n} />
      </span>
    ),
  )
}

function ComparisonCellView({ cell }: { cell: ComparisonCell }) {
  if (cell.status === 'not_compared') {
    return <span className="comparison-not-compared">not compared</span>
  }
  return (
    <div className="comparison-cell">
      {renderScore(cell)}
      {renderLanguageBreakdown(cell)}
      <ContaminationRiskLabel contaminationRisk={cell.contamination_risk} />
      {isAbsent(cell.verdict) ? (
        <Absent reason={cell.verdict.reason} detail={cell.verdict.detail} />
      ) : (
        <VerdictLabel
          verdict={cell.verdict.verdict}
          referenceRunId={cell.verdict.reference_run_id}
          differingFields={cell.verdict.differing_fields}
        />
      )}
    </div>
  )
}

function renderColumnHeader(column: ComparisonColumn): ReactNode {
  return (
    <th key={String(column.roster_entry_id)}>
      <div className="comparison-column-header">
        <span className="comparison-roster-entry-id">
          {renderMaybe(column.roster_entry_id)}
        </span>
        {Object.entries(column.dimensions).map(([dimension, value]) => (
          <span
            key={dimension}
            className={`comparison-dimension comparison-dimension-${dimension}`}
          >
            {isAbsent(value) ? (
              <Absent reason={value.reason} detail={value.detail} />
            ) : (
              JSON.stringify(value)
            )}
          </span>
        ))}
        <span className="comparison-quant">
          {isAbsent(column.roster_entry) ? (
            <Absent
              reason={column.roster_entry.reason}
              detail={column.roster_entry.detail}
            />
          ) : (
            column.roster_entry.quant
          )}
        </span>
        <span className="comparison-suite-version">
          suite_version {renderMaybe(column.suite_version)}
        </span>
        <span className="comparison-thinking-policy">
          {renderMaybe(column.thinking_policy)}
        </span>
      </div>
    </th>
  )
}

function distinctSuiteVersions(columns: ComparisonColumn[]): string[] {
  const versions = new Set<string>()
  for (const column of columns) {
    if (!isAbsent(column.suite_version)) {
      versions.add(String(column.suite_version))
    }
  }
  return [...versions].sort()
}

function ComparisonSuiteSection({
  suite,
}: {
  suite: ComparisonViewShape['suites'][number]
}) {
  const versions = distinctSuiteVersions(suite.columns)
  return (
    <section className="comparison-suite">
      <h2>Suite: {renderMaybe(suite.suite_id)}</h2>
      <table>
        <thead>
          <tr>
            <th>Item</th>
            {suite.columns.map(renderColumnHeader)}
          </tr>
        </thead>
        <tbody>
          {suite.items.map((item, index) => (
            <tr key={index}>
              <td>{renderMaybe(item.item_id)}</td>
              {item.cells.map((cell, cellIndex) => (
                <td key={cellIndex}>
                  <ComparisonCellView cell={cell} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {versions.length > 1 && (
        <p className="comparison-version-caveat">
          columns at suite_version {versions.map((v) => `"${v}"`).join(', ')} -- not
          unified, shown as captured.
        </p>
      )}
    </section>
  )
}

export function ComparisonView() {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<ComparisonViewShape>('/api/comparisons')
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
    return <p>Loading comparison…</p>
  }
  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  return (
    <div className="comparison-view">
      {state.view.suites.map((suite, index) => (
        <ComparisonSuiteSection key={index} suite={suite} />
      ))}
    </div>
  )
}
