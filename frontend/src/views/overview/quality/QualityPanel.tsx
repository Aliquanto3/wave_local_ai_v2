import { useEffect, useState, type ReactNode } from 'react'
import { apiFetch, UnauthorizedError } from '../../../api/client'
import type { Maybe } from '../../../api/types'
import { isAbsent } from '../../../api/types'
import { Absent } from '../../../components/Absent'
import { useKeyGate } from '../../../components/KeyGate'
import { ContaminationRiskLabel } from '../../../labels/ContaminationRiskLabel'
import { ContestedLabel } from '../../../labels/ContestedLabel'
import { DeclaredAbsenceLabel } from '../../../labels/DeclaredAbsenceLabel'
import { IndicativeLabel } from '../../../labels/IndicativeLabel'
import { SingleJudgeLabel } from '../../../labels/SingleJudgeLabel'
import { VerdictLabel } from '../../../labels/VerdictLabel'
import type { OverviewQualityEntry, OverviewQualityView } from './types'

type LoadState =
  | { status: 'loading' }
  | { status: 'loaded'; view: OverviewQualityView }
  | { status: 'unreachable'; message: string }

function renderMaybe(value: Maybe<unknown>): ReactNode {
  if (isAbsent(value)) {
    return <Absent reason={value.reason} detail={value.detail} />
  }
  return String(value)
}

// Unlike `QualityView.tsx`'s own `renderScore`, this entry is one per
// subject (`run_id`), never one per item -- so it renders the run's own
// suite-level score only, never an item's `correct`/`item_score`, which the
// backend no longer sends on this shape (see `_quality_subject_entry`).
function renderScore(entry: OverviewQualityEntry): ReactNode {
  if (entry.score_shape === 'exact_match') {
    return (
      <span className="quality-score">
        exact-match, suite accuracy: {renderMaybe(entry.suite_accuracy)}
      </span>
    )
  }
  return (
    <span className="quality-score">
      graded ({renderMaybe(entry.metric_id)}), suite score:{' '}
      {renderMaybe(entry.suite_score)}
    </span>
  )
}

// The suite's own caps beside the score they qualify, rendered inline
// rather than through `views/quality/CapsCell` -- `renderScore`'s own
// comment applies here too: this module imports no view directory other
// than `labels/`.
function renderCaps(entry: OverviewQualityEntry): ReactNode {
  return (
    <span className="caps-cell">
      <span>max_output_tokens: {renderMaybe(entry.max_output_tokens)}</span>{' '}
      <span>context_length: {renderMaybe(entry.context_length)}</span>{' '}
      <span>thinking_policy: {renderMaybe(entry.thinking_policy)}</span>
    </span>
  )
}

function QualityEntryRow({ entry }: { entry: OverviewQualityEntry }) {
  return (
    <li className="overview-quality-entry">
      <span className="overview-quality-run-id">{renderMaybe(entry.run_id)}</span>{' '}
      {renderScore(entry)}{' '}
      <ContaminationRiskLabel contaminationRisk={entry.contamination_risk} />{' '}
      <IndicativeLabel
        indicative={entry.indicative}
        reasons={entry.indicative_reasons}
      />{' '}
      {isAbsent(entry.verdict) ? (
        <Absent reason={entry.verdict.reason} detail={entry.verdict.detail} />
      ) : (
        <VerdictLabel
          verdict={entry.verdict.verdict}
          referenceRunId={entry.verdict.reference_run_id}
          differingFields={entry.verdict.differing_fields}
        />
      )}{' '}
      <SingleJudgeLabel
        singleJudge={entry.judge.single_judge}
        reason={entry.judge.single_judge_reason}
      />{' '}
      <ContestedLabel
        contested={entry.judge.contested}
        reason={entry.judge.contested_reason}
        threshold={entry.judge.contested_threshold}
      />{' '}
      {renderCaps(entry)}
    </li>
  )
}

export function QualityPanel({ suite }: { suite: string }) {
  const { reportUnauthorized } = useKeyGate()
  const [state, setState] = useState<LoadState>({ status: 'loading' })

  useEffect(() => {
    let cancelled = false

    apiFetch<OverviewQualityView>('/api/overview/quality')
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
    return <p>Loading quality…</p>
  }
  if (state.status === 'unreachable') {
    return <p className="error-state">could not reach the service: {state.message}</p>
  }

  const useCase = state.view.use_cases.find((entry) => entry.task_suite === suite)
  if (useCase === undefined) {
    return null
  }

  return (
    <section className="overview-quality-panel">
      <h3>Best local</h3>
      {isAbsent(useCase.leader) ? (
        <DeclaredAbsenceLabel
          reason="no leader set published for this suite and machine class"
          detail={useCase.leader.reason}
        />
      ) : useCase.leader.members.length === 0 ? (
        <DeclaredAbsenceLabel
          reason="leader set published, no member"
          detail="every evaluated row was excluded from this suite's leader set"
        />
      ) : (
        <ul className="overview-leader-members">
          {useCase.leader.members.map((entry, index) => (
            <QualityEntryRow key={index} entry={entry} />
          ))}
        </ul>
      )}
      <h3>Cloud comparators</h3>
      {useCase.cloud_comparators.length === 0 ? (
        <DeclaredAbsenceLabel
          reason="no cloud subject in the store for this suite"
          detail="no non-local provider has a row for this task_suite"
        />
      ) : (
        <ul className="overview-cloud-comparators">
          {useCase.cloud_comparators.map((entry, index) => (
            <QualityEntryRow key={index} entry={entry} />
          ))}
        </ul>
      )}
    </section>
  )
}
