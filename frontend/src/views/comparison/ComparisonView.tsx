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
  ComparisonSuite,
  ComparisonView as ComparisonViewShape,
} from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: ComparisonViewShape }
  | { status: 'unreachable'; message: string }

type ComparedCell = ComparisonCell & { status: 'compared' }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

// Accuracy to two places, a graded score to four -- the precision
// `aidd_docs/results/README.md` publishes each at, so the screen and the
// committed tables read the same figure.
function renderScore(
  value: Maybe<number> | undefined,
  shape: ComparedCell['score_shape'],
): ReactNode {
  if (value === undefined) {
    return null
  }
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return value.toFixed(shape === 'exact_match' ? 2 : 4)
}

interface Architecture {
  kind: string
  expert_count?: number | null
  active_params_b?: number | null
}

function isArchitecture(value: unknown): value is Architecture {
  return typeof value === 'object' && value !== null && 'kind' in value
}

// `architecture` reads as prose; any other dimension, including one added to
// `COMPARISON_DIMENSIONS` later, falls back to its raw value -- so a new
// dimension renders without a new branch here.
function describeDimension(dimension: string, value: unknown): string {
  if (dimension === 'architecture' && isArchitecture(value)) {
    const active = value.active_params_b ?? '?'
    if (value.kind === 'moe') {
      return `MoE, ${value.expert_count ?? '?'} experts, ${active}B active`
    }
    return `${value.kind}, ${active}B`
  }
  return typeof value === 'string' ? value : JSON.stringify(value)
}

function ColumnHeader({ column }: { column: ComparisonColumn }) {
  return (
    <th className="comparison-column-header">
      <span className="comparison-roster-entry-id">
        {renderMaybe(column.roster_entry_id)}
      </span>
      <span className="comparison-model">
        {renderMaybe(column.provider)} / {renderMaybe(column.model_id)}
      </span>
      {Object.entries(column.dimensions).map(([dimension, value]) => (
        <span
          key={dimension}
          className={`comparison-dimension comparison-dimension-${dimension}`}
        >
          {isAbsent(value) ? (
            <Absent reason={value.reason} detail={value.detail} />
          ) : (
            describeDimension(dimension, value)
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
        thinking {renderMaybe(column.thinking_policy)}
      </span>
      <span className="comparison-fiche">
        fiche{' '}
        {isAbsent(column.fiche_hash) ? (
          <Absent reason={column.fiche_hash.reason} detail={column.fiche_hash.detail} />
        ) : (
          <span title={column.fiche_hash}>{column.fiche_hash.slice(0, 12)}</span>
        )}
      </span>
      <span className="comparison-run-id">run {renderMaybe(column.run_id)}</span>
    </th>
  )
}

// The breakdown itself can be an absence (a row predating the field), not
// only one of its cells -- mirrors `QualityView.tsx`'s own
// `renderLanguageBreakdown`, restated per this module's boundary.
function renderLanguageBreakdown(cell: ComparedCell): ReactNode {
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
        {lang}{' '}
        {renderScore(
          'accuracy' in langCell ? langCell.accuracy : langCell.score,
          cell.score_shape,
        )}{' '}
        <IndicativeLabel indicative={langCell.indicative} reasons={[]} n={langCell.n} />
      </span>
    ),
  )
}

// The suite-level score and its language breakdown are the same on every
// row of one run, so they are read once per column, from its first compared
// cell, rather than repeated down the table.
function SuiteScoreCell({ cell }: { cell: ComparedCell | undefined }) {
  if (cell === undefined) {
    return <td className="comparison-not-compared">not compared</td>
  }
  const suiteScore =
    cell.score_shape === 'exact_match' ? cell.suite_accuracy : cell.suite_score
  return (
    <td className="comparison-suite-score">
      <strong>{renderScore(suiteScore, cell.score_shape)}</strong>
      {cell.score_shape === 'graded' && (
        <span className="comparison-metric"> {renderMaybe(cell.metric_id)}</span>
      )}
      {renderLanguageBreakdown(cell)}
    </td>
  )
}

function renderItemScore(cell: ComparedCell): ReactNode {
  if (cell.score_shape === 'graded') {
    return renderScore(cell.item_score, cell.score_shape)
  }
  if (cell.correct === undefined) {
    return null
  }
  if (isAbsent(cell.correct)) {
    return <Absent reason={cell.correct.reason} detail={cell.correct.detail} />
  }
  return cell.correct ? 'correct' : 'wrong'
}

function ItemCell({ cell }: { cell: ComparisonCell }) {
  if (cell.status === 'not_compared') {
    return <td className="comparison-not-compared">not compared</td>
  }
  return (
    <td className="comparison-cell">
      <span className="quality-score">{renderItemScore(cell)}</span>
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
    </td>
  )
}

function firstComparedCell(
  suite: ComparisonSuite,
  columnIndex: number,
): ComparedCell | undefined {
  for (const item of suite.items) {
    const cell = item.cells[columnIndex]
    if (cell.status === 'compared') {
      return cell
    }
  }
  return undefined
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

function ComparisonSuiteSection({ suite }: { suite: ComparisonSuite }) {
  const versions = distinctSuiteVersions(suite.columns)
  return (
    <section className="comparison-suite">
      <h2>Suite: {renderMaybe(suite.suite_id)}</h2>
      {versions.length > 1 && (
        <p className="comparison-version-caveat">
          columns at suite_version {versions.map((v) => `"${v}"`).join(', ')} -- not
          unified, shown as captured.
        </p>
      )}
      <div className="comparison-table-wrap">
        <table className="comparison-table">
          <thead>
            <tr>
              <th className="comparison-item-column">Item</th>
              {/* Keyed by position: two columns can share a roster_entry_id
                  (a cited comparator and its local subject). */}
              {suite.columns.map((column, index) => (
                <ColumnHeader key={index} column={column} />
              ))}
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Suite score</th>
              {suite.columns.map((_, index) => (
                <SuiteScoreCell key={index} cell={firstComparedCell(suite, index)} />
              ))}
            </tr>
            {suite.items.map((item, index) => (
              <tr key={index}>
                <td>{renderMaybe(item.item_id)}</td>
                {item.cells.map((cell, cellIndex) => (
                  <ItemCell key={cellIndex} cell={cell} />
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
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
