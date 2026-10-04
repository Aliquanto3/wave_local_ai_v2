# Walk report: logging a client session

Walker: independent reader, followed `docs/client-session-record.md` only (plus the
`## [x.y.z]` headings of `CHANGELOG.md`, as step 2 directs). Scenario:
`aidd_docs/tasks/2026_10/2026_10_04_client-showing-record/evidence/walk-scenario.md`.

## Record line written (scratch `client-sessions.jsonl`)

```jsonl
{"record_format": "1", "session_id": "session-bb1ac5ec34e1", "client_id": "client-46f8eeb3ba3e", "session_date": "2026-10-02", "logged_date": "2026-10-04", "release": "0.2.0", "audience": "external", "shown": "the quality overview of the classification suite and the runtime table of the dense models, from release 0.2.0", "outcome": "challenged", "backfilled": false, "challenges": [{"role": "client head of data", "criterion": "the GPU behind each runtime number is disclosed", "claims": ["fiche_disclosure"], "evidence_offered": "pointed at the runtime table, which shows tokens per second but has no GPU column", "resolving_evidence": "opened the hardware fiche each runtime row cites by fiche_hash, which records the GPU model and driver version"}, {"role": "client junior engineer", "claims": ["judge_agreement"], "evidence_offered": "none: stated that the judge's scores on the translation suite cannot be trusted, without giving a reason", "resolving_evidence": ""}]}
```

Ids minted with the step 1 commands: `session-bb1ac5ec34e1`, `client-46f8eeb3ba3e`
(new client, so new client id). Release `0.2.0` confirmed as `## [0.2.0] - 2026-09-22`
in CHANGELOG.md, so no `release_commit`.

## Check output

Command (from worktree root):
`uv run wave-local-ai-v2-client-sessions --sessions <scratch>/client-walk/client-sessions.jsonl`

```
Client-session record: C:/Users/Anael/AppData/Local/Temp/claude/C--Users-Anael-dev-wave-local-ai-v2/2554606c-a87d-454f-a374-f2d0c622109e/scratchpad/client-walk/client-sessions.jsonl
Records (1)
  line 1 session-bb1ac5ec34e1: 2026-10-02, external audience, release 0.2.0; challenged, 2 challenge(s)
Incomplete (1): reported, does not fail the check
  line 1: challenges[1].criterion: absent
Refusals (0)
PASS: 1 record(s), 1 incomplete field(s)
```

Exit code: 0.

## Deal remark

Stayed out. The purchasing-team remark appears in no field; no client name, sector
("logistics company") or client material either. Re-read done per step 5.

## The two challenges

1. Head of data, GPU not stated: criterion "the GPU behind each runtime number is
   disclosed", claims `["fiche_disclosure"]`, evidence offered = runtime table with no
   GPU column, resolving evidence = hardware fiche cited by `fiche_hash` (GPU model +
   driver version). Complete, resolved in session.
2. Junior engineer, judge not trustworthy on translation: `criterion` left out (no
   criterion stated, so not guessed), claims `["judge_agreement"]`, evidence offered
   stated as none given, `resolving_evidence` `""`, no `follow_up`. The check reported
   it as `challenges[1].criterion: absent` (incomplete, not refused), as step 3 predicts.

## Unclear, ambiguous or mismatched steps

1. Step 4: "Run the check on the file with your line appended: `uv run
   wave-local-ai-v2-client-sessions`". The command takes no path; the `--sessions`
   option is not documented in the procedure (only the scenario mentions it). A reader
   checking a draft line before appending to the real file has no documented way to.
2. Step 4: "It prints every record it read back". It prints a one-line summary per
   record (date, audience, release, outcome, challenge count), not the fields. The roles,
   criteria, claims and free text are not echoed, so the output does not help the
   step 5 re-read.
3. Step 3: "the read-back checks the criterion against the claims, and a mismatch is a
   finding". Unclear who or what does this read-back: the check printed nothing about
   claims vs criterion. A reader cannot tell whether the tool verifies it or a later
   human review does.
4. Step 3: "The claims must follow from the criterion" vs "If you cannot state one of
   them, leave it out". When `criterion` is left out, `claims` is still required
   non-empty, but there is no criterion for it to follow from. I derived
   `judge_agreement` from what the challenger said; the procedure does not say whether
   that is allowed or whether `other` is expected.
5. Step 3: `evidence_offered` when the challenger offered none. "If you cannot state one
   of them, leave it out" does not say whether "no evidence was offered" is a statable
   fact (write it) or a missing one (leave it out). The choice changes whether the
   challenge counts as complete. I wrote "none: ..."; had criterion been stated, this
   would have made the challenge count as complete with no evidence.
6. Step 3, `backfilled`: "`false` for a session logged the same day or after; `true` for
   a showing that predates this record". "logged ... after" and "predates this record"
   both describe a session logged two days later; the backfill section ("A showing that
   happened before it was logged") also matches it literally. I chose `false` reading
   "this record" as the record file/procedure, but the wording does not settle it.
7. Intro: "appends one record ... the same day". The scenario logs two days later; the
   procedure does not say what to do when the same-day rule was missed (other than via
   the ambiguous `backfilled` row).
8. Step 3 table: no guidance on whether `shown` should name the release again (the
   worked example does; I followed the example).
