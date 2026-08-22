# Three Amigos, delivery lens: Every published row explains and reproduces itself

- **target**: `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md`
- **snapshot**: `status: ready`, epic body at working-tree state, repo at `df8e294` (branch `main`, clean apart from untracked `.coverage` and this task directory)
- **role**: delivery (feasibility, dependencies, interfaces, constraints, operability, delivery unknowns)
- **verdict**: `revise`

Supported amendments resolve every finding below. Nothing here prevents the epic from being sliced, and no finding needs a decision the project cannot take itself. Two findings (D1, D5) change what a criterion means rather than how it is built, so they are worth settling before the first story rather than during it.

## Sources inspected

| Source | What it was read for |
| --- | --- |
| `aidd_docs/backlog/epics/every-published-row-explains-and-reproduces-itself.md` | the target |
| `aidd_docs/backlog/epics/{clean-machine-runs-it-and-nothing-reaches-main-unchecked,any-open-ended-output-carries-two-judges-or-an-honest-flag,the-pitch-runs-from-a-browser-and-only-with-the-key,no-use-case-is-silently-absent,quality-scored-comparison-first-three-use-cases}.md` | what each consumer waits on, and what it claims to own |
| `aidd_docs/tasks/2026_08/2026_08_21-wave-local-ai-v2-benchmark-suite-prd.md:36-54,89-109` | criteria 1-19 verbatim, and the acceptance criteria that cite them |
| `src/wave_local_ai_v2/{__init__,quality_cli,server,results,hardware,energy,gpu,timings,settings,classification_suite}.py` | the code every criterion has to change |
| `aidd_docs/results/{runtime,quality}-reference.jsonl`, `aidd_docs/results/runtime.jsonl`, `aidd_docs/results/README.md` | the rows that already exist, their shapes, and the curation rule behind the tracked ones |
| `aidd_docs/memory/{testing,architecture,coding-assertions}.md`, `aidd_docs/backlog/tech-debt.md`, `tests/test_cli.py` | the test layer's reach and the gate a story has to pass |
| Live probes on this machine (`psutil` 7.2.2, `pynvml` via `uv run`) | the criterion 7 spike's premise, checked rather than assumed |

## Findings

### D1 (material) - the fiche hash, computed over `flags` as they are written today, hashes a machine-local absolute path and cannot match across machines or after a model move

Criterion 14 says the fiche "carries CPU, RAM, GPU, driver, llama.cpp build, quant and flags, and is identified by a SHA-256 content hash". The flag list that would be hashed is written verbatim into the row and its first two elements are `-m` and the absolute model path:

```
"flags": ["-m", "D:\\ia\\models\\Qwen3.6-35B-A3B\\Qwen3.6-35B-A3B-UD-IQ4_XS.gguf", "-ngl", "99", ...]
```
(`aidd_docs/results/runtime-reference.jsonl`, both rows; produced by `server.build_flags`, `src/wave_local_ai_v2/server.py:47-81`, from `settings.slm_models_dir`, which is operator-configured, `src/wave_local_ai_v2/settings.py:41`)

Two consequences, both delivery-visible. The same machine changes its fiche hash when `SLM_MODELS_DIR` moves, so criterion 8's "same hardware fiche" comparison silently loses its reference. And a client engineer reproducing on their own machine can never produce a matching hash, so the reproduction verdict has no path to `reproduced` for the audience the epic is written for. The flag list also carries `--host`/`--port`, which describe the harness's local socket and not the machine.

Proposed amendment: state in Boundaries that the fiche hash is computed over a normalised projection of the fiche, with the model identified by its roster entry id and checksum rather than by its filesystem path, and with host and port excluded. Keep the raw flag list on the row as evidence; hash the normalised form.

### D2 (material) - criterion 6 needs a repetition topology decision, and the harness already documents why both obvious choices are wrong

The epic's unknowns table treats N>=5 purely as wall-clock: "N>=5 repetitions multiplies every runtime measurement's wall-clock by ~5 on the single development machine". The measurement semantics are the harder half, and the code has already recorded the trap in both directions:

- Repetitions inside one server process: the first request after a fresh model load carries a cold-start tax the harness accepts deliberately, and the documented fix contaminated the measurement. "a warm-up request tried to remove it, but bled its context into the measured request via the shared `-np 1` slot and wrecked `gen_tok_per_s` (26 -> 11.8)" (`src/wave_local_ai_v2/__init__.py:29-40`). So repetition 1 is systematically slower than 2..5, and the standard deviation criterion 7 tests against is inflated by a known artifact rather than by machine state.
- One server process per repetition: every repetition pays a full model load. `process_rss_bytes` on every reference row is about 15.2 GB with `--load-mode none` set (`server.py:71-72`, `architecture.md` Gotchas: "`--load-mode none` is required when `--n-cpu-moe` is set"), so the load is a 15 GB read, not a warm mmap. The load time is not measured anywhere in the repo today; `READY_TIMEOUT_S = 120.0` (`server.py:39`) is the only bound.

Proposed amendment: add a row to Dependencies and Unknowns naming the repetition topology as a decision taken during delivery, with the discarded-first-repetition option stated explicitly (run N+1, discard the cold one, record that the discard happened), and add "measure model load time once" as the cheap prerequisite that makes the wall-clock estimate real instead of assumed.

### D3 (material) - criterion 7's 10% unreliable flag will fire on this laptop for a thermal reason, and that is the honest outcome, not a bug to tune away

The only sustained-session evidence in the repo is a 34% swing attributable to GPU thermals, not to variance: `gen_tok_per_s` of 26.0 and 25.5 on the two curated rows against 17.1, 18.1, 18.8, 18.3 on rows from the same day, which `aidd_docs/results/README.md:27-30` excludes precisely because "their `gen_tok_per_s` of 17-18 was measured while this machine's GPU was in `sw_thermal_slowdown`". `__init__.py:184-199` records the same event confirmed via `nvidia-smi --query-gpu=clocks_event_reasons`.

Across the three rows measured at the final prompt length, spread is about 3.9% (26.046, 25.484, 26.480), comfortably inside the 10% threshold. Across a heated session it is 34%, far outside it. So N>=5 back-to-back repetitions on a laptop is not only 5x slower, it changes the thermal regime the measurement is taken in, and the flag exists to catch exactly that.

Proposed amendment: say so in the unknowns table. The repetition loop needs a stated inter-repetition posture (back-to-back, or a fixed cooldown, or cooldown until a GPU temperature ceiling), because that choice determines whether a published row describes a cold machine or a saturated one, and both are defensible only if declared. This is the same discipline `energy_method` already applies.

### D4 (material) - the criterion 7 spike is framed around the wrong sensor; the signal that explains this machine's variance is already reachable

The epic frames the spike as "whether a temperature is obtainable at the project's privilege level" for CPU package temperature. Measured on this machine, at ordinary privilege:

- `psutil.sensors_temperatures` does not exist on Windows at all. `hasattr(psutil, 'sensors_temperatures')` is `False` on psutil 7.2.2, so it raises `AttributeError` rather than returning an empty mapping. The epic's premise holds, and is now verified rather than assumed.
- GPU temperature is available now, through the NVML path the repo already owns (`src/wave_local_ai_v2/nvml.py`, `gpu.py`). `nvmlDeviceGetTemperature` returned 48 C, and `nvmlDeviceGetCurrentClocksEventReasons` returned `0x24`, which in NVML's documented bitmask is `SwPowerCap | SwThermalSlowdown`, on an idle machine. Confirm the decode against NVML's header before relying on it, but the read itself costs nothing and needs no driver.
- `psutil.getloadavg()` on Windows is an emulation, and it returned `(0.0, 0.0, 0.0)` both immediately and 7 seconds later while `cpu_percent(interval=1)` read 3.1%. A load figure captured "at start" from `getloadavg` is a fabricated zero, which is precisely the unfalsifiable number this epic exists to remove.

The workload is GPU-bound, the one observed regression was a GPU thermal event, and the flag reason is already what the debug session used. A CPU package temperature obtained through an elevated vendor driver would be an operability cost paid for the less informative signal.

Proposed amendment: rescope the spike from "can we read CPU package temperature" to "which thermal and load signals actually explain observed runtime variance on this platform, at the project's privilege level", with GPU temperature plus clock event reasons as the expected answer, `getloadavg`'s Windows emulation named as unusable, and CPU package temperature degrading to a declared-unavailable state as the epic already proposes.

### D5 (material) - criterion 8 needs a reference-selection rule, and today no code may write to the file it would compare against

Criterion 8 makes runtime reproduction "the re-run's median falls within 10% of the reference row's median on the same hardware fiche". That turns the reference file from acceptance evidence into load-bearing machinery, and the repo's own rule currently forbids it being either written or, by implication, read as an input: "The two `*-reference.jsonl` files [...] are curated snapshots: no CLI ever writes to them" (`aidd_docs/results/README.md:3-5`).

Unanswered by the epic: which row is *the* reference for a given fiche hash and roster entry, who selects it, and where the verdict is computed (in the CLI at re-run time, or by a later comparison over the store). The pitch epic assumes the reading direction is settled and excludes computing anything at read time: "No scoring, no agreement computed at read time, no methodology rule evaluated by the service" (`the-pitch-runs-from-a-browser-and-only-with-the-key.md`, Excludes). So the verdict has to be produced and stored by the harness, and the harness needs a defined way to find the reference.

Proposed amendment: add reference selection to Boundaries as part of criterion 8, and state the mechanism at epic level as "the row records the run id of the reference it was compared against", so a verdict is auditable rather than recomputed.

### D6 (material) - the verdict has a third outcome the epic does not name

Criterion 14 invalidates rows whose fiche changed. Criterion 8 compares only against the same fiche. A driver update, a llama.cpp build bump, or a roster edit therefore leaves a re-run with no comparable reference. Both the epic's Success Evidence ("a verdict, reproduced or not reproduced") and the PRD acceptance criterion ("an explicit verdict of reproduced or not reproduced") admit only two states, so the harness would have to report `not reproduced` for a run that simply has nothing to compare against. That is a false negative published under the project's own honesty rule, and it is the default outcome for the client engineer reproducing on their own hardware, which the architecture memory already says is not comparable ("Runtime metrics are NOT reproducible across machines", `aidd_docs/memory/architecture.md:41`).

Proposed amendment: name a third state in Success Evidence, `not comparable`, with the reason recorded (fiche mismatch, roster entry mismatch, absent reference). It is a widening of the PRD's criterion in the direction the PRD's own discipline demands, so record it as a decision taken here rather than as an implicit reading.

### D7 (material) - criteria 6 and 15/16 collide: an aggregated row has five energy figures and one energy field

Criterion 6 makes a published runtime metric the median of at least five repetitions. Criterion 15 requires "every row carries `energy_kwh`, `emissions_kg`, the emission factor and region", and 16 requires "a local row carries an energy cost derived from a configurable kWh price". `measure_energy` wraps one call and returns one figure (`src/wave_local_ai_v2/energy.py:26-55`), and the same applies to the point reads on a row today: `vram_used_mib`, `gpu_draw_w`, `process_rss_bytes`.

So an aggregated row needs a stated rule per field: the energy of the median repetition, the sum across repetitions, or the mean. Each is defensible; none is obvious. A row that publishes a median throughput next to a single unlabelled energy figure invites exactly the objection this epic exists to prevent.

Proposed amendment: add one line to Boundaries stating that every non-timing measurement on an aggregated row declares its aggregation (which repetition or which statistic), consistent with how N, mean and standard deviation are already required for the timing fields.

### D8 (material) - the suite definition shape is claimed by two epics

This epic includes "3 generation caps in the suite definition; 4 suite size and language mix; 5 item provenance", plus "a one-time migration of the classification suite". No suite definition exists: `CLASSIFICATION_TASK_SUITE` is a module-level list of ten `TypedDict` items imported directly by the CLI (`src/wave_local_ai_v2/classification_suite.py:45`, `quality_cli.py:19`), with the suite id written as a string literal at the write site (`quality_cli.py:206`). Meanwhile `no-use-case-is-silently-absent.md` includes "**the suite seam** - a suite definition shape and a registry [...] The shape carries the fields the methodology already demands of every suite: generation caps [...] per-item language tags [...] provenance", and says it "consumes the gate `every-published-row-explains-and-reproduces-itself` ships; it does not reimplement it".

Both statements cannot hold as written: this epic must invent the shape in order to migrate classification onto it, and that shape is the seam the other epic claims. The consequence if left unresolved is either duplicated work or a gate that validates a shape nobody owns.

Proposed amendment: state the split explicitly in Boundaries. This epic ships the suite definition shape and its validation gate, sized for the one suite that exists; the use-case epic adds the registry and the second through seventh suites against it. Mirror the sentence in the neighbour's Excludes when that epic is next touched.

### D9 (material) - the epic's premise about jinja templating does not describe the code path in use

Context states: "There is no prompt-template version and no stored rendered prompt for the local provider. The quality row stores the pre-template prompt string; what llama.cpp's jinja templating actually sent is not recoverable."

Both CLIs post to the raw completion endpoint, not the chat endpoint: `POST http://{HOST}:{PORT}/completion` (`__init__.py:201-208`, `quality_cli.py:145-153`). That endpoint takes `prompt` verbatim and applies no chat template; `--jinja` (`server.py:62`) governs `/v1/chat/completions` and tool-call parsing. The `no-use-case-is-silently-absent` epic states the same thing from the other side: "The local call is the raw completion endpoint. `POST /completion` [...] not `/v1/chat/completions`" and owns the migration.

So today's stored prompt is byte-identical to what was sent, and the real gap is that the row does not record *which* path produced it. Criterion 2 becomes non-trivial only once the endpoint migration lands, in a different epic.

Proposed amendment: correct the Context bullet, and scope criterion 2 here to recording the endpoint, the template id and the template content hash on every row, with `none` as a legitimate template value for the raw endpoint. That keeps criterion 2 shippable now and correct after the migration, and it is what makes rows written on either side of the migration distinguishable.

### D10 (material) - unhardcoding the flags collides with the constraint that the runtime baseline is frozen

The epic includes "making the hardcoded server flags, model file and llama.cpp build roster- and settings-driven rather than constants". The code states the opposite constraint in two places: `server.py` docstring, "Reproduces the validated baseline command from `context_input/baseline_qwen36.md` verbatim", and `quality_cli.py:36-40`, "`server.build_flags` must not change, because the runtime harness is required to reproduce its validated command exactly, so the sampler is pinned per request instead".

These are reconcilable but not automatically: the roster's first entry has to pin the exact validated flag set byte for byte, or the republished reference rows stop being comparable to the two rows that currently carry the project's headline throughput claim. Note also that the quality CLI's per-request sampler override exists *because* the flags were immutable; once flags are roster-driven, that workaround becomes a second place where sampling is decided, and the two must not drift.

Proposed amendment: add a line to Boundaries stating that the roster's first entry reproduces the validated baseline flag set exactly, and that the per-request sampler override in the quality path stays the single source of quality sampling, so criterion 1's two halves do not end up contradicting each other.

### D11 (material) - the live per-machine stores are not regenerated, and the pitch epic's contract cannot read a mixed-schema file honestly

The epic handles the tracked rows: "republishing `aidd_docs/results/{runtime,quality}-reference.jsonl` under the new row schema. The tracked rows predate it and are not migrated in place." It says nothing about the append-only live stores, which is where every consumer actually reads. `runtime.jsonl` on this machine already holds three distinct shapes in ten rows: rows without `run_id`, two rows carrying an extra `ttft_wall_clock_ms` from the reverted streaming experiment, and one row with `run_id`/`captured_at`. `read_rows` returns raw dicts with no version key (`src/wave_local_ai_v2/results.py:38-43`), and the pitch epic's default data source is exactly these files: "the store path as configuration, defaulting to the live per-machine stores rather than the tracked snapshots".

That breaks the declared-absent contract's meaning. That contract says "a field a row does not carry is reported absent, never defaulted and never inferred", but it cannot distinguish "absent because this row predates the field" from "absent because the value was genuinely unavailable on this run", and those two are opposite claims: one is a stale row, the other is an honest degradation.

Proposed amendment: add `schema_version` to the row contract in Boundaries, and state what happens to a live store containing pre-schema rows (rotate on schema change, or leave in place and let readers filter by version). Either is fine; silence is not, because the neighbouring epic has already committed to a contract that needs the distinction.

### D12 (minor) - criterion 19 can record a commit sha today, and needs a dirty-tree state

The epic defers to the CI epic for a release identifier and says it "records the identifier available at run time and degrades explicitly when there is none". Splitting the two halves makes the seam cheaper: the commit sha is obtainable from git with no dependency on tagging, and the version can fall back to the packaged `0.1.0` that `pyproject.toml` already declares. What the epic does not name is the third state: a run from a dirty working tree cites a sha that does not describe the code that produced the row.

Proposed amendment: state that run provenance records the sha plus a dirty flag, and that a dirty-tree row is marked as such. It is one boolean, and it is the difference between provenance and a provenance-shaped field.

## Dependency order among the criteria

Ordered by what unblocks a consumer, not by criterion number. "Blocks" means the consumer's work cannot be validated without it, not that the consumer cannot start.

| Primitive | Criteria | Blocks | Blocked by |
| --- | --- | --- | --- |
| Row contract, writer gate, `schema_version`, run provenance | 19, D11, D12 | judge epic's additive fields; pitch epic's runs list, which has no source today because the tracked rows predate `run_id`; every later criterion, since each adds fields through the same gate | nothing. Commit sha from git, version from package metadata, both degrade explicitly |
| Versioned roster file, settings-driven flags/model/build | 13, and the unhardcoding in Boundaries | criterion 14 (a fiche is not an identity until its inputs stop being source constants); CI epic's portable container image, which it already defers to this epic; judge epic's model-family field, which it currently declares locally as a named seam | row contract, for where the citation lands |
| Fiche identity and invalidation | 14 | criterion 8's "same hardware fiche"; pitch epic's runtime table | roster (13), D1's normalisation decision |
| Suite definition shape, gate, classification migration | 3, 4, 5, 9 | use-case epic's six suites, which are "born compliant against that gate"; quality epic's translation and rewriting stories, both `ready` and both citing 4 and 5 | row contract; D8's ownership split |
| Energy widening, cost | 15, 16 | pitch epic's per-run energy detail, the only one of its four views blocked solely by this epic | row contract. Independent of everything else, which makes it the cheapest parallel track |
| Runtime repetition and spread | 1 runtime half, 6 | criterion 7's flag (no spread, no flag); criterion 8's median | row contract; D2's topology decision; D7's aggregation rule |
| Machine state and unreliable flag | 7 | criterion 8's thermal and load hints | repetition (6); the D4 spike |
| Reproduction verdict | 8 | the epic's own headline outcome | 6, 7, 14, plus D5's reference selection and D6's third state |
| Republished reference rows | the epic's Boundaries | pitch epic's ability to demo from tracked data rather than from an untracked local store | everything above, plus one measured session on the bench machine |

Two ordering facts worth stating plainly:

- **Nothing in the other four epics is blocked by more than two of these primitives.** The row contract and the suite gate carry almost all of the cross-epic weight. Shipping those two first converts every other consumer's dependency into a wait for a field rather than a wait for a design.
- **The seam with the CI epic is mutual but not circular.** That epic says "this epic provides the tag, version and sha; that epic writes them into rows", and this epic says it "records the identifier available at run time". Both are satisfiable immediately if the sha comes from git and the version from package metadata (D12), so neither epic needs to move first.

## Slice order

Nine slices. Each is independently mergeable and each ends with something a reviewer can fail.

1. **Row contract and writer gate.** One module both CLIs write through, carrying `schema_version`, `run_id`, `captured_at`, release version, commit sha and dirty flag. The gate refuses a row missing a required field. Unblocks the pitch epic's runs list and gives the judge epic the additive seam it has already written into its own boundaries. Fully testable under the existing stubbed layer.
2. **Energy, emissions, factor, region, cost.** A widening of `energy.py`'s `EnergyResult` plus a configurable kWh price. Independent of every other slice, and it is the only thing standing between the pitch epic and one of its four views. Run it in parallel with slice 1 if two tracks are available.
3. **Roster file and settings-driven flags.** Roster entry shape (repo revision, file, quant, checksum, licence, per-model flag set, model family), flags built from the entry, llama.cpp build read from the running binary rather than asserted (the child's stderr is already captured for the whole context, `server.py:181-191`, and the startup banner carries the build). First entry reproduces the validated baseline exactly (D10). Retires tech-debt entry `__init__.py:25,217`.
4. **Fiche identity and invalidation.** Normalised hash (D1), rows citing it, and the observable invalidation the Success Evidence demands.
5. **Suite definition shape and the classification migration.** Caps, stop sequences, context length, per-item language tag, per-item provenance, contamination-risk marking, indicative marking below 20 items, failed-generation scoring with its reason. Ten items to twenty under the EN/FR/DE mix. This is the gate two other epics are waiting on, and it does not depend on slices 3 or 4, so it can run in parallel with them.
6. **The criterion 7 spike.** Rescoped per D4. Half a day, and it decides the shape of slices 7 and 8.
7. **Runtime repetition.** N, median, mean, standard deviation, raw repetitions retrievable, sampling recorded on runtime rows, aggregation rule declared per non-timing field (D7), repetition topology decided (D2). The heaviest slice, and the one whose wall-clock cost is felt on every subsequent manual run.
8. **Machine state, unreliable flag, reproduction verdict.** Slices 7 and 8 could merge; keeping them apart means the spread machinery lands and can be observed before a verdict is built on top of it. Needs D5's reference selection and D6's third state settled first.
9. **Republish the reference files.** One measured session on the bench machine, with the README rewritten to describe the new schema and to keep its existing honesty note about why the old rows were not back-filled.

Slice 5 is the one to pull forward if a consumer epic starts before this one finishes, because it is what the use-case epic and two `ready` quality stories are waiting on. Slice 9 is the only slice that cannot be scheduled freely: it needs a bench machine, a quiet thermal window, and at least one roster entry, and the roster's model set is the quality epic's output rather than this epic's.

## Testability constraint that shapes the slicing

`aidd_docs/memory/testing.md` is explicit: "No tests should start a real llama.cpp server or call live cloud APIs; stub the HTTP client", and "the benchmark runner itself is the integration harness". Criteria 6, 7 and 8 are the first work in this project whose behaviour is a property of a loop over real measurements rather than of a pure function.

The way to keep them inside the existing test layer is to make every one of them a pure function over a list of measurements: aggregation (N, median, mean, standard deviation) over a list of floats, the unreliable flag over a spread, the verdict over two aggregates plus two fiche hashes. What then remains untested is only the loop that collects the measurements, which is the same exposure the harness already carries. The same applies to the writer gate, which is what makes the Success Evidence checks ("cannot be produced by the harness at all", "editing a fiche invalidates the rows citing its hash, demonstrably") verifiable with stubs rather than with a bench run.

## Questions

| # | Finding | Missing decision or evidence | What the answer unlocks |
| --- | --- | --- | --- |
| Q1 | D2, D3 | The repetition topology: one server process for all repetitions with the cold one discarded, or one process per repetition; and the inter-repetition posture, back-to-back or cooled | The wall-clock cost of a published runtime row, and whether criterion 7's flag measures machine state or the harness's own cold-start artifact. Everything in slices 7 and 8 |
| Q2 | D5, D6 | How a re-run finds its reference row, and whether `not comparable` is admitted as a third verdict | Criterion 8, and whether a client engineer reproducing on their own hardware gets an honest answer or a false `not reproduced` |
| Q3 | D1 | Which fields the fiche hash is computed over, and whether an absolute model path may appear in a published row at all | Criterion 14, criterion 8's comparison, and whether cross-machine reproduction is possible in principle |
| Q4 | D7 | The aggregation rule for energy, VRAM, GPU draw and RSS on an aggregated row | Criteria 15 and 16 on runtime rows, and the pitch epic's energy headline |
| Q5 | D8 | Which epic owns the suite definition shape, and whether the registry lands here or in the use-case epic | Slice 5's size, and whether the use-case epic's six suites build on a shape or invent one |
| Q6 | D11 | What happens to a live store holding pre-schema rows: rotate, or filter by `schema_version` at read time | The pitch epic's declared-absent contract, which currently cannot distinguish a stale row from an honest degradation |

Nothing above is decided here. Each proposed amendment is a supported revision to the epic text; the caller decides which to apply.
