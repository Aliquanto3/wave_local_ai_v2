# Implementer brief (unattended run)

You implement ONE backlog story in an unattended run. The owner is away.

## Hard rules
- Work ONLY inside `C:\Users\Anael\dev\wave_local_ai_v2-impl` (a git worktree on branch `feat/ready-stories-unattended`). Never touch `C:\Users\Anael\dev\wave_local_ai_v2` (the main repo; another session is editing it).
- Never call AskUserQuestion, never wait for input. When a skill asks for a confirmation or a choice, take its recommended/default option and record the decision in the plan's Decisions table.
- Never push, merge or open a PR. No paid API call of any kind: no cloud subject, no judge, no calibration provider. No `.env` exists in the worktree; do not create one or copy the main repo's.
- Never edit an epic, the PRD, `owner-questions.md`, or any story's acceptance. If the story's acceptance turns out to be wrong against the code (it cannot be satisfied as written, or it contradicts the code in a way you cannot resolve without changing the acceptance), STOP: revert your changes (`git checkout -- <files>` / delete your new files) and report `ACCEPTANCE-CONFLICT: <one-line reason>`.
- Never download a model.
- English only in every repo artifact. Follow `CLAUDE.md` and `aidd_docs/memory/*` conventions. Surgical changes; match surrounding code.
- Do NOT commit unless the orchestrator explicitly tells you to. Leave your work as uncommitted changes. Do not stage or modify `aidd_docs/tasks/2026_10/2026_10_01_unattended-implementation/run-log.md`.

## Steps
1. Read `aidd_docs/memory/` first (all files except `external/`), then the story, its parent epic, every `depends_on` story, and the PRD sections its "Maps to:" line cites (PRD under `aidd_docs/`; find it with a search if the path is not given).
2. Run the skill `aidd-dev:01-plan` on the story, then `aidd-dev:02-implement`, then `aidd-dev:03-assert`. Put the plan and phase files in `aidd_docs/tasks/2026_10/2026_10_01_<story-slug>/` (story-slug = the story file name without `.md`, shortened sensibly if very long), matching the layout of `aidd_docs/tasks/2026_09/2026_09_22_pitch-overview-one-card-per-use-case/` (`plan.md` with front matter `objective`/`status`, `phase-N.md`, optional `evidence/`).
3. If the story says "Needs: a real local model run ... only for the evidence": the pinned build is at `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe` and the models are in `D:\ia\models` (all four roster GGUFs present). Produce the evidence by setting `LLAMA_SERVER_PATH` and `SLM_MODELS_DIR` explicitly in the command's environment, `QUALITY_PROVIDERS=local`, and pointing every results path (`QUALITY_RESULTS_PATH`, `RUNTIME_RESULTS_PATH`, fiche registry if written) into the story's task `evidence/` folder or a temp dir, never the committed stores under `aidd_docs/results/`. Save the decisive output in `evidence/`. If the run cannot be made to work, ship code and tests anyway and report `evidence pending: local run (<reason>)`.
4. Before reporting, all of these must pass, run from the worktree root: `uv run pytest` (coverage floor 95%), `uv run pre-commit run --all-files`, AND the secrets scan on every file you changed or created, since `--all-files` hands that hook no filenames and scans nothing: `uv run python -X utf8 -m detect_secrets.pre_commit_hook --baseline .secrets.baseline <every changed/new file>`. A public hash literal flagged by it gets the repo's inline `# pragma: allowlist secret` comment. Fix until all pass.
5. Story text: read the story, epic and dependencies from your worktree. If the orchestrator says the story lives on the PR branch, read it with `git -C C:\Users\Anael\dev\wave_local_ai_v2-impl show docs/slice-remaining-epics:<path>` (read-only; never merge, cherry-pick or check out that branch).

## Report (keep it under 15 lines)
- `STATUS: READY-FOR-REVIEW` or `ACCEPTANCE-CONFLICT: ...` or `FAILED: <reason>`
- Task folder path.
- Files changed (short list).
- Test evidence: the exact pytest summary line (`N passed ... Total coverage: X%`) and the pre-commit result.
- Local-run evidence: produced (path) / not needed / pending (reason).
- Any contradiction between the code and the backlog you noticed (one line each).
