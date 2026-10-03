# Logging a client session

Every time a benchmark result is shown to a client or their engineer, the
consultant appends one record to `aidd_docs/results/client-sessions.jsonl`
the same day (see "Logging late" when that slipped). The record says what was shown, from which release, to which
kind of audience, how it was received and, for each challenge, who raised it,
on which criterion, with which evidence, and what evidence settled it. A
reader who was not in the room must be able to answer those questions from
the record alone.

The file is append-only, one JSON object per line, and published under
CC-BY 4.0 with the rest of `aidd_docs/results/` (see `LICENSE-DATA`).

## Before you start: what never goes in the record

- **No client name.** Not the organisation, not a person, not a product or
  project that identifies them. The record carries a pseudonymous `client_id`
  only. The mapping from that id to the client lives outside the repository,
  in your own private notes; never commit it, never paste it into an issue.
- **No client-provided material.** No document, prompt, dataset, screenshot or
  excerpt the client gave you. Describe the evidence in your own words; never
  attach or quote it.
- **No deal outcome.** The record says how a result was received, never
  whether a deal was won, lost, priced or delayed.

The record has no field for any of these, and the check refuses any key it
does not know. It cannot see what you type into a free-text field, though:
this property is checked by reading the file, so re-read every free-text
field before you commit.

## The steps

1. **Mint the ids.** A new session gets a new `session_id`; a client you have
   never logged gets a new `client_id`. Both are a fixed prefix and 12
   lowercase hexadecimal characters drawn at random, never derived from the
   client's name:

   ```bash
   uv run python -c "import secrets; print('session-' + secrets.token_hex(6))"
   uv run python -c "import secrets; print('client-' + secrets.token_hex(6))"
   ```

   Reuse an existing `client_id` for a client you have logged before (look it
   up in your private mapping), and add any new one to that mapping now.

2. **Name the release.** Use the version of the `## [x.y.z] - YYYY-MM-DD`
   section of `CHANGELOG.md` the shown results came from, exactly as written
   between the brackets (`0.2.0`). If the results came from code that is not
   yet released, write `unreleased` and add `release_commit`, the full
   40-character hash of the commit they were produced from (`git rev-parse
   HEAD` on the machine that produced them). Leave `release_commit` out for a
   dated release. The check confirms the commit with `git cat-file -e` in the
   clone it runs in, so that commit must be pushed and fetched there first;
   CI runs the same check on the committed record, so a commit that never
   reaches the shared repository makes CI refuse the record.

3. **Fill the fields in this order**, one JSON object on one line. Write in
   English even when the session was held in French: translate what was said,
   do not transcribe it.

   | Key | Value |
   | --- | --- |
   | `record_format` | `"1"` |
   | `session_id` | the id minted in step 1 |
   | `client_id` | the client's pseudonymous id |
   | `session_date` | the day of the showing, `YYYY-MM-DD` |
   | `logged_date` | the day you write the record, `YYYY-MM-DD` |
   | `release` | the dated release version, or `"unreleased"` |
   | `release_commit` | only with `"unreleased"`: the full commit hash |
   | `audience` | `"external"` when the audience was outside your own firm, `"internal"` when it was inside it (only external sessions count toward a release's credibility) |
   | `shown` | what was shown, in words: which tables, views or rows. Naming the release again here is optional; `release` is the field that counts |
   | `outcome` | `"challenged"`, `"dismissed"` or `"accepted"` |
   | `backfilled` | `true` only for a showing held before the record file was first committed (see "Showings that predate the record"); `false` for every later session, however many days after it you log it |
   | `corrects` | only when this record replaces an earlier one: that record's `session_id` |
   | `challenges` | the list of challenges raised; `[]` when none was raised |

   Each challenge is an object with these keys, in this order:

   | Key | Value |
   | --- | --- |
   | `role` | the challenger's role, never their name (`"client data scientist"`) |
   | `criterion` | the acceptance criterion disputed, in words |
   | `claims` | the claims the criterion bears on, a non-empty list drawn from `fiche_disclosure`, `table_separation`, `judge_agreement` and `other` |
   | `evidence_offered` | the evidence the challenger offered for the challenge; `"none offered"` when you know they offered none |
   | `resolving_evidence` | the evidence presented within the session that resolved it, named so a reader can find it; `""` when nothing presented in the session resolved it, which makes the challenge sustained (step 4) |
   | `follow_up` | the repository path of the challenge's follow-up item (step 4): required when the challenge is sustained, optional otherwise |

   An outcome of `challenged` carries at least one challenge; `accepted` and
   `dismissed` carry `[]`.

   **The claims must follow from the criterion.** Pick the claims the
   criterion as you wrote it actually bears on: "the hardware behind the
   runtime numbers is not stated" is `fiche_disclosure`; "measured and
   estimated figures are mixed in one table" is `table_separation`; "the
   judge's scores are not reliable" is `judge_agreement`; anything else is
   `other`. When you leave the criterion out (below), `claims` is still
   required and never empty: name the claims the challenger's words bore on,
   and use `other` only when they bore on none of the three. Choosing `other`
   to avoid a claim hides the challenge from the credibility count.

   The check cannot judge whether the claims follow from the criterion: it
   reads no meaning and prints nothing about it. A person does: whoever reads
   the record back (the first real session's read-back, and the reviewer of
   the commit) compares the criterion with the claims, and a mismatch is
   corrected by appending a correction (see "Correcting a record").

   `role`, `criterion` and `evidence_offered` are the three facts the PRD
   requires. A fact you know is written, even a negative one: a challenger
   who gave no reason is `"evidence_offered": "none offered"`, and that
   challenge is complete. A fact you do not know or no longer remember is
   left out rather than guessed: the check keeps the record and reports it
   incomplete, and an incomplete record does not count toward a release's
   credibility. Never write `""` for one of these three: the check reports
   it as stated empty, which is incomplete too.

4. **File a follow-up item for every sustained challenge.** A challenge is
   sustained when its `resolving_evidence` is `""` (or `null`, or blank): no
   evidence presented within the session is named as having resolved it. No
   other field says whether a challenge is sustained, so nothing can
   contradict it. Evidence found after the session never goes into
   `resolving_evidence`; write it into the follow-up item instead.

   Choose the item's kind from what the session showed, and record it by
   where you file the item:

   - a **defect**, under `aidd_docs/backlog/defects/` with frontmatter
     `type: defect`, when the session showed a claim to be wrong;
   - a **spike**, under `aidd_docs/backlog/spikes/` with frontmatter
     `type: spike`, when the session left a claim unresolved.

   The item is a Markdown file whose YAML frontmatter carries `type` and
   `status`, like every other item in those folders. Its text contains the
   record's `client_id` and its `session_id`, and nothing else about the
   client: like the record, the item never names the client organisation
   and never carries client-provided material. Then set `follow_up` to the
   item's path relative to the repository root, with forward slashes
   (`aidd_docs/backlog/defects/<slug>.md`); the check refuses a backslash,
   an absolute path and `..`.

   One item may serve several sustained challenges, of the same record or of
   later ones. A resolved challenge may link an item too; the check holds
   that link to the same rules and the challenge stays resolved.

   The item records the follow-up; it does not build the fix. The epic that
   owns the disputed criterion works it.

   **The item's path is frozen once a record cites it.** Never rename or
   delete the file: cancel it by setting its status and keeping the file
   with its Cancellation section. A `cancelled` or `done` item never turns
   the challenge into a resolved one, because the check reads sustained from
   the record alone. If the path must change anyway, append a correction
   (see "Correcting a record") naming the new path. The item may name the
   session id of any record of the correction chain, so an item opened for
   the original record keeps serving its correction.

5. **Run the check.** From the repository root, after appending your line to
   `aidd_docs/results/client-sessions.jsonl`:

   ```bash
   uv run wave-local-ai-v2-client-sessions
   ```

   With no option it checks `aidd_docs/results/client-sessions.jsonl`
   against `CHANGELOG.md`. To try a draft line before touching the real
   file, put it in a scratch file outside the repository and pass that file:

   ```bash
   uv run wave-local-ai-v2-client-sessions --sessions <scratch file>
   ```

   A draft checked alone is not checked against the earlier records (a
   repeated `session_id`, a `corrects` naming an earlier record), so always
   run the check once more on the real file after appending.

   It prints one summary line per record it accepted (session id, date,
   audience, release, outcome, number of challenges, and the markings
   backfilled, corrects and corrected by), then the incomplete fields, then
   the refusals, then `PASS` or `FAIL`. It does not echo the free text:
   step 6 re-reads your line itself.

   - `Refusals`: each line names the record's line number and field, such as
     `line 3: release: '0.3.0' is neither a dated section of CHANGELOG.md
     nor 'unreleased' with a commit`. Fix that field in your new line and run
     again. Exit code `1`.
   - `Incomplete`: a content field left out or stated empty. The check still
     passes (exit `0`); fill it if you can, or accept that the record will
     not count.
   - A `follow_up` refusal names the session and the challenge, such as
     `line 3: challenges[0].follow_up: session session-<id>, challenge 0:
     the challenge is sustained (no resolving evidence named) and names no
     follow-up item`. It also fires when the item is outside the two
     folders, does not exist, has a frontmatter `type` that does not match
     its folder, or lacks the record's `client_id` or a `session_id` of its
     correction chain. CI runs the same check on the committed record on
     every push, so a cited item renamed or deleted later fails CI.
   - `nothing checked` on stderr (exit `2`): the record file or `CHANGELOG.md`
     could not be read; run the command from the repository root.

6. **Re-read the line** you wrote, every free-text field of it, and every
   follow-up item you filed, for client names, client material and deal
   outcomes, then commit the record and its items together:

   ```bash
   git add aidd_docs/results/client-sessions.jsonl aidd_docs/backlog/defects/<slug>.md
   git commit -m "docs(results): log client session session-<id>"
   ```

## Logging late

Log the session the day it happens. When that slipped, log it as soon as you
can, by the same steps: `session_date` is the day of the showing,
`logged_date` the day you write the record, and `backfilled` stays `false`.
The gap between the two dates is in the record for any reader to weigh. A
late record follows the same rule as any other: a fact you no longer
remember is left out, never reconstructed by guesswork.

## Showings that predate the record (backfill)

A showing held before the record file was first committed (`git log
--diff-filter=A --format=%ad --date=short --
aidd_docs/results/client-sessions.jsonl` prints that date) is entered only
if you can still name the release, the challenger's role, the evidence
offered and the criterion disputed. Enter it with `"backfilled": true` and a `logged_date` of
the day you write it. A showing you cannot reconstruct that far is not
entered at all.

## Correcting a record

A committed line is never edited or removed; a test walks the file's
committed history and fails when a version is not a line-for-line prefix of
the next. To correct a mistaken record, append a new record with its own new
`session_id`, every field restated with the correction, and `corrects` naming
the mistaken record's `session_id`. The earlier line stays in place. A record
can be corrected once; to correct a correction, correct the latest record, so
the chain's last link is the record a reader reads.

## Worked example

A consultant showed release 0.2.0's classification overview and runtime table
to an external client on 2026-10-01. The client's ML engineer challenged the
runtime numbers: the hardware behind them was not stated. The consultant
opened the hardware fiche the rows cite and the challenge was settled in the
session. The record, appended on the same day:

```jsonl
{"record_format": "1", "session_id": "session-5e0c9a71d2b4", "client_id": "client-a83f0d6e19c2", "session_date": "2026-10-01", "logged_date": "2026-10-01", "release": "0.2.0", "audience": "external", "shown": "the classification overview and the runtime table of release 0.2.0", "outcome": "challenged", "backfilled": false, "challenges": [{"role": "client ML engineer", "criterion": "the hardware behind each runtime number is disclosed", "claims": ["fiche_disclosure"], "evidence_offered": "pointed out that the runtime table names no GPU", "resolving_evidence": "opened the hardware fiche the runtime rows cite by fiche_hash, which names the GPU and driver"}]}
```

Two days later the consultant notices the session was held on 2026-09-30, not
2026-10-01, and appends a correction; the first line stays as it was:

```jsonl
{"record_format": "1", "session_id": "session-c7149e2a0f85", "client_id": "client-a83f0d6e19c2", "session_date": "2026-09-30", "logged_date": "2026-10-03", "release": "0.2.0", "audience": "external", "shown": "the classification overview and the runtime table of release 0.2.0", "outcome": "challenged", "backfilled": false, "corrects": "session-5e0c9a71d2b4", "challenges": [{"role": "client ML engineer", "criterion": "the hardware behind each runtime number is disclosed", "claims": ["fiche_disclosure"], "evidence_offered": "pointed out that the runtime table names no GPU", "resolving_evidence": "opened the hardware fiche the runtime rows cite by fiche_hash, which names the GPU and driver"}]}
```

This example lives here, not in the record file: the record holds real
sessions only.
