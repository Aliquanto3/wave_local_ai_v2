# Review: a model below its declared minimum refuses, and the refusal is published

## Round 1

Scope: the uncommitted working tree on top of `5c06009` (24 modified files, plus untracked `preflight.py`, `tests/test_preflight.py` and this task folder).

VERDICT: PASS

Gates: `uv run pytest -q` => `2410 passed, 2 warnings in 157.45s`, coverage 98.31%. `ruff check` => all checks passed. `ruff format --check` => 688 files already formatted. `mypy src/ scripts/` => no issues in 65 files. The test run wrote nothing to `aidd_docs/results/refusals/`, which does not exist. `git check-ignore` confirms the path is tracked (not ignored).

### Acceptance, line by line

1. Requirements declared per entry and per mode, each with its source. **Proven, with VRAM declared as an honest absence.**
   - The shape is enforced by `roster._parse_requirements`, and an entry without the block is refused by `load_roster` (`test_a_roster_entry_missing_its_requirements_is_refused`, `test_a_malformed_requirement_is_refused_by_name`).
   - Flagship gpu RAM 15.23 = max `process_rss_bytes` 15225831424 in `runtime-reference.jsonl` (`test_the_shipped_gpu_ram_minimums_are_the_published_peaks`).
   - The 1.7B (2277 MB) and the 4B (4275 MB) match `aidd_docs/results/README.md:1099-1100`.
   - The 0.6B cpu_only 4.77 = 4761899008 in the named-run-profiles evidence.
   - Disk = `bytes_on_disk`, rounded up to two decimals.
   - The three cpu_only "lower bound" values (max of the gpu peak and the weights' size) are labelled as such in `read_from` and in `docs/setup.md`. Each is derived from published figures, so none is invented.
   - VRAM is `not_yet_declared` (null value, with the reason stated). This is justified: published `vram_used_mib` is device-wide, and the 4B's 6115 MiB exceeds the laptop's 5.1 GB allocatable on a run published as successful, so declaring it would refuse a run that is known to work. "None is invented" outranks "declares VRAM" here.
   - `docs/setup.md` section 1.2 states that a too-low declaration surfaces as a run that starts and then fails.
2. Pre-flight before the weights are looked for and before `llama-server` starts. **Proven.**
   - All three writers call `preflight.enforce` right after `profiles.resolve_for_run` and before the model path is resolved: `__init__.py:276`, `quality_cli.py:288`, `judge_probe.py:483`.
   - The writer tests delete the weights and assert "model file not found" is absent, `running_server` and `probe_build` are not called, and exit is 1 (`test_a_run_below_its_declared_minimum_refuses_before_the_weights_and_any_spawn` ×3).
   - Observed VRAM comes from the machine's declared allocatable value, falling back to NVML. Free disk is read only while the weights are absent (`test_observe_*`).
3. The refusal names the requirement, mode, declared and observed values, exits non-zero, and writes no row. **Proven** (`test_each_requirement_refuses_alone_naming_itself_and_the_mode` and the three writer tests: no results file).
4. A raised declaration refuses and a lowered one runs. **Proven** in code (`test_a_raised_declaration_refuses_and_the_lowered_one_runs_on_one_machine`) and live on the laptop:
   - `evidence/runtime-raised.log`: 64 GB declared against 33.72 GB observed, exit 1, one record.
   - `evidence/runtime-restored.log`: exit 0, one schema-"26" row.
   - `validate.log`: `checked 1 row(s)`, exit 0.
5. Nothing is substituted, and a refused gpu run names the cpu_only profile. **Proven.**
   - `test_a_refused_gpu_run_names_the_cpu_only_profile_and_runs_nothing`, `..._with_no_cpu_only_profile_names_none`, `test_a_refused_cpu_only_run_offers_no_other_mode`.
   - In all three writer tests the server is never started.
6. One refusal record per refusal, carrying every field, never read as a row, in its own tracked per-machine file. **Proven.**
   - `REFUSAL_FIELDS` covers every field the story lists. The record carries `refusal_contract_version` and `record_kind` in place of `schema_version`, and `validate_refusal` refuses a record that has one. This is sound: a row view's schema floor can never select a refusal record (`test_a_refusal_record_is_never_read_as_a_runtime_row`).
   - The record is written to `REFUSALS_DIR/<machine_id>.jsonl`, default `aidd_docs/results/refusals/`, which is tracked.
   - Nothing is committed there, which is correct: the story asks only for the laptop evidence in `evidence/`.

Legitimately pending (D1, epic level, not this story): epic success check 5, the professional PC refusing the flagship under cpu_only (17.74 GB declared against ~17 GB decimal). No acceptance line and no "Evidence it publishes" item of this story requires it. **The story can be marked `done` now.**

Blocking findings: none.

### Non-blocking findings

1. `models.json` (0.6B `gpu.ram_gb.read_from`) and `docs/setup.md:79` cite "1077411840 of the published row, README 1078 MB". That byte count is from `tasks/2026_10/2026_10_02_gpu-cpu-never-share-a-fiche/evidence/runtime.jsonl`, not the published row (1077411840 B is 1077 MB, not 1078). The value 1.08 is still correct. Fix: cite the README's 1078 MB only, or name the evidence file.
2. `preflight.first_failure`: an unreadable free disk (`_free_disk_gb` OSError => None) is skipped silently, while unreadable RAM or VRAM raises `PreflightError`. The comment "either way the run needs no further disk" is false for the unreadable case. Rare, because `SLM_MODELS_DIR` must exist at settings load.
3. No tech-debt entry tracks the two declared gaps: no per-process VRAM peak yet, and the cpu_only lower bounds. The 0.6B shows the bound rule under-reads by 4.4x (it gives 1.08 against a measured 4.77). Fix: file one entry so these are measured before the campaign.
4. The refusal record has no `tree_dirty`. The live record cites `commit_sha` 5c06009, which does not contain `preflight.py`. Rows carry this flag; consider adding it to the refusal contract.
5. `README.md` says a run "refuses before it downloads or loads anything". The harness never downloads anything, so this only holds if the operator runs before step 3 of `docs/setup.md`, and setup.md does not say to.
