# Implementer brief (night run, 2026-10-02)

You implement ONE backlog story in an unattended run. The owner is asleep.

## Hard rules
- Work ONLY inside `C:\Users\Anael\dev\wave_local_ai_v2-night` (a git worktree on branch `feat/night-run-2026-10-02`). Never touch `C:\Users\Anael\dev\wave_local_ai_v2` (the main repo) nor `C:\Users\Anael\dev\wave_local_ai_v2-refine` (a parallel refinement session). Read every story, epic and spike from your own worktree.
- Never call AskUserQuestion, never wait for input. When a skill asks for a confirmation or a choice, take its recommended/default option and record the decision in the plan's Decisions table.
- Never commit, push, merge or open a PR. Leave your work as uncommitted changes. Do not stage or modify anything under `aidd_docs/tasks/2026_10/2026_10_02_night-run/`.
- No paid API call of any kind: no cloud subject, no judge, no calibration provider (owner decision D2). Cloud logic is proven on constructed rows or stubbed HTTP; real cloud evidence is reported as pending. No `.env` exists in the worktree; never create one or copy the main repo's.
- No model download, no Docker image pull, no system install, no account creation, no network write (no `git push`, no PR, no release, no deposit).
- Never edit an epic, the PRD, an `owner-questions` file, a spike, a proposed item, or any story's `depends_on` or acceptance. If the acceptance cannot be satisfied as written against the code, STOP: revert your changes (`git checkout -- <files>` and delete your new files) and report `ACCEPTANCE-CONFLICT: <one-line reason>` with the options you see.
- Do not edit the committed stores under `aidd_docs/results/` unless the orchestrator says this story is the bundle republication story.
- Do not run `pre-commit install` (it rewrites the shared hooks). Run hooks with `uv run pre-commit run`.
- English only in every repo artifact. Follow `CLAUDE.md` and `aidd_docs/memory/*` conventions. Surgical changes; match surrounding code.
- Read and write files in moderate pieces (a few hundred lines at most per read; split large writes). A stalled run gets resumed.

## Steps
1. Read `aidd_docs/memory/` first (all files except `external/`), then the story, its parent epic, every `depends_on` story, and the PRD sections its "Maps to:" line cites (PRD under `aidd_docs/`; find it with a search if the path is not given).
2. Run the skill `aidd-dev:01-plan` on the story, then `aidd-dev:02-implement`, then `aidd-dev:03-assert`. Put the plan and phase files in `aidd_docs/tasks/2026_10/2026_10_02_<story-slug>/` (story-slug = the story file name without `.md`, shortened sensibly if very long), matching the layout of `aidd_docs/tasks/2026_10/2026_10_01_unattended-implementation/` siblings (`plan.md` with front matter `objective`/`status`, `phase-N.md`, optional `evidence/`).
3. Local model runs, when the story needs one for its evidence: pinned build `C:\Users\Anael\llama_cpp\llama-b10537-bin-win-cuda-12.4-x64\llama-server.exe`, models in `D:\ia\models` (all roster GGUFs present). Set in the command's environment `LLAMA_SERVER_PATH`, `SLM_MODELS_DIR=D:\ia\models` and `QUALITY_PROVIDERS=local`, and point every results path (`QUALITY_RESULTS_PATH`, `RUNTIME_RESULTS_PATH`, fiche registry, records) into the story's task `evidence/` folder or a temp dir, never the committed stores. Save the decisive output in `evidence/`. Stop any llama-server you started by its PID; never `taskkill /IM`; a server already running before you started is not yours. Docker: only images already present locally (`docker image ls`), never pull. If a run cannot be made to work, ship code and tests anyway and report `evidence pending: local run (<reason>)`.
4. Before reporting, all of these must pass, run from the worktree root:
   - `uv run pytest` (coverage floor 95%);
   - `uv run pre-commit run --all-files`;
   - the secrets scan on every file you changed or created (`--all-files` hands that hook no filenames): `uv run python -X utf8 -m detect_secrets.pre_commit_hook --baseline .secrets.baseline <files>`. A public hash literal gets the repo's inline `# pragma: allowlist secret` comment;
   - `uv run python scripts/audit_dependencies.py` exits 0 (a new dependency only if the story names it, added with `uv add`);
   - `uv run wave-local-ai-v2-validate aidd_docs/results/quality-reference.jsonl` and `... runtime-reference.jsonl` exit 0.
   Fix until all pass.

## Report (keep it under 15 lines)
- `STATUS: READY-FOR-REVIEW` or `ACCEPTANCE-CONFLICT: ...` or `FAILED: <reason>`
- Task folder path.
- Files changed (short list).
- Test evidence: the exact pytest summary line (`N passed ... Total coverage: X%`) and the pre-commit result.
- Acceptance lines whose evidence is pending (operator, another machine, cloud), each with what it needs.
- Local-run evidence: produced (path) / not needed / pending (reason).
- Any contradiction between the code and the backlog you noticed (one line each).
