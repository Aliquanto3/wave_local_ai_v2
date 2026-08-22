# Review: The fast gate refuses a bad commit before it is written

- **Verdict**: changes-requested — the three 🟡 are fixed in this branch, the two 🟢 are filed to `tech-debt.md`; no second round
- **Diff**: `d4be560...working-tree`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 3 warning, 2 minor

## Phases

### Phase 1 — The gate exists and the tree passes it

- [x] Exactly five hooks; the four commit-stage entries are the four before-commit commands in the documented order, pytest the only push-stage hook — `.pre-commit-config.yaml:7-36`, entries byte-identical to `aidd_docs/memory/coding-assertions.md:13-16`; `pre-commit run --all-files` listed 4 hooks, `--hook-stage pre-push` listed only `pytest`
- [x] Baseline holds no `.venv/` path, no untracked path, every key returned by `git ls-files`; surviving entries audited — `.secrets.baseline`: `"results": {}` (508 lines removed, all 36 prior entries gone), and `detect_secrets.filters.common.is_baseline_file` registered
- [x] Both git hook files exist after one install command; both `run --all-files` invocations report every hook Passed, nothing Skipped — `.git/hooks/pre-commit` and `.git/hooks/pre-push` present; ruff check / ruff format --check / mypy src/ / detect-secrets all `Passed`, pytest `Passed`

### Phase 2 — Three refused commits, kept as evidence

- [x] Falsification ran on a never-pushed branch, hooks shown installed before the first attempt — reflog: `chore/fast-gate-falsification` checked out 13:50:15, hook files written 13:49; branch absent from `git branch -a` and from `remotes/origin/*`
- [x] Three commits refused, each by a different named hook, each succeeding once its single defect was removed — `evidence.md:17,40,62` name `ruff-check`, `ruff-format` and `detect-secrets`; the three post-fix commits `a7a4771`, `2779364`, `09b0bc9` are all in the reflog
- [x] `evidence.md` carries six transcripts naming the refusing hook; no scratch file and no scratch branch survive — `evidence.md:8-83` (3 refusals + 3 passes + attribution table); `ls scratch_*` empty, scratch branch deleted

### Phase 3 — The docs and the memory stop saying manual

- [x] Neither memory file claims the gate is manual or unhooked; each names the hook file and the stage; neither claims server-side CI — `aidd_docs/memory/coding-assertions.md:7-9,20-22`, `aidd_docs/memory/architecture.md:9-16`; grep for "manually"/"no pre-commit" across `README.md`, `docs/`, `aidd_docs/memory/`, `CONTRIBUTING.md` returns nothing; architecture.md:14-16 points at the open CI story, which exists on disk
- [x] Both docs carry the same one-line install command, placed before a fresh clone's first commit — `docs/setup.md:27` (section 1, right after `uv sync`), `CONTRIBUTING.md:15`
- [x] Fresh-machine story reads `done`, baseline tech-debt row closed, no other line changed in either file — `a-fresh-machine-reaches-both-benchmarks-from-the-readme-alone.md:3`, `tech-debt.md:17`; `git diff` shows one changed line per file

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | rot | 3 | `docs/setup.md:30` | "`uv sync` is the only command needed before the platform-specific steps below" sits directly under a block that now holds two commands, so the sentence reads as contradicting the code it introduces. | Fixed: "the only command needed to reach the platform-specific steps below", and `pre-commit install` labelled the contributor step that running the benchmarks does not require. |
| 🟡 | conform | 3 | `aidd_docs/GUIDELINES.md:15-16` | The house-rules file every agent loads was the fourth copy of the gate and the only one left saying "run the fast gate", after three other sources were rewritten to say it is enforced — the exact drift `phase-3.md:72` names as the risk. | Fixed: both lines now name the stage and the single install command, plus the manual form. |
| 🟡 | code | 1 | `aidd_docs/memory/coding-assertions.md:16`, `CONTRIBUTING.md:23` | Row 4 is published as a copy-pasteable gate command, but `uv run detect-secrets-hook --baseline .secrets.baseline` with no filenames exits 0 having scanned nothing (verified: `exit=0`; the same command given a file carrying a fake AWS access key exits 1). The table is declared "the contract", so a false green sits inside it. | Fixed: both files now state that the hook hands row 4 the staged filenames, and that the manual equivalent of the whole gate is `uv run pre-commit run --all-files`. |
| 🟢 | code | 1 | `.pre-commit-config.yaml:25-29` | `detect-secrets` is the only hook without `always_run: true`; on an empty file set it reports `(no files to check)Skipped` while the three always-run hooks still execute (verified with `--from-ref HEAD --to-ref HEAD`). A deletion-only commit therefore passes with the secret gate never running. | Filed to `tech-debt.md`. Low impact — a deletion-only commit cannot introduce a secret. |
| 🟢 | conform | 1 | `.pre-commit-config.yaml:1-2` | No `minimum_pre_commit_version`, though `default_install_hook_types` needs pre-commit ≥2.18 and the `pre-commit`/`pre-push` stage names need ≥3.2. `uv run` resolves ≥4.6.2 from `uv.lock`, but a contributor on a globally installed older binary gets an obscure parse error. | Filed to `tech-debt.md`. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (9/9)                                        |
| Files checked | `.pre-commit-config.yaml`, `.secrets.baseline`, `CONTRIBUTING.md`, `docs/setup.md`, `aidd_docs/memory/architecture.md`, `aidd_docs/memory/coding-assertions.md`, `aidd_docs/backlog/tech-debt.md`, `aidd_docs/backlog/stories/a-fresh-machine-reaches-both-benchmarks-from-the-readme-alone.md`, `aidd_docs/tasks/2026_08/2026_08_22_fast-gate-pre-commit-hook/evidence.md` |
| Unchecked     | none                                              |
| Unplanned     | none in the tracked diff. `.coverage` sits untracked in the tree but predates the branch (mtime 09:02 versus branch cut 13:49) and is already an open `tech-debt.md` row from `fresh-machine-onboarding`. |
