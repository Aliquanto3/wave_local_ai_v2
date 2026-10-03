# Run log: owner arbitration session (2026-10-03)

Interactive session with the owner present, on branch `docs/refine-proposed-items-2026-10-02` (worktree `wave_local_ai_v2-refine`, not yet merged into `main`, so no new branch was cut). Nothing was pushed. No model was run, nothing was installed or downloaded, no account was created and no provider was called: the execution spikes below are desk research with dated sources, and their scripts were only parsed or run against local stubs.

## Summary

### Answers given

All 36 questions were answered with the recommended default. Each answer is recorded in its source file as "Owner answer".

- Q100 to Q122 (`aidd_docs/tasks/2026_10/2026_10_02_backlog-refinement/owner-questions.md`): (a) everywhere except Q103 (c), Q110 (c) and Q113 (b), each of which was the recommended option.
- Q123 to Q135 (`owner-questions.md` in this folder), raised by this session's three-amigos reviews: (a) everywhere.
- The unanswered-question check on `aidd_docs/tasks/2026_10/2026_10_01_autonomous-slicing/owner-questions.md` found none: Q1 to Q76 all carry an answer.

Owner-approved edits to the PRD, `ready` epics and `done` stories, each shown before -> after and applied on the owner's yes:

| Edit | Artifact | From |
| --- | --- | --- |
| Methodology 12 rewritten (release or snapshot id, live list or one-token probe, build markers, refusal on a marker change); Methodology 10 cites it | PRD | Q102 |
| Methodology 11 and the calibration acceptance criterion: two agreement figures, one per judge | PRD | Q116 |
| Licence open question and dependency: drawn items keep their own permissive licence inside the CC-BY bundle | PRD | Q106 |
| Pinning discipline, judge fields, calibration figures, dependency row | judge epic | Q102, Q116 |
| Generated-completions row marked verified; search responses never enter the download | bundle epic | Q111, Q114 |
| `status: proposed -> ready` | credible-sessions epic | Q101 |
| Gate two names order 11 | interval epic | Q130 |
| Q117 refusals listed as refused, not as a failure | `a-campaign-is-declared-as-data-and-an-empty-cell-fails-it` (`ready`) | Q117 |
| Null rule covers a derived reasoning count | `every-judge-call-names-who-answered-its-reasoning-effort-and-its-reasoning-tokens` (`done`) | Q121 |
| Stale list of item-literal modules | `the-data-is-cc-by-4-0-the-code-stays-mit-and-each-says-so-where-it-lives` (`done`) | Q122 |

### Items moved to `ready`, in dependency order

Each one passed a three-amigos review (product, delivery and quality lenses run independently, then reconciled). Every finding was applied, or it became one of Q123 to Q135 and was answered. Every "Current state" section was verified against the code on this branch, whose code equals `main` at `c68b23e`.

| # | Item | Tag | Waits on |
| --- | --- | --- | --- |
| 1 | epic `a-release-is-called-credible-only-by-its-logged-client-sessions` | n/a | |
| 2 | `each-release-reads-its-credibility-verdict-from-its-records-in-its-changelog-entry` (credible order 3) | code-only | orders 1 and 2 (`ready`) |
| 3 | `the-first-real-client-session-is-logged-the-same-day-and-read-back-by-someone-who-was-not-there` (credible order 4) | operator (a real client session) | orders 1 to 3 |
| 4 | `the-half-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder` (size order 5) | local run + operator: gate runs, 1.12 GB of downloads, GPU free | nothing (`depends_on` done) |
| 5 | `the-two-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder` (size order 6) | local run + operator: 5.97 GB | nothing |
| 6 | `the-four-billion-class-spans-two-families-or-is-published-as-a-searched-single-family-ladder` (size order 7) | local run + operator: up to 10.65 GB | nothing |
| 7 | `the-top-class-spans-two-families-with-dense-and-moe-or-says-why-not` (size order 8) | local run + operator: 6.4 GB, or 19.97 GB if the 26B-A4B also runs | nothing |
| 8 | `a-publication-level-classification-suite-stands-beside-the-hand-written-one` (interval order 7) | local run (a 300-item publication batch and a 20-item development batch, plus the MInDS-14 fetch) | `the-laptop-proves-both-modes-and-republishes-the-bundle-once` (`ready`, Q134) |
| 9 | `a-publication-level-translation-suite-stands-beside-the-hand-written-one` (interval order 8) | local run (a 300-item batch and a 21-item batch, plus the WMT24++ fetch) | the same laptop story |
| 10 | `the-threshold-review-is-written-from-the-first-publication-run` (interval order 9) | code-only (analysis over published rows) | interval orders 7 and 8 |
| 11 | `a-drawn-item-reaches-the-download-under-its-own-terms-or-as-a-visible-hole` (bundle order 7) | code-only | interval orders 7 and 8, and `each-release-attaches-one-archive-that-needs-no-clone` (`ready`) |

None of these needs a paid key. The size-class gate runs are not a spike: under Q108 (a) they are the stories' own first runs, and the GGUF spike closes per architecture on them (Q125 (a)).

Created and left `proposed`: `the-roster-ranks-the-same-way-at-the-development-and-publication-levels` (interval order 11, Q130 (a)). It has not had a three-amigos review yet.

### Execution spikes, in recommended order

Each spike covers one sitting. Each reuses the commands its parent spikes already hold, by reference, and adds only what was missing. Each parent spike's Follow-up now points to its execution spike.

| # | Spike | Tag | Prerequisites | Time | Cost | Closes |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | `does-one-paid-key-session-capture-what-the-three-judge-provider-spikes-need` | paid key + operator | DeepSeek, Z.ai (`api.z.ai`) and OpenAI accounts with prepaid credit (owner act; OpenAI at least $5, Tier 1 so the burst can reach a 429); the DeepSeek opt-out email sent first (Q103 (c)); three keys in `.env`; Z.ai console open in a browser | about 1.5 h | about $0.42 of calls ($0.27 DeepSeek, $0.12 Z.ai, $0.04 OpenAI), up to $0.64 if the Z.ai burst needs 600 requests; the real outlay is the prepaid credit | the DeepSeek, GLM and Luna spikes; unblocks judge orders 8, 9, 11, then the whole judge chain (judge 10 and 6, quality 2, 5, 6, use-case 3 and 5) |
| 2 | `are-the-three-ollama-spikes-live-captures-obtainable-in-one-ollama-v0-35-1-session` | install + local run | GPU free, 8 GB free on D:, ports 11500 and 8080, Ollama v0.35.1 zip (sha256 pinned), b10537 `llama-server` | 60 to 90 min | electricity only | the three Ollama spikes; unblocks engine orders 6, 7, 8 and 11 |
| 3 | `which-llmlingua-2-class-compressor-fits-the-reference-machine-and-in-which-placement` (existing spike, runbook completed in place) | install + local run | GPU free, about 7 GB of disk, an isolated venv | 45 to 75 min | electricity only | the compressor spike; unblocks engine order 9, then the campaign (order 12) together with order 8 |
| 4 | `does-one-local-session-capture-the-tool-call-probes-and-harness-driver-runs` | install + local run | GPU free, ports 8080 and 8081, the four roster GGUFs on disk (22.7 GB, no new download), PyPI access for the `harness-probe` group in a throwaway worktree | 2.5 to 4 h | electricity only | the tool-call spike; unblocks use-case orders 6, 7 and 8 |
| 5 | `does-one-session-capture-searxng-and-mojeek-responses-with-their-upstreams` | install + paid key + operator | Docker Desktop (installed; the owner confirms its licence covers this use), a Mojeek Business account through its contact form (owner act; minimum credit not published), `MOJEEK_API_KEY` | about 1 h, plus Mojeek's reply time | about £0.07 of queries, plus Mojeek's minimum credit | the search spike; use-case orders 9 and 10 then still wait on the judge chain |

Why this order: spike 1 unblocks the widest chain, and its accounts take lead time, so open them first. Spikes 2 and 3 are free and can share one laptop day. Spike 4 is the longest local sitting. Spike 5 goes last because its stories also wait on the judge chain, but its Mojeek contact form should go out early. After each sitting, run `aidd-pm:05-spike` (investigate, then conclude) on the parent spikes, with the capture folder as input.

## Details

### Commits

`6acb452` answers recorded; `24131f2` PRD; `e5774d2` credible-sessions epic; `ab43af6` judge epic; `8714ef2` quality epic; `37ce307` use-case epic; `b81c72c` engine epic; `a1d1aa1` interval epic; `f9acd4d` bundle epic; `50a278e` size-class epic. Before each commit, `uv run pre-commit run --files ...` passed on all changed files: ruff check, ruff format, mypy, and detect-secrets (the hook runs under `python -X utf8`).

- Ruff 0.16 formats the Python embedded in markdown, so one execution spike was run through `ruff format`.
- Three published sha256 values (the Ollama zip and two Hugging Face templates) were flagged by detect-secrets. They carry the repo's inline `pragma: allowlist secret` idiom; nothing was added to the baseline.

### How the stories were applied

- Five agents applied Q100 to Q122 to the proposed stories and blocked spikes, one agent per epic cluster. They reported every edit that needed the owner as before -> after, and those edits were put to the owner before being applied.
- Three-amigos ran nine lens agents over three clusters: credible sessions, size classes, and publication suites.
- Two spikes resolved from the answers alone: the classification benchmark spike (Q105) and the translation benchmark spike (Q106). Every other spike stays `blocked` on its live work.

### Noted, not changed

- The 2026-10-02 run log still lists Q100 to Q122 as blockers. It is history, and this log supersedes its status tables.
- `aidd_docs/backlog/epics/the-engine-and-the-prompt-variant-are-measured-not-assumed.md` line 29 still cites `local_client._thinking_kwargs`; the function is now the public `thinking_kwargs`.
- The use-case epic promises the pitch a "drill-down to an archived source set". Under Q114 (a), only someone holding the run archive can see that set.
- The flagship's `expert_count: 40` (its layer count; its header says 256) has no tech-debt row, only the 2026-10-01 run log line.
- Tool-call finding at b10537: `parse_tool_calls: false` is ignored whenever tools are sent. The execution spike attributes model against parser by relaunching with `--skip-chat-parsing` instead.
- `scripts/audit_dependencies.py` audits only the runtime and `dev` dependencies. Interval order 7 now extends it to its `loaders` group (Q135).
- Unrelated code note: `candidate_gate`'s hub listing aborts on a 404 instead of recording a refusal.
- Gaps left explicit in the execution spikes, never invented:
  - the Z.ai concurrency figure (shown only in the console) and whether its model-list endpoint exists;
  - the OpenAI Services Agreement, which returns 403 and needs a manual save;
  - Mojeek's sign-up terms and error responses;
  - parts of three framework APIs (smolagents plain-text answers, the pinning of `llama-index-llms-openai`, pydantic-ai's docstring parsing).
