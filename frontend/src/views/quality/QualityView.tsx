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
        exact-match: {renderMaybe(entry.correct)} (suite {renderMaybe(entry.suite_accuracy)})
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
        <SingleJudgeLabel singleJudge={singleJudge} reason={judge.single_judge_reason} />
      )}
      {hasAgreement && <span className="agreement-figure">agreement: {String(agreement)}</span>}
    </span>
  )
}

function QualityRow({ entry }: { entry: QualityEntry }) {
  return (
    <tr>
      <td>{renderMaybe(entry.item_id)}</td>
      <td>{renderMaybe(entry.language)}</td>
      <td>{renderScore(entry)}</td>
      <td>
        {entry.score_shape === 'exact_match' && entry.language_breakdown !== undefined
          ? Object.entries(entry.language_breakdown).map(([lang, cell]) =>
              isAbsent(cell) ? (
                <Absent key={lang} reason={cell.reason} detail={cell.detail} />
              ) : (
                <span key={lang} className="language-cell">
                  {lang}: {renderMaybe(cell.accuracy)}{' '}
                  <IndicativeLabel indicative={cell.indicative} reasons={[]} n={cell.n} />
                </span>
              )
            )
          : entry.score_shape === 'graded' &&
            entry.score_breakdown !== undefined &&
            Object.entries(entry.score_breakdown).map(([lang, cell]) =>
              isAbsent(cell) ? (
                <Absent key={lang} reason={cell.reason} detail={cell.detail} />
              ) : (
                <span key={lang} className="language-cell">
                  {lang}: {renderMaybe(cell.score)}{' '}
                  <IndicativeLabel indicative={cell.indicative} reasons={[]} n={cell.n} />
                </span>
              )
            )}
      </td>
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

function SuiteLevelSummary({ entries }: { entries: QualityEntry[] }) {
  return (
    <section className="quality-suite-summary">
      {entries.map((entry, index) => (
        <div key={index} className="quality-suite-summary-row">
          <IndicativeLabel indicative={entry.indicative} reasons={entry.indicative_reasons} />
          {!isAbsent(entry.judge.contested) && (
            <ContestedLabel
              contested={entry.judge.contested}
              reason={entry.judge.contested_reason}
              threshold={entry.judge.contested_threshold}
            />
          )}
          {!isAbsent(entry.judge.judged_headline_excluded_n) && (
            <span className="excluded-count">
              excluded from headline: {entry.judge.judged_headline_excluded_n}
            </span>
          )}
        </div>
      ))}
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
