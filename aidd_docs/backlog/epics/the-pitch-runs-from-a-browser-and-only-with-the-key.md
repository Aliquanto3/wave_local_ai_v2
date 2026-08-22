---
type: epic
status: ready
source: aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md
goal: aidd_docs/product/wave-local-ai-v2.md
related_to:
  - aidd_docs/backlog/epics/clean-machine-runs-it-and-nothing-reaches-main-unchecked.md
  - aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md
  - aidd_docs/backlog/epics/quality-scored-comparison-first-three-use-cases.md
---

# Epic: The pitch runs from a browser, and only with the key

Given a completed benchmark run on the consultant's machine, a decision-maker reads the comparison from a second laptop in a browser — quality and runtime never on one table, every caveat label present — and the same address refuses a request that carries no API key.

## Context and Value

The audience is the third one the brief names and the only one that never sees the repo: "Client decision makers: see only the front end during a pitch; they judge the comparison, not the code" (`aidd_docs/product/wave-local-ai-v2.md`, Audience and Context). Behind them stands the consultant's own story — "I want to present the results from a browser rather than a terminal, so that a pitch doesn't depend on me running commands in front of a client" — and the demo story: "query the benchmark running on one of my machines from another of my machines during a live demo, using an API key" (PRD, User Stories).

Verified current state, at `a2ffe37`:

- **No HTTP service of ours exists.** `pyproject.toml` declares five runtime dependencies (`codecarbon`, `nvidia-ml-py`, `psutil`, `python-dotenv`, `requests`) — no FastAPI, no ASGI server. The twelve modules under `src/wave_local_ai_v2/` are all benchmark-side. There is no front-end directory and no Node manifest. The brief already named FastAPI + React as the stack; nothing has been built against that decision yet.
- **The only listening process is not ours.** `server.py:23` sets `HOST = "127.0.0.1"` for the llama.cpp subprocess the CLI launches. This epic introduces the first process of the project's own that a second machine can reach — so bind address, TLS and access control are new surface, not a hardening pass over something existing.
- **There is no key material and no certificate anywhere.** Secrets are `.env` only (`.env` and `.env.example` present), and nothing in the repo terminates TLS.
- **The tracked result files cannot answer "list the runs".** `aidd_docs/results/README.md` states the two `*-reference.jsonl` snapshots are curated evidence that "no CLI ever writes to", and both predate the `run_id` / `captured_at` keys. The files a pitch would actually show are the live `runtime.jsonl` and `quality.jsonl`, which are per-machine and gitignored.
- **Two of the mandatory caveat labels have no field to read.** A runtime row today carries `energy_method` (`measured_nvml` on the reference rows) but no `emissions_kg`, no emission factor, no region, no fiche hash, no N, mean or standard deviation, and no run provenance. A quality row carries `sampling` and `suite_accuracy` but no judge model id, no agreement figure and no single-judge flag. So of the four views the PRD's acceptance criterion names, the runs list cannot be built over tracked rows at all, and Methodology 11's single-judge flag has nowhere to come from yet.

What each of the four views can read today, and what it waits on:

| View (PRD acceptance criterion) | Available in a row now | Waits on |
| --- | --- | --- |
| List of runs | `run_id`, `captured_at` — live stores only | Run provenance on every row, criterion 19 — row epic |
| Quality table | `model_id`, `provider`, `task_suite`, item, expected and predicted label, `correct`, `suite_accuracy`, `sampling` | Judge model ids, agreement, single-judge flag, criteria 10 and 11 — quality epic |
| Runtime table with its fiche | CPU, RAM, GPU, driver, build, quant, flags, TTFT, throughput, VRAM, draw | Fiche content hash, N with mean and standard deviation, machine state, criteria 6, 7, 14 — row epic |
| Per-run energy detail | `energy_kwh`, `energy_method` | `emissions_kg`, emission factor, region, cloud Scope-3 formula id, criterion 15 — row epic |

The value has two halves, and the second is the one worth stating plainly. The first is reach: the other three epics make the numbers correct, checkable and reproducible, and none of them makes them legible to the person who signs. The second is that a dashboard is precisely where the project's honesty discipline is easiest to lose. A headline energy figure is exactly the thing that gets shown large and unlabelled, and a single-judge cloud score is exactly the thing that reads as agreed when nothing says otherwise. Methodology 15's `energy_method` label and 11's single-judge flag are rules about a *published number*, and this epic is where a number gets published to a human. Enforcing them at the surface — refusing to render rather than rendering bare — is this epic's contribution to the product bet, not a presentation detail.

## Boundaries

- Includes: a read-only FastAPI service over the two stores, exposing the four views the PRD names — the list of runs, the quality table, the runtime table with its fiche, and the per-run energy detail with its method, factor and region — plus judge agreement and the single-judge flag surfaced wherever a row carries them.
- Includes: keeping the two stores separate the whole way to the screen. Separate endpoints, separate tables, no join, and no response that returns both. The architecture memory's rule ("the two are never merged into a single table") is enforced by there being no endpoint that could.
- Includes: read-only in the strict sense — the service opens the JSONL files for reading and never writes. There is no endpoint, and no dashboard control, that produces or mutates a row.
- Includes: the store path as configuration, defaulting to the live per-machine stores rather than the tracked snapshots.
- Includes: a **declared-absent contract**, the rule that makes the surface honest before the neighbouring epics land and correct after. A field a row does not carry is reported absent, never defaulted and never inferred; the dashboard renders no headline energy number for a row without `energy_method`, and renders no judged score that carries neither an agreement figure nor the single-judge flag. Absence is shown as absence.
- Includes: a React dashboard readable at pitch distance — runs list, quality table, runtime table with the fiche visible on every runtime view (not behind a toggle), the energy headline labelled estimate or measurement with a drill-down to the calculation that produced it, and the model roster side by side with MoE and dense candidates on the same items.
- Includes: demo hardening — bind address configurable and defaulting to loopback, TLS with a self-signed or a provided certificate, a static API key read from the environment with the service refusing to start without one, every non-loopback request requiring that key, the key never logged and never written into the repo, and CORS restricted to the configured dashboard origin.
- Includes: the single-origin topology decided for this epic. The service serves the built dashboard bundle and the JSON endpoints on the same host and port, so the second laptop gets one URL and one certificate; the browser holds the key for the session only, entered once, and sends it as a header. CORS stays configured and restricted as defence in depth, not as the access mechanism.
- Includes: what a refusal looks like to a person. A keyless or wrong-key browser gets a refusal the consultant can show a client without embarrassment — not a stack trace, not a blank page, not a silent hang.
- Includes: the second machine's certificate step in the documented demo path, so the trust decision is made before the pitch rather than in front of the client.
- Includes: a security review of the service before merge, scoped to this demo's own threat model.
- Includes: defining the front-end build and its checks, since this epic brings the repo's first non-Python code.
- Excludes: writing rows. The two CLIs remain the only writers, and no view triggers a run or a re-run.
- Excludes: every piece of benchmark logic. No scoring, no agreement computed at read time, no methodology rule evaluated by the service. A number absent from a row is absent from the screen.
- Excludes: producing the fields the dashboard labels. Fiche hash, emissions, factor, region, repetition spread and run provenance belong to `every-published-row-explains-and-reproduces-itself`; judge ids, agreement and the single-judge flag belong to `quality-scored-comparison-first-three-use-cases`. This epic renders those fields and enforces their labels; it does not create them.
- Excludes: authentication beyond one static API key — no accounts, no roles, no per-user or rotating keys, no login session, no multi-tenant (PRD Non-Goals).
- Excludes: any public-internet posture. No reverse proxy, no hosting, no threat model past the LAN demo the PRD scopes.
- Excludes: shipping the service inside the container image, and the CI workflow that would run its checks — `clean-machine-runs-it-and-nothing-reaches-main-unchecked` owns both. The seam is named: this epic defines the front-end build and checks, that epic hosts them in the suite it already owns.
- Excludes: a database. The results store stays file-based JSONL read by the service for this release, per the stack decision already taken in the brief.

## Success Evidence

The pitch walk, done once for real. The consultant starts the service on the bench machine bound to its LAN address, opens the URL on a second laptop, enters the key once, and takes a client through the comparison without touching a terminal.

Five checks, each able to fail:

- A request from the second machine without a key, or with a wrong one, is refused — verified from that machine, not by reading the middleware.
- The service refuses to start when no key is in the environment, and the key's value appears in no log line and no tracked file — verified by searching the run's output for it, not by asserting the code never logs it.
- A row without `energy_method` yields no headline energy figure anywhere in the dashboard — verified by handing the service such a row and watching the number be withheld and its absence stated.
- A judged score carrying neither an agreement figure nor the single-judge flag is never rendered as a plain score — verified the same way, by removing the field and watching the surface refuse.
- Quality and runtime never arrive together — verified by there being no endpoint that returns both, not by a convention about how the pages are laid out.

Once `done`, record here what a client actually asked to see that the dashboard did not show, whether a certificate warning appeared in front of anyone, and whether the declared-absent contract ever had to be relaxed to make a pitch presentable.

## Dependencies and Unknowns

| Item | Kind | Handling |
| --- | --- | --- |
| Most fields the four views must label do not exist in a row yet | dependency | Owned by the two data epics per the table above. The declared-absent contract is what lets this epic ship honestly before they land and correctly after; neither direction blocks the other's start. |
| The tracked reference rows carry no `run_id`, so no runs list can be built over them | assumption | Accepted: the service reads the live per-machine stores by default, path configurable. The tracked snapshots stay acceptance evidence for the repo audience, not the pitch's data source. |
| Single-origin topology — the service also serves the dashboard bundle | decision | Taken this session over the two-origin alternative: one process, one certificate, one URL on the LAN, and CORS reduced from mechanism to defence in depth. The key is entered once in the browser and sent as a header. |
| A self-signed certificate warns the viewer, in front of a client | decision | Not left to the moment. The demo path documents trusting the certificate on the second machine beforehand, and the service accepts a provided certificate so a consultant holding a real one avoids the warning entirely. |
| The API key sits in the second machine's browser session | assumption | Accepted for this threat model: the PRD rules out a public-internet threat model and any auth beyond one static key. The dashboard holds it for the session and never persists it to disk. |
| "Refuses to start without a key" applies to a loopback bind too | decision | The PRD's criterion is unconditional and is taken literally rather than relaxed for local development. The documented setup generates a key; no value ships in the repo, including in `.env.example`. |
| First non-Python code in the repo needs a Node toolchain, a build step and its own checks | dependency | The CI epic scoped its suite to pure-Python tests on two operating systems. This epic defines the front-end build and its checks; extending that workflow to run them is agreed with that epic rather than assumed of it. |
| Whether the built bundle is committed or built during setup | decision | Not fixed at epic level — it changes the fresh-machine path the CI epic owns, so it is decided with that epic during delivery. |
| The dashboard's language | decision | English, per the repo's language rule; French pitch material is produced outside the repo. If a French-speaking decision-maker needs the surface itself translated, that is a later, explicit decision rather than a silent exception made mid-build. |
| FastAPI, an ASGI server and TLS support are new pinned runtime dependencies | dependency | Named by the brief's stack decision. They enter the same dependency and security gate the CI epic owns, which is where a finding against them blocks a merge. |
| The side-by-side MoE-versus-dense view has one local and one cloud model to show today | dependency | The roster is the quality epic's output. This epic builds a view that renders whatever the roster holds; a two-entry roster renders as two columns and grows without a change to the surface. |
| Scope of the pre-merge security review | decision | Reviewed against this demo's threat model — key handling and leakage, TLS configuration, bind address, CORS, traversal on the configurable store path, and what a refusal discloses — not against the public-internet model the PRD explicitly excludes. |

## Cancellation

n/a — not cancelled.
