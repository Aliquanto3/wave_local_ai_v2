import { useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../../api/client'
import type { Maybe } from '../../api/types'
import { isAbsent } from '../../api/types'
import { Absent } from '../../components/Absent'
import { useKeyGate } from '../../components/KeyGate'
import { ContaminationRiskLabel } from '../../labels/ContaminationRiskLabel'
import { ContestedLabel } from '../../labels/ContestedLabel'
import { DeclaredAbsenceLabel } from '../../labels/DeclaredAbsenceLabel'
import { IndicativeLabel } from '../../labels/IndicativeLabel'
import { SingleJudgeLabel } from '../../labels/SingleJudgeLabel'
import { VerdictLabel } from '../../labels/VerdictLabel'
import { CapsCell } from './CapsCell'
import { CoverageRecord } from './CoverageRecord'
import { FailureCountsCell } from './FailureCountsCell'
import type { QualityEntry, QualityView as QualityViewShape } from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: QualityViewShape }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

function renderScore(entry: QualityEntry): ReactNode {
  if (entry.score_shape === 'exact_match') {
    return (
      <span className="quality-score">
        exact-match: {renderMaybe(entry.correct)} (suite{' '}
        {renderMaybe(entry.suite_accuracy)})
      </span>
    )
  }
  return (
    <span className="quality-score">
      graded ({renderMaybe(entry.metric_id)}): {renderMaybe(entry.item_score)} (suite{' '}
      {renderMaybe(entry.suite_score)})
    </span>
  )
}

// Methodology 11: the judge block's own `judged_headline_score` -- distinct
// from the row's own exact-match/graded score, which always renders (see
// `renderScore`). A judged score renders only with two judges and an
// agreement figure, or with the single-judge flag visible; a row carrying
// neither is a declared absence, never a plain score.
function renderJudgeBlock(entry: QualityEntry): ReactNode {
  const { judge } = entry
  const singleJudge = judge.single_judge
  const agreement = judge.agreement

  const hasAgreement = !isAbsent(agreement)
  const isSingleJudge = !isAbsent(singleJudge) && singleJudge === true

  if (!hasAgreement && !isSingleJudge) {
    return (
      <DeclaredAbsenceLabel
        reason="judged-score-withheld"
        detail="no judge row backs this item"
      />
    )
  }

  return (
    <span className="quality-judge-block">
      <span className="judged-headline-score">
        judged score: {renderMaybe(judge.judged_headline_score)}
      </span>
      {isSingleJudge && (
        <SingleJudgeLabel
          singleJudge={singleJudge}
          reason={judge.single_judge_reason}
        />
      )}
      {hasAgreement && (
        <span className="agreement-figure">agreement: {String(agreement)}</span>
      )}
    </span>
  )
}

// The breakdown itself can be an absence (a row predating the field), not
// only one of its cells.
function renderLanguageBreakdown(entry: QualityEntry): ReactNode {
  const breakdown =
    entry.score_shape === 'exact_match'
      ? entry.language_breakdown
      : entry.score_breakdown
  if (breakdown === undefined) {
    return null
  }
  if (isAbsent(breakdown)) {
    return <Absent reason={breakdown.reason} detail={breakdown.detail} />
  }
  return Object.entries(breakdown).map(([lang, cell]) =>
    isAbsent(cell) ? (
      <Absent key={lang} reason={cell.reason} detail={cell.detail} />
    ) : (
      <span key={lang} className="language-cell">
        {lang}: {renderMaybe('accuracy' in cell ? cell.accuracy : cell.score)}{' '}
        <IndicativeLabel indicative={cell.indicative} reasons={[]} n={cell.n} />
      </span>
    ),
  )
}

function QualityRow({ entry }: { entry: QualityEntry }) {
  return (
    <tr>
      <td>{renderMaybe(entry.item_id)}</td>
      <td>{renderMaybe(entry.language)}</td>
      <td>{renderScore(entry)}</td>
      <td>{renderLanguageBreakdown(entry)}</td>
      <td>
        <ContaminationRiskLabel contaminationRisk={entry.contamination_risk} />
      </td>
      <td>
        <FailureCountsCell failureCounts={entry.failure_counts} />
      </td>
      <td>
        <CapsCell
          maxOutputTokens={entry.max_output_tokens}
          stopSequences={entry.stop_sequences}
          contextLength={entry.context_length}
          thinkingPolicy={entry.thinking_policy}
        />
      </td>
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
      <td>{renderJudgeBlock(entry)}</td>
    </tr>
  )
}

// One summary row per suite, not per item: the indicative mark and the
// headline exclusion count qualify the suite's score, and the contested
// items are listed by id under the suite whose headline excludes them.
function SuiteLevelSummary({ entries }: { entries: QualityEntry[] }) {
  const suites = new Map<string, QualityEntry[]>()
  for (const entry of entries) {
    const key = JSON.stringify([entry.suite_id, entry.suite_version])
    suites.set(key, [...(suites.get(key) ?? []), entry])
  }

  return (
    <section className="quality-suite-summary">
      {[...suites].map(([key, suiteEntries]) => {
        const [first] = suiteEntries
        // Never let a raised mark on one row be hidden by a silent sibling.
        const indicativeSource =
          suiteEntries.find((entry) => entry.indicative === true) ?? first
        const excludedN = suiteEntries
          .map((entry) => entry.judge.judged_headline_excluded_n)
          .find((n) => !isAbsent(n))
        return (
          <div key={key} className="quality-suite-summary-row">
            {renderMaybe(first.suite_id)}:{' '}
            <IndicativeLabel
              indicative={indicativeSource.indicative}
              reasons={indicativeSource.indicative_reasons}
            />
            {suiteEntries
              .filter((entry) => entry.judge.contested === true)
              .map((entry, index) => (
                <span key={index} className="contested-item">
                  {' '}
                  {renderMaybe(entry.item_id)}:{' '}
                  <ContestedLabel
                    contested={entry.judge.contested}
                    reason={entry.judge.contested_reason}
                    threshold={entry.judge.contested_threshold}
                  />
                </span>
              ))}
            {excludedN !== undefined && (
              <span className="excluded-count">
                {' '}
                excluded from headline: {String(excludedN)}
              </span>
            )}
          </div>
        )
      })}
    </section>
  )
}

export function QualityView({ runId }: { runId: string }) {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<QualityViewShape>(`/api/runs/${runId}/quality`)
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
    return <p>Loading quality…</p>
  }
  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  return (
    <div className="quality-view">
      <CoverageRecord />
      <table>
        <thead>
          <tr>
            <th>Item</th>
            <th>Language</th>
            <th>Score</th>
            <th>Per-language</th>
            <th>Contamination risk</th>
            <th>Failure counts</th>
            <th>Caps</th>
            <th>Verdict</th>
            <th>Judge</th>
          </tr>
        </thead>
        <tbody>
          {state.view.entries.map((entry, index) => (
            <QualityRow key={index} entry={entry} />
          ))}
        </tbody>
      </table>
      <SuiteLevelSummary entries={state.view.entries} />
    </div>
  )
}
