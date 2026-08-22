# Review: fresh-machine-onboarding

- **Verdict**: changes-requested
- **Diff**: `443e710...working-tree`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 4 warning, 3 minor

## Phases

### Phase 1 — README as the entry point

- [x] README opens with what the benchmark is and names both audiences without following a link — `README.md:3-15`
- [x] Never-merged rule stated in prose, links `architecture.md` and `aidd_docs/results/README.md` — `README.md:17-22`
- [x] Hardware class above every download instruction — was met on `README.md:24-38` only, while the page carrying the 17.7 GB download stated no floor; fixed in session, `docs/setup.md:14-18` now names the floor and links the README section
- [x] Every `.env.example` key in the table, `GOOGLE_API_KEY` marked reserved — `README.md:52-59`
- [x] "no cloud credential" attached to `wave-local-ai-v2`, `MISTRAL_API_KEY` to `wave-local-ai-v2-quality` — `README.md:61-63`
- [x] Energy caveat names both `estimated_tdp` and `measured_nvml` plus the factor-2-3 qualifier — `estimated_tdp` was absent; fixed in session, `README.md:84-95` now lists all three `energy_method` values
- [x] `aidd_docs/backlog/` and `CONTRIBUTING.md` both linked and both exist — `README.md:89-90`

### Phase 2 — Fresh-machine setup walk + env hygiene

- [x] `uv sync` is the only setup command before the platform-specific steps, no GPU or key — `docs/setup.md:18-25`
- [x] Windows-CUDA, Windows-CPU and Linux x86_64 each name their asset and the release URL, `b10537` pinned as distinct — `docs/setup.md:29-54`
- [x] Source-build fallback present and not conditioned on today's release — `docs/setup.md:56-62`
- [x] Repo, revision, filename and sha256 together, verification command for POSIX and Windows in the same step — `docs/setup.md:66-102`
- [x] Target path matches `MODEL_RELATIVE_PATH` — `docs/setup.md:77` vs `src/wave_local_ai_v2/__init__.py:26` and `quality_cli.py:28-29`
- [x] The no-credential command and the `MISTRAL_API_KEY` command each named next to what they gate — `docs/setup.md:116-129`
- [x] Six keys still in `.env.example`, `GOOGLE_API_KEY` carries the reserved comment, `.gitignore` header has no French — `.env.example:1-7`, `.gitignore:12`

### Phase 3 — Contribution gate + cross-doc proof

- [x] No `{...}` placeholder, all five items present — `CONTRIBUTING.md:1-40`
- [x] Fast gate's four commands in `coding-assertions.md` order — `CONTRIBUTING.md:17-22` vs `aidd_docs/memory/coding-assertions.md:11-14`
- [x] Every relative link across the three pages resolves — 11 links extracted and resolved, 0 missing
- [x] README key set and `.env.example` key set identical, six each — `README.md:54-59` vs `.env.example:1-7`
- [x] CLI names spelled as `[project.scripts]` — `pyproject.toml:23-24` vs `README.md:54-68`, `docs/setup.md:119,128`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | functional | 1 | `README.md:79-84` | The energy caveat names `measured_nvml` and the factor-2-3 qualifier but never `estimated_tdp`, so the reader cannot map a row's `energy_method` value to the caveat. `energy.py:52-53` emits `estimated_tdp`, and `energy.py:34,46,50` emit a third value, `unavailable`, mentioned nowhere. | Name both `energy_method` values in the caveat, and state that `unavailable` means no figure was produced. |
| 🟡 | functional | 1 | `docs/setup.md:9-16` | The hardware floor (32 GB RAM, NVIDIA GPU, ~18 GB disk) exists only in `README.md`. `docs/setup.md` carries the 17.7 GB download at step 3 and states no floor, so a reader arriving via the developer link at `README.md:13-14` fetches gigabytes without ever seeing whether their machine qualifies. | Add a prerequisites bullet in `docs/setup.md:9-16` naming the floor and linking the README's hardware section. |
| 🟡 | rot | 1 | `README.md:61-62` | "it only talks to a local `llama-server`" is false. `measure_energy` (`__init__.py:214`) starts CodeCarbon's `EmissionsTracker`, the online tracker, which resolves geo metadata over HTTP (`emissions_tracker.py:1428-1431` → `geography.py:92-117`, geojs then `https://ipinfo.io/json`) and probes cloud metadata. The call is best-effort and non-fatal, but the claim reads as an offline guarantee in a project whose pitch is on-prem. | Narrow the claim to the credential (which is the acceptance criterion) and note the best-effort, non-fatal geo lookup CodeCarbon makes. |
| 🟡 | fit | 2 | `docs/setup.md:46-54` | The Windows-CPU and Linux x86_64 assets are CPU builds, offered with no statement of what they yield. `README.md:29-31` requires an NVIDIA GPU and `docs/setup.md:5-7` says step 4.2 needs a GPU-bearing machine, so the two CPU paths lead to a runtime row that is not comparable to the CUDA reference evidence, with nothing saying so. Section 2 warns only about the build tag, not the backend. | State under both CPU paths that a CPU build runs but its runtime rows are not comparable to `*-reference.jsonl`, the same way the build tag is qualified. |
| 🟢 | code | 2 | `docs/setup.md:106-109` | `cp` and `copy` share one ```sh block, so a POSIX reader pasting the block gets `copy: command not found` after the copy already succeeded. | Split into two blocks, one labelled POSIX, one labelled Windows. |
| 🟢 | fit | 2 | `docs/setup.md:19` | `git clone <this-repo-url>` leaves a placeholder in a copy-pasteable block though the remote is known (`git remote -v` → `https://github.com/Aliquanto3/wave_local_ai_v2.git`). | Inline the real clone URL. |
| 🟢 | rot | - | `.gitignore:12-24` | `.coverage` is a generated artifact sitting untracked in the working tree (`git status` → `?? .coverage`) while every other generated path is ignored in the Project section. The phase touched `.gitignore` and left the gap. | Add `.coverage` to the Project section. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (19/19) after the in-session fixes; 89% (17/19) as reviewed |
| Files checked | `README.md`, `docs/setup.md`, `CONTRIBUTING.md`, `.env.example`, `.gitignore` |
| Unchecked     | Energy caveat names `estimated_tdp` — fixed; hardware class above every download instruction — fixed |
| Unplanned     | `.coverage` present and untracked in the working tree, outside the plan's file list |
