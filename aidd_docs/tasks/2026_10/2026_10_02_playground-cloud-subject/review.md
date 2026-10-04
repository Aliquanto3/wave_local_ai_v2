# Review: The playground reaches a cloud subject only when configured, and says so first

- **Verdict**: approve (VERDICT: PASS). Story stays `ready`: browser QA video operator-pending, real-provider exchange cloud-pending (D2).
- **Diff**: `a12092c...working tree` (uncommitted)
- **Axes run**: code, functional, relevancy
- **Date**: 2026_10_03
- **Findings**: 0 critical, 0 warning, 4 minor

## Phases

### Phase 1 — The setting and the cloud path

- [x] Unset by default, keys alone enable nothing, bad value refuses start — settings.py:427; test_settings `test_holding_a_benchmark_key_enables_no_playground_cloud_subject`, `test_a_misconfigured_playground_cloud_subject_refuses_service_start`
- [x] Through the existing client, `Pacer` + `call_with_retry`; rate limit/provider failure = refusal naming the provider — playground.py:488-535; `test_a_rate_limit_is_retried_then_shown_as_a_refusal_naming_the_provider`, `test_a_provider_failure_names_the_provider_and_never_the_clients_message`, `test_consecutive_cloud_sends_are_paced_at_the_providers_interval`
- [x] Refused during a run, checked per send — playground.py:345, 383; `test_the_cloud_subject_is_refused_while_a_run_holds_the_lock`, `test_a_send_is_refused_if_a_run_took_the_lock_after_the_selection`

### Phase 2 — The selector and the per-send statement

- [x] Same selector and label; send control names the provider on every send, not a dialog; absent for a local subject — PlaygroundPanel.tsx:40, 323; vitest "names the provider on the send control before every send", "carries no statement on the send control for a local subject"

### Phase 3 — Refusal tests and evidence

- [x] Unset => absent, refused, client never called with benchmark keys present; local exchange never reaches a cloud client; key in no body/log — `test_unconfigured_the_cloud_subject_is_absent_refused_and_never_called`, `test_a_local_exchange_never_reaches_a_cloud_client`, `test_no_response_body_or_log_line_carries_the_provider_key`; evidence/key-search.txt (loopback stub, 0 hits)
- [ ] Browser QA video — operator-pending (not-applicable to this unattended run)

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟢 | code | 1 | playground.py:507 | A provider `Retry-After` hint is uncapped (`call_with_retry` caps only computed backoff): a large hint holds the HTTP response and the session send lock for minutes on the pitch screen | Cap the hint for the playground or refuse when the hint exceeds a small bound |
| 🟢 | code | 1 | playground.py:488 | An exception outside the caught set (client bug) aborts the stream with no `final` event | Acceptable; optionally a last `except Exception` naming the provider and class |
| 🟢 | fit | 2 | PlaygroundPanel.tsx:298 | Thinking-policy selector stays active for the cloud subject though nothing is sent (`not_sent`) | Disable or annotate it while the cloud subject is loaded |
| 🟢 | code | 3 | evidence/key-search.py.txt | Script calls `load_service_settings()` (runs `load_dotenv`); run from a checkout with a `.env` it would read real keys into the process (unused for the mistral subject) | Patch `settings.load_dotenv` to a no-op in the script |

## Verification

| Metric        | Value |
| ------------- | ----- |
| Verified      | 86% (6/7); `uv run pytest -q`: 2692 passed, coverage 98.45%; ruff/format/mypy clean; vitest 156 passed; `tsc -b --noEmit` clean |
| Files checked | settings.py, playground.py, demo_console.py, service.py, PlaygroundPanel.tsx, types.ts (playground, console), holder.ts, test_playground.py, test_settings.py, PlaygroundPanel.test.tsx, evidence/* |
| Unchecked     | Browser QA video — not-applicable (operator-pending); real provider exchange — not-applicable (D2) |
| Unplanned     | none |
