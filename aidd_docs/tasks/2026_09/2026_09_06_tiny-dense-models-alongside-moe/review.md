# Review: Tiny dense models compared alongside the MoE flagship

- **Verdict**: changes-requested
- **Diff**: `main...feat/dense-roster`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_09_06
- **Findings**: 0 critical, 5 warning, 6 minor

## Phases

### Phase 1 — The three dense entries and their weights on this machine

- [x] Three GGUF files exist under `SLM_MODELS_DIR` in per-model directories, each byte size equal to the plan's table — `Get-FileHash`/`Get-Item` on `D:\ia\models\{Qwen3-0.6B,Qwen3-1.7B,Qwen3-4B}`: 639,446,688 / 1,834,426,016 / 2,497,280,256 B, exact match
- [x] Three lowercase 64-hex checksums recorded, each traceable to its file — `aidd_docs/roster/models.json:43,77,111`, `docs/setup.md:243-247`, `tests/test_roster.py:388,397,406`; all three recomputed off disk and equal
- [x] Four entries at `roster_version` 2; each dense entry declares `kind: "dense"`, `n_cpu_moe: null`, `load_mode: "auto"`, no MoE-offload flag; MoE entry unchanged — `aidd_docs/roster/models.json:2,37-138`; the MoE block is byte-identical in the diff (only `roster_version` and the three appended entries changed)
- [x] `load_roster` returns four entries with no `RosterError`; every `sha256` matches disk; `pytest tests/test_roster.py` and the fast gate green — `759 passed`; `ruff check` / `ruff format --check` / `mypy src/ scripts/` / `detect-secrets` all Passed
- [x] `docs/setup.md` reaches the same three files from repo, revision, file name and checksum, and states the total disk cost — `docs/setup.md:207-280` (4.63 GiB total, largest 2.33 GiB)

### Phase 2 — The dense launch seam and each entry's real `-ngl`

- [x] `SERVER_N_CPU_MOE` unset → `host_n_cpu_moe is None`; set → value and validation unchanged — `src/wave_local_ai_v2/settings.py:126,252-261`; `tests/test_settings.py:114-156`
- [x] MoE at default settings still builds the byte-identical baseline; dense builds the same list minus `--n-cpu-moe`, with `--load-mode auto` — `src/wave_local_ai_v2/server.py:66-83`; `tests/test_server.py:44,126-175`
- [x] `pytest` green including a dense entry given an explicit offload value refusing with `RosterError` and spawning nothing — `tests/test_server.py:178-197`
- [x] Each dense entry's `n_gpu_layers` is one a live launch reached ready with, and the observed VRAM figure is recorded — the three committed fiches carry `-ngl 99` with no `--n-cpu-moe`; load-time VRAM in `docs/setup.md:352-355` (4377 / 5537 / 5961 MiB), generation-time in `aidd_docs/results/README.md:397-399`
- [x] `docs/setup.md` explains the unset/set semantics and carries a copy-pasteable loop over all three entries and both suites — `docs/setup.md:299-345` (PowerShell and POSIX)

### Phase 3 — The live runs, model by model

- [x] The pilot's outcome is written down with its `failure_counts` and one verbatim completion, the decision it drove is stated, and no prompt, cap or suite was edited — `aidd_docs/results/README.md:309,315-319,362-370`; no `suite-definitions/` or suite module in the diff, so `PROMPT_SET_HASH` did not move (the completion's provenance is finding F2)
- [x] Three runtime rows, one per dense entry, each with five counted repetitions, spreads, `unreliable`, machine state, energy and cost — `runtime.jsonl` rows `68a5e1df` / `e5714fcb` / `f8678fe0`, all `repetitions_n: 5`, `warmup_count: 1`, `cooldown_s: 10.0`
- [x] Six local batches — three models × two suites — each its own `run_id`, headline score, per-language breakdown and failure counts — `d7f08b1a` / `c836bacc` / `9dd45420` (20 rows each) and `350cac2f` / `c370c862` / `80eec0cd` (21 rows each), all `roster_version` 2
- [x] The google comparator rows identified by `run_id` and suite version and cited unchanged — `1f3c94b9` (classification `suite_version` `"2"`) and `80803767` (translation `"1"`), `gemini-3.5-flash-lite`, no new google rows in the diff
- [x] `wave-local-ai-v2-validate` exits `0` over both live stores and every cited fiche is committed — re-run here: `checked 432 row(s)`, exit `0`; all 432 rows' `fiche_hash` resolve against `aidd_docs/results/fiches/`

### Phase 4 — The side-by-side record

- [ ] A dated section with one table per use case and one runtime table, four models each, run ids, quants and flag sets; **every number traces to a row and a committed fiche**; the generation gap, the quant asymmetry and the untouched bundle each stated — tables, run ids, quants, flag sets and all three caveats are present and every quality figure matches its rows exactly, but four published items do not trace: the RSS column (F1), the classification completion (F2), the section's schema/bundle provenance sentence (F3) and the 4B completion's "verbatim" claim (F4)
- [x] The CHANGELOG names the three entries, the roster bump, the launch seam, the settings change and every divergence — `CHANGELOG.md:12-70,388-399`; "Five divergences" matches `plan.md` D1-D5 and the story's own table
- [x] `cli.md`, `architecture.md`, `README.md` and `docs/setup.md` describe the shipped behaviour, with no remaining claim that the roster ships one entry or that `SERVER_N_CPU_MOE` defaults to 37 — grepped across all four; every such claim is rewritten
- [x] The story's status and divergence record are updated, the live findings are filed as tech debt rather than patched, and the fast gate and test suite are green — `stories/tiny-dense-models-compared-alongside-moe.md:3,24-42`; three entries appended to `tech-debt.md:109-111`

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 | functional | 4 | `aidd_docs/results/README.md` | Phase 4 criterion 1's "every number traces to a row and a committed fiche" does not hold. Four published items are mis-derived or unsourced; the four rows below are its instances, not a fifth problem. | Apply F1-F4. |
| 🟡 | rot | 4 | `aidd_docs/results/README.md:397-400`, `README.md:51` | The runtime table publishes `process_rss_bytes` as MiB under an `MB` label (1028 / 2172 / 4077 / 14520), and the root README derives "1.0 GB" / "14.5 GB" from it. The flagship row is 15,225,831,424 B = 15.2 GB, the figure this repo already publishes for that same row (`aidd_docs/tasks/2026_08/2026_08_22_three-amigos-row-epic/delivery.md:42`), so "14.5 GB" matches neither GB nor GiB. Rounding is also inconsistent (4076.49 MiB → 4077, 14520.98 MiB → 14520). | Publish byte-derived decimal MB — 1078 / 2277 / 4275 / 15226 — and make the root README "1.1 GB" against "15.2 GB". The 1/14th ratio is unaffected. |
| 🟡 | fit | 4 | `aidd_docs/results/README.md:362-370` | The `Qwen3-0.6B` / `billing-02` completion is presented in the same row-quoted style as the translation one, but no classification row in the store carries `subject_output` — it is `null` on all 280 classification rows, this run's included. The text can only come from the direct `/completion` probe the truncation-defect section describes at `:435`. Phase 4's own edge case is "a number that cannot be traced to a run id and a fiche is cut, not softened". | Name the provenance in one clause: from the direct probe below, because classification rows do not persist `subject_output`. |
| 🟡 | rot | 4 | `aidd_docs/results/README.md:274-277` | "Not part of the committed bundle. These rows live in the untracked live stores ... at `schema_version` `"10"`" is false for three rows the section's own tables cite: the flagship runtime row `f7faeef7...` **is** in `runtime-reference.jsonl` at `schema_version` `"7"`, and the two `1f3c94b9...` classification rows are live-store rows at `"8"`. | Scope the sentence to the dense rows and say where each cited comparator actually lives and at which schema. |
| 🟡 | rot | 4 | `aidd_docs/results/README.md:345-361` | The `Qwen3-4B` `fr-de-03` block is introduced as "verbatim from the row's `subject_output`" but stops at `**Note:`, ~40 words before the completion ends (it ran the 128-token cap dry). The prose then calls `**Note:` "trailing", which the row contradicts. | Mark the cut with an ellipsis and drop "trailing", or quote the remainder. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/server.py:66-68` | `resolved_n_cpu_moe` takes `Any` from `entry.validated_host["n_cpu_moe"]` (`validated_host` is `dict[str, Any]` and `roster._parse_entry` type-checks only `sha256`). The `--n-cpu-moe` value can now reach the command line straight from JSON without ever passing `_require_numeric`; a string there would make `validate_host_fit`'s ceiling check raise `TypeError` instead of `RosterError`. | Annotate `resolved_n_cpu_moe: int \| None`, and type-check `validated_host.n_cpu_moe` in `_parse_entry` the way `sha256` already is. |
| 🟢 | code | 2 | `src/wave_local_ai_v2/settings.py:252-261` | "Unset" is now decided in two places — `os.environ.get("SERVER_N_CPU_MOE") is None` here and the same test inside `_require_numeric` — and the branch passes a `default` its own comment calls unreachable. Two definitions of one meaning. | Add an `_optional_numeric` wrapper (or let `_require_numeric` take `default=None`) so "unset" is decided once. |
| 🟢 | rot | 2 | `src/wave_local_ai_v2/quality_cli.py:96-97` | "The local server is launched with the runtime benchmark's validated flag set, which samples at `--temp 1.0` with no seed" is now only the flagship's; the three dense entries launch at `--temp 0.6`. The point (the sampler is pinned per request, so the server's own values are irrelevant here) still stands. | Say "the selected entry's flag set, whatever its sampler" instead of naming `1.0`. |
| 🟢 | rot | 2 | `docs/setup.md:92` | "`--n-cpu-moe 37` (the `SERVER_N_CPU_MOE` host setting, no longer a `server.py` constant)" now attributes 37 to the env var, but unset it comes from the flagship entry's own `validated_host`. | Attribute it to the entry, with `SERVER_N_CPU_MOE` named as the override. |
| 🟢 | rot | 4 | `aidd_docs/results/README.md:294-296` | "with under 200 MiB to spare" has no figure behind it in that file: the runtime table's own `6115` of `6144` is 29 MiB, and the 183 MiB the phrase comes from is a load-time `nvidia-smi` read published only in `docs/setup.md:352-355`. | Say which reading it is, or cite the load-time figure alongside. |
| 🟢 | rot | 4 | `README.md:48-49` | "4.63 GB" / "2.33 GB" are GiB values labelled GB (`docs/setup.md` and the CHANGELOG both say GiB). Follows the file's pre-existing "17.7 GB", so it is a file-wide convention slip rather than this diff's invention. | Relabel the file-size figures in `README.md` as GiB in one pass. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 95% (18/19)                                       |
| Files checked | `aidd_docs/roster/models.json`, `src/wave_local_ai_v2/{server,settings,quality_cli,__init__}.py`, `tests/test_{roster,server,settings,launch_byte_identical}.py`, `aidd_docs/results/README.md`, `aidd_docs/results/fiches/{f804bee0,067530ef,dfd5a5ea}...json`, `aidd_docs/results/{runtime,quality}.jsonl` (live, untracked), `docs/setup.md`, `README.md`, `CHANGELOG.md`, `.env.example`, `.secrets.baseline`, `aidd_docs/memory/{cli,architecture}.md`, `aidd_docs/backlog/{stories/tiny-dense-models-compared-alongside-moe.md,tech-debt.md}`, `D:\ia\models\{Qwen3-0.6B,Qwen3-1.7B,Qwen3-4B}\*.gguf` |
| Unchecked     | Phase 4 criterion 1 (every number traces to a row and a committed fiche) — fix |
| Unplanned     | none — every changed file appears in a phase's architecture projection |
