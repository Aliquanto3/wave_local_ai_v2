"""The row contract: one required-field list per row kind, extended by every
later story rather than duplicated.

`append_row` (`results.py`) gates on `validate_row` before writing a line, so
an incomplete row can never land on disk. A key present with value `None` is
not missing -- several fields degrade to an explicit `None` on capture failure
(`hardware.py`, `timings.py`, `gpu.py`, `energy.py`) and are still complete.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Literal

from wave_local_ai_v2 import (
    aggregation,
    cost,
    engines,
    gpu,
    hardware,
    harness,
    judge,
    judge_protocol,
    machines,
    prompt_provenance,
    prompt_variants,
    roster,
    score_interval,
    suite_gate,
    timings,
)

# "2": the runtime row's shape changed incompatibly (a scalar `gen_tok_per_s`
# became a median over a repetition set). Quality rows move to "2" with it
# because the constant is shared -- splitting into per-kind versions is out
# of scope for this increment.
# "3": `fiche_hash` and `verdict` became required on both row kinds, and the
# ten flattened hardware/run fields left the runtime row (fiche_hash-reproduction-
# verdict increment).
# "4": `energy_method` is gone, replaced by three independently-labelled
# per-channel energy fields plus emissions/scope fields, on both row kinds
# (Story 15: rows-carry-per-channel-energy-emissions-and-their-scope-boundary).
# "5": twelve cost + derivation-input fields became required on both row
# kinds (Story 16: rows-carry-a-cost-and-what-it-was-derived-from).
# "6": `list_price_input_per_million` and `list_price_output_per_million`
# became required on both row kinds. `list_price_per_million_tokens` alone is
# a blended effective rate derived FROM cost_total, so a row carrying only it
# could not recompute its own cost -- the two rates the price table actually
# charges have to be on the row for Story 16's "carries what it was derived
# from" to hold.
# "7": `language_breakdown` (per-language accuracy/n/indicative) became
# required on quality rows (Story 20: the-classification-suite-reaches-
# twenty-items-across-three-languages).
# "8": `retries` and `resumed` became required on quality rows only (a
# rate-limited run persists, resumes and never re-pays) -- the runtime row is
# untouched, since resume and retry are quality-CLI-only in this story's scope.
# "9": a judged quality row carries a judge block -- each judge's own call
# record, the prompt/rubric provenance the score was produced under, either an
# agreement figure over two judges or the single-judge flag, the contested
# state, and the judge calls' egress and cost (`JUDGED_FIELDS`). Required only
# on a row that carries any of it, so a deterministic quality row -- today's
# classification rows, which declare no rubric -- validates unchanged.
# "10": a deterministic *graded* quality row carries a graded block -- the
# metric that produced the score and the parameters it ran under, the item's
# own score, the suite mean, the per-language breakdown, and the reference
# text the score was computed against (`GRADED_FIELDS`). Required only on a
# row that carries any of it, the same conditional shape "9" established, so
# an exact-match classification row and a judged probe row both validate
# unchanged and no reference bundle is regenerated.
# "11": `thinking_policy` became required on quality rows only -- the runtime
# row is untouched, since it runs no suite and renders no chat template. Added
# because the local subject path moved to the chat endpoint, where a
# thinking-by-default model spends its whole generation cap reasoning and
# returns an empty answer unless the suite says otherwise: the same model at
# the same cap on the same endpoint produces a score or no score depending on
# one request argument, so a row that does not name the policy cannot be
# compared to anything (the local-subject-prompts-are-never-chat-templated
# defect).
# "12": `active_window_s`, `idle_window_s` and `energy_window_method` became
# required on runtime rows only -- fixes finding C3 of the 2026-09-22 audit
# (`aidd_docs/tasks/2026_09/2026_09_22_audit/report.md`): the runtime row's
# energy/emissions/cost-per-token figures used to span the whole counted-
# repetition window, cooldowns included, biasing every fast model's figures
# upward. `energy_kwh` and its three per-channel siblings now sum each
# repetition's own isolated `start_task`/`stop_task` delta instead, and the
# three new fields name the method and the two window sizes that were
# measured, so a reader does not have to guess which span a row's numbers
# cover. Quality rows are untouched: the quality-side energy window (server
# launch plus model load) is a separate, still-open finding (W4).
# "13": every judge call record on a judged row carries six more fields --
# the provider that actually answered and where that was read from, the
# reasoning effort as the request carried it, and the reasoning-token count
# apart from the output tokens with where it came from (reported or derived
# from the response's totals), or null with its reason -- and each
# `judge_cost.per_provider` entry carries the reasoning tokens and the basis
# the provider bills them on (Story: every judge call names who answered,
# its reasoning effort, and its reasoning tokens). A record whose answering
# provider differs from its bound one is refused. Additive inside
# the judge block only: a deterministic quality row and every runtime row
# validate unchanged.
# "14": `prompt_variant_id`, `prompt_variant_version` and
# `prompt_before_template` (the prompt as the variant left it, before the
# engine's templating) became required on both row kinds (Story: every row
# names its prompt variant, and a baseline row carries the authored prompt).
# The variant must be registered at that version (`prompt_variants`), and a
# row declaring `baseline` must carry the item's authored text unchanged. A
# row below "14" is read under its own version and never back-filled with
# `baseline`: nothing on it says which prompt shape produced it.
# "15": `suite_level` (the level the row's suite was certified at,
# `development` or `publication`), `item_licence`, `item_source` and
# `item_source_revision` (the item's own declarations, copied from the suite
# definition) became required on quality rows only (Story: a suite is
# certified to its declared level, and every item names its licence and
# source). A hand-written item carries a licence and no source: its row holds
# the two source fields as `null`. A publication row holds all three. The
# declarations are the author's: nothing checks that a licence or a source is
# the true one. A row below "15" is read under its own version and never
# back-filled with `development`.
# "16": `subject_egress` became required on both row kinds (Story: every row
# records whether its prompt left the machine; owner decision Q72): `none`
# when the subject prompt was served on the machine, else the id of the cloud
# provider that received it. Never null -- a writer always knows where it
# sent a prompt -- held to `none` on a runtime row, and on a quality row
# never in contradiction with `provider`. It describes the subject call alone: the judge block's
# `judge_egress` stays as it is and is not merged into it. A row below "16"
# is read under its own version and never back-filled with `none`.
# "17": `retry_budget` and `partial_failure` became required on quality rows
# only (Story: a publication-size cloud batch survives its rate limits and
# resumes per item). `retry_budget` maps each cloud provider the row's batch
# called (subject and judges) to the retry total those calls drew from,
# derived from the batch's item count rather than one fixed total, and is
# `{}` for a batch that made no cloud call. `partial_failure` is `null` on a
# row whose batch was complete when the row was written, else the provider,
# item and reason of the call that stopped it: a cloud failure mid-batch now
# persists the items already answered instead of discarding them, and
# `--resume` completes the batch per item. A partial row publishes no
# suite-level score. The runtime row is untouched: it makes no cloud call
# and has no resume. A row below "17" is read under its own version and never
# back-filled.
# "18": eleven per-item measurement fields became required on quality rows
# only (Story: each quality item records the tokens and the first-token time
# its generation took; owner decision Q24 (a)). Until "17" a quality row
# carried tokens and energy as batch figures and no TTFT, so no per-item
# paired test was possible on either. The row now carries the item's own
# input and output tokens, its engine-reported first-token time under its
# `item_ttft_source` label (the runtime row's `ttft_source` discipline), and
# the prompt tokens the engine reused from its cache, each a value or null
# with its `*_null_reason` (never a zero); `item_measurement_kind` labels it
# a single per-item generation, not Methodology 6's aggregate (no warm-up
# exclusion, no repetitions); `item_first_in_batch` marks the batch's cold
# first generation. Energy stays per batch. The runtime row is untouched. A
# row below "18" is read under its own version and never back-filled.
# "19": `family` and `size_class` became required on quality rows only (Story:
# the composition check names every size class and refuses an unlabelled
# single-family one). `family` is the row's *subject's* family as
# `roster.family_of` resolves it -- never the family of the local entry a
# cloud row cites as the one it ran beside -- and `size_class` is the local
# entry's declared class, `null` on a cloud row, whose model has none. Both
# are required only on a row whose own `schema_version` is "19" or later
# (`SUBJECT_COMPOSITION_SCHEMA_VERSION`): a row below "19" still validates
# without them and is never back-filled. The runtime row is untouched.
# "20": `harness_id`, `harness_version` and `harness_prompt_overhead` became
# required on quality rows only (Task: register the closed harness candidate
# set and its three row fields; Methodology 23, owner answer Q33 (a)). The id
# is one of `harness.HARNESS_IDS`, closed at five; the version is read from
# the harness's installed package when the row is written; the overhead is
# `{"tokens", "null_reason"}`: per call, the engine's prompt-token count minus
# the item's own rendered prompt's (tool definitions included) under the row's
# tokenizer, or null with one of `harness.OVERHEAD_NULL_REASONS` --
# `unmeasurable` for a harness that rewrites rather than wraps the item's
# prompt -- and never a zero in place of a measurement. Owed only from "20"
# (`HARNESS_SCHEMA_VERSION`): a row below "20" still validates without them
# and is never back-filled. The runtime row is untouched.
# "21": `score_interval` became required on quality rows only (Story: every
# quality batch publishes its interval and what it could resolve;
# Methodology 24). One block per batch, identical on every row of it: the
# confidence level, resample count, method, seed, generator and draw
# procedure id (`score_interval.DRAW_PROCEDURE_ID`), then a `suite` cell and
# one `by_language` cell per language, each `{n, lower, upper,
# minimum_detectable_effect, null_reason}` -- three values, or none and one of
# `score_interval.NULL_REASONS`. Null exactly when the row publishes no suite
# score (a partial batch, a judge-probe row). Owed only from "21"
# (`SCORE_INTERVAL_SCHEMA_VERSION`): a row below "21" still validates without
# it and is never back-filled. The runtime row is untouched.
# "22": `engine_id` and `engine_build` (the inference engine that produced
# the row and its live-probed build) became required on both row kinds
# (Story: every row names the engine that produced it, and the fiche hashes
# it). A runtime row and a local quality row name an engine the tracked
# registry (`engines.py`) holds; a row no local engine produced (a cloud
# subject's quality row, the judge probe's cloud-subject row included)
# states `engine_id: "not_applicable"` with a null build. A judge-probe row
# whose subject is local carries `llama.cpp` like any local row. From this version a cited
# fiche is hashed under projection "2" (`ENGINE_FICHE_SCHEMA_VERSION`), which
# carries `engine_id`, `engine_build` and `engine_config_hash` in place of
# `llama_cpp_build`. Owed only from "22": a row below "22" still validates
# without them, is verified under projection "1", and is never back-filled
# with `llama.cpp`.
# "23": `machine_id` and `compute_mode` became required on both row kinds
# (Story: a GPU run and a CPU-only run never share a fiche; Methodology 21).
# A runtime row and a local quality row name a machine the tracked registry
# (`machines.py`) declares and `gpu` or `cpu_only`; a row no local model
# produced (a cloud subject's quality row) states `not_applicable` for both.
# From this version a cited fiche is hashed under projection "3"
# (`MACHINE_FICHE_SCHEMA_VERSION`), which carries both inside the identity, so
# a `gpu` and a `cpu_only` run of one model on one machine never share a
# fiche. Owed only from "23": a row below "23" still validates without them,
# is verified under projection "1" or "2", and is never back-filled.
# "24": `campaign_id` became required on both row kinds (Story: a campaign is
# declared as data, and an empty cell fails it; Methodology 22). A run started
# under a campaign (`CAMPAIGN_ID`, `campaigns.py`) stamps that campaign's id on
# every row; a run started under none states `NO_CAMPAIGN`, and a row no local
# model produced (a cloud subject's quality row) always does, since a campaign
# declares engines and a cloud subject runs on none. Owed only from "24": a row
# below "24" still validates without it and is never back-filled.
# "25": a `cpu_only` runtime row states `vram_used_mib: "not_applicable"`
# (`VRAM_NOT_APPLICABLE`) at the row level (its peak aggregate) and on every
# counted and warm-up repetition, and a `gpu` row never does (Story: every view
# names the machine and the mode, and a cpu_only row's VRAM reads not
# applicable; Methodology 21). `null` keeps meaning a VRAM read that failed.
# No field is added; a row below "25" is not re-checked and never rewritten.
# "26": `profile_id` and `profile_overrides` became required on both row kinds
# (Story: each model, machine and mode runs under its own named profile;
# Methodology 21). A runtime row and a local quality row name the run profile
# of their (roster entry x machine x compute mode) triple (`profiles.py`) and
# map every value the operator overrode to `{"profile": ..., "operator": ...}`
# (`{}` when the run is the profile as declared), so a row never claims a
# profile it did not run under. A row no local model produced (a cloud
# subject's quality row) states `PROFILE_NOT_APPLICABLE` for both. Owed only
# from "26": a row below "26" still validates without them and is never
# back-filled.
# "27": `prompt_variant_noop` became required on quality rows (Story: the
# terse-output variant runs every item and meets baseline in a paired test;
# Methodology 2, 22). A variant declares the task families it applies to; an
# item of any other family is still run, with its authored prompt unchanged,
# and its row states `true`. The gate checks the value against the registry
# for the row's `task_suite`, and checks `prompt_before_template` against the
# variant applied to the item's authored text for every variant, not only
# `baseline`. Runtime rows run one fixed prompt of no task family and carry
# no such field. Owed only from "27": a row below "27" still validates
# without it and is never back-filled.
# "28": `constraint_mechanism` and `constraint_grammar_hash` became required
# on quality rows (Story: the constrained-output variant runs under a
# llama.cpp grammar and names its mechanism; Methodology 2, 22). The
# mechanism the item's answer was decoded under (`gbnf`, or `none`) and the
# content hash of the grammar sent (null under `none`); the gate checks both
# against the registry for the row's variant and `task_suite`. Runtime rows
# run one fixed prompt of no task family and carry neither. Owed only from
# "28": a row below "28" still validates without them and is never
# back-filled.
SCHEMA_VERSION = "28"

# The two subject-composition fields "19" added, and the version from which a
# quality row owes them.
SUBJECT_COMPOSITION_FIELDS: frozenset[str] = frozenset({"family", "size_class"})
SUBJECT_COMPOSITION_SCHEMA_VERSION = "19"

# The three harness fields "20" added, and the version from which a quality
# row owes them.
HARNESS_FIELDS: frozenset[str] = frozenset(
    {"harness_id", "harness_version", "harness_prompt_overhead"}
)
HARNESS_SCHEMA_VERSION = "20"

# The interval block "21" added, and the version from which a quality row
# owes it.
SCORE_INTERVAL_FIELDS: frozenset[str] = frozenset({"score_interval"})
SCORE_INTERVAL_SCHEMA_VERSION = "21"

# The value `subject_egress` takes when the subject prompt never left the
# machine, and the `provider` a quality row names for a subject served by the
# local llama-server. Every other provider is a cloud one, and its id is the
# egress value.
SUBJECT_EGRESS_NONE = "none"
SUBJECT_PROVIDER_LOCAL = "local"

# The two values `thinking_policy` may take. This is the **suite's** declared
# policy, not a report of what each provider did with it: it is published on
# every quality row of a batch, cloud rows included, exactly as
# `stop_sequences` already is, and only the local path can currently enforce
# it (llama-server's `chat_template_kwargs`). What each provider was actually
# sent is the call-path fields' business. Recording it only where it is
# enforceable would make one field mean two things depending on which row you
# read it from.
#
# It sits with `max_output_tokens`, `stop_sequences` and `context_length`
# under Methodology 3 -- what a model is permitted to spend its cap on is the
# same class of constraint as how much cap it has, it belongs to the suite
# definition, and it is recorded per row.
THINKING_POLICY_DISABLED = "disabled"
THINKING_POLICY_ALLOWED = "allowed"
THINKING_POLICIES = frozenset({THINKING_POLICY_DISABLED, THINKING_POLICY_ALLOWED})

# What a row no local engine produced says in `engine_id` (a cloud subject's
# quality row): a stated non-applicability, never a null a reader could take
# for a missing value, and never `llama.cpp`. Its `engine_build` is null.
ENGINE_NOT_APPLICABLE = "not_applicable"

# The schema version at which `fiche_hash` (and `verdict`) became required.
# Fixed at "3" regardless of future `SCHEMA_VERSION` bumps: a stored row whose
# own `schema_version` is below this predates the fiche-hash contract
# entirely, so its missing `fiche_hash` is not an integrity failure the
# validator should treat as fatal (`fiche_validator.py`'s `legacy` class).
FICHE_HASH_SCHEMA_VERSION = "3"

# The schema version from which a cited fiche is hashed under projection "2"
# (`hardware.FICHE_PROJECTIONS`: the engine fields in place of
# `llama_cpp_build`), and from which a row owes `ENGINE_FIELDS`. Fixed at
# "22" like the constant above: which projection a stored fiche is verified
# under is decided by the citing row's own version, never by a field the fiche
# happens to lack.
ENGINE_FIELDS: frozenset[str] = frozenset({"engine_id", "engine_build"})
ENGINE_FICHE_SCHEMA_VERSION = "22"


# The schema version from which a cited fiche is hashed under projection "3"
# (`machine_id` and `compute_mode` inside the identity), and from which a row
# owes `MACHINE_FIELDS`. Fixed at "23" like the two constants above.
MACHINE_FIELDS: frozenset[str] = frozenset({"machine_id", "compute_mode"})
MACHINE_FICHE_SCHEMA_VERSION = "23"

# What a row no local model produced (a cloud subject's quality row) says in
# both `machine_id` and `compute_mode`: neither a declared machine nor `gpu` /
# `cpu_only` produced it, which the row states rather than leaving null.
MACHINE_NOT_APPLICABLE = "not_applicable"

# The schema version from which a row owes `campaign_id`, fixed at "24".
CAMPAIGN_SCHEMA_VERSION = "24"

# The schema version from which a runtime row's VRAM fields are checked
# against its compute mode, fixed at "25"; and the marker a `cpu_only` row
# carries in them, owned by `gpu.py` so the repetition loop can write it.
VRAM_NOT_APPLICABLE_SCHEMA_VERSION = "25"
VRAM_NOT_APPLICABLE = gpu.VRAM_NOT_APPLICABLE

# The schema version from which a row owes the run profile fields, fixed at
# "26"; the two fields; what a row no local model produced states in both; and
# the values an operator may override.
PROFILE_SCHEMA_VERSION = "26"
PROFILE_FIELDS: frozenset[str] = frozenset({"profile_id", "profile_overrides"})
PROFILE_NOT_APPLICABLE = MACHINE_NOT_APPLICABLE
OVERRIDABLE_PROFILE_VALUES: frozenset[str] = frozenset({"n_cpu_moe", "threads"})

# The schema version from which a quality row owes `prompt_variant_noop`.
VARIANT_NOOP_SCHEMA_VERSION = "27"
VARIANT_NOOP_FIELD = "prompt_variant_noop"

# The schema version from which a quality row owes the two constraint fields.
CONSTRAINT_SCHEMA_VERSION = "28"
CONSTRAINT_FIELDS: frozenset[str] = frozenset(
    {"constraint_mechanism", "constraint_grammar_hash"}
)

# What a row run under no campaign says in `campaign_id`: it belongs to none,
# stated rather than left null. Reserved: no campaign may take it as its id.
NO_CAMPAIGN = "none"


def fiche_projection_for(schema_version: object) -> str:
    """The `hardware.FICHE_PROJECTIONS` version a row at `schema_version` cites.

    Below `ENGINE_FICHE_SCHEMA_VERSION`: "1". Below
    `MACHINE_FICHE_SCHEMA_VERSION`: "2". At or above it, and for a version
    that cannot be read as a number: the current projection -- an unreadable
    version cannot be proven old, so it is held to today's rule.
    """
    try:
        version = int(schema_version)  # type: ignore[call-overload]
    except (TypeError, ValueError):
        return hardware.CURRENT_FICHE_PROJECTION
    if version < int(ENGINE_FICHE_SCHEMA_VERSION):
        return "1"
    if version < int(MACHINE_FICHE_SCHEMA_VERSION):
        return "2"
    return hardware.CURRENT_FICHE_PROJECTION


RowKind = Literal["runtime", "quality"]

REQUIRED_FIELDS: dict[RowKind, frozenset[str]] = {
    "runtime": frozenset(
        {
            "schema_version",
            "run_id",
            "captured_at",
            # provenance.capture_provenance
            "release_version",
            "commit_sha",
            "tree_dirty",
            # roster.load_roster / roster.resolve_entry
            "roster_entry_id",
            "roster_version",
            # prompt_provenance: call-path identity
            "endpoint",
            "prompt_template_id",
            "prompt_template_hash",
            "prompt_capture",
            # prompt_variants: which transformation the authored prompt went
            # through before the engine's templating, and its output
            # (schema "14")
            "prompt_variant_id",
            "prompt_variant_version",
            "prompt_before_template",
            # Where the subject prompt went: always `none` for a runtime row,
            # which serves its prompt from the local llama-server only
            # (schema "16")
            "subject_egress",
            # engines: the registered engine that produced the row and its
            # live-probed build (schema "22")
            "engine_id",
            "engine_build",
            # machines: the declared machine and the compute mode the run was
            # executed under (schema "23")
            "machine_id",
            "compute_mode",
            # profiles: the run profile the launch resolved and every value
            # the operator overrode, or `PROFILE_NOT_APPLICABLE` for both on a
            # cloud subject's row (schema "26")
            "profile_id",
            "profile_overrides",
            # campaigns: the campaign the run belongs to, or `NO_CAMPAIGN`
            # (schema "24")
            "campaign_id",
            # fiche_registry: the hardware + run-specific fiche, cited by hash
            "fiche_hash",
            # verdict.runtime_verdict
            "verdict",
            "prompt",
            "max_tokens",
            "wall_clock_s",
            # timings.Timings
            "ttft_ms",
            "prompt_tok_per_s",
            "gen_tok_per_s",
            "ttft_source",
            # gpu.GpuStats
            "vram_used_mib",
            "gpu_draw_w",
            "process_rss_bytes",
            # energy.EnergyResult
            "cpu_energy_kwh",
            "cpu_energy_method",
            "gpu_energy_kwh",
            "gpu_energy_method",
            "ram_energy_kwh",
            "ram_energy_method",
            "energy_kwh",
            # energy.RepetitionEnergyTracker: the two window sizes and the
            # method the four energy fields above were measured with (schema
            # "12" / audit finding C3)
            "active_window_s",
            "idle_window_s",
            "energy_window_method",
            # emissions.local_emissions / emissions.scope3_cloud_emissions
            "emissions_kg",
            "emission_factor_kg_per_kwh",
            "emission_region",
            "emissions_scope",
            "emissions_scope_formula_id",
            "scope_comparability",
            # cost.cloud_cost / cost.local_cost / cost.cost_per_million_tokens
            "tokens_in_total",
            "tokens_out_total",
            "cost_total",
            "cost_currency",
            "cost_per_million_tokens",
            "normalization_unit",
            "kwh_price_eur",
            "kwh_price_currency",
            "kwh_price_recorded_at",
            # The two rates the price table charges, plus the blended
            # effective rate this batch's own token mix worked out to.
            "list_price_input_per_million",
            "list_price_output_per_million",
            "list_price_per_million_tokens",
            "list_price_currency",
            "list_price_retrieved_at",
            # repetitions.run_repetition_set / __init__._run
            "sampling",
            "seed_pinned",
            "warmup_count",
            "warmup_repetitions",
            "restart_between_repetitions",
            "cooldown_s",
            "repetitions_n",
            "slot_reset_method",
            "repetitions",
            # aggregation.aggregate_timings / aggregation.AGGREGATION_LABELS
            "aggregation",
            "ttft_ms_mean",
            "ttft_ms_sd",
            "ttft_ms_spread",
            "prompt_tok_per_s_mean",
            "prompt_tok_per_s_sd",
            "prompt_tok_per_s_spread",
            "gen_tok_per_s_mean",
            "gen_tok_per_s_sd",
            "gen_tok_per_s_spread",
            "unreliable",
            "thermal_posture",
        }
    ),
    "quality": frozenset(
        {
            "schema_version",
            "run_id",
            "captured_at",
            # provenance.capture_provenance
            "release_version",
            "commit_sha",
            "tree_dirty",
            # roster.load_roster / roster.resolve_entry
            "roster_entry_id",
            "roster_version",
            # prompt_provenance: call-path identity
            "endpoint",
            "prompt_template_id",
            "prompt_template_hash",
            "prompt_capture",
            # prompt_variants: which transformation the authored prompt went
            # through before the engine's templating, and its output
            # (schema "14")
            "prompt_variant_id",
            "prompt_variant_version",
            "prompt_before_template",
            # whether the variant skipped this item's task family (schema "27")
            VARIANT_NOOP_FIELD,
            # the decoding constraint the answer ran under (schema "28")
            *CONSTRAINT_FIELDS,
            "model_id",
            "provider",
            # Where the subject prompt went: `none` for a local subject, the
            # provider id for a cloud one; checked against `provider`
            # (schema "16")
            "subject_egress",
            # engines: the local engine that produced the row, or
            # `ENGINE_NOT_APPLICABLE` when none did (schema "22")
            "engine_id",
            "engine_build",
            # machines: the declared machine and compute mode a local subject
            # ran under, or `MACHINE_NOT_APPLICABLE` for both on a cloud
            # subject's row (schema "23")
            "machine_id",
            "compute_mode",
            # profiles: the run profile the launch resolved and every value
            # the operator overrode, or `PROFILE_NOT_APPLICABLE` for both on a
            # cloud subject's row (schema "26")
            "profile_id",
            "profile_overrides",
            # campaigns: the campaign the run belongs to, or `NO_CAMPAIGN`
            # (schema "24")
            "campaign_id",
            "fiche_hash",
            # energy.EnergyResult / emissions.local_emissions / scope3_cloud_emissions
            # -- same twelve fields as the runtime row (plan.md's Decisions:
            # quality rows carry the same per-channel/emissions/cost shape).
            "cpu_energy_kwh",
            "cpu_energy_method",
            "gpu_energy_kwh",
            "gpu_energy_method",
            "ram_energy_kwh",
            "ram_energy_method",
            "energy_kwh",
            "emissions_kg",
            "emission_factor_kg_per_kwh",
            "emission_region",
            "emissions_scope",
            "emissions_scope_formula_id",
            "scope_comparability",
            # cost.cloud_cost / cost.local_cost / cost.cost_per_million_tokens
            "tokens_in_total",
            "tokens_out_total",
            "cost_total",
            "cost_currency",
            "cost_per_million_tokens",
            "normalization_unit",
            "kwh_price_eur",
            "kwh_price_currency",
            "kwh_price_recorded_at",
            "list_price_input_per_million",
            "list_price_output_per_million",
            "list_price_per_million_tokens",
            "list_price_currency",
            "list_price_retrieved_at",
            # verdict.quality_verdict
            "verdict",
            "task_suite",
            "item_id",
            "prompt",
            "expected_label",
            "predicted_label",
            "correct",
            "suite_accuracy",
            "language_breakdown",
            "sampling",
            "max_output_tokens",
            "stop_sequences",
            # The fourth generation constraint the suite declares, beside the
            # three above (Methodology 3). See THINKING_POLICIES below for why
            # it is on every row of a batch rather than only the local ones.
            "thinking_policy",
            "context_length",
            "suite_id",
            "suite_version",
            "prompt_set_hash",
            "language",
            "provenance",
            "contamination_risk",
            "indicative",
            "indicative_reasons",
            # suite_gate: the level the suite was certified at, and the item's
            # licence and source declarations (schema "15")
            "suite_level",
            "item_licence",
            "item_source",
            "item_source_revision",
            # scoring.score_item / score_suite
            "failure_reason",
            "failure_counts",
            # retry.call_with_retry / quality_cli's --resume (Story: a
            # rate-limited run persists, resumes and never re-pays)
            "retries",
            "resumed",
            # The retry total each cloud provider's calls drew from, and the
            # failure that left the batch partial, if any (schema "17").
            "retry_budget",
            "partial_failure",
            # quality_rows.item_measurement_fields: the item's own generation
            # figures and their labels (schema "18").
            *(
                "item_tokens_in",
                "item_tokens_in_null_reason",
                "item_tokens_out",
                "item_tokens_out_null_reason",
                "item_ttft_ms",
                "item_ttft_ms_null_reason",
                "item_ttft_source",
                "item_prompt_tokens_cached",
                "item_prompt_tokens_cached_null_reason",
                "item_measurement_kind",
                "item_first_in_batch",
            ),
            # quality_rows.subject_composition_fields: the subject's family and
            # size class (schema "19"; not owed below it).
            *SUBJECT_COMPOSITION_FIELDS,
            # harness.row_fields: the harness that ran the row, its installed
            # version and its per-call prompt overhead (schema "20"; not owed
            # below it).
            *HARNESS_FIELDS,
            # score_interval.interval_block: the batch's bootstrap interval
            # and minimum detectable effect (schema "21"; not owed below it).
            *SCORE_INTERVAL_FIELDS,
        }
    ),
}

# The four per-item values a quality row carries beside their null reasons
# (schema "18"): a value, or null with one of `timings.ITEM_NULL_REASONS`.
ITEM_MEASUREMENT_VALUE_FIELDS: tuple[str, ...] = (
    "item_tokens_in",
    "item_tokens_out",
    "item_ttft_ms",
    "item_prompt_tokens_cached",
)
ITEM_MEASUREMENT_FIELDS: frozenset[str] = frozenset(
    {
        *ITEM_MEASUREMENT_VALUE_FIELDS,
        *(f"{field}_null_reason" for field in ITEM_MEASUREMENT_VALUE_FIELDS),
        "item_ttft_source",
        "item_measurement_kind",
        "item_first_in_batch",
    }
)

# The keys a non-null `partial_failure` carries: who failed, on which item,
# and what it said.
PARTIAL_FAILURE_FIELDS: frozenset[str] = frozenset({"provider", "item_id", "reason"})

# The suite-level score fields a partial row holds `null`: a mean over the
# items that happened to finish before a failure is a biased sample, not a
# partial score. `failure_counts` is not among them -- it is a tally of the
# items written, a count rather than a rate.
PARTIAL_NULL_SCORE_FIELDS: tuple[str, ...] = (
    "suite_accuracy",
    "language_breakdown",
    "suite_score",
    "score_breakdown",
    "judged_headline_score",
    "score_interval",
)


# The complete judge block. Not a member of REQUIRED_FIELDS["quality"]: a
# quality row carrying none of these validates exactly as it did under "8",
# and a row carrying any of them owes all of them. That conditional shape is
# what lets a deterministic classification row stay unchanged while a judged
# row is held to the whole set -- an unconditional list would force every
# deterministic row to write a dozen null judge keys.
JUDGED_FIELDS: frozenset[str] = frozenset(
    {
        # judge_protocol.render_judge_prompt: which prompt was issued, in
        # which language, against which rubric revision.
        "judge_prompt_id",
        "judge_prompt_template_hash",
        "judge_prompt_language",
        "rubric_id",
        "rubric_version",
        "rubric_kind",
        # judge.run_judge_call: one JudgeCallRecord per judge that ran.
        "judges",
        # Independence and agreement: either a named statistic over two judges
        # of different families, or the flag saying only one judged.
        "single_judge",
        "single_judge_reason",
        "agreement",
        "agreement_statistic",
        # agreement.is_contested / agreement.headline_score: the disagreement
        # stays visible, only the headline excludes it and says how many.
        "contested",
        "contested_reason",
        "contested_threshold",
        "judged_headline_score",
        "judged_headline_excluded_n",
        # Where the item and the subject output went, and how many calls it took.
        "judge_egress",
        # cost.judge_cost_fields: the judge calls' own tokens and cost, priced
        # per judge provider. Deliberately not summed into `cost_total`, which
        # stays the subject generation's.
        "judge_cost",
    }
)

# The inner key sets a judged row's three records carry. Declared here, on the
# contract, rather than in the modules that build them: this is the module a
# reader checks a published row against.
JUDGE_EGRESS_FIELDS: frozenset[str] = frozenset(
    {
        "item_left_machine",
        "subject_output_left_machine",
        "providers",
        "generation_count",
        "judge_call_count",
    }
)

JUDGE_COST_FIELDS: frozenset[str] = frozenset(
    {
        "tokens_in_total",
        "tokens_out_total",
        "cost_total",
        "cost_currency",
        "per_provider",
    }
)

# The keys each `judge_cost.per_provider` entry carries
# (`cost.judge_cost_fields`): the provider's own tokens, reasoning apart from
# output with the basis it is billed on, and the rates it was charged at.
JUDGE_COST_PROVIDER_FIELDS: frozenset[str] = frozenset(
    {
        "provider",
        "model_id",
        "tokens_in",
        "tokens_out",
        "reasoning_tokens",
        "reasoning_tokens_null_reason",
        "reasoning_tokens_billing",
        "cost_total",
        "list_price_input_per_million",
        "list_price_output_per_million",
        "list_price_retrieved_at",
    }
)


# The complete graded block, the same conditional shape as `JUDGED_FIELDS`: a
# quality row carrying none of these is an exact-match row and validates
# exactly as it did under "9"; a row carrying any of them owes all of them.
#
# `subject_output` is deliberately NOT a member. `judge_probe.py` already
# writes it as a non-required extra key on every probe row, so including it
# here would make each of those rows declare itself graded and then fail for
# the seven metric fields it does not carry. It is required *inside* the
# structural check below instead, where it applies only to a row that really
# is graded.
GRADED_FIELDS: frozenset[str] = frozenset(
    {
        # chrf.METRIC_ID / METRIC_VERSION / METRIC_PARAMS: which metric, at
        # which revision, under which parameters.
        "metric_id",
        "metric_version",
        "metric_params",
        # scoring.score_translation_item / score_graded_suite: this item's
        # score and the batch mean it contributes to.
        "item_score",
        "suite_score",
        # scoring.score_graded_suite_by_language: score, n and the indicative
        # mark per language.
        "score_breakdown",
        # The text the score was computed against. A derived value carries
        # what it was derived from (Methodology 16): with this, the row's own
        # `subject_output` and the metric parameters above, an auditor
        # recomputes the score with sacreBLEU and catches us.
        "reference_output",
    }
)

# The three keys every `score_breakdown` cell carries. Declared here, on the
# contract, for the same reason the judge block's inner key sets are.
GRADED_LANGUAGE_CELL_FIELDS: frozenset[str] = frozenset({"score", "n", "indicative"})


class RowContractError(ValueError):
    """Raised when a row is missing one or more of its kind's required fields."""


# The refusal record (`preflight.py`): a run refused below its entry's declared
# minimum. Its own small contract, versioned apart from the row schema: it
# carries no `schema_version`, so no view's schema floor ever selects it as a
# row, and it lives in its own per-machine file, never in a results store.
REFUSAL_RECORD_KIND = "refusal"
REFUSAL_CONTRACT_VERSION = "1"
REFUSAL_FIELDS: frozenset[str] = frozenset(
    {
        "record_kind",
        "refusal_contract_version",
        "roster_entry_id",
        "machine_id",
        "compute_mode",
        "profile_id",
        "requirement",
        "declared",
        "observed",
        "unit",
        "release_version",
        "commit_sha",
        "refused_at",
    }
)


def validate_refusal(record: dict[str, Any]) -> None:
    """Raise `RowContractError` unless `record` is a complete refusal record.

    Refuses a missing field by name, a `record_kind` other than `refusal`,
    and a record carrying `schema_version`: a refusal is never a row.
    """
    missing = REFUSAL_FIELDS - record.keys()
    if missing:
        raise RowContractError(
            f"refusal record missing required fields: {', '.join(sorted(missing))}"
        )
    if record["record_kind"] != REFUSAL_RECORD_KIND:
        raise RowContractError(
            f"refusal record has record_kind {record['record_kind']!r}, "
            f"expected {REFUSAL_RECORD_KIND!r}"
        )
    if "schema_version" in record:
        raise RowContractError(
            "a refusal record carries no schema_version: it is never a row"
        )


def validate_row(kind: RowKind, row: dict[str, Any]) -> None:
    """Raise `RowContractError` naming every field `kind` requires but `row` lacks.

    A key present with value `None` satisfies the contract; only an absent key
    counts as missing.
    """
    missing = REQUIRED_FIELDS[kind] - row.keys()
    if kind == "quality" and _predates(row, SUBJECT_COMPOSITION_SCHEMA_VERSION):
        missing -= SUBJECT_COMPOSITION_FIELDS
    if kind == "quality" and _predates(row, HARNESS_SCHEMA_VERSION):
        missing -= HARNESS_FIELDS
    if kind == "quality" and _predates(row, SCORE_INTERVAL_SCHEMA_VERSION):
        missing -= SCORE_INTERVAL_FIELDS
    if _predates(row, ENGINE_FICHE_SCHEMA_VERSION):
        missing -= ENGINE_FIELDS
    if _predates(row, MACHINE_FICHE_SCHEMA_VERSION):
        missing -= MACHINE_FIELDS
    if _predates(row, CAMPAIGN_SCHEMA_VERSION):
        missing -= {"campaign_id"}
    if _predates(row, PROFILE_SCHEMA_VERSION):
        missing -= PROFILE_FIELDS
    if kind == "quality" and _predates(row, VARIANT_NOOP_SCHEMA_VERSION):
        missing -= {VARIANT_NOOP_FIELD}
    if kind == "quality" and _predates(row, CONSTRAINT_SCHEMA_VERSION):
        missing -= CONSTRAINT_FIELDS
    if missing:
        raise RowContractError(
            f"row of kind {kind!r} is missing required field(s): "
            f"{', '.join(sorted(missing))}"
        )

    endpoint = row["endpoint"]
    prompt_template_id = row["prompt_template_id"]
    if not prompt_provenance.is_consistent(endpoint, prompt_template_id):
        raise RowContractError(
            f"row of kind {kind!r} pairs endpoint {endpoint!r} with "
            f"prompt_template_id {prompt_template_id!r}: an endpoint that "
            f"applies a template cannot declare 'none'"
        )

    _validate_prompt_variant(kind, row)
    _validate_subject_egress(kind, row)
    if not _predates(row, ENGINE_FICHE_SCHEMA_VERSION):
        _validate_engine(kind, row)
    if not _predates(row, MACHINE_FICHE_SCHEMA_VERSION):
        _validate_machine(kind, row)
    if not _predates(row, CAMPAIGN_SCHEMA_VERSION):
        _validate_campaign(kind, row)
    if not _predates(row, PROFILE_SCHEMA_VERSION):
        _validate_profile(kind, row)

    cost_total = row["cost_total"]
    # The two bases are the values the cost was actually computed from: a kWh
    # price for a local run, the table's own input rate for a cloud one.
    # `list_price_per_million_tokens` is deliberately not accepted here -- it
    # is a blended rate derived FROM cost_total, so a row carrying only it
    # would satisfy the gate without carrying any input at all.
    if (
        cost_total is not None
        and row["kwh_price_eur"] is None
        and row["list_price_input_per_million"] is None
    ):
        raise RowContractError(
            f"row of kind {kind!r} carries cost_total={cost_total!r} but both "
            "kwh_price_eur and list_price_input_per_million are null: a "
            "non-null cost must carry at least one derivation basis"
        )

    if kind == "runtime":
        ttft_source = row["ttft_source"]
        valid_ttft_sources = {
            timings.TTFT_SOURCE_SERVER_REPORTED,
            timings.TTFT_SOURCE_CLIENT_MEASURED,
        }
        if ttft_source not in valid_ttft_sources:
            raise RowContractError(
                f"row of kind 'runtime' has an unrecognised ttft_source: {ttft_source!r}"
            )
        _validate_runtime_repetition_structure(row)
        if not _predates(row, VRAM_NOT_APPLICABLE_SCHEMA_VERSION):
            _validate_vram_applicability(row)

    if kind == "quality":
        _validate_suite_level(row)
        _validate_retry_budget(row)
        _validate_partial_failure(row)
        _validate_item_measurement(row)
        _validate_subject_composition(row)
        _validate_harness(row)
        _validate_judged_fields(row)
        _validate_graded_fields(row)
        # After the graded block: a malformed graded score is named as such
        # before the interval beside it is checked against it.
        _validate_score_interval(row)


def _predates(row: dict[str, Any], since: str) -> bool:
    """True when the row's own `schema_version` is below `since`.

    A version that is not an integer string is not read as old: the row is
    held to the current contract rather than excused by a malformed field.
    """
    version = row.get("schema_version")
    if not isinstance(version, str) or not version.isdigit():
        return False
    return int(version) < int(since)


def _validate_harness(row: dict[str, Any]) -> None:
    """Refuse a harness outside the closed five, a version that was not read,
    and an overhead that is neither a count nor a null with its reason.

    A negative count is refused: a harness only adds around the item's own
    prompt, so the writer records `unmeasurable` where the subtraction comes
    out below zero.
    """
    if not HARNESS_FIELDS <= row.keys():
        return
    harness_id = row["harness_id"]
    if not isinstance(harness_id, str) or harness_id not in harness.HARNESS_IDS:
        raise RowContractError(
            f"row of kind 'quality' has harness_id {harness_id!r}, not one of "
            f"{', '.join(sorted(harness.HARNESS_IDS))}"
        )
    version = row["harness_version"]
    if not isinstance(version, str) or not version:
        raise RowContractError(
            f"row of kind 'quality' has harness_version {version!r}: the "
            "harness's installed version, read when the row is written"
        )
    overhead = row["harness_prompt_overhead"]
    if not isinstance(overhead, dict) or overhead.keys() != harness.OVERHEAD_KEYS:
        raise RowContractError(
            f"row of kind 'quality' has harness_prompt_overhead {overhead!r}: "
            "an object carrying exactly tokens and null_reason"
        )
    tokens = overhead["tokens"]
    reason = overhead["null_reason"]
    if tokens is None:
        if reason not in harness.OVERHEAD_NULL_REASONS:
            raise RowContractError(
                f"row of kind 'quality' has a null harness_prompt_overhead with "
                f"null_reason {reason!r}, not one of "
                f"{', '.join(sorted(harness.OVERHEAD_NULL_REASONS))}"
            )
        return
    if isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0:
        raise RowContractError(
            f"row of kind 'quality' has harness_prompt_overhead tokens "
            f"{tokens!r}: a non-negative token count, or null with its reason"
        )
    if reason is not None:
        raise RowContractError(
            f"row of kind 'quality' has harness_prompt_overhead tokens {tokens!r} "
            f"beside null_reason {reason!r}: a measured overhead has no reason"
        )


def _validate_score_interval(row: dict[str, Any]) -> None:
    """Refuse an interval block that cannot qualify the score beside it.

    Null exactly when the row publishes no suite score (`suite_accuracy` and
    `suite_score` both null: a partial batch, a judge-probe row); otherwise
    the six header values, a `suite` cell and one cell per language, each
    carrying its three values and no reason, or no values and one named
    reason -- never both. Whether the interval and the score were computed
    over the same items is a batch property, checked by
    `score_interval.check_batch_invariants` before a batch is written.
    """
    if not SCORE_INTERVAL_FIELDS <= row.keys():
        return
    block = row["score_interval"]
    publishes_score = (
        row.get("suite_accuracy") is not None or row.get("suite_score") is not None
    )
    if block is None:
        if publishes_score:
            raise RowContractError(
                "row of kind 'quality' publishes a suite score but a null "
                "score_interval: every published score carries its interval"
            )
        return
    if not publishes_score:
        raise RowContractError(
            "row of kind 'quality' carries a score_interval beside no suite "
            "score: an interval qualifies a published score"
        )
    if not isinstance(block, dict) or block.keys() != score_interval.BLOCK_KEYS:
        raise RowContractError(
            f"row of kind 'quality' has score_interval {block!r}: an object "
            f"carrying exactly {', '.join(sorted(score_interval.BLOCK_KEYS))}"
        )
    header = {
        "confidence_level": score_interval.CONFIDENCE_LEVEL,
        "resamples": score_interval.RESAMPLES,
        "method": score_interval.METHOD_PERCENTILE,
        "draw_procedure_id": score_interval.DRAW_PROCEDURE_ID,
    }
    for key, expected in header.items():
        if block[key] != expected:
            raise RowContractError(
                f"row of kind 'quality' has score_interval {key}={block[key]!r}, "
                f"expected {expected!r}"
            )
    seed = block["seed"]
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise RowContractError(
            f"row of kind 'quality' has score_interval seed {seed!r}: an integer"
        )
    generator = block["generator"]
    if not (
        isinstance(generator, dict)
        and generator.keys() == score_interval.GENERATOR_KEYS
        and all(isinstance(value, str) and value for value in generator.values())
    ):
        raise RowContractError(
            f"row of kind 'quality' has score_interval generator {generator!r}: "
            "the generator's library and version"
        )
    by_language = block["by_language"]
    if not isinstance(by_language, dict) or set(by_language) != set(
        suite_gate.LANGUAGES
    ):
        raise RowContractError(
            f"row of kind 'quality' has score_interval by_language {by_language!r}: "
            f"one cell per language, {sorted(suite_gate.LANGUAGES)!r}"
        )
    _validate_interval_cell("suite", block["suite"])
    for language, cell in by_language.items():
        _validate_interval_cell(language, cell)


def _validate_interval_cell(where: str, cell: Any) -> None:
    """Refuse a cell that is not three values and no reason, or none and one."""
    if not isinstance(cell, dict) or cell.keys() != score_interval.CELL_KEYS:
        raise RowContractError(
            f"row of kind 'quality' has score_interval {where} cell {cell!r}: an "
            f"object carrying exactly {', '.join(sorted(score_interval.CELL_KEYS))}"
        )
    n = cell["n"]
    if isinstance(n, bool) or not isinstance(n, int) or n < 0:
        raise RowContractError(
            f"row of kind 'quality' has score_interval {where} n={n!r}: a "
            "non-negative item count"
        )
    values = [cell[key] for key in score_interval.CELL_VALUE_KEYS]
    reason = cell["null_reason"]
    if reason is not None:
        if reason not in score_interval.NULL_REASONS or any(
            value is not None for value in values
        ):
            raise RowContractError(
                f"row of kind 'quality' has score_interval {where} cell {cell!r}: "
                "a null interval carries no value and one of "
                f"{', '.join(sorted(score_interval.NULL_REASONS))}"
            )
        # Each reason only from the state that names it: an empty cell is
        # `no_items`, and a cell holding items is never.
        if (reason == score_interval.NULL_NO_ITEMS) != (n == 0):
            raise RowContractError(
                f"row of kind 'quality' has score_interval {where} cell with "
                f"null_reason {reason!r} at n={n}: no_items names an empty cell "
                "and only an empty cell"
            )
        return
    if n == 0:
        raise RowContractError(
            f"row of kind 'quality' has score_interval {where} cell with an "
            "interval over n=0: an empty cell publishes no_items"
        )
    if any(
        isinstance(value, bool) or not isinstance(value, int | float)
        for value in values
    ):
        raise RowContractError(
            f"row of kind 'quality' has score_interval {where} cell {cell!r}: an "
            "interval carries its lower, upper and minimum detectable effect, "
            "or none of them and a null_reason"
        )


def _validate_subject_composition(row: dict[str, Any]) -> None:
    """Refuse an unknown family, an unknown size class, and a size class on a
    cloud row.

    A writer always knows its subject's family (`roster.family_of` refuses
    rather than defaults), so `family` is never null. `size_class` is a local
    entry's declaration: a cloud subject has none, and a local entry that
    declares none publishes `null`, which the composition check names.
    """
    if not SUBJECT_COMPOSITION_FIELDS <= row.keys():
        return
    family = row["family"]
    if not isinstance(family, str) or family not in roster.KNOWN_FAMILIES:
        raise RowContractError(
            f"row of kind 'quality' has family {family!r}, not one of "
            f"{', '.join(sorted(roster.KNOWN_FAMILIES))}"
        )
    size_class = row["size_class"]
    if size_class is None:
        return
    if size_class not in roster.SIZE_CLASSES:
        raise RowContractError(
            f"row of kind 'quality' has size_class {size_class!r}, not one of "
            f"{', '.join(roster.SIZE_CLASSES)} or null"
        )
    if row["provider"] != SUBJECT_PROVIDER_LOCAL:
        raise RowContractError(
            f"row of kind 'quality' has size_class {size_class!r} but provider "
            f"{row['provider']!r}: a cloud subject has no size class, so its "
            "row records null"
        )


def subject_egress_for(provider: str) -> str:
    """The `subject_egress` value a subject served by `provider` records.

    The one mapping both the writers and the gate use, so a writer cannot
    stamp a value the gate would read differently: the local llama-server
    sends nothing off the machine, any other provider received the prompt.
    """
    if provider == SUBJECT_PROVIDER_LOCAL:
        return SUBJECT_EGRESS_NONE
    return provider


def _validate_subject_egress(kind: RowKind, row: dict[str, Any]) -> None:
    """Refuse a null or malformed `subject_egress`, a runtime one other than
    `none`, and a quality one that contradicts `provider`.

    A null is refused here, unlike the contract's general "present as None is
    complete" rule: a capture can fail, but a writer always knows where it
    sent a prompt. A runtime row carries no `provider`, but the runtime
    benchmark serves its prompt from the local llama-server only, so it is
    held to `none`.
    """
    egress = row["subject_egress"]
    if egress is None:
        raise RowContractError(
            f"row of kind {kind!r} has subject_egress null: a row states where "
            f"its subject prompt went, {SUBJECT_EGRESS_NONE!r} or the provider "
            "that received it"
        )
    if not (isinstance(egress, str) and egress.strip()):
        raise RowContractError(
            f"row of kind {kind!r} has a malformed subject_egress: {egress!r}"
        )
    if kind == "runtime":
        if egress != SUBJECT_EGRESS_NONE:
            raise RowContractError(
                f"row of kind 'runtime' has subject_egress {egress!r}: the "
                "runtime benchmark serves its prompt from the local "
                f"llama-server only, so it records {SUBJECT_EGRESS_NONE!r}"
            )
        return
    provider = row["provider"]
    expected = subject_egress_for(provider)
    if egress != expected:
        raise RowContractError(
            f"row of kind 'quality' has subject_egress {egress!r} but provider "
            f"{provider!r}: a subject served by {provider!r} records "
            f"subject_egress {expected!r}"
        )


def _validate_retry_budget(row: dict[str, Any]) -> None:
    """Refuse a malformed `retry_budget`, a cloud row that does not name its
    own provider's budget, and per-item `retries` beyond that budget.

    The subject call of a cloud row drew its retries from its provider's
    budget, so that budget is on the row and the item's retries fit in it.
    """
    budget = row["retry_budget"]
    if not isinstance(budget, dict):
        raise RowContractError(
            f"row of kind 'quality' has a non-object retry_budget: {budget!r}"
        )
    for provider, total in budget.items():
        if not (isinstance(provider, str) and provider.strip()):
            raise RowContractError(
                f"row of kind 'quality' has a retry_budget keyed by {provider!r}: "
                "each key names a cloud provider"
            )
        if isinstance(total, bool) or not isinstance(total, int) or total < 0:
            raise RowContractError(
                f"row of kind 'quality' has retry_budget[{provider!r}]={total!r}: "
                "a retry budget is a non-negative whole number"
            )
    provider = row["provider"]
    if provider == SUBJECT_PROVIDER_LOCAL:
        return
    if provider not in budget:
        raise RowContractError(
            f"row of kind 'quality' has provider {provider!r} but no "
            f"retry_budget entry for it: a cloud subject's calls ran under a "
            "budget, and the row names it"
        )
    retries = row["retries"]
    if isinstance(retries, int) and retries > budget[provider]:
        raise RowContractError(
            f"row of kind 'quality' carries retries={retries!r} above its "
            f"provider's retry_budget of {budget[provider]!r}"
        )


def _validate_partial_failure(row: dict[str, Any]) -> None:
    """Refuse a malformed `partial_failure`, and a partial row that publishes
    a suite-level score."""
    failure = row["partial_failure"]
    if failure is None:
        return
    if not isinstance(failure, dict):
        raise RowContractError(
            f"row of kind 'quality' has a non-object partial_failure: {failure!r}"
        )
    missing = PARTIAL_FAILURE_FIELDS - failure.keys()
    if missing:
        raise RowContractError(
            f"row of kind 'quality' has a partial_failure missing field(s): "
            f"{', '.join(sorted(missing))}"
        )
    for field in ("provider", "item_id"):
        value = failure[field]
        if not (isinstance(value, str) and value.strip()):
            raise RowContractError(
                f"row of kind 'quality' has a partial_failure whose {field} is "
                f"{value!r}: a partial batch names the failing provider and item"
            )
    for field in PARTIAL_NULL_SCORE_FIELDS:
        if row.get(field) is not None:
            raise RowContractError(
                f"row of kind 'quality' is partial but carries {field}="
                f"{row[field]!r}: a partial batch publishes no suite-level score"
            )


def _validate_item_measurement(row: dict[str, Any]) -> None:
    """Refuse a per-item value that is neither a number nor null with a reason.

    Exactly one of a value and its null reason is set: a null without a
    reason is an unexplained gap, a value beside a reason contradicts itself.
    A TTFT names its source (and only a TTFT does), on the runtime row's
    `ttft_source` discipline; the measurement kind is the one label this
    schema defines; the first-generation mark is a boolean.
    """
    for field in ITEM_MEASUREMENT_VALUE_FIELDS:
        value = row[field]
        reason = row[f"{field}_null_reason"]
        if value is None:
            if reason not in timings.ITEM_NULL_REASONS:
                raise RowContractError(
                    f"row of kind 'quality' has {field} null with "
                    f"{field}_null_reason {reason!r}: a null value names one of "
                    f"{', '.join(sorted(timings.ITEM_NULL_REASONS))}"
                )
            continue
        if reason is not None:
            raise RowContractError(
                f"row of kind 'quality' carries {field}={value!r} beside "
                f"{field}_null_reason {reason!r}: a reported value has no null reason"
            )
        numeric = isinstance(value, int) or (
            field == "item_ttft_ms" and isinstance(value, float)
        )
        if isinstance(value, bool) or not numeric or value < 0:
            raise RowContractError(
                f"row of kind 'quality' has a malformed {field}: {value!r}"
            )
    source = row["item_ttft_source"]
    if row["item_ttft_ms"] is None:
        if source is not None:
            raise RowContractError(
                f"row of kind 'quality' has item_ttft_source {source!r} but no "
                "item_ttft_ms: only a reported first-token time names its source"
            )
    elif source not in {
        timings.TTFT_SOURCE_SERVER_REPORTED,
        timings.TTFT_SOURCE_CLIENT_MEASURED,
    }:
        raise RowContractError(
            f"row of kind 'quality' has an unrecognised item_ttft_source: {source!r}"
        )
    kind = row["item_measurement_kind"]
    if kind != timings.ITEM_MEASUREMENT_SINGLE_GENERATION:
        raise RowContractError(
            f"row of kind 'quality' has item_measurement_kind {kind!r}: expected "
            f"{timings.ITEM_MEASUREMENT_SINGLE_GENERATION!r}"
        )
    if not isinstance(row["item_first_in_batch"], bool):
        raise RowContractError(
            "row of kind 'quality' has a non-boolean item_first_in_batch: "
            f"{row['item_first_in_batch']!r}"
        )


_ITEM_SOURCE_FIELDS = ("item_licence", "item_source", "item_source_revision")


def _validate_engine(kind: RowKind, row: dict[str, Any]) -> None:
    """Refuse an unregistered engine, and an engine on a row none produced.

    A runtime row and a local quality row must name an engine the tracked
    registry holds; its build may be null (an unreadable probe is an explicit
    null, never an assumed value). Any other quality row must state
    `ENGINE_NOT_APPLICABLE` with a null build.
    """
    engine_id = row["engine_id"]
    engine_build = row["engine_build"]
    if engine_build is not None and not (
        isinstance(engine_build, str) and engine_build.strip()
    ):
        raise RowContractError(
            f"row of kind {kind!r} has a malformed engine_build: {engine_build!r}"
        )

    if kind == "runtime" or row["provider"] == SUBJECT_PROVIDER_LOCAL:
        try:
            registered = engines.registered_engine_ids()
        except engines.EngineRegistryError as exc:
            raise RowContractError(
                f"row of kind {kind!r}: the engine registry cannot be read: {exc}"
            ) from exc
        if engine_id not in registered:
            raise RowContractError(
                f"row of kind {kind!r} names engine_id {engine_id!r}, which is "
                f"not a registered engine (registered: {', '.join(sorted(registered))})"
            )
        return

    if engine_id != ENGINE_NOT_APPLICABLE or engine_build is not None:
        raise RowContractError(
            f"row of kind {kind!r} from provider {row['provider']!r} was produced "
            f"by no local engine: it must carry engine_id "
            f"{ENGINE_NOT_APPLICABLE!r} and a null engine_build, got "
            f"{engine_id!r} / {engine_build!r}"
        )


def _validate_campaign(kind: RowKind, row: dict[str, Any]) -> None:
    """Refuse a `campaign_id` that is not a non-empty string, and a campaign
    id on a row no local model produced.

    A cloud subject's quality row always states `NO_CAMPAIGN`: a campaign
    declares engines, and a cloud subject runs on none.
    """
    campaign_id = row["campaign_id"]
    if not isinstance(campaign_id, str) or not campaign_id.strip():
        raise RowContractError(
            f"row of kind {kind!r} has campaign_id {campaign_id!r}; it names "
            f"its campaign, or {NO_CAMPAIGN!r} for a run under none"
        )
    if (
        kind == "quality"
        and row["provider"] != SUBJECT_PROVIDER_LOCAL
        and campaign_id != NO_CAMPAIGN
    ):
        raise RowContractError(
            f"row of kind {kind!r} from provider {row['provider']!r} names "
            f"campaign {campaign_id!r}: a cloud subject belongs to no campaign "
            f"and states {NO_CAMPAIGN!r}"
        )


def _validate_profile(kind: RowKind, row: dict[str, Any]) -> None:
    """Refuse a row that does not name its run profile and its overrides.

    A runtime row and a local quality row name a non-empty profile id and map
    each overridden value (`n_cpu_moe`, `threads`) to exactly `profile` and
    `operator`. Any other quality row states `PROFILE_NOT_APPLICABLE` for both.
    """
    profile_id = row["profile_id"]
    overrides = row["profile_overrides"]
    if kind == "runtime" or row["provider"] == SUBJECT_PROVIDER_LOCAL:
        if (
            not isinstance(profile_id, str)
            or not profile_id.strip()
            or profile_id == PROFILE_NOT_APPLICABLE
        ):
            raise RowContractError(
                f"row of kind {kind!r} has profile_id {profile_id!r}; a locally "
                "produced row names the run profile it launched under"
            )
        if not isinstance(overrides, dict):
            raise RowContractError(
                f"row of kind {kind!r} has profile_overrides {overrides!r}; it "
                "maps each overridden value to its profile and operator values, "
                "or is {} when nothing was overridden"
            )
        for name, record in overrides.items():
            if name not in OVERRIDABLE_PROFILE_VALUES or not (
                isinstance(record, dict) and set(record) == {"profile", "operator"}
            ):
                raise RowContractError(
                    f"row of kind {kind!r} has profile_overrides entry "
                    f"{name!r}: {record!r}; an override names one of "
                    f"{', '.join(sorted(OVERRIDABLE_PROFILE_VALUES))} with "
                    "exactly its 'profile' and 'operator' values"
                )
        return

    if profile_id != PROFILE_NOT_APPLICABLE or overrides != PROFILE_NOT_APPLICABLE:
        raise RowContractError(
            f"row of kind {kind!r} from provider {row['provider']!r} was produced "
            f"by no local model: it must carry profile_id and profile_overrides "
            f"{PROFILE_NOT_APPLICABLE!r}, got {profile_id!r} / {overrides!r}"
        )


def _validate_machine(kind: RowKind, row: dict[str, Any]) -> None:
    """Refuse an undeclared machine or an unknown mode, and either on a row no
    local model produced.

    A runtime row and a local quality row must name a machine the tracked
    registry declares and a compute mode (`gpu` or `cpu_only`). Any other
    quality row must state `MACHINE_NOT_APPLICABLE` for both: a cloud
    subject's row never carries `gpu` or `cpu_only`.
    """
    machine_id = row["machine_id"]
    compute_mode = row["compute_mode"]
    if kind == "runtime" or row["provider"] == SUBJECT_PROVIDER_LOCAL:
        try:
            declared = machines.declared_machine_ids()
        except machines.MachineRegistryError as exc:
            raise RowContractError(
                f"row of kind {kind!r}: the machine registry cannot be read: {exc}"
            ) from exc
        if machine_id not in declared:
            raise RowContractError(
                f"row of kind {kind!r} names machine_id {machine_id!r}, which is "
                f"not a declared machine (declared: {', '.join(sorted(declared))})"
            )
        if compute_mode not in machines.COMPUTE_MODES:
            raise RowContractError(
                f"row of kind {kind!r} has compute_mode {compute_mode!r}; a "
                f"locally produced row names {' or '.join(machines.COMPUTE_MODES)}"
            )
        return

    if machine_id != MACHINE_NOT_APPLICABLE or compute_mode != MACHINE_NOT_APPLICABLE:
        raise RowContractError(
            f"row of kind {kind!r} from provider {row['provider']!r} was produced "
            f"by no local model: it must carry machine_id and compute_mode "
            f"{MACHINE_NOT_APPLICABLE!r}, got {machine_id!r} / {compute_mode!r}"
        )


def _validate_vram_applicability(row: dict[str, Any]) -> None:
    """Refuse a VRAM figure on a `cpu_only` row and the marker on a `gpu` row.

    A `cpu_only` row carries `VRAM_NOT_APPLICABLE` at the row level and on
    every counted and warm-up repetition: no number, zero included. A `gpu`
    row carries a number or `null` (a failed read) in each place, never the
    marker, so the two absences stay distinct.
    """
    places: list[tuple[str, Any]] = [("vram_used_mib", row["vram_used_mib"])]
    for field in ("repetitions", "warmup_repetitions"):
        repetitions = row[field]
        if not isinstance(repetitions, list):
            raise RowContractError(
                f"row of kind 'runtime' has a non-list {field}: {repetitions!r}"
            )
        for position, repetition in enumerate(repetitions):
            if not isinstance(repetition, dict) or "vram_used_mib" not in repetition:
                raise RowContractError(
                    f"row of kind 'runtime' has {field}[{position}] without "
                    "vram_used_mib"
                )
            places.append(
                (f"{field}[{position}].vram_used_mib", repetition["vram_used_mib"])
            )

    cpu_only = row["compute_mode"] == machines.COMPUTE_MODE_CPU_ONLY
    for where, value in places:
        if cpu_only and value != VRAM_NOT_APPLICABLE:
            raise RowContractError(
                f"row of kind 'runtime' under compute_mode 'cpu_only' carries "
                f"{where}={value!r}: a cpu_only run has no VRAM figure and "
                f"states {VRAM_NOT_APPLICABLE!r}"
            )
        is_number = isinstance(value, int | float) and not isinstance(value, bool)
        if not cpu_only and not (value is None or is_number):
            raise RowContractError(
                f"row of kind 'runtime' under compute_mode "
                f"{row['compute_mode']!r} carries {where}={value!r}: a VRAM "
                "figure is a number, or null when the read failed"
            )


def _validate_suite_level(row: dict[str, Any]) -> None:
    """Refuse an unknown level, a malformed item declaration, and a
    publication row missing any of the three item declarations its suite
    could only have been certified with."""
    level = row["suite_level"]
    if level not in suite_gate.SUITE_LEVELS:
        raise RowContractError(
            f"row of kind 'quality' has suite_level {level!r}, not one of "
            f"{', '.join(sorted(suite_gate.SUITE_LEVELS))}"
        )
    for field in _ITEM_SOURCE_FIELDS:
        value = row[field]
        if value is None:
            if level == suite_gate.LEVEL_PUBLICATION:
                raise RowContractError(
                    f"row of kind 'quality' has suite_level 'publication' but "
                    f"{field} is null: a publication item declares its licence, "
                    "its source and that source's revision"
                )
        elif not (isinstance(value, str) and value.strip()):
            raise RowContractError(
                f"row of kind 'quality' has a malformed {field}: {value!r}"
            )


def _validate_prompt_variant(kind: RowKind, row: dict[str, Any]) -> None:
    """Refuse a variant the registry does not hold, and an unchecked prompt.

    The variant is a claim this gate checks rather than a label it trusts:
    the row's `prompt_before_template` must equal the variant applied to the
    authored text of the item it names, resolved from the code that owns that
    text -- never from a field on the row, which a hand-built row could forge
    alongside the transformed prompt. `baseline` is checked on every row and
    refused when its text cannot be resolved; another variant is checked
    from schema "27" whenever its text resolves. From "27" a quality row's
    `prompt_variant_noop` must equal the registry's answer for its
    `task_suite`.
    """
    variant_id = row["prompt_variant_id"]
    version = row["prompt_variant_version"]
    if not any(key[0] == variant_id for key in prompt_variants.REGISTRY):
        raise RowContractError(
            f"row of kind {kind!r} has prompt_variant_id {variant_id!r}: not a "
            "registered prompt variant"
        )
    if (variant_id, version) not in prompt_variants.REGISTRY:
        raise RowContractError(
            f"row of kind {kind!r} has prompt_variant_version {version!r}: "
            f"prompt variant {variant_id!r} has no such registered version"
        )

    variant = prompt_variants.REGISTRY[(variant_id, version)]
    # A quality row names its task family; a runtime row's fixed prompt
    # belongs to none.
    task_family = row.get("task_suite") if kind == "quality" else None
    owes_noop = kind == "quality" and not _predates(row, VARIANT_NOOP_SCHEMA_VERSION)
    if owes_noop:
        noop = row[VARIANT_NOOP_FIELD]
        expected_noop = not prompt_variants.applies(variant, task_family)
        if noop is not expected_noop:
            raise RowContractError(
                f"row of kind {kind!r} has {VARIANT_NOOP_FIELD} {noop!r}: prompt "
                f"variant {variant_id!r} version {version!r} "
                f"{'does not apply' if expected_noop else 'applies'} to task "
                f"family {task_family!r}, so it must be {expected_noop!r}"
            )

    if kind == "quality" and not _predates(row, CONSTRAINT_SCHEMA_VERSION):
        expected_constraint = prompt_variants.constraint_row_fields(
            variant, task_family
        )
        for field, expected_value in sorted(expected_constraint.items()):
            if row[field] != expected_value:
                raise RowContractError(
                    f"row of kind {kind!r} has {field} {row[field]!r}: prompt "
                    f"variant {variant_id!r} version {version!r} on task family "
                    f"{task_family!r} sends {expected_value!r}"
                )

    if variant_id != prompt_variants.BASELINE_ID and not owes_noop:
        return
    authored, unresolved_reason = _authored_prompt(kind, row)
    if authored is None:
        if variant_id != prompt_variants.BASELINE_ID:
            return
        raise RowContractError(
            f"row of kind {kind!r} declares prompt variant 'baseline' but its "
            f"prompt_before_template cannot be checked: {unresolved_reason}"
        )
    expected = prompt_variants.apply_variant(variant, authored, task_family).prompt
    if row["prompt_before_template"] != expected:
        raise RowContractError(
            f"row of kind {kind!r} declares prompt variant {variant_id!r} "
            f"version {version!r} but its prompt_before_template differs from "
            "that variant applied to the item's authored text: a "
            f"{variant_id!r} row carries what the variant made of the authored "
            "prompt"
        )


def _authored_prompt(kind: RowKind, row: dict[str, Any]) -> tuple[str | None, str]:
    """The authored text the row's prompt started from, or None and why not.

    Imported here rather than at module level: every module below imports
    this one, so a top-level import would be a cycle.
    """
    if kind == "runtime":
        from wave_local_ai_v2 import FIXED_PROMPT

        return FIXED_PROMPT, ""

    from wave_local_ai_v2 import judge_probe, suite_registry

    suite_id = row["suite_id"]
    items: Sequence[Mapping[str, Any]]
    if suite_id == judge_probe.SUITE_ID:
        suite_version, items = judge_probe.SUITE_VERSION, judge_probe.JUDGE_PROBE_ITEMS
    elif suite_id in suite_registry.registered_ids():
        definition = suite_registry.resolve(suite_id)
        suite_version, items = definition.suite_version, definition.items
    else:
        return None, f"suite_id {suite_id!r} is not a suite this code defines"
    if row["suite_version"] != suite_version:
        return None, (
            f"suite {suite_id!r} is at version {suite_version!r} in this code, "
            f"not {row['suite_version']!r}"
        )
    for item in items:
        if item["item_id"] == row["item_id"]:
            return str(item["prompt"]), ""
    return None, f"suite {suite_id!r} has no item {row['item_id']!r}"


def _validate_judged_fields(row: dict[str, Any]) -> None:
    """Hold a row that declares itself judged to the whole judge block.

    A quality row carrying none of `JUDGED_FIELDS` is deterministic and
    returns untouched. Carrying any of them is the declaration: the row is a
    judged score, and every remaining judge field is named as missing.
    """
    present = JUDGED_FIELDS & row.keys()
    if not present:
        return

    missing = JUDGED_FIELDS - row.keys()
    if missing:
        raise RowContractError(
            f"row of kind 'quality' declares itself judged by carrying "
            f"{', '.join(sorted(present))} but is missing judge field(s): "
            f"{', '.join(sorted(missing))}"
        )

    _validate_judged_structure(row)


def _validate_judged_structure(row: dict[str, Any]) -> None:
    """Raise on a judge block that cannot back the judgement it publishes."""
    judges = row["judges"]
    if not isinstance(judges, list) or not judges:
        raise RowContractError(
            f"row of kind 'quality' has judges={judges!r}: a judged row "
            "carries at least one judge call record"
        )
    for index, record in enumerate(judges):
        if not isinstance(record, dict):
            raise RowContractError(
                f"row of kind 'quality' has a non-object judges[{index}]: {record!r}"
            )
        missing_keys = judge.JUDGE_CALL_RECORD_FIELDS - record.keys()
        if missing_keys:
            raise RowContractError(
                f"row of kind 'quality' has judges[{index}] missing "
                f"field(s): {', '.join(sorted(missing_keys))}"
            )
        _validate_judge_call_record(index, record)

    language = row["judge_prompt_language"]
    if language not in judge_protocol.JUDGE_LANGUAGES:
        raise RowContractError(
            f"row of kind 'quality' has judge_prompt_language {language!r}: "
            f"must be one of {', '.join(judge_protocol.JUDGE_LANGUAGES)}"
        )

    rubric_kind = row["rubric_kind"]
    if rubric_kind not in judge_protocol.RUBRIC_KINDS:
        raise RowContractError(
            f"row of kind 'quality' has rubric_kind {rubric_kind!r}: must be "
            f"one of {', '.join(judge_protocol.RUBRIC_KINDS)}"
        )

    # A judged score states how it was reached: either two judges agreed to
    # some measured degree, or one judged and the row says so. Neither is an
    # unattributed number.
    row_agreement = row["agreement"]
    single_judge = row["single_judge"]
    if row_agreement is None and single_judge is not True:
        raise RowContractError(
            "row of kind 'quality' carries agreement=None and "
            f"single_judge={single_judge!r}: a judged score must carry either "
            "an agreement figure or the single_judge flag, and this row "
            "carries neither"
        )
    if single_judge is True and row_agreement is not None:
        raise RowContractError(
            "row of kind 'quality' carries single_judge=True alongside a "
            f"non-null agreement ({row_agreement!r}): one judge produces no "
            "agreement figure, so the row cannot be both"
        )

    _require_block_fields(row, "judge_egress", JUDGE_EGRESS_FIELDS)
    _require_block_fields(row, "judge_cost", JUDGE_COST_FIELDS)
    _validate_judge_cost_providers(row["judge_cost"]["per_provider"])

    egress = row["judge_egress"]
    if not egress["providers"]:
        raise RowContractError(
            "row of kind 'quality' has an empty judge_egress providers list: "
            "a judged row was scored by someone"
        )
    if egress["judge_call_count"] != len(judges):
        raise RowContractError(
            f"row of kind 'quality' has judge_egress judge_call_count="
            f"{egress['judge_call_count']!r} but carries {len(judges)} judge "
            "call record(s): an egress record that disagrees with the calls "
            "on the row is worse than no record"
        )


def _validate_judge_call_record(index: int, record: dict[str, Any]) -> None:
    """Raise on a judge call record whose provenance cannot back its score.

    No fallback routing: a judge bound to one provider and answered by
    another is a silently substituted judgement, so it is refused naming
    both rather than published under either name.
    """
    bound = record["provider"]
    answering = record["answering_provider"]
    if answering != bound:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] answered by provider "
            f"{answering!r} but bound to provider {bound!r}: a judge call is "
            "never re-routed to another provider"
        )

    source = record["answering_provider_source"]
    if source not in judge.ANSWERING_PROVIDER_SOURCES:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] "
            f"answering_provider_source {source!r}: must be one of "
            f"{', '.join(judge.ANSWERING_PROVIDER_SOURCES)}"
        )

    effort = record["reasoning_effort"]
    if not isinstance(effort, str) or not effort:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] reasoning_effort "
            f"{effort!r}: the effort sent, or "
            f"{judge.REASONING_EFFORT_NOT_SENT!r} when none was"
        )

    tokens = record["reasoning_tokens"]
    if tokens is not None and (
        isinstance(tokens, bool) or not isinstance(tokens, int) or tokens < 0
    ):
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] reasoning_tokens="
            f"{tokens!r}: a reasoning count is a non-negative integer or null"
        )

    # A count carries where it came from and no null reason; a null count
    # carries a reason and no source.
    source = record["reasoning_tokens_source"]
    if tokens is not None and source not in judge.REASONING_TOKENS_SOURCES:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] reasoning_tokens="
            f"{tokens!r} with reasoning_tokens_source {source!r}: a count names "
            f"one of {', '.join(judge.REASONING_TOKENS_SOURCES)}"
        )
    if tokens is None and source is not None:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] reasoning_tokens=None "
            f"alongside reasoning_tokens_source {source!r}: a null count has "
            "no source"
        )
    reason = record["reasoning_tokens_null_reason"]
    if tokens is None and reason not in judge.REASONING_TOKENS_NULL_REASONS:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] reasoning_tokens=None "
            f"with reasoning_tokens_null_reason {reason!r}: a null count names "
            f"one of {', '.join(judge.REASONING_TOKENS_NULL_REASONS)}"
        )
    if tokens is not None and reason is not None:
        raise RowContractError(
            f"row of kind 'quality' has judges[{index}] reasoning_tokens="
            f"{tokens!r} alongside reasoning_tokens_null_reason {reason!r}: a "
            "reported count carries no null reason"
        )


def _validate_judge_cost_providers(per_provider: Any) -> None:
    """Raise unless every `per_provider` entry is complete and states its basis."""
    if not isinstance(per_provider, list):
        raise RowContractError(
            f"row of kind 'quality' has a non-list judge_cost per_provider: "
            f"{per_provider!r}"
        )
    for index, entry in enumerate(per_provider):
        if not isinstance(entry, dict):
            raise RowContractError(
                f"row of kind 'quality' has a non-object judge_cost "
                f"per_provider[{index}]: {entry!r}"
            )
        missing = JUDGE_COST_PROVIDER_FIELDS - entry.keys()
        if missing:
            raise RowContractError(
                f"row of kind 'quality' has judge_cost per_provider[{index}] "
                f"missing field(s): {', '.join(sorted(missing))}"
            )
        billing = entry["reasoning_tokens_billing"]
        if billing not in cost.REASONING_TOKEN_BILLING_BASES:
            raise RowContractError(
                f"row of kind 'quality' has judge_cost per_provider[{index}] "
                f"reasoning_tokens_billing {billing!r}: must be one of "
                f"{', '.join(cost.REASONING_TOKEN_BILLING_BASES)}"
            )


def _validate_graded_fields(row: dict[str, Any]) -> None:
    """Hold a row that declares itself graded to the whole graded block.

    A quality row carrying none of `GRADED_FIELDS` is an exact-match row and
    returns untouched. Carrying any of them is the declaration: the row
    publishes a graded score, and every remaining graded field is named as
    missing -- the same message shape `_validate_judged_fields` uses.
    """
    present = GRADED_FIELDS & row.keys()
    if not present:
        return

    missing = GRADED_FIELDS - row.keys()
    if missing:
        raise RowContractError(
            f"row of kind 'quality' declares itself graded by carrying "
            f"{', '.join(sorted(present))} but is missing graded field(s): "
            f"{', '.join(sorted(missing))}"
        )

    _validate_graded_structure(row)


def _validate_graded_structure(row: dict[str, Any]) -> None:
    """Raise on a graded block that cannot back the score it publishes."""
    partial = row.get("partial_failure") is not None
    for field in ("item_score", "suite_score"):
        value = row[field]
        # Held null by `_validate_partial_failure` on a partial row.
        if partial and field == "suite_score" and value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int | float):
            raise RowContractError(
                f"row of kind 'quality' has a non-numeric {field}: {value!r}"
            )
        if not 0.0 <= value <= 1.0:
            raise RowContractError(
                f"row of kind 'quality' has {field}={value!r}, outside the "
                "published 0..1 scale"
            )

    # A score nobody can recompute is not evidence: the row carries the text
    # that was scored beside the reference it was scored against.
    if "subject_output" not in row:
        raise RowContractError(
            "row of kind 'quality' declares itself graded but carries no "
            "subject_output: a score with no scored text cannot be recomputed"
        )

    # Methodology 9 made checkable at the writer instead of trusted at the
    # scorer: a named failure is a zero, always.
    failure_reason = row["failure_reason"]
    if failure_reason is not None and row["item_score"] != 0.0:
        raise RowContractError(
            f"row of kind 'quality' names failure_reason {failure_reason!r} "
            f"but carries item_score={row['item_score']!r}: a failed "
            "generation scores 0.0"
        )

    # One row cannot publish an exact-match rate and a graded score at once:
    # whichever a reader picked up would be the wrong one half the time.
    for field in ("correct", "suite_accuracy"):
        if row[field] is not None:
            raise RowContractError(
                f"row of kind 'quality' carries a graded block alongside a "
                f"non-null {field} ({row[field]!r}): a graded score and an "
                "exact-match score cannot both be published on one row"
            )

    if not (partial and row["score_breakdown"] is None):
        _validate_graded_breakdown(row["score_breakdown"])


def _validate_graded_breakdown(breakdown: Any) -> None:
    """Raise unless `breakdown` is one complete cell per published language."""
    if not isinstance(breakdown, dict):
        raise RowContractError(
            f"row of kind 'quality' has a non-object score_breakdown: {breakdown!r}"
        )
    expected = set(suite_gate.LANGUAGES)
    if set(breakdown) != expected:
        raise RowContractError(
            f"row of kind 'quality' has a score_breakdown over {sorted(breakdown)!r}, "
            f"expected one cell per language: {sorted(expected)!r}"
        )
    for language, cell in breakdown.items():
        if not isinstance(cell, dict):
            raise RowContractError(
                f"row of kind 'quality' has a non-object score_breakdown "
                f"cell for {language!r}: {cell!r}"
            )
        missing = GRADED_LANGUAGE_CELL_FIELDS - cell.keys()
        if missing:
            raise RowContractError(
                f"row of kind 'quality' has a score_breakdown cell for "
                f"{language!r} missing field(s): {', '.join(sorted(missing))}"
            )


def _require_block_fields(
    row: dict[str, Any], field: str, required: frozenset[str]
) -> None:
    """Raise unless `row[field]` is an object carrying every key in `required`."""
    block = row[field]
    if not isinstance(block, dict):
        raise RowContractError(
            f"row of kind 'quality' has a non-object {field}: {block!r}"
        )
    missing = required - block.keys()
    if missing:
        raise RowContractError(
            f"row of kind 'quality' has {field} missing field(s): "
            f"{', '.join(sorted(missing))}"
        )


def _validate_runtime_repetition_structure(row: dict[str, Any]) -> None:
    """Raise on a repetition set that cannot back the aggregates it publishes."""
    repetitions_n = row["repetitions_n"]
    if repetitions_n < 2:
        raise RowContractError(
            f"row of kind 'runtime' has repetitions_n={repetitions_n!r}: "
            "the sample sd is undefined below N=2"
        )

    repetitions = row["repetitions"]
    if len(repetitions) != repetitions_n:
        raise RowContractError(
            f"row of kind 'runtime' has {len(repetitions)} repetitions but "
            f"repetitions_n={repetitions_n!r}"
        )
    indices = [rep["index"] for rep in repetitions]
    if indices != list(range(1, repetitions_n + 1)):
        raise RowContractError(
            f"row of kind 'runtime' has non-contiguous repetition indices: "
            f"{indices!r}, expected 1..{repetitions_n}"
        )

    # This catches the declaration drifting from the declared field set. That
    # every name in MEASUREMENT_FIELDS is also a REQUIRED_FIELDS entry -- so a
    # row reaching here already carries all of them, checked above -- is a
    # static invariant between two hand-maintained sets, guarded by
    # tests/test_row_contract.py's
    # test_every_declared_measurement_is_a_required_runtime_field rather than
    # re-derived per row.
    declared = set(row["aggregation"])
    if declared != aggregation.MEASUREMENT_FIELDS:
        raise RowContractError(
            "row of kind 'runtime' has an aggregation map that does not "
            f"match the declared measurement set: {declared!r} != "
            f"{set(aggregation.MEASUREMENT_FIELDS)!r}"
        )
