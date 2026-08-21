# Audit: original expectations vs specs vs implementation

- **Date**: 2026-08-21
- **Source of truth for expectations**: the founding Claude Chat prompt (French), restated below as E1..E14.
- **Spec artifacts inspected**: `aidd_docs/product/wave-local-ai-v2.md` (product brief), `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` (PRD), `aidd_docs/backlog/` (1 epic, 4 stories), both plans under `aidd_docs/tasks/2026_08/`, `aidd_docs/memory/*`.
- **Implementation inspected**: `src/wave_local_ai_v2/*` (13 modules), `tests/*` (55 tests), repo root, GitHub remote (`gh api`).
- **Gates re-run today**: `uv run pytest -q` -> 55 passed; `uv run ruff check .` -> all passed; `uv run ruff format --check .` -> 63 files formatted; `uv run mypy src` -> no issues (13 files).

## 1. Expectation coverage matrix

Legend: **Spec** = where the expectation is written down; **Impl** = what exists in code/repo; **Status**: done / partial / spec-only / missing.

| # | Expectation (from founding prompt) | Spec | Impl | Status |
| --- | --- | --- | --- | --- |
| E1 | Time to first token | PRD goals; brief domain table | `timings.py` parses llama-server `ttft_ms`; server-reported only, independent cross-check attempted and reverted (`__init__.py:178-193`) | partial (done, uncorroborated) |
| E2 | Tokens/second | PRD goals | `prompt_tok_per_s`, `gen_tok_per_s` from server timings; validated against baseline | done |
| E3 | Environmental impact: energy AND carbon | PRD goals + AC ("headline number + retrievable calculation"); brief gotcha on `energy_method` | `energy.py` stores `energy_kwh` + `energy_method` only. **Carbon (kg CO2e) is not stored** (`tracker.final_emissions_data.emissions` discarded). No Scope-3 estimate for cloud models (PRD Dependencies names it). No "headline vs detailed calculation" split | partial |
| E4 | Memory consumed (RAM/VRAM) | PRD goals | `gpu.py` (VRAM used MiB, GPU draw W), `timings.read_process_rss` (process RSS) | done |
| E5 | Task performance across 10 use cases: classification, translation, doc comparison, text rewriting, code, agentic planning, agentic tool calling, web search, RAG answer, multilingual EN/FR/DE | PRD goals + AC (each use case has a suite or is explicitly marked out of scope); epic 1 scopes classification + translation + rewriting only and defers the other 7 to "later epics" that do not exist | Classification only: 10 hand-written items, exact-label match, Qwen3.6 vs Mistral. Translation and rewriting: stories `ready`, no plan, no code. Remaining 7: no epic, no story, no code | partial (1/10 implemented, 2/10 storied, 7/10 PRD-only) |
| E6 | Dense models proposed where more relevant (e.g. classification) | PRD goal + AC; `context_input/model_candidates.md`; story 4 (`tiny-dense-models-compared-alongside-moe.md`, `ready`) | None. Both CLIs hardcode `Qwen3.6-35B-A3B` (`__init__.py:26`, `quality_cli.py:28-29`) | spec-only |
| E7 | Hosted on GitHub, presentable to clients in pitches | PRD overview; brief audience "client decision makers see only the front end" | Repo public at `github.com/Aliquanto3/wave_local_ai_v2`; `origin/main` holds docs-only commits (`e4c06b6`), feature branch **never pushed**; `README.md` is **0 bytes**; no front end | partial (hosted, not presentable) |
| E8 | Python back end + React front end; scripts first to get early results | Brief summary names FastAPI + React. **PRD has no goal, story, or AC for the API or the front end** | Scripts-first: yes (`wave-local-ai-v2`, `wave-local-ai-v2-quality` entry points). No FastAPI, no React, no `frontend/` dir | scripts done; API/front **missing from PRD and code** |
| E9 | SOTA on-prem gen-AI tooling (uv not pip, etc.) | Architecture memory (uv, llama.cpp, ruff, mypy) | uv 0.11.7 + `uv.lock`, llama.cpp b10537, ruff/mypy, `requests` only (no SDKs by decision) | done |
| E10 | Particular care on benchmark test design so results are truly relevant | PRD says "defensible" and "reproducible" but sets **no measurable rigor criterion** (no seed/temperature policy, no repetition count, no spread reporting, no minimum suite size, no prompt-versioning rule). No spec artifact | Local generation runs at `--temp 1.0 --top-p 0.95` with **no seed** (`server.py:30-34`); Mistral call sends **no temperature, no seed** (`mistral_client.py:35`). Brief's own definition ("quality score: reproducible given model + prompt + seed") is therefore not met. Runtime harness is single-shot while `context_input/baseline_qwen36.md` itself requires `-r 5` minimum and says nothing under 10% spread is reliable. Classification suite = 10 items | **missing in spec, weak in code** |
| E11 | Reproducible on other machines when cloned from GitHub | PRD goal + AC (fresh clone or container image, documented setup, no manual fixes) | `uv.lock` present; `.env.example` present; `README.md` empty; no `Dockerfile`/compose; `N_CPU_MOE=37`, `THREADS=8`, model filename and `LLAMA_CPP_BUILD="b10537"` hardcoded for the laptop (`server.py:24-29`, `__init__.py:25-27`); llama-server binary is an external, undocumented download | partial |
| E12 | CI/CD best practices: automated tests, versioning, hooks, containerization | PRD goals + AC (check suite must pass before mergeable; tag + changelog per release; container image). Epic 1 **explicitly excludes** these and points to "a separate, parallel epic" that was never written | **0 GitHub Actions workflows** (`gh api .../actions/workflows` -> 0); **no `.pre-commit-config.yaml`**, no hooks in `.git/hooks` (memory `architecture.md:9` and `coding-assertions.md:7` claim pre-commit "wires the fast gate" - false); no `CHANGELOG.md`; no git tag; no `Dockerfile`; no Dependabot/pip-audit; `main` unprotected; `pre-commit` and `detect-secrets` are installed as dev deps but unwired | spec-only (PRD), no epic/story, **not implemented** |
| E13 | Security for on-prem hosting + API-key auth for the two-machine demo | PRD goal + AC + non-goals (API-key-gated demo only, no multi-tenant); brief open decision. No epic/story; no threat-model/spec | Nothing to secure yet (no server process of ours). Good hygiene present: `.env` gitignored and untracked, llama-server bound to `127.0.0.1`, `.secrets.baseline` exists (but hook unwired). No API key, no auth, no CORS/bind policy | spec-only |
| E14 | Internet: web-search tool(s); Mistral + Google AI Studio as judges and as benchmark subjects | PRD goal + AC (>=2 web-search tools compared; 2 judges + agreement); story 2 (`judge-scoring...`, `ready`) | Mistral as **subject**: done (`mistral_client.py`). Google AI: no client. Judge role + inter-judge agreement: not started. Web search: no story, no code | partial (1 of 4 roles) |
| E15 | Code architecture, modularity, documentation, maintainability; showcase AI-built code quality to developer clients | PRD goal ("repo demonstrates engineering quality"); memory files | Small clean modules with docstrings, typed, 55 stubbed tests, two AIDD reviews on file. Weak spots: `README.md` empty; `aidd_docs/GUIDELINES.md` and `CONTRIBUTING.md` still hold template placeholders; both CLIs are hardcoded single runs with duplicated model constants; no coverage tooling (v1 reported 86.5%); `cli.md` memory stale (does not list `wave-local-ai-v2-quality`, says "implementation in progress") | partial |
| E16 | Developed with the AIDD framework | Memory bank, brief, PRD, epic, stories, plans, reviews all present | No `spec` artifact (`aidd-pm:04-spec`) anywhere; backlog, PRD and full-branch review are **untracked** (never committed); `GUIDELINES.md` unfilled | partial |

Counts: done 3 (E2, E4, E9) / partial 8 / spec-only 3 (E6, E12, E13) / missing-from-spec 2 (E8 API+front, E10 rigor).

Your suspicion is half right: CI/CD and security **are** in the PRD (goals + acceptance criteria), but they were never decomposed into an epic/stories/plan and nothing is implemented. The two things that are genuinely **absent from the specs** are the API + React front end (only named in the brief's summary sentence) and a measurable benchmark-rigor policy.

## 2. Cross-cutting findings

### 2.1 Spec gaps (PRD level)

1. No goal/AC for the FastAPI back end or the React front end (only "client decision makers see only the front end" in the brief). The API-key demo AC implies an HTTP surface that is nowhere specified.
2. No measurable benchmark-rigor policy: seeds, temperature, repetitions (N >= 5 per the baseline note), spread reporting (mean +/- std), minimum items per suite, prompt versioning, contamination avoidance, judge prompt versioning, agreement metric definition (which statistic: Cohen's kappa? exact-match rate?).
3. Carbon is conflated with energy: PRD says "carbon/energy figure" but the implemented schema carries energy only. The Scope-3 cloud estimate is in Dependencies, not in an AC.
4. Web-search tool comparison has an AC but no candidate tools, query set, or scoring rule even at a sketch level (PRD open question; still open).
5. Multilingual EN/FR/DE is listed as a use case but has no definition (its own suite? a dimension of every suite?).

### 2.2 Decomposition gaps (PRD -> backlog)

Only one epic exists. Missing epics the PRD requires:

- Engineering credibility infrastructure: CI (lint/type/test/coverage/secrets/dependency scan), pre-commit, Dockerfile + compose, release tag + CHANGELOG, README/setup for fresh-machine reproduction, branch protection.
- Measurement methodology: seed/temperature pinning, repetitions + spread, suite sizing rules, carbon fields + cloud Scope-3 estimate, headline vs detailed calc, fiche completeness (RAM speed, build auto-detected, optional signature/hash).
- API + front end + API-key remote demo.
- Second cloud provider + judge machinery (Google AI client, judge prompts, agreement) - partly covered by story 2 but Google client is a prerequisite not spelled out.
- Remaining use cases: doc comparison, code generation, agentic planning, tool calling, web search (>=2 tools), RAG answer, multilingual.

### 2.3 Memory / doc drift

- `architecture.md:9` and `coding-assertions.md:5-15`: pre-commit "wires the fast gate" -> no config exists, no hook installed. Either wire it or reword.
- `cli.md`: missing `wave-local-ai-v2-quality`; says "implementation in progress".
- `codebase-map.md`: no `tests/`, no `aidd_docs/results/`, no `aidd_docs/backlog/`.
- `GUIDELINES.md`, `CONTRIBUTING.md`: template placeholders still in place.
- `pyproject.toml`: `description = "Add your description here"`.

### 2.4 Branch hygiene (blocks everything else)

- Uncommitted: the full-branch review's two warning fixes (`quality_cli.py` shape guard + early key check, already applied in the working tree and covered by `test_quality_cli.py`), `CLAUDE.md` rules, `.secrets.baseline` regeneration, the runtime review's extra section.
- Untracked: `aidd_docs/backlog/`, the PRD, the full-branch review.
- `feat/runtime-measurement-harness` not pushed; `origin/main` is docs-only.

### 2.5 Implementation correctness of what exists

Both plans were reviewed (`approve` for runtime harness; `changes-requested` for the full branch with 2 warnings, both now fixed in the working tree). Code matches its plans. The caveats that matter for the founding expectations:

- TTFT is server-reported, uncorroborated (documented, acceptable for now).
- Quality scores are not reproducible (temp 1.0, no seed) - contradicts the brief's definition of a quality score.
- Runtime is single-shot; no repetition/spread.
- Carbon not persisted.
- `LLAMA_CPP_BUILD` is a constant, not detected from the binary; a different binary silently mislabels the fiche.

## 3. Plan to close the gaps

Conventions used below:

- **Model/effort** follows `CLAUDE.md` tiers. Haiku 4.5 low = trivial; Sonnet 5 medium = routine; Opus 5 high/xhigh = design, ambiguity, independent review. Fable 5 is not needed for any step here.
- **/clear**: "yes" when the step only needs files on disk (plans, PRD, memory); "no" when it depends on decisions made in the same conversation.
- AIDD dev loop for every story: `aidd-dev:01-plan` -> /clear -> `aidd-dev:02-implement` -> (same context) `aidd-dev:03-assert` -> /clear -> `aidd-dev:05-review` -> `aidd-vcs:01-commit` -> `aidd-vcs:02-pull-request`. For small, well-bounded stories, `aidd-orchestrator:01-sdlc` runs that loop autonomously in one shot.

### Step 0 - Close the current branch (today)

| Sub-step | Skill | Prompt | Model / effort | /clear |
| --- | --- | --- | --- | --- |
| 0.1 Finish the runtime review file | none (manual edit or ask) | "In `aidd_docs/tasks/2026_08/2026_08_21_runtime-measurement-harness/review.md`, fold the `### Independent re-derivation` section into `## Verification` (row `Unplanned`) and fix the findings header count so the file matches the review template." | Haiku 4.5 low | yes |
| 0.2 Commit in atomic slices | `aidd-vcs:01-commit` | "Commit the working tree as separate conventional commits: (1) `fix(quality): guard /completion shape and check Mistral key before local suite` (quality_cli.py, tests), (2) `docs: add PRD, backlog epic and stories, branch review`, (3) `chore(claude): add model/effort and next-skill rules` (CLAUDE.md), (4) `chore: regenerate detect-secrets baseline`. Do not push yet." | Sonnet 5 medium | yes |
| 0.3 Push + PR + merge | `aidd-vcs:02-pull-request` | "Push `feat/runtime-measurement-harness` and open a draft PR to `main` summarizing the two implemented plans and the review verdicts." Then merge it yourself on GitHub (no CI yet to wait on). | Sonnet 5 medium | no |

### Step 1 - Repair the specs (PRD and memory), before any new code

| Sub-step | Skill | Prompt | Model / effort | /clear |
| --- | --- | --- | --- | --- |
| 1.1 Shadow scan the PRD | `aidd-refine:03-shadow-areas` | "Scan `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md` for blind spots. Known suspects: no API/front-end goal or AC, no measurable benchmark-rigor policy (seed, temperature, repetitions, spread, suite size, prompt versioning, judge agreement metric), carbon vs energy conflation, undefined multilingual use case, web-search tool set undefined." | Opus 5 high | yes |
| 1.2 Refine the PRD | `aidd-pm:03-prd` | "Refine the existing PRD using the shadow report at `<path from 1.1>`. Add: (a) a goal + AC for a FastAPI results API and a React front end used in pitches, (b) a Benchmark Methodology section with measurable AC: every generation pinned to seed + temperature recorded in the row; runtime rows carry N>=5 repetitions with mean and std; each suite has a minimum item count and a version id; judged scores define the agreement statistic; (c) carbon (kg CO2e) persisted next to energy, plus a Scope-3 estimate for cloud rows; (d) a definition of the multilingual use case. Keep everything else." | Opus 5 high | no (keep 1.1 context) |
| 1.3 Refresh memory + fill placeholders | `aidd-context:02-project-memory` | "Refresh `aidd_docs/memory/`: `cli.md` must list both entry points; `architecture.md` and `coding-assertions.md` must stop claiming pre-commit is wired until it is; `codebase-map.md` must add `tests/`, `aidd_docs/results/`, `aidd_docs/backlog/`. Fill `aidd_docs/GUIDELINES.md` and `CONTRIBUTING.md` placeholders with this repo's real rules (English only, stubbed tests only, quality/runtime split, conventional commits)." | Sonnet 5 medium | yes |
| 1.4 Commit | `aidd-vcs:01-commit` | "Commit as `docs(prd): add API/front-end and benchmark-methodology criteria` and `docs(memory): refresh memory bank and guidelines`." | Haiku 4.5 low | no |

### Step 2 - Write the missing epics and stories

Run `aidd-pm:07-epic` once per epic, /clear between each (they only need the PRD on disk). Then `aidd-pm:02-user-stories` per epic, /clear first. Suggested epics and the prompt for each:

| Epic | Prompt for `aidd-pm:07-epic` | Model / effort |
| --- | --- | --- |
| E-A Engineering credibility infrastructure | "Frame an epic from the PRD for the engineering-credibility infrastructure epic 1 explicitly deferred: GitHub Actions CI (ruff, ruff format, mypy, pytest with coverage, detect-secrets, pip-audit/uv audit), `.pre-commit-config.yaml` wired and installed, `Dockerfile` + compose for a reproducible run, release tagging + `CHANGELOG.md`, README with fresh-machine setup (including llama-server binary acquisition), branch protection requiring CI. Outcome: a client engineer clones or pulls the image and reproduces a run; every merge is CI-gated." | Opus 5 high |
| E-B Measurement methodology | "Frame an epic making benchmark results defensible per the PRD's new methodology section: seed + temperature pinned per request for local (llama-server `/completion` params) and cloud (Mistral `random_seed`/`temperature`) and recorded in every row; runtime runs repeated N>=5 with mean/std and a `thermal_state` hint; carbon persisted; cloud Scope-3 estimate; fiche carries RAM speed and auto-detected llama.cpp build; server flags (threads, n-cpu-moe, model) configurable, not hardcoded." | Opus 5 high |
| E-C Results API + front end + API-key demo | "Frame an epic for a FastAPI service exposing quality and runtime tables (read-only), a React dashboard presentable in a client pitch (quality table, runtime table tagged by fiche, energy headline with drill-down, judge agreement), and the two-machine demo: bind address configurable, API key required for non-loopback access, CORS restricted, `.env`-only secrets. Non-goal: user accounts." | Opus 5 high |
| E-D Second provider and judge machinery | "Frame an epic for Google AI Studio as a second cloud provider (subject + judge), the judge protocol (versioned judge prompts, rubric, two judges from different families), and inter-judge agreement reporting - the prerequisite for epic 1 story 2." | Opus 5 high |
| E-E Remaining use cases | "Frame an epic sequencing the seven deferred use cases: document comparison, code generation, agentic planning, agentic tool calling, web research with >=2 search tools, RAG answer generation, multilingual EN/FR/DE. Each must land as its own story with a suite definition, scoring rule (deterministic or judged), and harness capability needed (tool-call transcript, retrieval corpus, search tool adapter)." | Opus 5 high |

Then for each epic: `aidd-pm:02-user-stories` with prompt "Slice `<epic path>` into ordered stories, each with acceptance that maps to a PRD AC." Sonnet 5 medium, /clear yes. Optional but worthwhile on E-B: `aidd-pm:08-three-amigos` (Opus 5 high) to stress the methodology before building.

Commit after each epic/story batch with `aidd-vcs:01-commit` (Haiku 4.5 low).

### Step 3 - Implement, in this order

Each line = one story through the dev loop. Model/effort given per phase: plan / implement / review.

| Order | Story (epic) | Why this order | Skills + prompt seed | Model / effort |
| --- | --- | --- | --- | --- |
| 3.1 | Pre-commit config + hooks installed + memory claim made true (E-A) | 1-hour win; makes every later commit gated | `aidd-orchestrator:01-sdlc`: "Implement story `<path>`: add `.pre-commit-config.yaml` running ruff check, ruff format, mypy src, detect-secrets with the existing baseline; document `uv run pre-commit install` in README." | Sonnet 5 medium end to end |
| 3.2 | GitHub Actions CI on push/PR (E-A) | Unblocks branch protection and the PRD AC "must pass before mergeable" | `aidd-dev:01-plan` then `02-implement`: "Workflow `ci.yml`: uv setup, `uv sync`, ruff check, ruff format --check, mypy src, pytest with coverage artifact, detect-secrets, dependency audit. Windows and Ubuntu matrix for the pure-Python tests (no llama-server)." Then enable branch protection requiring it. | plan Sonnet 5 medium / implement Sonnet 5 medium / review Opus 5 high |
| 3.3 | README + setup doc + pyproject description (E-A) | Repo is currently not presentable (0-byte README) | `aidd-dev:02-implement` from a short plan: "README: what it is, hardware class, setup with uv, `.env` keys, llama-server acquisition, run the two CLIs, results layout, quality/runtime split, energy_method caveat." | Sonnet 5 medium |
| 3.4 | Seed/temperature pinning + recorded in rows (E-B) | Cheapest fix to the biggest credibility hole; touches both CLIs | `aidd-dev:01-plan`: "Add `seed` and `temperature` to `/completion` and Mistral payloads from settings (defaults seed=42, temperature=0 for quality runs; runtime run keeps baseline sampling but records it); persist both in every row; tests assert they are sent." | plan Opus 5 high / implement Sonnet 5 medium / review Opus 5 high |
| 3.5 | Repetitions + mean/std + configurable flags + carbon persisted (E-B) | Completes runtime defensibility and portability to the Tour machine | plan: "N repetitions per runtime row set (env `RUNTIME_REPETITIONS`, default 5), aggregate row with mean/std per metric plus raw rows; persist `emissions_kg`; move `THREADS`, `N_CPU_MOE`, model file into settings with current values as defaults; detect llama.cpp build from `llama-server --version`." | Opus 5 high / Sonnet 5 medium / Opus 5 high |
| 3.6 | Dockerfile + compose + tag v0.1.0 + CHANGELOG (E-A) | Closes the container and release ACs | `aidd-orchestrator:01-sdlc` for Docker; then `aidd-vcs:03-release-tag`: "Cut v0.1.0 with notes covering the runtime harness, classification scoring, CI, Docker." | Sonnet 5 medium; tag Haiku 4.5 low |
| 3.7 | Google AI client as subject (E-D) | Prerequisite for judge + second comparison point | dev loop; plan prompt: "Mirror `mistral_client.py` for Google AI Studio generateContent, same error type pattern, same stubbed tests, key in settings/.env.example." | Sonnet 5 medium / Sonnet 5 medium / Opus 5 high |
| 3.8 | Rewriting suite + two judges + agreement (epic 1 story 2 + E-D) | Proves judged path | dev loop; Opus for plan (judge rubric design is a tradeoff-heavy step) | Opus 5 xhigh / Sonnet 5 medium / Opus 5 high |
| 3.9 | Translation suite, deterministic (epic 1 story 3) | Second deterministic use case, uses the pinned seeds from 3.4 | dev loop | Sonnet 5 medium / Sonnet 5 medium / Opus 5 high |
| 3.10 | Dense roster across the three suites (epic 1 story 4) | Answers the founding "dense where relevant" question | dev loop; plan must include model download doc and per-model flag sets (dense = no `--n-cpu-moe`) | Opus 5 high / Sonnet 5 medium / Opus 5 high |
| 3.11 | FastAPI results API + API key + bind policy (E-C) | First externally reachable surface; run `/security-review` before merge | dev loop; add `security-review` skill on the PR, and `aidd-dev:07-refactor` security axis if it flags anything | Opus 5 high / Sonnet 5 medium / Opus 5 high + security-review |
| 3.12 | React dashboard (E-C) | Pitch artifact | dev loop + `aidd-dev:11-browser-qa` for evidence videos | Opus 5 high / Sonnet 5 medium / Opus 5 high |
| 3.13 | Remaining use cases (E-E), one story each | Widest scope, last | dev loop per story; web-search story needs a spike first: `aidd-pm:05-spike` "Compare candidate search tools (self-hosted e.g. SearXNG vs one hosted API) for cost, rate limits, determinism of results" | spike Opus 5 high; stories Sonnet 5 medium / Opus 5 high review |

Milestone checks: after 3.6 and after 3.12, run `aidd-dev:04-audit` ("Audit the codebase across all seven pillars, read-only") with Opus 5 high, /clear yes, and feed the report into `aidd-dev:07-refactor` if anything ranks high.

### Context hygiene rules for the whole plan

- /clear before every `01-plan`, every `05-review`, every `04-audit`, every epic/story generation: these must read from disk, not from conversation residue.
- Do not /clear between `02-implement` and `03-assert`, nor between 1.1 and 1.2 (the shadow report informs the PRD refine).
- After a `05-review` returns `changes-requested`, fix in the same context (the findings are live there), then /clear and re-run review.
- Keep `aidd_docs/memory/` current after any step that changes stack, CLI surface, or gates (1.3 is the first pass; repeat after 3.2, 3.6, 3.11).
