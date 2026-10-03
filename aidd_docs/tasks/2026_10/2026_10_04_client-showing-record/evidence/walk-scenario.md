# Walk scenario: log one client session by following the procedure

For a reader who did not write the procedure (a separate agent session
counts). Follow `docs/client-session-record.md` only, from the worktree
root, and do not read `src/wave_local_ai_v2/client_sessions.py` or its tests
first. **Commit nothing and do not edit `aidd_docs/results/client-sessions.jsonl`**:
write the record to a scratch file outside the repository instead and point
the check at it with `--sessions <scratch file>`.

## The scenario (invented; no real client)

On 2026-10-02 the consultant held a one-hour session, in French, with a
logistics company outside the consultant's firm. They showed release 0.2.0:
the quality overview for the classification suite and the runtime table for
the dense models. Nothing was given to the consultant by the client.

- The client's head of data said, in French, "vos chiffres de vitesse ne
  disent pas sur quelle carte graphique ils tournent". Asked what made them
  say so, they pointed at the runtime table, which shows tokens per second
  but no GPU column. The consultant opened the hardware fiche each runtime
  row cites by its `fiche_hash` and showed the GPU model and driver version
  it records. The head of data agreed that this answered the point.
- A junior engineer then said the judge's scores could not be trusted on the
  translation suite. They gave no reason and the session ran out of time;
  nothing was shown in reply. Nobody recorded which acceptance criterion the
  engineer meant.
- At the end, the client said their purchasing team would decide next month
  whether to buy hardware. (Deal-related: does not belong in the record.)

The consultant logs the session today. The consultant has never logged this
client before.

## What to file with the delivery

1. The record line you wrote (the scratch file's content).
2. The full output of `uv run wave-local-ai-v2-client-sessions --sessions
   <scratch file>` and its exit code.
3. One line per step of the procedure that was unclear, missing or wrong, or
   "none".
