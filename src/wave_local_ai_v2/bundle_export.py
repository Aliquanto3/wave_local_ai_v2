"""The published bundle as five flat CSV tables and the dictionary that reads them.

`wave-local-ai-v2-export` reads the bundle parts -- the two
`*-reference.jsonl` row files, `fiches/`, the roster file,
`suite-definitions/`, and the analysis records in `comparisons/` and
`leader-sets/` -- and writes, into a directory it is told:

- `quality_items.csv`: one row per quality row;
- `runtime_aggregates.csv`: one row per runtime row;
- `fiches.csv`: one row per stored fiche;
- `roster.csv`: one row per roster entry;
- `comparison_records.csv`: one row per comparison-family record, per
  comparison it holds, per leader-set record and per subject that record
  lists, the kind named in `record_kind`;
- `column_dictionary.csv`: every column of every table, what it means, its
  unit, the source field it came from and what an empty cell means there, plus
  the fields the bundle read does not carry, each with its owner;
- `bundle_manifest.csv`: what was read, and the `schema_version` the rows
  carry -- never the live `row_contract.SCHEMA_VERSION`.

Four rules hold everywhere in this module:

1. **Nothing is computed.** Every cell is a value a bundle file carries. The
   per-repetition arrays stay in the bundle, not in a table.
2. **Absence stays absence.** A field a row does not carry and a field it
   records as `null` are both an empty cell; the row's `fields_not_carried`
   column lists the columns whose emptiness means "not carried", so the two
   stay distinguishable without a `null` token turning a numeric column into
   text.
3. **Every column is documented or the export refuses.** Columns follow the
   paths the bundle's records actually carry, and each one is described by
   `_REGISTRY`; a path it does not know stops the export naming that path.
   An unresolved pointer stops it too. Nothing is written until everything
   has been read.
4. **The format is pinned, not defaulted** (`CSV_FORMAT`): UTF-8 without a
   BOM, comma delimiter, double-quote quoting with doubling and minimal
   quoting, CRLF record terminator (RFC 4180), floats as Python's shortest
   round-trip `repr`, booleans as `true`/`false`, lists and the judge block's
   nested records as compact JSON.

Standard library only: the runtime dependency set does not grow for this.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from wave_local_ai_v2 import (
    comparison,
    field_doc,
    leader_set,
    results,
    roster,
    row_contract,
    score_interval,
    settings,
)
from wave_local_ai_v2.fiche_registry import read_fiche
from wave_local_ai_v2.field_doc import FieldDoc
from wave_local_ai_v2.suite_snapshot import snapshot_filename

QUALITY_TABLE = "quality_items"
RUNTIME_TABLE = "runtime_aggregates"
FICHE_TABLE = "fiches"
ROSTER_TABLE = "roster"
COMPARISON_TABLE = "comparison_records"
TABLES: tuple[str, ...] = (
    QUALITY_TABLE,
    RUNTIME_TABLE,
    FICHE_TABLE,
    ROSTER_TABLE,
    COMPARISON_TABLE,
)
DICTIONARY_FILE = "column_dictionary.csv"
MANIFEST_FILE = "bundle_manifest.csv"

# The column every row table ends with: the columns of that row whose empty
# cell means "the source does not carry this field" rather than a recorded
# `null`, as a JSON array in column order.
NOT_CARRIED_COLUMN = "fields_not_carried"

# Stated once, here, and repeated in `aidd_docs/results/README.md`.
CSV_FORMAT: dict[str, str] = {
    "encoding": "utf-8 (no byte-order mark)",
    "delimiter": ",",
    "quotechar": '"',
    "quoting": "minimal (a cell holding a delimiter, quote or line break is quoted)",
    "escaping": "a quote inside a quoted cell is doubled",
    "record_terminator": "CRLF (RFC 4180); line breaks inside quoted cells are kept",
    "float": "Python repr: the shortest text that reads back as the same double",
    "boolean": "true / false",
    "list": "compact JSON array",
    "empty_cell": "recorded null, or not carried (then listed in fields_not_carried)",
}

# Per-repetition arrays: published on the row, left in the bundle. The
# aggregates table carries the row's own aggregates over them, never the
# arrays and never anything recomputed from them.
_EXCLUDED_ROW_PATHS: frozenset[tuple[str, ...]] = frozenset(
    {
        ("repetitions",),
        ("warmup_repetitions",),
        ("verdict", "reference_repetitions"),
    }
)
EXCLUDED_NOTE = (
    "Per-repetition arrays (`repetitions`, `warmup_repetitions`, "
    "`verdict.reference_repetitions`) stay in the bundle's runtime rows and are "
    "not a column of any table; the aggregates beside them are the row's own."
)

# Nested records kept whole as one JSON cell: their shape is a list of
# records or a record of records, with no fixed column set.
_JSON_CELL_ROW_FIELDS: frozenset[str] = frozenset(
    {"judges", "judge_egress", "judge_cost", "profile_overrides"}
)


class ExportError(RuntimeError):
    """Raised when the bundle cannot be exported without inventing or dropping data."""


# --------------------------------------------------------------------------
# The registry: what every column means.
#
# Keyed by source path, `*` standing for one key whose name varies (a
# language code, a metric name). A path the bundle carries and the registry
# does not know refuses the export. `tests/test_bundle_export.py` partitions
# the row registry against `row_contract`, so a field added to the contract
# fails the build until it is described here.
# --------------------------------------------------------------------------


_ROW_EMPTY = (
    "The row records null for this field; if the row does not carry the field "
    "at all, the column name is also listed in its fields_not_carried."
)
_RESOLVED_EMPTY = (
    "The cited record does not carry this field (the column name is then listed "
    "in the row's fields_not_carried), or records it as null."
)
_NEVER_EMPTY = "Never empty."
_ENERGY_EMPTY = (
    "No measurement exists for this channel on this row (a cloud row, or no "
    "GPU found); the matching *_energy_method column says which."
)
_PRICE_EMPTY = (
    "Not a list-priced row: a local row is costed from energy, not a price table."
)

_ID = field_doc.ID
_TEXT = field_doc.TEXT
_BOOL = field_doc.BOOL
_COUNT = field_doc.COUNT
_JSON_ARRAY = field_doc.JSON_ARRAY
_JSON_OBJECT = field_doc.JSON_OBJECT
_SHA = field_doc.SHA
_RATIO = field_doc.RATIO

_COMMON_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    # Identity and provenance.
    ("schema_version",): FieldDoc(
        "Row-contract version this row was written under, as the row states it.",
        _ID,
    ),
    ("run_id",): FieldDoc("One benchmark invocation; shared by its rows.", _ID),
    ("captured_at",): FieldDoc(
        "When the invocation started.", "ISO 8601 timestamp, UTC offset"
    ),
    ("release_version",): FieldDoc("Packaged version of the code that ran.", _TEXT),
    ("commit_sha",): FieldDoc("Git commit of the code that ran.", "git SHA-1, hex"),
    ("tree_dirty",): FieldDoc(
        "Whether the working tree had uncommitted changes when the row was written.",
        _BOOL,
    ),
    ("roster_entry_id",): FieldDoc(
        "Roster entry the run launched (for a cloud row, the local subject's "
        "entry it was run beside). Resolved into the roster_entry_* columns.",
        _ID,
    ),
    ("roster_version",): FieldDoc(
        "Roster file version the run read, as the row states it; compare with "
        "roster_file_version, the version the export resolved against.",
        "integer",
    ),
    ("endpoint",): FieldDoc("Endpoint the prompt was sent to.", "URL or path"),
    ("prompt_template_id",): FieldDoc(
        "Which prompt wrapping the call path applied ('none' when sent raw).", _ID
    ),
    ("prompt_template_hash",): FieldDoc(
        "Content hash of that template.",
        _SHA,
        "No template was applied (prompt_template_id is 'none'), or the row "
        "does not carry the field.",
    ),
    ("prompt_capture",): FieldDoc(
        "Whether the prompt text on the row is the text actually sent.", _ID
    ),
    ("prompt_variant_id",): FieldDoc(
        "Prompt variant applied to the authored prompt before templating.", _ID
    ),
    ("prompt_variant_version",): FieldDoc("Version of that variant.", _ID),
    ("subject_egress",): FieldDoc(
        "Where the subject prompt went: 'none' when it was served on the "
        "machine, else the id of the cloud provider that received it. The "
        "subject call only; judge calls are described by judge_egress.",
        _ID,
    ),
    ("prompt_before_template",): FieldDoc(
        "The prompt as the variant left it, before the engine's templating.", _TEXT
    ),
    ("engine_id",): FieldDoc(
        "Inference engine that produced the row, as the engine registry names "
        "it; not_applicable on a row no local engine produced (a cloud subject).",
        _ID,
    ),
    ("engine_build",): FieldDoc(
        "Engine build as the binary reported it at run time (live probe).",
        _ID,
        "The build could not be read, or no local engine produced the row "
        "(engine_id is then not_applicable).",
    ),
    ("machine_id",): FieldDoc(
        "Declared machine (aidd_docs/roster/machines.json) the run was executed "
        "on; not_applicable on a row no local model produced (a cloud subject).",
        _ID,
    ),
    ("compute_mode",): FieldDoc(
        "Compute mode the run was executed under: gpu or cpu_only; "
        "not_applicable on a row no local model produced (a cloud subject).",
        _ID,
    ),
    ("profile_id",): FieldDoc(
        "Run profile the launch resolved (aidd_docs/roster/profiles.json), "
        "named <roster_entry_id>@<machine_id>/<compute_mode>; not_applicable on "
        "a row no local model produced (a cloud subject).",
        _ID,
        "The row predates the run profile fields (schema below 26).",
    ),
    ("profile_overrides",): FieldDoc(
        "Every launch value the operator overrode, each with the profile's "
        "value and the operator's; {} when the run is the profile as declared; "
        "not_applicable on a row no local model produced (a cloud subject).",
        _JSON_OBJECT,
        "The row predates the run profile fields (schema below 26).",
    ),
    ("campaign_id",): FieldDoc(
        "Campaign the run belongs to (aidd_docs/campaigns/<campaign_id>.json); "
        "none for a run started under no campaign and on every cloud subject's "
        "row.",
        _ID,
    ),
    ("fiche_hash",): FieldDoc(
        "Hardware and run fiche the row cites. Resolved into the fiche_* columns.",
        _SHA,
    ),
    ("prompt",): FieldDoc("The prompt text the row was produced from.", _TEXT),
    # Reproduction verdict.
    ("verdict", "verdict"): FieldDoc(
        "Reproduction verdict against a reference run: reproduced, "
        "not_reproduced or not_comparable.",
        _ID,
    ),
    ("verdict", "reference_run_id"): FieldDoc(
        "Run the verdict was judged against.",
        _ID,
        "No reference run matched (verdict not_comparable).",
    ),
    ("verdict", "differing_fields"): FieldDoc(
        "Items (quality) or fields (runtime) that differed from the reference.",
        _JSON_ARRAY,
    ),
    ("verdict", "reason"): FieldDoc(
        "Why the verdict is what it is.", _TEXT, "The verdict needs no reason."
    ),
    ("verdict", "compared_field"): FieldDoc(
        "Row field the quality verdict compared item by item.", _ID
    ),
    ("verdict", "gen_tok_per_s_delta"): FieldDoc(
        "Relative difference of gen_tok_per_s from the reference run.", "ratio"
    ),
    ("verdict", "ttft_ms_delta"): FieldDoc(
        "Relative difference of ttft_ms from the reference run.", "ratio"
    ),
    ("verdict", "prompt_tok_per_s_delta"): FieldDoc(
        "Relative difference of prompt_tok_per_s from the reference run.", "ratio"
    ),
    # Sampling, as sent.
    ("sampling", "seed"): FieldDoc("Sampler seed sent with the request.", "integer"),
    ("sampling", "random_seed"): FieldDoc(
        "Sampler seed, under the name Mistral's API uses.", "integer"
    ),
    ("sampling", "temperature"): FieldDoc("Sampling temperature.", "number"),
    ("sampling", "top_p"): FieldDoc("Nucleus sampling threshold.", _RATIO),
    ("sampling", "top_k"): FieldDoc("Top-k cut-off (0 disables it).", _COUNT),
    ("sampling", "min_p"): FieldDoc("Min-p sampling threshold.", _RATIO),
    ("sampling", "presence_penalty"): FieldDoc("Presence penalty.", "number"),
    # The blocks themselves, for a bundle where no row carries any of them:
    # the dictionary then names the block as not carried.
    ("sampling",): FieldDoc("Sampler settings sent with the request.", _JSON_OBJECT),
    ("verdict",): FieldDoc("Reproduction verdict block.", _JSON_OBJECT),
}

_ENERGY_COST_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("cpu_energy_kwh",): FieldDoc(
        "CPU energy over the measured window.", "kWh", _ENERGY_EMPTY
    ),
    ("cpu_energy_method",): FieldDoc(
        "How cpu_energy_kwh was obtained (estimated_tdp is an estimate).", _ID
    ),
    ("gpu_energy_kwh",): FieldDoc(
        "GPU energy over the measured window.", "kWh", _ENERGY_EMPTY
    ),
    ("gpu_energy_method",): FieldDoc(
        "How gpu_energy_kwh was obtained (measured_nvml is a measurement).", _ID
    ),
    ("ram_energy_kwh",): FieldDoc(
        "RAM energy over the measured window.", "kWh", _ENERGY_EMPTY
    ),
    ("ram_energy_method",): FieldDoc(
        "How ram_energy_kwh was obtained (estimated_constant is an estimate).", _ID
    ),
    ("energy_kwh",): FieldDoc(
        "Total energy of the batch or run, across the three channels.", "kWh"
    ),
    ("active_window_s",): FieldDoc(
        "Time the energy channels were measured over (generations only).",
        "seconds",
    ),
    ("idle_window_s",): FieldDoc(
        "Cooldown time excluded from the energy window.", "seconds"
    ),
    ("energy_window_method",): FieldDoc(
        "Which window the energy fields were measured over.", _ID
    ),
    ("emissions_kg",): FieldDoc("Emissions attributed to the batch or run.", "kg CO2e"),
    ("emission_factor_kg_per_kwh",): FieldDoc(
        "Grid emission factor applied to energy_kwh.", "kg CO2e per kWh"
    ),
    ("emission_region",): FieldDoc("Region the emission factor is for.", _ID),
    ("emissions_scope",): FieldDoc(
        "GHG scope of the emissions (scope_2 local, scope_3 cloud estimate).", _ID
    ),
    ("emissions_scope_formula_id",): FieldDoc(
        "Formula a scope-3 estimate was computed with.",
        _ID,
        "Not a scope-3 estimate: the emissions were measured on this machine.",
    ),
    ("scope_comparability",): FieldDoc(
        "Statement of what a scope-3 figure may be compared with.",
        _TEXT,
        "Not a scope-3 estimate.",
    ),
    ("tokens_in_total",): FieldDoc(
        "Prompt tokens over the batch or run.",
        "tokens",
        "The call path reported no prompt token count.",
    ),
    ("tokens_out_total",): FieldDoc("Output tokens over the batch or run.", "tokens"),
    ("cost_total",): FieldDoc(
        "Cost of the batch or run, in cost_currency.", "currency (cost_currency)"
    ),
    ("cost_currency",): FieldDoc("Currency of cost_total.", "ISO 4217 code"),
    ("cost_per_million_tokens",): FieldDoc(
        "cost_total per million tokens, as the row states it.",
        "currency per million tokens",
        "Not computable on this row: a token count it needs is null.",
    ),
    ("normalization_unit",): FieldDoc(
        "Token basis cost_per_million_tokens is normalised on.", _ID
    ),
    ("kwh_price_eur",): FieldDoc(
        "Electricity price a local cost was computed from.",
        "EUR per kWh",
        "Not an energy-costed row: a cloud row is list-priced.",
    ),
    ("kwh_price_currency",): FieldDoc(
        "Currency of kwh_price_eur.", "ISO 4217 code", "Not an energy-costed row."
    ),
    ("kwh_price_recorded_at",): FieldDoc(
        "Date the electricity price was recorded.",
        "date, YYYY-MM-DD",
        "Not an energy-costed row.",
    ),
    ("list_price_input_per_million",): FieldDoc(
        "Provider list price for input tokens.",
        "currency per million tokens",
        _PRICE_EMPTY,
    ),
    ("list_price_output_per_million",): FieldDoc(
        "Provider list price for output tokens.",
        "currency per million tokens",
        _PRICE_EMPTY,
    ),
    ("list_price_per_million_tokens",): FieldDoc(
        "Blended rate this batch's token mix worked out to.",
        "currency per million tokens",
        _PRICE_EMPTY,
    ),
    ("list_price_currency",): FieldDoc(
        "Currency of the list prices.", "ISO 4217 code", _PRICE_EMPTY
    ),
    ("list_price_retrieved_at",): FieldDoc(
        "Date the list prices were read.", "date, YYYY-MM-DD", _PRICE_EMPTY
    ),
}

# A partial row (`partial_failure` set) publishes no suite-level score: the
# batch stopped on a failure, and a mean over the items that finished first
# is a biased sample.
_PARTIAL_SCORE_DOC = (
    "or the row's batch was partial when it was written (see partial_failure): "
    "a partial batch publishes no suite-level score."
)

# An item_ value is null only with its reason; a row below schema "18" does
# not carry the field at all.
_ITEM_NULL_DOC = (
    "The value was not reported; its _null_reason column says why. A row "
    "below schema 18 does not carry the field."
)
_ITEM_REPORTED_DOC = "The value was reported, or the row does not carry the field."

# The interval block's cells (schema "21"): the suite's and one per language.
_INTERVAL_CELLS: tuple[tuple[tuple[str, ...], str], ...] = (
    (("score_interval", "suite"), "suite score's"),
    (("score_interval", "by_language", "*"), "language cell's"),
)
_INTERVAL_SCALE = "the suite's score scale (suite_accuracy or suite_score, 0..1)"
# A row written before the interval existed does not carry the block, and a
# row with no suite score records it as null: either way an empty cell, never
# a zero, and never a value back-filled onto a row that did not publish it.
_INTERVAL_EMPTY = (
    "The row carries no interval block: a row written before schema 21 does "
    "not carry the field (the column is then listed in its fields_not_carried), "
    "and a partial or judge-probe row records the block as null. Never a zero, "
    "never back-filled."
)
_INTERVAL_VALUE_EMPTY = (
    "The interval is undefined and null_reason says why, or the row carries "
    "no interval block (written before schema 21, listed in fields_not_carried; "
    "or recorded null). Never a zero, never back-filled."
)
_INTERVAL_PERCENT = f"{score_interval.CONFIDENCE_LEVEL:.0%}"

_QUALITY_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("model_id",): FieldDoc("Model that answered the item.", _ID),
    ("provider",): FieldDoc("Who ran the model: local, mistral or google.", _ID),
    ("task_suite",): FieldDoc(
        "Suite kind; select on it before comparing any score column.", _ID
    ),
    ("item_id",): FieldDoc("Suite item this row scores.", _ID),
    ("expected_label",): FieldDoc(
        "Label the item should be routed to (exact-match suites).",
        _TEXT,
        "Not an exact-match item.",
    ),
    ("predicted_label",): FieldDoc(
        "Label extracted from the model's answer.",
        _TEXT,
        "No label could be extracted; failure_reason says why.",
    ),
    ("correct",): FieldDoc(
        "Whether predicted_label equals expected_label. The per-item value "
        "suite_accuracy and the language accuracies are means of.",
        _BOOL,
        "Not an exact-match row (a graded row records null here).",
    ),
    ("suite_accuracy",): FieldDoc(
        "Share of the batch's items answered correctly, as published on the "
        "row; the same on every row of one (run_id, provider, model_id) batch.",
        _RATIO,
        f"Not an exact-match row, {_PARTIAL_SCORE_DOC}",
    ),
    ("language_breakdown", "*", "accuracy"): FieldDoc(
        "Share of the batch's items in this language answered correctly.", _RATIO
    ),
    ("language_breakdown", "*", "n"): FieldDoc(
        "Items in this language in the batch.", _COUNT
    ),
    ("language_breakdown", "*", "indicative"): FieldDoc(
        "Whether the language cell is too small to rank on.", _BOOL
    ),
    ("language_breakdown",): FieldDoc(
        "Per-language accuracy block.",
        _JSON_OBJECT,
        f"Not an exact-match row, {_PARTIAL_SCORE_DOC}",
    ),
    # The batch's bootstrap interval (schema "21", Methodology 24).
    ("score_interval",): FieldDoc(
        "Bootstrap confidence interval block of the batch's suite score "
        "(suite_accuracy or suite_score) and of each language cell; the same "
        "on every row of one batch.",
        _JSON_OBJECT,
        f"No suite score to qualify (a judge-probe row), {_PARTIAL_SCORE_DOC} "
        "A row below schema 21 does not carry the field.",
    ),
    ("score_interval", "confidence_level"): FieldDoc(
        f"Confidence level of the interval ({score_interval.CONFIDENCE_LEVEL}).",
        _RATIO,
        _INTERVAL_EMPTY,
    ),
    ("score_interval", "resamples"): FieldDoc(
        f"Bootstrap resamples drawn per interval ({score_interval.RESAMPLES}).",
        _COUNT,
        _INTERVAL_EMPTY,
    ),
    ("score_interval", "method"): FieldDoc(
        f"Interval method: {score_interval.METHOD_PERCENTILE}.", _ID, _INTERVAL_EMPTY
    ),
    ("score_interval", "seed"): FieldDoc(
        "Seed each interval's generator was freshly seeded with.",
        "integer",
        _INTERVAL_EMPTY,
    ),
    ("score_interval", "generator", "library"): FieldDoc(
        "Random generator that drew the resamples.", _TEXT, _INTERVAL_EMPTY
    ),
    ("score_interval", "generator", "version"): FieldDoc(
        "Interpreter major.minor version the generator ran under.",
        _TEXT,
        _INTERVAL_EMPTY,
    ),
    ("score_interval", "draw_procedure_id"): FieldDoc(
        "Versioned draw procedure, defined in score_interval.py. "
        f"{score_interval.DRAW_PROCEDURE_ID}: a cell's items in ascending "
        "item_id order, each item's value correct as 1 or 0, or item_score; "
        "each cell from a fresh random.Random(seed); each resample draws n "
        "indexes in turn, one index being getrandbits(n.bit_length()) redrawn "
        "until below n; a resample's value is math.fsum of its values over n; "
        "the sorted resample values give the bounds as type-7 quantiles at "
        "q = (1 - confidence_level) / 2 and 1 - q: at h = (resamples - 1) * q, "
        "low + (h - floor(h)) * (high - low), low and high the values at "
        "positions floor(h) and floor(h) + 1 counted from 0.",
        _ID,
        _INTERVAL_EMPTY,
    ),
    ("score_interval", "suite", "n"): FieldDoc(
        "Items the suite interval was resampled over, unstratified.",
        _COUNT,
        _INTERVAL_EMPTY,
    ),
    ("score_interval", "by_language", "*", "n"): FieldDoc(
        "Items in this language the language interval was resampled over.",
        _COUNT,
        _INTERVAL_EMPTY,
    ),
    **{
        (*prefix, "lower"): FieldDoc(
            f"Lower bound of the {scope} {_INTERVAL_PERCENT} interval.",
            _INTERVAL_SCALE,
            _INTERVAL_VALUE_EMPTY,
        )
        for prefix, scope in _INTERVAL_CELLS
    },
    **{
        (*prefix, "upper"): FieldDoc(
            f"Upper bound of the {scope} {_INTERVAL_PERCENT} interval.",
            _INTERVAL_SCALE,
            _INTERVAL_VALUE_EMPTY,
        )
        for prefix, scope in _INTERVAL_CELLS
    },
    **{
        (*prefix, "minimum_detectable_effect"): FieldDoc(
            f"Minimum detectable effect: the smallest difference the {scope} "
            "interval could resolve, half its width, read off the same resample.",
            _INTERVAL_SCALE,
            _INTERVAL_VALUE_EMPTY,
        )
        for prefix, scope in _INTERVAL_CELLS
    },
    **{
        (*prefix, "null_reason"): FieldDoc(
            f"Why the {scope} interval is undefined: "
            f"{score_interval.NULL_ZERO_WIDTH} (every item scored the same, as "
            f"a suite scored 1.0 or 0.0) or {score_interval.NULL_NO_ITEMS} (the "
            "cell holds no item).",
            _ID,
            "The interval is defined, or the row carries no interval block "
            "(written before schema 21, listed in fields_not_carried; or "
            "recorded null). Never back-filled.",
        )
        for prefix, scope in _INTERVAL_CELLS
    },
    ("max_output_tokens",): FieldDoc("Output token cap per item.", "tokens"),
    ("stop_sequences",): FieldDoc("Stop sequences sent with each item.", _JSON_ARRAY),
    ("thinking_policy",): FieldDoc(
        "Suite-declared reasoning policy: disabled or allowed.", _ID
    ),
    ("context_length",): FieldDoc("Context window the suite declares.", "tokens"),
    ("suite_id",): FieldDoc(
        "Suite cited; with suite_version, resolved into suite_definition_* columns.",
        _ID,
    ),
    ("suite_version",): FieldDoc("Suite version cited.", _ID),
    ("prompt_set_hash",): FieldDoc(
        "Content hash of the suite's item set, as the row states it.", _SHA
    ),
    ("language",): FieldDoc("Language of the item.", "ISO 639-1 code"),
    ("provenance",): FieldDoc("Where the item comes from (hand_written).", _ID),
    ("contamination_risk",): FieldDoc(
        "Whether the item may appear in public training data.", _BOOL
    ),
    ("indicative",): FieldDoc(
        "Whether the suite-level score is marked indicative only.", _BOOL
    ),
    ("indicative_reasons",): FieldDoc(
        "Why the score is indicative; empty array when it is not.", _JSON_ARRAY
    ),
    ("suite_level",): FieldDoc(
        "Level the suite was certified at: development or publication.", _ID
    ),
    ("family",): FieldDoc(
        "Model family (vendor lineage) of the row's subject: the local entry's "
        "for a local row, the cloud model's own for a cloud row.",
        _ID,
        "The row predates schema 19 and does not carry the field.",
    ),
    ("size_class",): FieldDoc(
        "Size class of the local entry the row's subject is (~0.5B, ~2B, ~4B, "
        "~8B-and-up, banded on total parameters).",
        _ID,
        "A cloud subject, which has no size class; a local entry declaring none; "
        "or the row predates schema 19 and does not carry the field.",
    ),
    # The agentic harness that ran the row (schema "20", Methodology 23).
    ("harness_id",): FieldDoc(
        "Agentic harness the row ran under, one of direct (plain client calls, "
        "no framework), smolagents, langgraph, pydantic-ai or llamaindex.",
        _ID,
        "The row predates schema 20 and does not carry the field.",
    ),
    ("harness_version",): FieldDoc(
        "Installed version of the harness's package, read when the row was "
        "written (for direct, the requests HTTP client its calls go through).",
        _TEXT,
        "The row predates schema 20 and does not carry the field.",
    ),
    ("harness_prompt_overhead",): FieldDoc(
        "Per-call prompt overhead block: tokens and null_reason.",
        _JSON_OBJECT,
        "The row predates schema 20 and does not carry the field.",
    ),
    ("harness_prompt_overhead", "tokens"): FieldDoc(
        "Tokens the harness added around the item's own prompt on this call: "
        "the engine's prompt-token count minus the item's own rendered prompt "
        "(its tool definitions included) under the same tokenizer.",
        "tokens",
        "No measurement exists; harness_prompt_overhead.null_reason says why "
        "(never a zero in its place), or the row predates schema 20.",
    ),
    ("harness_prompt_overhead", "null_reason"): FieldDoc(
        "Why harness_prompt_overhead.tokens is empty: unmeasurable (the harness "
        "rewrites the item's prompt rather than wrapping it), "
        "item_prompt_not_counted (no count of the item's own prompt under the "
        "row's tokenizer, as for a cloud subject), or the engine count's own "
        "reason (not_reported_by_engine, not_reported_by_provider, "
        "no_generation_call).",
        _ID,
        "The overhead was measured, or the row predates schema 20.",
    ),
    ("item_licence",): FieldDoc(
        "Licence the item is redistributed under, as its author declares it "
        "(CC-BY-4.0 for a hand-written item). Declared, not verified.",
        "SPDX licence identifier",
    ),
    ("item_source",): FieldDoc(
        "Public source the item was drawn from, as its author declares it. "
        "Declared, not verified.",
        _ID,
        "The item was not drawn from a source (a hand-written item), or the "
        "row does not carry the field.",
    ),
    ("item_source_revision",): FieldDoc(
        "Revision of that source the item was drawn at.",
        _ID,
        "The item was not drawn from a source (a hand-written item), or the "
        "row does not carry the field.",
    ),
    ("failure_reason",): FieldDoc(
        "Why no usable answer was produced for this item.",
        _ID,
        "The item produced an answer.",
    ),
    ("failure_counts", "empty"): FieldDoc(
        "Items in the batch with an empty answer.", _COUNT
    ),
    ("failure_counts", "unparseable"): FieldDoc(
        "Items in the batch whose answer held no label.", _COUNT
    ),
    ("failure_counts", "truncated_max_tokens"): FieldDoc(
        "Items in the batch cut by the output cap, as the row reports it.", _COUNT
    ),
    ("failure_counts", "truncated_context"): FieldDoc(
        "Items in the batch cut by the context window.", _COUNT
    ),
    ("failure_counts",): FieldDoc("Batch failure counts block.", _JSON_OBJECT),
    ("retries",): FieldDoc("Retries the item's request took.", _COUNT),
    ("resumed",): FieldDoc("Whether the row was written by a --resume run.", _BOOL),
    ("retry_budget",): FieldDoc(
        "The retry total each cloud provider's calls in this row's batch drew "
        "from, keyed by provider, derived from the batch's item count; {} for "
        "a batch with no cloud call.",
        _JSON_OBJECT,
    ),
    ("partial_failure",): FieldDoc(
        "Empty when the batch was complete when this row was written; else the "
        "provider, item_id and reason of the call that left it partial. A "
        "partial row carries no suite-level score.",
        _JSON_OBJECT,
        "The batch was complete when this row was written.",
    ),
    # The item's own generation figures (schema "18"): one generation per
    # item, never the runtime protocol's aggregate.
    ("item_tokens_in",): FieldDoc(
        "Prompt tokens of this item's own generation, as its engine or provider "
        "reported them.",
        "tokens",
        _ITEM_NULL_DOC,
    ),
    ("item_tokens_in_null_reason",): FieldDoc(
        "Why item_tokens_in is empty: not_reported_by_engine, "
        "not_reported_by_provider or no_generation_call.",
        _ID,
        _ITEM_REPORTED_DOC,
    ),
    ("item_tokens_out",): FieldDoc(
        "Output tokens of this item's own generation, as its engine or provider "
        "reported them.",
        "tokens",
        _ITEM_NULL_DOC,
    ),
    ("item_tokens_out_null_reason",): FieldDoc(
        "Why item_tokens_out is empty (same reasons as item_tokens_in).",
        _ID,
        _ITEM_REPORTED_DOC,
    ),
    ("item_ttft_ms",): FieldDoc(
        "Engine-reported time to first token of this item's one generation "
        "(llama-server timings.prompt_ms). A single per-item generation, not "
        "the runtime protocol's ttft_ms: no warm-up exclusion, no repetitions.",
        "milliseconds",
        _ITEM_NULL_DOC,
    ),
    ("item_ttft_ms_null_reason",): FieldDoc(
        "Why item_ttft_ms is empty (a cloud provider reports none).",
        _ID,
        _ITEM_REPORTED_DOC,
    ),
    ("item_ttft_source",): FieldDoc(
        "Where item_ttft_ms was read from, on ttft_source's values.",
        _ID,
        "item_ttft_ms is empty.",
    ),
    ("item_prompt_tokens_cached",): FieldDoc(
        "Prompt tokens the engine reused from its cache for this item "
        "(llama-server timings.cache_n); item_ttft_ms covers only the rest.",
        "tokens",
        _ITEM_NULL_DOC,
    ),
    ("item_prompt_tokens_cached_null_reason",): FieldDoc(
        "Why item_prompt_tokens_cached is empty.",
        _ID,
        _ITEM_REPORTED_DOC,
    ),
    ("item_measurement_kind",): FieldDoc(
        "single_generation: the item_ fields describe one generation of this "
        "item, not an aggregate over repetitions.",
        _ID,
    ),
    ("item_first_in_batch",): FieldDoc(
        "Whether this item was its batch's first generation (on a freshly "
        "launched server for a local row), the one a reader may exclude as cold.",
        _BOOL,
    ),
    ("subject_output",): FieldDoc(
        "The model's raw answer.", _TEXT, "Not recorded for this suite kind."
    ),
}

# The graded block: present on a translation row, absent from an exact-match one.
_GRADED_DOC = "Not a graded row."
_GRADED_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("metric_id",): FieldDoc("Metric the item was scored with.", _ID, _GRADED_DOC),
    ("metric_version",): FieldDoc("Version of that metric.", _ID, _GRADED_DOC),
    ("metric_params", "*"): FieldDoc(
        "One metric parameter, named by the column suffix.", "as the metric defines"
    ),
    ("metric_params",): FieldDoc("Metric parameter block.", _JSON_OBJECT, _GRADED_DOC),
    ("item_score",): FieldDoc("This item's score.", _RATIO, _GRADED_DOC),
    ("suite_score",): FieldDoc(
        "Mean item_score of the batch.",
        _RATIO,
        f"Not a graded row, {_PARTIAL_SCORE_DOC}",
    ),
    ("score_breakdown", "*", "score"): FieldDoc(
        "Mean item_score over the batch's items in this source language.", _RATIO
    ),
    ("score_breakdown", "*", "n"): FieldDoc(
        "Items in this source language in the batch.", _COUNT
    ),
    ("score_breakdown", "*", "indicative"): FieldDoc(
        "Whether the language cell is too small to rank on.", _BOOL
    ),
    ("score_breakdown",): FieldDoc(
        "Per-language score block.",
        _JSON_OBJECT,
        f"Not a graded row, {_PARTIAL_SCORE_DOC}",
    ),
    ("reference_output",): FieldDoc(
        "Reference text the score was computed against.", _TEXT, _GRADED_DOC
    ),
}

# The judge block: present only on a judged row.
_JUDGED_DOC = "Not a judged row."
_JUDGED_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("judge_prompt_id",): FieldDoc("Judge prompt issued.", _ID, _JUDGED_DOC),
    ("judge_prompt_template_hash",): FieldDoc(
        "Content hash of the judge prompt template.", _SHA, _JUDGED_DOC
    ),
    ("judge_prompt_language",): FieldDoc(
        "Language of the judge prompt.", "ISO 639-1 code", _JUDGED_DOC
    ),
    ("rubric_id",): FieldDoc("Rubric the judges scored against.", _ID, _JUDGED_DOC),
    ("rubric_version",): FieldDoc("Version of that rubric.", _ID, _JUDGED_DOC),
    ("rubric_kind",): FieldDoc("Kind of rubric.", _ID, _JUDGED_DOC),
    ("judges",): FieldDoc("One record per judge call.", _JSON_ARRAY, _JUDGED_DOC),
    ("single_judge",): FieldDoc(
        "Whether only one judge scored the item.", _BOOL, _JUDGED_DOC
    ),
    ("single_judge_reason",): FieldDoc(
        "Why only one judge scored the item.", _TEXT, _JUDGED_DOC
    ),
    ("agreement",): FieldDoc(
        "Inter-judge agreement figure.", "as agreement_statistic states", _JUDGED_DOC
    ),
    ("agreement_statistic",): FieldDoc(
        "Statistic agreement is expressed in.", _ID, _JUDGED_DOC
    ),
    ("contested",): FieldDoc(
        "Whether the judges disagreed past the threshold.", _BOOL, _JUDGED_DOC
    ),
    ("contested_reason",): FieldDoc("Why the item is contested.", _TEXT, _JUDGED_DOC),
    ("contested_threshold",): FieldDoc(
        "Disagreement threshold applied.", "score points", _JUDGED_DOC
    ),
    ("judged_headline_score",): FieldDoc(
        "Headline judged score, contested items excluded.",
        "score",
        "Not a judged row, no judge left a numeric score on an included item, "
        + _PARTIAL_SCORE_DOC,
    ),
    ("judged_headline_excluded_n",): FieldDoc(
        "Items excluded from the headline as contested.",
        _COUNT,
        f"Not a judged row, {_PARTIAL_SCORE_DOC}",
    ),
    ("judge_egress",): FieldDoc(
        "What left the machine for judging, and how many calls it took.",
        _JSON_OBJECT,
        _JUDGED_DOC,
    ),
    ("judge_cost",): FieldDoc(
        "Judge calls' own tokens and cost, per provider.", _JSON_OBJECT, _JUDGED_DOC
    ),
}

_RUNTIME_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("max_tokens",): FieldDoc("Output token cap per repetition.", "tokens"),
    ("seed_pinned",): FieldDoc("Whether the sampler seed was pinned.", _BOOL),
    ("warmup_count",): FieldDoc("Uncounted warm-up generations run first.", _COUNT),
    ("restart_between_repetitions",): FieldDoc(
        "Whether the server was restarted between repetitions.", _BOOL
    ),
    ("cooldown_s",): FieldDoc("Pause between counted repetitions.", "seconds"),
    ("slot_reset_method",): FieldDoc(
        "How server-side prompt caching was defeated between repetitions.", _ID
    ),
    ("thermal_posture",): FieldDoc("How heat between repetitions was handled.", _ID),
    ("wall_clock_s",): FieldDoc(
        "Wall clock over the counted repetitions; aggregation_wall_clock_s "
        "states how it was aggregated.",
        "seconds",
    ),
    ("ttft_ms",): FieldDoc(
        "Time to first token; aggregation_ttft_ms states the statistic.",
        "milliseconds",
    ),
    ("ttft_ms_mean",): FieldDoc(
        "Mean time to first token over the counted repetitions.", "milliseconds"
    ),
    ("ttft_ms_sd",): FieldDoc(
        "Sample standard deviation of time to first token.", "milliseconds"
    ),
    ("ttft_ms_spread",): FieldDoc(
        "Spread of time to first token; aggregation_ttft_ms_spread states how.",
        "ratio",
    ),
    ("prompt_tok_per_s",): FieldDoc(
        "Prompt (prefill) throughput; aggregation_prompt_tok_per_s states the "
        "statistic.",
        "tokens per second",
    ),
    ("prompt_tok_per_s_mean",): FieldDoc(
        "Mean prompt throughput over the counted repetitions.", "tokens per second"
    ),
    ("prompt_tok_per_s_sd",): FieldDoc(
        "Sample standard deviation of prompt throughput.", "tokens per second"
    ),
    ("prompt_tok_per_s_spread",): FieldDoc(
        "Spread of prompt throughput; aggregation_prompt_tok_per_s_spread states how.",
        "ratio",
    ),
    ("gen_tok_per_s",): FieldDoc(
        "Generation throughput; aggregation_gen_tok_per_s states the statistic.",
        "tokens per second",
    ),
    ("gen_tok_per_s_mean",): FieldDoc(
        "Mean generation throughput over the counted repetitions.",
        "tokens per second",
    ),
    ("gen_tok_per_s_sd",): FieldDoc(
        "Sample standard deviation of generation throughput.", "tokens per second"
    ),
    ("gen_tok_per_s_spread",): FieldDoc(
        "Spread of generation throughput; aggregation_gen_tok_per_s_spread states how.",
        "ratio",
    ),
    ("repetitions_n",): FieldDoc("Counted repetitions the aggregates cover.", _COUNT),
    ("unreliable",): FieldDoc(
        "Whether a spread crossed the reliability threshold.", _BOOL
    ),
    ("ttft_source",): FieldDoc("Where time to first token was read from.", _ID),
    ("vram_used_mib",): FieldDoc(
        "GPU memory used; aggregation_vram_used_mib states the statistic. "
        "'not_applicable' on a cpu_only row (schema 25+): the run used no VRAM.",
        "MiB (2^20 bytes)",
    ),
    ("process_rss_bytes",): FieldDoc(
        "Server process resident memory; aggregation_process_rss_bytes states "
        "the statistic.",
        "bytes",
    ),
    ("gpu_draw_w",): FieldDoc(
        "GPU power draw; aggregation_gpu_draw_w states the statistic.", "watts"
    ),
    ("aggregation", "*"): FieldDoc(
        "How the row field named by the column suffix was aggregated over the "
        "counted repetitions, as the row states it.",
        _ID,
    ),
    ("aggregation",): FieldDoc("Aggregation labels block.", _JSON_OBJECT),
}

ROW_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    **_COMMON_FIELDS,
    **_ENERGY_COST_FIELDS,
    **_QUALITY_FIELDS,
    **_GRADED_FIELDS,
    **_JUDGED_FIELDS,
    **_RUNTIME_FIELDS,
}

FICHE_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("cpu",): FieldDoc("CPU as the OS reports it.", _TEXT),
    ("cuda_ceiling",): FieldDoc("Highest CUDA version the driver supports.", _TEXT),
    ("flags",): FieldDoc("llama-server command line, as launched.", _JSON_ARRAY),
    ("gpu_driver_version",): FieldDoc("GPU driver version.", _TEXT),
    ("gpu_name",): FieldDoc("GPU model.", _TEXT),
    ("llama_cpp_build",): FieldDoc(
        "llama.cpp build that served the model, on a fiche hashed under "
        "projection 1 (cited by rows below schema 22).",
        _ID,
        "The fiche is hashed under projection 2, which carries engine_build "
        "instead (the column name is then listed in fields_not_carried).",
    ),
    ("engine_id",): FieldDoc(
        "Engine that served the model, on a fiche hashed under projection 2.",
        _ID,
        "The fiche predates the engine fields (projection 1).",
    ),
    ("engine_build",): FieldDoc(
        "Engine build the binary reported at launch, on a fiche hashed under "
        "projection 2.",
        _ID,
        "The build could not be read, or the fiche predates the engine fields.",
    ),
    ("engine_config_hash",): FieldDoc(
        "Hash of the engine's launch configuration with the model path replaced "
        "by the roster entry and the host and port removed.",
        _SHA,
        "The fiche predates the engine fields (projection 1).",
    ),
    ("machine_id",): FieldDoc(
        "Declared machine the run was executed on, on a fiche hashed under "
        "projection 3.",
        _ID,
        "The fiche predates the machine fields (projection 1 or 2).",
    ),
    ("compute_mode",): FieldDoc(
        "Compute mode (gpu or cpu_only), on a fiche hashed under projection 3.",
        _ID,
        "The fiche predates the machine fields (projection 1 or 2).",
    ),
    ("profile_id",): FieldDoc(
        "Run profile the launch resolved, as evidence outside the hashed "
        "projection: the first profile stored under this hash.",
        _ID,
        "The fiche predates the run profile field (rows below schema 26).",
    ),
    ("model_sha256",): FieldDoc("Checksum of the model file served.", _SHA),
    ("os",): FieldDoc("Operating system.", _TEXT),
    ("quant",): FieldDoc("Quantization of the model file served.", _ID),
    ("ram_gb",): FieldDoc("Installed RAM.", "GB"),
    ("roster_entry_id",): FieldDoc("Roster entry the fiche was recorded for.", _ID),
}

ROSTER_ENTRY_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("repo",): FieldDoc("Hugging Face repository the model file comes from.", _ID),
    ("revision",): FieldDoc("Repository revision pinned.", _ID),
    ("file",): FieldDoc("Model file within the repository.", "path"),
    ("display_id",): FieldDoc("Model name as a human names it.", _TEXT),
    ("quant",): FieldDoc("Quantization of the model file.", _ID),
    ("sha256",): FieldDoc("Checksum of the model file.", _SHA),
    ("size_class",): FieldDoc(
        "Size class the composition rule counts the entry in, banded on total "
        "parameters (below 1B ~0.5B, below 3B ~2B, below 6B ~4B, else "
        "~8B-and-up).",
        _ID,
        "The roster entry declares no size class (the column name is then "
        "listed in fields_not_carried); the composition check names it.",
    ),
    ("bytes_on_disk",): FieldDoc(
        "Size of the model file on disk: the footprint published beside the "
        "class, never banded.",
        "bytes",
        "The roster entry declares no size on disk (the column name is then "
        "listed in fields_not_carried); the composition check names it.",
    ),
    ("family",): FieldDoc(
        "Model family, when the roster entry declares one.",
        _ID,
        "The roster entry declares no family (the column name is then listed "
        "in fields_not_carried).",
    ),
    ("thinking_control",): FieldDoc(
        "Request arguments that disable reasoning under the entry's own chat "
        "template, or none for a model that does not reason.",
        f"{_JSON_OBJECT}, or the identifier none",
        "The roster entry declares no thinking control (the column name is then "
        "listed in fields_not_carried); it cannot run under a disabled policy.",
    ),
    ("licence", "id"): FieldDoc(
        "Licence the model's weights ship under, as the repository states it.",
        "SPDX licence identifier",
    ),
    ("licence", "client_commercial_use"): FieldDoc(
        "Whether the licence permits commercial use on a client's own machine.",
        _BOOL,
    ),
    ("licence", "read_on"): FieldDoc(
        "Date the licence terms were read; terms move, so the reading is dated.",
        "ISO 8601 date",
    ),
    ("licence", "source_url"): FieldDoc(
        "Licence file or model card the terms were read from, at the entry's revision.",
        "URL",
    ),
    ("language_claim", "languages"): FieldDoc(
        "Which of en, fr and de the vendor's model card names as supported. A "
        "claim, not a measurement: the suites test it, and a row contradicting "
        "it does not change it.",
        f"{_JSON_ARRAY} of language codes; [] when the card names none of the three",
    ),
    ("language_claim", "source_url"): FieldDoc(
        "Model card the language claim was read from, at the entry's revision.",
        "URL",
    ),
    ("language_claim", "read_on"): FieldDoc(
        "Date the language claim was read.", "ISO 8601 date"
    ),
    ("language_claim", "statement"): FieldDoc(
        "The model card's own wording on language support, verbatim.",
        _TEXT,
        "The model card says nothing on language support (the column name is "
        "then listed in fields_not_carried).",
    ),
    ("architecture", "kind"): FieldDoc("Architecture: moe or dense.", _ID),
    ("architecture", "expert_count"): FieldDoc(
        "Experts per MoE layer (0 for dense).", _COUNT
    ),
    ("architecture", "active_params_b"): FieldDoc(
        "Parameters active per token.", "billions of parameters"
    ),
    ("architecture", "total_params"): FieldDoc(
        "Every parameter the model file holds, summed over its tensors as the "
        "GGUF header states them; the figure the size class is banded on.",
        "parameters",
        "The roster entry declares no total (the column name is then listed in "
        "fields_not_carried); the composition check names it.",
    ),
    ("server_flags", "n_gpu_layers"): FieldDoc("Layers offloaded to GPU.", _COUNT),
    ("server_flags", "context_size"): FieldDoc("Context window launched.", "tokens"),
    ("server_flags", "flash_attention"): FieldDoc("Flash attention setting.", _ID),
    ("server_flags", "jinja"): FieldDoc("Whether --jinja templating is on.", _BOOL),
    ("server_flags", "parallel_slots"): FieldDoc("Server request slots.", _COUNT),
    ("server_flags", "load_mode"): FieldDoc("Model load mode.", _ID),
    ("server_flags", "sampler", "temperature"): FieldDoc(
        "Server default sampling temperature.", "number"
    ),
    ("server_flags", "sampler", "top_p"): FieldDoc(
        "Server default nucleus threshold.", _RATIO
    ),
    ("server_flags", "sampler", "top_k"): FieldDoc(
        "Server default top-k cut-off.", _COUNT
    ),
    ("server_flags", "sampler", "min_p"): FieldDoc(
        "Server default min-p threshold.", _RATIO
    ),
    ("server_flags", "sampler", "presence_penalty"): FieldDoc(
        "Server default presence penalty.", "number"
    ),
}

SUITE_DEFINITION_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("context_length",): FieldDoc("Context window the suite declares.", "tokens"),
    ("max_output_tokens",): FieldDoc("Output token cap the suite declares.", "tokens"),
    ("prompt_set_hash",): FieldDoc(
        "Content hash of the suite's item set, as the definition states it.", _SHA
    ),
    ("stop_sequences",): FieldDoc("Stop sequences the suite declares.", _JSON_ARRAY),
    ("thinking_policy",): FieldDoc(
        "Reasoning policy the suite declares.",
        _ID,
        "This suite version declares no thinking policy (the column name is "
        "then listed in fields_not_carried).",
    ),
}

# The key columns the fiche and roster tables are keyed by, and the roster
# file's own version: values the bundle carries outside any record's fields.
FICHE_KEY_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("fiche_hash",): FieldDoc(
        "Content hash the fiche is stored under (its file name); rows cite it.",
        _SHA,
    ),
}
ROSTER_KEY_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("entry_id",): FieldDoc("Roster entry id; rows cite it as roster_entry_id.", _ID),
}
ROSTER_FILE_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("version",): FieldDoc(
        "roster_version of the roster file the export resolved against.",
        "integer",
    ),
}

# The roster-entry fields a row table resolves `roster_entry_id` into: the
# model's identity. Launch flags and the validated host are the roster
# table's, one join away by design of what a row cites.
_MODEL_FIELD_KEYS: tuple[str, ...] = (
    "repo",
    "revision",
    "file",
    "display_id",
    "quant",
    "sha256",
    "family",
    "architecture",
)

_NOT_CARRIED_DOC = FieldDoc(
    "Columns of this row whose empty cell means the source does not carry the "
    "field, as opposed to recording it as null.",
    "JSON array of column names, in column order",
    "Never empty: [] when every column's source carries its field.",
)

_ROW_EPIC = "every-published-row-explains-and-reproduces-itself (the row contract)"
_STATS_EPIC = "a-score-is-published-with-its-interval-a-difference-with-its-test"


# --------------------------------------------------------------------------
# The fifth table: comparison-family, comparison and leader-set records.
#
# The records are written by `wave-local-ai-v2-compare` (owned by the
# statistics epic); this table flattens them and computes nothing. The
# meaning, unit and null reasons of their fields are defined beside the code
# that writes them (`comparison.FAMILY_RECORD_FIELDS`,
# `comparison.COMPARISON_RECORD_FIELDS`, `leader_set.LEADER_SET_RECORD_FIELDS`,
# `leader_set.SUBJECT_RECORD_FIELDS`) and read here, never redefined; each
# column names that epic and module in the dictionary's `owner` cell. What an
# empty cell means on a row of another kind is this table's to say.
# --------------------------------------------------------------------------

KIND_FAMILY = comparison.RECORD_TYPE
KIND_COMPARISON = "comparison"
KIND_LEADER_SET = leader_set.RECORD_TYPE
KIND_SUBJECT = "leader_set_subject"
FAMILY_OWNER = f"epic {_STATS_EPIC} (defined in comparison.py)"
LEADER_SET_OWNER = f"epic {_STATS_EPIC} (defined in leader_set.py)"

RECORD_KEY_FIELDS: dict[tuple[str, ...], FieldDoc] = {
    ("record_kind",): FieldDoc(
        "Which record this row is: comparison_family (a family record), "
        "comparison (one comparison a family record holds), leader_set (a "
        "leader-set record) or leader_set_subject (one subject a leader-set "
        "record lists).",
        _TEXT,
        _NEVER_EMPTY,
    ),
    ("record_file",): FieldDoc(
        "File name of the record the row is read from, in comparisons/ or "
        "leader-sets/; a comparison or subject row names the record holding it.",
        _TEXT,
        _NEVER_EMPTY,
    ),
}

# The row-kind half of an empty record cell; the record module's definition
# adds what a null means for that field (`_empty_cell`).
_FAMILY_EMPTY = (
    "A leader_set or leader_set_subject row, or a family record that does not "
    "carry the field (an earlier record_version): the column is then listed in "
    "fields_not_carried."
)
_COMPARISON_EMPTY = (
    "Not a comparison row, or a comparison that does not carry the field: the "
    "column is then listed in fields_not_carried."
)
_LEADER_EMPTY = (
    "A comparison_family or comparison row: the column is then listed in "
    "fields_not_carried."
)
_SUBJECT_EMPTY = (
    "Not a leader_set_subject row: the column is then listed in fields_not_carried."
)
_RECORD_NULL = "Otherwise the record holds null."
_PARENT_NULL = "Empty too when an object above it in the record is null."

# What the dictionary names when the bundle read holds no record of a kind.
RECORD_KINDS: dict[str, str] = {
    KIND_FAMILY: (
        "Comparison-family records (comparisons/): one closed family of paired "
        "comparisons with their multiplicity-adjusted p-values."
    ),
    KIND_COMPARISON: (
        "Comparisons a family record holds: one paired test, observation or "
        "refusal each."
    ),
    KIND_LEADER_SET: (
        "Leader-set records (leader-sets/): per suite and machine class, the "
        "local models not distinguishable from the best, with their subjects."
    ),
}


# --------------------------------------------------------------------------
# Flattening a record into columns.
# --------------------------------------------------------------------------


class _NotCarried:
    """The one marker for "this source does not carry the field"."""


NOT_CARRIED = _NotCarried()


@dataclass(frozen=True)
class Source:
    """One record that feeds a table row, and how its fields are named and read.

    `record` is the record itself, `None` when the pointer that would have
    found it is recorded as null, or `NOT_CARRIED` when the row carries no
    such pointer at all.
    """

    prefix: str
    label: str
    registry: Mapping[tuple[str, ...], FieldDoc]
    record: Mapping[str, Any] | None | _NotCarried
    empty: str
    excluded: frozenset[tuple[str, ...]] = frozenset()
    json_cells: frozenset[str] = frozenset()
    # Who defines the fields this source carries, when that is not this
    # export: written to the dictionary's `owner` cell of each column. Such a
    # field's `FieldDoc.empty` says what a null means for it, and `empty`
    # above what an empty cell means otherwise (`_empty_cell`).
    owner: str = ""


def lookup_doc(
    registry: Mapping[tuple[str, ...], FieldDoc], path: tuple[str, ...]
) -> FieldDoc | None:
    """The registry entry for `path`: an exact key first, else a `*` pattern."""
    if path in registry:
        return registry[path]
    for pattern, doc in registry.items():
        if len(pattern) == len(path) and all(
            part in ("*", key) for part, key in zip(pattern, path, strict=True)
        ):
            return doc
    return None


def _leaf_paths(
    value: Any,
    path: tuple[str, ...],
    excluded: frozenset[tuple[str, ...]],
    json_cells: frozenset[str],
) -> list[tuple[str, ...]]:
    """Every leaf path under `value`; a non-empty object is walked, not a leaf."""
    if path in excluded:
        return []
    is_json_cell = len(path) == 1 and path[0] in json_cells
    if isinstance(value, dict) and value and not is_json_cell:
        leaves: list[tuple[str, ...]] = []
        for key, item in value.items():
            leaves += _leaf_paths(item, (*path, str(key)), excluded, json_cells)
        return leaves
    return [path]


def _read_path(record: Any, path: tuple[str, ...], context: str) -> Any:
    """The value at `path`, `None` under a recorded null, or `NOT_CARRIED`."""
    current = record
    for depth, key in enumerate(path):
        if current is NOT_CARRIED or current is None:
            return current
        if not isinstance(current, dict):
            raise ExportError(
                f"{context}: `{'.'.join(path[:depth])}` is a value on this record "
                "and an object on another; one column cannot hold both"
            )
        if key not in current:
            return NOT_CARRIED
        current = current[key]
    # A non-empty object cannot sit at a column's path: its leaves would have
    # made sub-columns, and this path would not be a column.
    return current


def format_cell(value: Any, context: str) -> str:
    """One cell's text, under the pinned format. `None` is the empty cell."""
    if value is None or value is NOT_CARRIED:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ExportError(f"{context}: {value!r} has no CSV form that reads back")
        return repr(value)
    if isinstance(value, str):
        return value
    if isinstance(value, list | dict):
        try:
            return json.dumps(
                value, ensure_ascii=False, separators=(",", ":"), allow_nan=False
            )
        except ValueError as error:
            raise ExportError(f"{context}: {error}") from error
    raise ExportError(f"{context}: unsupported value type {type(value).__name__}")


@dataclass(frozen=True)
class Column:
    """One table column: its name and where its cells are read from."""

    name: str
    source_index: int
    path: tuple[str, ...]
    doc: FieldDoc
    source_label: str
    empty: str
    owner: str = ""


@dataclass(frozen=True)
class Table:
    """A table's header, its column metadata and its rows of cell text."""

    name: str
    columns: tuple[Column, ...]
    rows: tuple[tuple[str, ...], ...]

    @property
    def header(self) -> tuple[str, ...]:
        return (*(column.name for column in self.columns), NOT_CARRIED_COLUMN)


def build_table(name: str, row_sources: Sequence[Sequence[Source]]) -> Table:
    """Flatten every row's sources into one table with a fixed column set.

    Columns are the leaf paths the sources carry, in order of first
    appearance; a path that is a leaf on one record and an object on another
    keeps the object's sub-columns (the leaf is then a recorded null, or the
    export refuses). Every column must have a registry entry.
    """
    order: dict[tuple[int, tuple[str, ...]], None] = {}
    for sources in row_sources:
        for index, source in enumerate(sources):
            if isinstance(source.record, dict):
                for path in _leaf_paths(
                    source.record, (), source.excluded, source.json_cells
                ):
                    order.setdefault((index, path), None)
    # Grouped by source (the row's own fields first, then each record it
    # cites), first appearance within a source; `sorted` is stable.
    keys = sorted(
        (
            (index, path)
            for index, path in order
            if not any(
                other_index == index
                and len(other) > len(path)
                and other[: len(path)] == path
                for other_index, other in order
            )
        ),
        key=lambda key: key[0],
    )

    columns: list[Column] = []
    seen: dict[str, str] = {}
    template = row_sources[0] if row_sources else ()
    for index, path in keys:
        source = template[index]
        column_name = source.prefix + "_".join(path)
        dotted = ".".join(path)
        doc = lookup_doc(source.registry, path)
        if doc is None:
            raise ExportError(
                f"{name}: {source.label} field `{dotted}` has no dictionary entry; "
                "describe it in bundle_export before exporting it"
            )
        if column_name in seen or column_name == NOT_CARRIED_COLUMN:
            raise ExportError(
                f"{name}: column `{column_name}` would hold both "
                f"{seen.get(column_name, NOT_CARRIED_COLUMN)} and "
                f"{source.label} `{dotted}`"
            )
        seen[column_name] = f"{source.label} `{dotted}`"
        columns.append(
            Column(
                column_name,
                index,
                path,
                doc,
                source.label,
                source.empty,
                source.owner,
            )
        )

    rows: list[tuple[str, ...]] = []
    for number, sources in enumerate(row_sources, start=1):
        cells: list[str] = []
        not_carried: list[str] = []
        for column in columns:
            context = f"{name} row {number}, column `{column.name}`"
            value = _read_path(
                sources[column.source_index].record, column.path, context
            )
            if value is NOT_CARRIED:
                not_carried.append(column.name)
            cells.append(format_cell(value, context))
        cells.append(format_cell(not_carried, f"{name} row {number}"))
        rows.append(tuple(cells))
    return Table(name, tuple(columns), tuple(rows))


# --------------------------------------------------------------------------
# Reading the bundle.
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class BundlePaths:
    """Where the bundle parts are read from."""

    runtime_rows: Path
    quality_rows: Path
    fiche_dir: Path
    roster: Path
    suite_definitions: Path
    comparisons_dir: Path
    leader_sets_dir: Path


def default_bundle_paths() -> BundlePaths:
    """The committed bundle: the reference files, never the live stores."""
    return BundlePaths(
        runtime_rows=Path(settings.DEFAULT_RUNTIME_REFERENCE_PATH),
        quality_rows=Path(settings.DEFAULT_QUALITY_REFERENCE_PATH),
        fiche_dir=Path(settings.DEFAULT_FICHE_REGISTRY_DIR),
        roster=Path(settings.DEFAULT_ROSTER_PATH),
        suite_definitions=Path(settings.DEFAULT_SUITE_DEFINITIONS_DIR),
        comparisons_dir=Path(settings.DEFAULT_COMPARISONS_DIR),
        leader_sets_dir=Path(settings.DEFAULT_LEADER_SETS_DIR),
    )


@dataclass(frozen=True)
class Bundle:
    """The bundle as read: rows, every stored fiche, the roster, cited suites,
    and the analysis records, each keyed by its file name."""

    runtime_rows: list[dict[str, Any]]
    quality_rows: list[dict[str, Any]]
    fiches: dict[str, dict[str, Any]]
    roster_version: int
    roster_entries: dict[str, dict[str, Any]]
    suite_definitions: dict[tuple[str, str], dict[str, Any]]
    family_records: dict[str, dict[str, Any]]
    leader_set_records: dict[str, dict[str, Any]]


def _read_row_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise ExportError(f"no row file at {path.as_posix()}")
    try:
        return results.read_rows(path)
    except json.JSONDecodeError as error:
        raise ExportError(
            f"{path.as_posix()}: not one JSON row per line: {error}"
        ) from error


def _read_fiches(fiche_dir: Path) -> dict[str, dict[str, Any]]:
    if not fiche_dir.is_dir():
        raise ExportError(f"no fiche directory at {fiche_dir.as_posix()}")
    fiches: dict[str, dict[str, Any]] = {}
    for path in sorted(fiche_dir.glob("*.json")):
        try:
            fiche = read_fiche(path.stem, fiche_dir)
        except json.JSONDecodeError as error:
            raise ExportError(f"fiche {path.name} is not JSON: {error}") from error
        if not isinstance(fiche, dict):
            raise ExportError(f"fiche {path.name} is not a JSON object")
        fiches[path.stem] = fiche
    return fiches


def _read_roster(path: Path) -> tuple[int, dict[str, dict[str, Any]]]:
    try:
        parsed = roster.load_roster(path)
    except roster.RosterError as error:
        raise ExportError(f"roster {path.as_posix()}: {error}") from error
    # Validated by `load_roster`, flattened from the raw file so a field an
    # entry does not declare stays absent rather than becoming a default.
    raw = json.loads(path.read_text(encoding="utf-8"))
    return parsed.roster_version, dict(raw["entries"])


def _read_suite_definitions(
    quality_rows: Iterable[Mapping[str, Any]], directory: Path
) -> dict[tuple[str, str], dict[str, Any]]:
    definitions: dict[tuple[str, str], dict[str, Any]] = {}
    for row in quality_rows:
        suite_id, suite_version = row.get("suite_id"), row.get("suite_version")
        if suite_id is None or suite_version is None:
            continue
        pair = (str(suite_id), str(suite_version))
        if pair in definitions:
            continue
        path = directory / snapshot_filename(*pair)
        try:
            definition = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ExportError(
                f"run {row.get('run_id')!r} cites suite {pair[0]}@{pair[1]}, "
                f"which does not resolve in {directory.as_posix()}: {error}"
            ) from error
        if not isinstance(definition, dict):
            raise ExportError(f"suite definition {path.name} is not a JSON object")
        definitions[pair] = definition
    return definitions


def _read_records(directory: Path, record_type: str) -> dict[str, dict[str, Any]]:
    """Every `*.json` record in `directory`, keyed by file name, in name order.

    A missing directory holds no record of the kind: a bundle may predate it,
    and the dictionary then names the kind as not carried. A path that exists
    but is not a directory, or a file that is not a JSON object of
    `record_type`, refuses: nothing in a record directory is skipped silently.
    """
    if not directory.exists():
        return {}
    if not directory.is_dir():
        raise ExportError(f"{directory.as_posix()} is not a record directory")
    records: dict[str, dict[str, Any]] = {}
    for path in sorted(directory.glob("*.json")):
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as error:
            raise ExportError(f"record {path.name} is not JSON: {error}") from error
        if not isinstance(record, dict) or record.get("record_type") != record_type:
            raise ExportError(
                f"{directory.as_posix()}/{path.name} is not a {record_type} record"
            )
        records[path.name] = record
    return records


def _entries(name: str, record: Mapping[str, Any], key: str) -> list[dict[str, Any]]:
    """`record[key]` as a list of objects (none when absent), or a refusal."""
    entries = record.get(key, [])
    if not isinstance(entries, list) or not all(
        isinstance(entry, dict) for entry in entries
    ):
        raise ExportError(f"record {name}: `{key}` is not a list of objects")
    return entries


def _record_id(name: str, record: Mapping[str, Any], key: str) -> str:
    """The record's own id, or a refusal: every record is cited by it."""
    value = record.get(key)
    if not isinstance(value, str):
        raise ExportError(f"record {name}: `{key}` is not an id")
    return value


def _check_record_pointers(
    families: Mapping[str, Mapping[str, Any]],
    leader_sets: Mapping[str, Mapping[str, Any]],
    quality_rows: Iterable[Mapping[str, Any]],
) -> None:
    """Refuse a record citing a run or a record the bundle read does not hold.

    Checked, not joined: the table carries the ids as the records write them.
    """
    run_ids = {row.get("run_id") for row in quality_rows}
    family_ids = {_record_id(n, r, "family_id") for n, r in families.items()}
    leader_set_ids = {_record_id(n, r, "leader_set_id") for n, r in leader_sets.items()}
    cited: list[tuple[str, str, Any, set[Any]]] = []
    for name, record in families.items():
        for member in _entries(name, record, "members"):
            for side in ("reference_run_id", "candidate_run_id"):
                cited.append((name, side, member.get(side), run_ids))
        for entry in _entries(name, record, "supersedes"):
            cited.append((name, "supersedes", entry.get("family_id"), family_ids))
    for name, record in leader_sets.items():
        for subject in _entries(name, record, "subjects"):
            cited.append((name, "subject run_id", subject.get("run_id"), run_ids))
        if record.get("family_id") is not None:
            cited.append((name, "family_id", record["family_id"], family_ids))
        for entry in _entries(name, record, "supersedes"):
            cited.append(
                (name, "supersedes", entry.get("leader_set_id"), leader_set_ids)
            )
    for name, pointer, value, held in cited:
        if not isinstance(value, str) or value not in held:
            raise ExportError(
                f"record {name}: {pointer} {value!r} does not resolve in the bundle read"
            )


def read_bundle(paths: BundlePaths) -> Bundle:
    """Read every part, refusing anything that would leave a hole."""
    quality_rows = _read_row_file(paths.quality_rows)
    roster_version, roster_entries = _read_roster(paths.roster)
    family_records = _read_records(paths.comparisons_dir, KIND_FAMILY)
    leader_set_records = _read_records(paths.leader_sets_dir, KIND_LEADER_SET)
    _check_record_pointers(family_records, leader_set_records, quality_rows)
    return Bundle(
        runtime_rows=_read_row_file(paths.runtime_rows),
        quality_rows=quality_rows,
        fiches=_read_fiches(paths.fiche_dir),
        roster_version=roster_version,
        roster_entries=roster_entries,
        suite_definitions=_read_suite_definitions(
            quality_rows, paths.suite_definitions
        ),
        family_records=family_records,
        leader_set_records=leader_set_records,
    )


# --------------------------------------------------------------------------
# The tables.
# --------------------------------------------------------------------------


def _row_context(kind: str, row: Mapping[str, Any]) -> str:
    return f"{kind} row of run {row.get('run_id')!r}, item {row.get('item_id')!r}"


def _resolve(
    row: Mapping[str, Any],
    pointer: str,
    found: Mapping[str, Any] | None,
    context: str,
) -> Mapping[str, Any] | None | _NotCarried:
    """The record `row[pointer]` cites; refuses a pointer that resolves to nothing."""
    if pointer not in row:
        return NOT_CARRIED
    if row[pointer] is None:
        return None
    if found is None:
        raise ExportError(f"{context}: {pointer} {row[pointer]!r} does not resolve")
    return found


def _model_fields(entry: Mapping[str, Any]) -> dict[str, Any]:
    return {key: entry[key] for key in _MODEL_FIELD_KEYS if key in entry}


def _row_sources(kind: str, row: dict[str, Any], bundle: Bundle) -> list[Source]:
    context = _row_context(kind, row)
    fiche = _resolve(
        row, "fiche_hash", bundle.fiches.get(str(row.get("fiche_hash"))), context
    )
    entry = bundle.roster_entries.get(str(row.get("roster_entry_id")))
    model = _resolve(
        row,
        "roster_entry_id",
        None if entry is None else _model_fields(entry),
        context,
    )
    sources = [
        Source(
            "",
            f"{kind} row",
            ROW_FIELDS,
            row,
            _ROW_EMPTY,
            _EXCLUDED_ROW_PATHS,
            _JSON_CELL_ROW_FIELDS,
        ),
        Source("fiche_", "fiche via fiche_hash", FICHE_FIELDS, fiche, _RESOLVED_EMPTY),
        Source(
            "roster_entry_",
            "roster entry via roster_entry_id",
            ROSTER_ENTRY_FIELDS,
            model,
            _RESOLVED_EMPTY,
        ),
        Source(
            "roster_file_",
            "roster file",
            ROSTER_FILE_FIELDS,
            {"version": bundle.roster_version},
            _NEVER_EMPTY,
        ),
    ]
    if kind == "quality":
        sources.append(_suite_source(row, bundle))
    return sources


def _suite_source(row: dict[str, Any], bundle: Bundle) -> Source:
    if "suite_id" not in row or "suite_version" not in row:
        record: Mapping[str, Any] | None | _NotCarried = NOT_CARRIED
    elif row["suite_id"] is None or row["suite_version"] is None:
        record = None
    else:
        pair = (str(row["suite_id"]), str(row["suite_version"]))
        definition = bundle.suite_definitions[pair]
        record = {
            key: value
            for key, value in definition.items()
            if key not in ("items", "suite_id", "suite_version")
        }
    return Source(
        "suite_definition_",
        "suite definition via suite_id/suite_version",
        SUITE_DEFINITION_FIELDS,
        record,
        _RESOLVED_EMPTY,
    )


def _without(record: Mapping[str, Any], key: str) -> dict[str, Any]:
    return {field: value for field, value in record.items() if field != key}


def _record_row(
    kind: str,
    file_name: str,
    family: Mapping[str, Any] | _NotCarried = NOT_CARRIED,
    member: Mapping[str, Any] | _NotCarried = NOT_CARRIED,
    leader: Mapping[str, Any] | _NotCarried = NOT_CARRIED,
    subject: Mapping[str, Any] | _NotCarried = NOT_CARRIED,
) -> list[Source]:
    """One row's five sources, a source that is not the row's kind not carried."""
    return [
        Source(
            "",
            "export",
            RECORD_KEY_FIELDS,
            {"record_kind": kind, "record_file": file_name},
            _NEVER_EMPTY,
        ),
        Source(
            "family_",
            "comparison-family record",
            comparison.FAMILY_RECORD_FIELDS,
            family,
            _FAMILY_EMPTY,
            owner=FAMILY_OWNER,
        ),
        Source(
            "comparison_",
            "comparison (a member of the family record)",
            comparison.COMPARISON_RECORD_FIELDS,
            member,
            _COMPARISON_EMPTY,
            owner=FAMILY_OWNER,
        ),
        Source(
            "leader_set_",
            "leader-set record",
            leader_set.LEADER_SET_RECORD_FIELDS,
            leader,
            _LEADER_EMPTY,
            owner=LEADER_SET_OWNER,
        ),
        Source(
            "subject_",
            "leader-set subject",
            leader_set.SUBJECT_RECORD_FIELDS,
            subject,
            _SUBJECT_EMPTY,
            owner=LEADER_SET_OWNER,
        ),
    ]


def _record_rows(bundle: Bundle) -> list[list[Source]]:
    """Each family record then its comparisons, each leader set then its subjects,
    records in file-name order, members and subjects in the order written."""
    rows: list[list[Source]] = []
    for name, record in bundle.family_records.items():
        family = _without(record, "members")
        rows.append(_record_row(KIND_FAMILY, name, family=family))
        for member in record.get("members", []):
            rows.append(_record_row(KIND_COMPARISON, name, family, member=member))
    for name, record in bundle.leader_set_records.items():
        leader = _without(record, "subjects")
        rows.append(_record_row(KIND_LEADER_SET, name, leader=leader))
        for subject in record.get("subjects", []):
            rows.append(_record_row(KIND_SUBJECT, name, leader=leader, subject=subject))
    return rows


def build_tables(bundle: Bundle) -> dict[str, Table]:
    """The five tables, keyed by table name, in `TABLES` order."""
    quality = build_table(
        QUALITY_TABLE,
        [_row_sources("quality", row, bundle) for row in bundle.quality_rows],
    )
    runtime = build_table(
        RUNTIME_TABLE,
        [_row_sources("runtime", row, bundle) for row in bundle.runtime_rows],
    )
    fiches = build_table(
        FICHE_TABLE,
        [
            [
                Source(
                    "",
                    "fiche file",
                    FICHE_KEY_FIELDS,
                    {"fiche_hash": key},
                    _NEVER_EMPTY,
                ),
                Source("", "fiche", FICHE_FIELDS, fiche, _RESOLVED_EMPTY),
            ]
            for key, fiche in bundle.fiches.items()
        ],
    )
    roster_table = build_table(
        ROSTER_TABLE,
        [
            [
                Source(
                    "roster_file_",
                    "roster file",
                    ROSTER_FILE_FIELDS,
                    {"version": bundle.roster_version},
                    _NEVER_EMPTY,
                ),
                Source(
                    "",
                    "roster entry key",
                    ROSTER_KEY_FIELDS,
                    {"entry_id": key},
                    _NEVER_EMPTY,
                ),
                Source(
                    "",
                    "roster entry",
                    ROSTER_ENTRY_FIELDS,
                    entry,
                    _RESOLVED_EMPTY,
                    # One cell, not one column per control spelling: the
                    # object's keys differ by family.
                    json_cells=frozenset({"thinking_control"}),
                ),
            ]
            for key, entry in bundle.roster_entries.items()
        ],
    )
    return {
        QUALITY_TABLE: quality,
        RUNTIME_TABLE: runtime,
        FICHE_TABLE: fiches,
        ROSTER_TABLE: roster_table,
        COMPARISON_TABLE: build_table(COMPARISON_TABLE, _record_rows(bundle)),
    }


# --------------------------------------------------------------------------
# The dictionary and the manifest.
# --------------------------------------------------------------------------

DICTIONARY_HEADER: tuple[str, ...] = (
    "table",
    "column",
    "carried",
    "source",
    "meaning",
    "unit",
    "empty_cell",
    "owner",
)
MANIFEST_HEADER: tuple[str, ...] = (
    "part",
    "path",
    "entries_read",
    "version_field",
    "versions_read",
)

_EXCLUDED_TOP_LEVEL: frozenset[str] = frozenset(
    path[0] for path in _EXCLUDED_ROW_PATHS if len(path) == 1
)


def contract_fields(kind: row_contract.RowKind) -> frozenset[str]:
    """Every top-level field the row contract defines for `kind`."""
    fields = row_contract.REQUIRED_FIELDS[kind]
    if kind == "quality":
        fields = (
            fields
            | row_contract.GRADED_FIELDS
            | row_contract.JUDGED_FIELDS
            | {"subject_output"}
        )
    return fields


# A contract field another epic defines, named with that owner when no row
# read carries it.
_CONTRACT_FIELD_OWNERS: dict[str, str] = {
    field: f"epic {_STATS_EPIC}" for field in row_contract.SCORE_INTERVAL_FIELDS
}


def _not_carried_by_contract(
    kind: row_contract.RowKind, table: Table
) -> list[tuple[str, ...]]:
    carried = {column.path[0] for column in table.columns if column.source_index == 0}
    entries: list[tuple[str, ...]] = []
    for field in sorted(contract_fields(kind) - carried - _EXCLUDED_TOP_LEVEL):
        doc = lookup_doc(ROW_FIELDS, (field,))
        if doc is None:
            raise ExportError(f"row contract field `{field}` has no dictionary entry")
        entries.append(
            (
                table.name,
                field,
                "false",
                f"{kind} row `{field}`",
                doc.meaning,
                doc.unit,
                "Not a column: no row of the bundle read carries this field.",
                _CONTRACT_FIELD_OWNERS.get(field, _ROW_EPIC),
            )
        )
    return entries


def _record_kinds_not_carried(table: Table) -> list[tuple[str, ...]]:
    """The record kinds no row of the fifth table holds, each named with its owner."""
    position = table.header.index("record_kind") if table.rows else 0
    held = {row[position] for row in table.rows}
    return [
        (
            COMPARISON_TABLE,
            f"{kind} records",
            "false",
            "not in the bundle read",
            meaning,
            "",
            "Not a row: the bundle read holds no record of this kind.",
            f"epic {_STATS_EPIC}",
        )
        for kind, meaning in RECORD_KINDS.items()
        if kind not in held
    ]


def _empty_cell(column: Column) -> str:
    """What an empty cell of `column` means.

    A field this module describes states it whole. A field a record module
    defines (a column with an owner) states what a null means for it; the
    table adds the row-kind case before it, and the null object above it.
    """
    if not column.owner:
        return column.doc.empty or column.empty
    parts = [column.empty, column.doc.empty or _RECORD_NULL]
    if len(column.path) > 1:
        parts.append(_PARENT_NULL)
    return " ".join(parts)


def build_dictionary(tables: Mapping[str, Table]) -> list[tuple[str, ...]]:
    """Every column of every table, then everything the bundle does not carry."""
    entries: list[tuple[str, ...]] = []
    for name in TABLES:
        for column in tables[name].columns:
            entries.append(
                (
                    name,
                    column.name,
                    "true",
                    f"{column.source_label} `{'.'.join(column.path)}`",
                    column.doc.meaning,
                    column.doc.unit,
                    _empty_cell(column),
                    column.owner,
                )
            )
        entries.append(
            (
                name,
                NOT_CARRIED_COLUMN,
                "true",
                "export (which columns of the row are not carried by their source)",
                _NOT_CARRIED_DOC.meaning,
                _NOT_CARRIED_DOC.unit,
                _NOT_CARRIED_DOC.empty or "",
                "",
            )
        )
    for path in sorted(_EXCLUDED_ROW_PATHS):
        entries.append(
            (
                RUNTIME_TABLE,
                "_".join(path),
                "false",
                f"runtime row `{'.'.join(path)}`",
                EXCLUDED_NOTE,
                _JSON_ARRAY,
                "Not a column: per-repetition values stay in the bundle.",
                "the bundle (runtime-reference.jsonl)",
            )
        )
    entries += _not_carried_by_contract("quality", tables[QUALITY_TABLE])
    entries += _not_carried_by_contract("runtime", tables[RUNTIME_TABLE])
    entries += _record_kinds_not_carried(tables[COMPARISON_TABLE])
    return entries


def _version_sort_key(value: str) -> tuple[int, int, str]:
    return (0, int(value), "") if value.isdigit() else (1, 0, value)


def declared_versions(rows: Iterable[Mapping[str, Any]]) -> str:
    """The distinct `schema_version` values `rows` carry, as read.

    Read from the bytes, never from `row_contract.SCHEMA_VERSION`: a bundle
    regenerated under a later schema declares that one with no code change.
    A row with no `schema_version` key is declared as `not_carried`.
    """
    values = {
        str(row["schema_version"]) if "schema_version" in row else "not_carried"
        for row in rows
    }
    return ";".join(sorted(values, key=_version_sort_key))


def build_manifest(paths: BundlePaths, bundle: Bundle) -> list[tuple[str, ...]]:
    """What was read, part by part, and the versions each part declares."""
    return [
        (
            "runtime_rows",
            paths.runtime_rows.as_posix(),
            str(len(bundle.runtime_rows)),
            "schema_version",
            declared_versions(bundle.runtime_rows),
        ),
        (
            "quality_rows",
            paths.quality_rows.as_posix(),
            str(len(bundle.quality_rows)),
            "schema_version",
            declared_versions(bundle.quality_rows),
        ),
        ("fiches", paths.fiche_dir.as_posix(), str(len(bundle.fiches)), "", ""),
        (
            "roster",
            paths.roster.as_posix(),
            str(len(bundle.roster_entries)),
            "roster_version",
            str(bundle.roster_version),
        ),
        (
            "suite_definitions",
            paths.suite_definitions.as_posix(),
            str(len(bundle.suite_definitions)),
            "suite_id@suite_version",
            ";".join(f"{a}@{b}" for a, b in sorted(bundle.suite_definitions)),
        ),
        (
            "comparison_families",
            paths.comparisons_dir.as_posix(),
            str(len(bundle.family_records)),
            "record_version",
            _record_versions(bundle.family_records.values()),
        ),
        (
            "leader_sets",
            paths.leader_sets_dir.as_posix(),
            str(len(bundle.leader_set_records)),
            "record_version",
            _record_versions(bundle.leader_set_records.values()),
        ),
    ]


def _record_versions(records: Iterable[Mapping[str, Any]]) -> str:
    values = {str(record.get("record_version")) for record in records}
    return ";".join(sorted(values, key=_version_sort_key))


# --------------------------------------------------------------------------
# Writing and the command.
# --------------------------------------------------------------------------


def build_export(paths: BundlePaths) -> dict[str, list[tuple[str, ...]]]:
    """Every output file's rows, header first, keyed by file name.

    Reads and checks everything before anything is written, so a refusal
    leaves no half-written export behind.
    """
    bundle = read_bundle(paths)
    tables = build_tables(bundle)
    files: dict[str, list[tuple[str, ...]]] = {
        f"{name}.csv": [tables[name].header, *tables[name].rows] for name in TABLES
    }
    files[DICTIONARY_FILE] = [DICTIONARY_HEADER, *build_dictionary(tables)]
    files[MANIFEST_FILE] = [MANIFEST_HEADER, *build_manifest(paths, bundle)]
    return files


def write_csv(path: Path, rows: Iterable[Sequence[str]]) -> None:
    """Write `rows` under the pinned format (`CSV_FORMAT`)."""
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(
            handle,
            delimiter=",",
            quotechar='"',
            doublequote=True,
            quoting=csv.QUOTE_MINIMAL,
            lineterminator="\r\n",
            strict=True,
        )
        writer.writerows(rows)


def _refuse_bundle_directory(output_dir: Path, paths: BundlePaths) -> None:
    bundle_dirs = {
        paths.runtime_rows.parent,
        paths.quality_rows.parent,
        paths.fiche_dir,
        paths.roster.parent,
        paths.suite_definitions,
        paths.comparisons_dir,
        paths.leader_sets_dir,
    }
    target = output_dir.resolve()
    if any(target == directory.resolve() for directory in bundle_dirs):
        raise ExportError(
            f"{output_dir.as_posix()} holds bundle files; write the export elsewhere"
        )


def export_bundle(paths: BundlePaths, output_dir: Path) -> dict[str, int]:
    """Read the bundle, write every file into `output_dir`, return data-row counts."""
    _refuse_bundle_directory(output_dir, paths)
    files = build_export(paths)
    output_dir.mkdir(parents=True, exist_ok=True)
    for file_name, rows in files.items():
        write_csv(output_dir / file_name, rows)
    return {file_name: len(rows) - 1 for file_name, rows in files.items()}


def _parser() -> argparse.ArgumentParser:
    defaults = default_bundle_paths()
    parser = argparse.ArgumentParser(
        prog="wave-local-ai-v2-export",
        description=(
            "Write the published bundle as five flat CSV tables, their column "
            "dictionary and a manifest. Reads the committed reference bundle "
            "unless pointed elsewhere; runs no benchmark and changes no bundle file."
        ),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--runtime-rows", type=Path, default=defaults.runtime_rows)
    parser.add_argument("--quality-rows", type=Path, default=defaults.quality_rows)
    parser.add_argument("--fiche-dir", type=Path, default=defaults.fiche_dir)
    parser.add_argument("--roster", type=Path, default=defaults.roster)
    parser.add_argument(
        "--suite-definitions", type=Path, default=defaults.suite_definitions
    )
    parser.add_argument(
        "--comparisons-dir", type=Path, default=defaults.comparisons_dir
    )
    parser.add_argument(
        "--leader-sets-dir", type=Path, default=defaults.leader_sets_dir
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """`wave-local-ai-v2-export`: exit 0 on a written export, 1 on a refusal."""
    args = _parser().parse_args(argv)
    paths = BundlePaths(
        runtime_rows=args.runtime_rows,
        quality_rows=args.quality_rows,
        fiche_dir=args.fiche_dir,
        roster=args.roster,
        suite_definitions=args.suite_definitions,
        comparisons_dir=args.comparisons_dir,
        leader_sets_dir=args.leader_sets_dir,
    )
    try:
        counts = export_bundle(paths, args.output_dir)
    except ExportError as error:
        print(f"export refused: {error}", file=sys.stderr)
        return 1
    for file_name, count in counts.items():
        print(f"wrote {(args.output_dir / file_name).as_posix()} ({count} rows)")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
