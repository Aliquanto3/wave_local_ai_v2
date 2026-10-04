# Reviewer brief (night run, 2026-10-02)

You independently review ONE story's uncommitted implementation. The owner is asleep.

## Hard rules
- Work ONLY inside `C:\Users\Anael\dev\wave_local_ai_v2-night`. Read-only: never edit code, never commit, never stage. Never touch the main repo `C:\Users\Anael\dev\wave_local_ai_v2` nor `C:\Users\Anael\dev\wave_local_ai_v2-refine`.
- Never call AskUserQuestion. If a skill asks for a choice, take its default.
- No paid API call, no model download, no Docker image pull, no network write.
- Stop any llama-server you start by its PID, never `taskkill /IM`.

## Steps
1. Read `aidd_docs/memory/` (except `external/`), the story file (its acceptance is the contract), its parent epic, and the plan in the task folder you are given.
2. The change under review is the uncommitted working tree: `git status --short`, `git diff`, plus every untracked file.
3. Run the skill `aidd-dev:05-review` against the story's acceptance. Check every acceptance condition one by one and say for each whether the code and tests actually prove it (cite file:line or test name), or whether its evidence is legitimately pending (operator, another machine, paid cloud call: owner decisions D1 to D3 in the orchestrator's message). Also check correctness bugs, scope creep, and conformance with `aidd_docs/memory/coding-assertions.md`.
4. Run `uv run pytest -q` yourself and quote the summary line.
5. Write the review report to `<task folder>/review.md` (this one file is the only file you may create). If a `review.md` already exists from a previous round, append a new `## Round N` section instead of overwriting.

## Report (under 20 lines)
- `VERDICT: PASS` (no blocking finding) or `VERDICT: CHANGES-REQUIRED`.
- Blocking findings: numbered, each one line with file:line and the fix expected. Blocking = an acceptance condition not met or not proved by a test, a correctness bug, a broken gate, a hard-rule violation.
- Non-blocking findings: at most 5, one line each.
- `ACCEPTANCE-WRONG: <reason>` only if an acceptance condition cannot be satisfied against the code as it stands.
