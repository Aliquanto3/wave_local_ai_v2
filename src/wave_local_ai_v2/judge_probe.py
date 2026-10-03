# Licence notice: the hand-written item literals in this module
# (`JUDGE_PROBE_ITEMS`) are data licensed under CC-BY 4.0, see LICENSE-DATA.
# The surrounding code is licensed under the MIT License, see LICENSE.
"""The judge probe: ten hand-written open-ended items in EN, FR and DE, run
end to end through the judged machinery on this machine.

What this is. A deliberate one-off proof that the whole judged path works
against real providers: llama-server generates one output per item, both cloud
providers judge each of those outputs, and one Google-generated output is
judged by Mistral alone because the Google judge is the subject's own family
and `judge.select_judges` refuses it. Eleven rows, two paths, three languages.

What this is not. Not a task suite, and its file is never read as a suite
reference: it publishes no benchmark score, every `expected_label` /
`predicted_label` / `correct` / `suite_accuracy` on its rows is `null`, and the
only score it produces is the judged one. It sits below
`suite_gate.MIN_SUITE_ITEMS` on purpose -- ten items is too few for
Methodology 4's gate, and the rows say so themselves through `indicative` and
its reason rather than leaving it to a README. It does not pre-empt the
rewriting suite either: that suite owns its own items and its own rubric text,
so the probe deliberately reuses the generic shipped rubric
(`judge_protocol.OPEN_ENDED_QUALITY_1_TO_5`).

Two behaviours differ from `quality_cli` on purpose. The probe **refuses**
when either judge is unavailable -- a missing key, a provider absent from
`QUALITY_PROVIDERS` -- where the quality CLI skips that provider and
continues: the quality CLI's cloud providers are subjects, so losing one costs
a comparison column, while the probe's judges are the thing being proven and a
run that quietly produced ten single-judge rows would publish the honest-flag
path as if it were the two-judge path. And it writes into the tracked
`judge-probe-reference.jsonl` rather than an untracked live store (see
`settings.DEFAULT_JUDGE_PROBE_REFERENCE_PATH`). It never writes to
`quality.jsonl`.
"""

from __future__ import annotations

import argparse
import sys
import time
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, NotRequired, TypedDict

from wave_local_ai_v2 import (
    agreement,
    cost,
    engines,
    fiche_registry,
    google_client,
    judge,
    judge_backends,
    judge_protocol,
    local_client,
    mistral_client,
    preflight,
    profiles,
    prompt_provenance,
    prompt_variants,
    provenance,
    quality_rows,
    results,
    retry,
    roster,
    row_contract,
    scoring,
    server,
    suite_gate,
    suite_registry,
    timings,
    verdict,
)
from wave_local_ai_v2.energy import measure_energy
from wave_local_ai_v2.hardware import build_fiche, capture_fiche
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.settings import (
    Settings,
    SettingsError,
    load_settings,
    require_run_profile,
)
from wave_local_ai_v2.suite_gate import SuiteGateResult

REQUEST_TIMEOUT_S = 300

# The prompt variant every probe row runs under, applied to the item's
# authored prompt before any templating (`prompt_variants`). The judges are
# still handed the authored item text: a variant transforms the subject's
# prompt and never the scorer.
PROMPT_VARIANT_ID = prompt_variants.BASELINE_ID

# The exponential-backoff base for a retryable cloud failure with no
# provider-supplied retry hint. Same value and same role as
# `quality_cli._RETRY_BASE_DELAY_S` and `judge_backends._RETRY_BASE_DELAY_S`.
_RETRY_BASE_DELAY_S = 1.0

# Deliberately the same value as `quality_cli.QUALITY_SEED`, and deliberately
# not imported from it: a CLI module is not a library, and nothing else under
# `src/` imports one. Two CLIs pinning the same seed is a fact worth stating
# twice; a cross-CLI import would be a dependency worth avoiding.
PROBE_SEED = 20260821

# The subject sampling blocks, key for key and value for value what
# `quality_cli` sends, so a probe generation and a quality generation are
# sampled identically on the same provider.
LOCAL_SAMPLING: dict[str, Any] = {
    "seed": PROBE_SEED,  # server default: -1, a fresh random seed per request
    "temperature": 0,  # server launched with --temp 1.0
    "top_k": 0,  # disabled; server launched with --top-k 20
    "top_p": 1.0,  # disabled; server launched with --top-p 0.95
    # The server is launched with --presence-penalty 1.5, applied to the
    # logits before the sampler selects: temperature 0 alone would still be
    # greedy over penalised logits.
    "presence_penalty": 0,
}

GOOGLE_SAMPLING: dict[str, Any] = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 1,
    "seed": PROBE_SEED,
}

# The judge calls' own sampling. Temperature 0 with the seed pinned, and a
# small cap: the rubric asks for one integer, so a judge that needs more than
# sixteen tokens has already failed to answer in the form it was asked for --
# and `judge.parse_judge_score` records that as a named failure rather than a
# score.
JUDGE_MAX_TOKENS = 16
JUDGE_SAMPLING_MISTRAL: dict[str, Any] = {
    "temperature": 0,
    "random_seed": PROBE_SEED,
}
JUDGE_SAMPLING_GOOGLE: dict[str, Any] = {
    "temperature": 0,
    "top_p": 1,
    "top_k": 1,
    "seed": PROBE_SEED,
}


class ProbeItem(TypedDict):
    """One probe item: an open-ended prompt and its declaration tags.

    Deliberately carries no `expected_label` and no scoring key of any kind.
    The rubric is the only scoring rule the probe has; an item with a label
    would make this a task suite, which is exactly what the probe must not
    become.
    """

    item_id: str
    prompt: str
    language: Literal["en", "fr", "de"]
    provenance: Literal["hand_written", "licensed", "public"]
    contamination_risk: bool
    licence: str


def _item(item_id: str, prompt: str, language: Literal["en", "fr", "de"]) -> ProbeItem:
    """One hand-written item. Every probe item is hand-written, uncontaminated
    and published under the repository's hand-written-item licence."""
    return ProbeItem(
        item_id=item_id,
        prompt=prompt,
        language=language,
        provenance="hand_written",
        contamination_risk=False,
        licence=suite_gate.HAND_WRITTEN_LICENCE,
    )


# Ten items: four EN, three FR, three DE. Each FR and DE item is written
# natively in its own language -- instruction and material both -- never a
# translation of an EN item, and no two items are the same underlying text in
# two languages. Each is a few lines at most: the probe pays two cloud judge
# calls per item, and a longer set would read as a benchmark.
JUDGE_PROBE_ITEMS: list[ProbeItem] = [
    _item(
        "improve-en-01",
        "A colleague sent this one-line reply to a client who had asked for "
        "an earlier delivery date:\n\n"
        '"No. Friday is the date, stop asking."\n\n'
        "Rewrite it so it reads as considerate and professional. Do not "
        "change what it says: the date does not move.",
        "en",
    ),
    _item(
        "improve-en-02",
        "Rewrite this meeting invitation as a shorter, clearer one, without "
        "dropping anything a reader would need:\n\n"
        '"Hi all, so I was thinking, given everything that came up last week '
        "and the fact that a couple of us are travelling, maybe we should get "
        "together at some point, probably Tuesday, to go over the migration "
        "work and also the budget question if there is time, room 3 or the "
        'other one, let me know."',
        "en",
    ),
    _item(
        "summarise-en-01",
        "Summarise this note in two sentences:\n\n"
        '"The supplier called this morning. The connectors they were shipping '
        "us are held at customs, so the parts we expected on the 12th now "
        "arrive on the 19th at the earliest. Assembly can start without them, "
        'but the final test rig cannot."',
        "en",
    ),
    _item(
        "summarise-en-02",
        "Summarise the decisions below so a colleague who missed the call "
        "could act on them:\n\n"
        '"We agreed Marta owns the data migration. Nobody wants to touch the '
        "legacy export before the audit, so that waits. The client asked for "
        "a weekly status note, Tuesdays, one page. We are not hiring a second "
        "contractor this quarter. And the staging environment gets rebuilt "
        'before the next demo."',
        "en",
    ),
    _item(
        "improve-fr-01",
        "Reformule ce message pour qu'il soit plus courtois, sans en changer "
        "le fond :\n\n"
        "« Ton compte rendu est illisible. Refais-le avant ce soir. »",
        "fr",
    ),
    _item(
        "summarise-fr-01",
        "Résume ces notes de réunion en deux phrases :\n\n"
        "« Point budget repoussé. Claire a dit que le prestataire répond mal. "
        "On garde le prestataire pour l'instant. Relance du client mardi ? "
        "Personne ne s'est proposé. Le rapport annuel est décalé de deux "
        "semaines, validé par la direction. »",
        "fr",
    ),
    _item(
        "improve-fr-02",
        "Réécris ce paragraphe pour qu'un lecteur non spécialiste le "
        "comprenne, sans en retirer d'information :\n\n"
        "« La mise en production du socle applicatif est conditionnée à la "
        "levée des points bloquants identifiés lors de la recette "
        "fonctionnelle, dont l'arbitrage relève du comité de pilotage au "
        "regard des impacts capacitaires constatés en préproduction. »",
        "fr",
    ),
    _item(
        "improve-de-01",
        "Formuliere diese Rückmeldung sachlicher, ohne die Kritik "
        "abzuschwächen:\n\n"
        "„Deine Präsentation war eine Zumutung. So kann man das keinem Kunden "
        "zeigen.“",
        "de",
    ),
    _item(
        "summarise-de-01",
        "Fasse diese Terminabsage kurz zusammen:\n\n"
        "„Sehr geehrte Frau Berger, leider muss ich Ihnen mitteilen, dass der "
        "für Donnerstag, den 14., vereinbarte Werkstatttermin nicht wie "
        "geplant stattfinden kann, da unser Ersatzteillieferant einen Engpass "
        "gemeldet hat und die benötigte Komponente frühestens in der "
        "Folgewoche eintrifft. Wir bieten Ihnen ersatzweise den 21. zur "
        "gleichen Uhrzeit an und bitten um kurze Rückmeldung.“",
        "de",
    ),
    _item(
        "improve-de-02",
        "Schreibe diesen Absatz klarer und kürzer, ohne Inhalt wegzulassen:\n\n"
        "„Im Rahmen der Umsetzung der beschlossenen Maßnahmen ist vorgesehen, "
        "dass die zuständigen Fachbereiche unter Berücksichtigung der "
        "vorliegenden Rückmeldungen eine Priorisierung vornehmen, wobei die "
        "hierfür erforderlichen Abstimmungen im Vorfeld der nächsten Sitzung "
        "zu erfolgen haben.“",
        "de",
    ),
]

# The probe's own identity, versioned independently of the row schema, exactly
# as each registered suite's definition declares its own.
SUITE_ID = "judge-probe-open-ended"
SUITE_VERSION = "1"
# The same hashing rule every registered suite is hashed by, not a second one:
# two published `prompt_set_hash` values are comparable because one function
# produced both.
PROMPT_SET_HASH = suite_registry.prompt_set_hash(JUDGE_PROBE_ITEMS)
# Open-ended prose, not a one-word label: 32 tokens (the classification
# suite's cap) would truncate every single answer.
MAX_OUTPUT_TOKENS = 256
STOP_SEQUENCES: list[str] = []
# What the subject may spend that cap on (Methodology 3), the same declaration
# both shipped suites carry. `disabled` here too: this probe measures whether
# the judged machinery works end to end, and a subject that spends 256 tokens
# reasoning and answers nothing would test the judges against empty strings. A
# rewriting suite that wants deliberation declares `allowed` and sizes its own
# cap for it -- that is the suite's call, not this probe's.
THINKING_POLICY = row_contract.THINKING_POLICY_DISABLED
# The context every compared model is assumed to run at -- the shipped roster
# entry's own `server_flags.context_size`, written out as a literal for the
# same reason the shipped suites' `context_length` is: `server.py` exposes no
# one context-size constant to import, since a second roster entry could run
# at a different context.
CONTEXT_LENGTH = 32768

# The one item the cloud subject answers, named as a constant rather than
# "whichever item ran first": the single-judge row has to be reproducible.
CLOUD_SUBJECT_ITEM_ID = "improve-en-01"

# The generic shipped rubric, on purpose. The rewriting suite owns its own
# rubric text; reusing this one is what keeps the probe from becoming that
# suite's draft.
RUBRIC = judge_protocol.OPEN_ENDED_QUALITY_1_TO_5

TASK_SUITE = "judge-probe"

PROVIDER_LOCAL = "local"

# The four failure-taxonomy keys every quality row's `failure_counts` carries.
# `unparseable` and `truncated_context` are structurally unreachable for an
# open-ended item -- there is no label to fail to parse, and the local
# `/completion` path reports only its own cap -- but the key set is the
# contract's, not this suite's, so a reader comparing two stores compares the
# same four keys.
_FAILURE_COUNT_KEYS = (
    scoring.FAILURE_REASON_EMPTY,
    scoring.FAILURE_REASON_UNPARSEABLE,
    scoring.FAILURE_REASON_TRUNCATED_MAX_TOKENS,
    scoring.FAILURE_REASON_TRUNCATED_CONTEXT,
)

# `verdict.quality_verdict` is deliberately not called. It decides by
# comparing `predicted_label` across runs, and every probe row's
# `predicted_label` is null: a second probe run compared against the first
# would find every item "identical" and publish `reproduced` off two sets of
# nulls -- a reproduction claim about labels that do not exist. The honest
# block says what there is: nothing to be compared against.
_VERDICT_NOT_COMPARABLE_REASON = (
    "the probe publishes no label and no score: there is nothing for a later "
    "run to be compared against"
)


class JudgeCallError(RuntimeError):
    """Raised when a judge call fails, naming the item and the provider.

    A live-run finding. `retry.RetryBudgetExhausted` says only "retry budget
    exhausted after N retries" and the clients' own errors name a status code
    but not the call that produced it, so a probe that died mid-judging left
    the operator with nothing to act on -- and "which provider gave up, and on
    which item" is exactly the evidence the free-tier question is answered
    from. `__cause__` keeps the original error inspectable.
    """

    def __init__(self, message: str, *, provider: str, item_id: str) -> None:
        super().__init__(message)
        self.provider = provider
        self.item_id = item_id


class _ProbeCompletion(TypedDict):
    """One subject generation, unified across the local and cloud shapes."""

    content: str
    truncated: bool
    generated_tokens: int
    retries: int
    # Reported by the local chat endpoint's `usage` block; absent on the cloud
    # shape, which totals its own prompt tokens separately.
    prompt_tokens: NotRequired[int]
    # The item's own engine-reported tokens and first-token time (schema "18").
    measurement: timings.ItemMeasurement
    # The item's own rendered prompt under the loaded model's tokenizer, the
    # `direct` overhead's subtrahend (schema "20"); absent on the cloud shape.
    item_prompt_tokens: NotRequired[int]


@dataclass(frozen=True)
class _RunContext:
    """Everything one invocation resolves once and every row of it repeats."""

    settings: Settings
    run_id: str
    resumed: bool
    provenance_fields: dict[str, Any]
    roster_entry: roster.RosterEntry
    roster_version: int
    fiche_hash: str
    gate_result: SuiteGateResult
    # The retry total each cloud provider's calls drew from this invocation,
    # by provider: every probe row's subject or judges called both.
    retry_budget: dict[str, int]
    # The engine the local subject runs on, and what its local rows carry for
    # it: its id and live-probed build. A cloud subject's rows state that no
    # engine applies.
    engine: engines.EngineEntry
    local_producer_fields: dict[str, Any]


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="wave-local-ai-v2-judge-probe")
    parser.add_argument(
        "--resume",
        metavar="RUN_ID",
        default=None,
        help=(
            "Resume a prior invocation's run_id: a batch whose rows for that "
            "run_id are already complete is skipped, never re-paid for; an "
            "incomplete one generates and judges only the items it never "
            "wrote. Every row this invocation writes is marked resumed=true."
        ),
    )
    return parser.parse_args(argv)


def main() -> None:
    args = _parse_args()
    try:
        _run(resume_run_id=args.resume)
    except (
        SettingsError,
        server.ServerStartupError,
        # requests.RequestException subclasses OSError, so every HTTP failure
        # and every disk failure append_row can raise lands here as one line.
        OSError,
        roster.RosterError,
        local_client.LocalRequestError,
        JudgeCallError,
        suite_gate.SuiteGateError,
        # Both providers' request errors and an exhausted retry budget abort
        # the probe rather than being skipped, unlike the quality CLI: the
        # probe's judges are the thing being proven, not an optional subject.
        mistral_client.MistralRequestError,
        google_client.GoogleRequestError,
        retry.RetryBudgetExhausted,
        # `--resume` over rows written under another configuration.
        results.ResumeConfigurationError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run(resume_run_id: str | None = None) -> None:
    settings = load_settings()
    # The declared machine and compute mode, before anything else: a missing
    # or undeclared one refuses before any judge preflight or process.
    run_profile = require_run_profile(settings)
    # No campaign can declare the probe: its suite is not a registered suite
    # and its two judges are cloud calls. Refused rather than ignored, so a
    # set `CAMPAIGN_ID` never yields rows that silently belong to none.
    if settings.campaign_id is not None:
        raise SettingsError(
            f"CAMPAIGN_ID={settings.campaign_id!r} is set: the judge probe runs "
            "under no campaign (its suite is not a registered suite and its "
            "judges are cloud calls); unset CAMPAIGN_ID"
        )
    # Offline, before anything is generated or paid for: a probe missing a
    # judge must cost nothing at all.
    _preflight_judges(settings)

    run_id = resume_run_id or new_run_id()
    is_resume = resume_run_id is not None
    # Printed before anything can fail. A live-run finding: a run that dies
    # before its first row is written (a generation failure, a judge failure
    # on the first item) leaves nothing on disk to read its own id back off --
    # and `--resume` needs that id. It costs one stdout line to make the
    # failure recoverable.
    print(f"run_id={run_id}")
    # Every row states that the probe belongs to no campaign.
    provenance_fields = {
        **provenance.capture_provenance(),
        "campaign_id": row_contract.NO_CAMPAIGN,
    }
    loaded_roster = roster.load_roster(settings.roster_path)
    roster_entry = roster.resolve_entry(loaded_roster, settings.roster_entry_id)
    # The (entry x machine x mode) run profile, with any operator override:
    # a triple with no declared profile refuses here, before any spawn.
    launch_profile = profiles.resolve_for_run(
        roster_entry,
        run_profile.machine_id,
        run_profile.compute_mode,
        operator_n_cpu_moe=settings.host_n_cpu_moe,
        operator_threads=settings.host_threads,
    )
    # Below the entry's declared minimum for this mode, the run refuses here,
    # recorded, before the weights are looked for or any process starts.
    preflight.enforce(
        roster_entry,
        run_profile.machine,
        launch_profile,
        models_dir=settings.slm_models_dir,
        refusals_dir=settings.refusals_dir,
    )
    model_path = _local_model_path(settings, roster_entry)
    # Expected to come back indicative, naming the sub-20 item count. Not
    # suppressed: the probe sits below the gate deliberately and every row
    # says so. The gate still refuses an item whose language or provenance
    # declaration is missing or self-inconsistent, which is worth having on a
    # hand-written set.
    gate_result = suite_gate.gate_suite(JUDGE_PROBE_ITEMS)
    engine = engines.tracked_reference_engine()
    flags = server.build_flags(roster_entry, launch_profile, model_path, engine=engine)
    engine_fields = engines.fiche_fields(
        engine, settings.llama_server_path, flags, roster_entry.entry_id
    )
    local_producer_fields = quality_rows.local_producer_fields(
        engine_fields,
        machine_id=run_profile.machine_id,
        compute_mode=run_profile.compute_mode,
        profile=launch_profile,
    )
    # After the build probe (the engine and its build are part of the
    # configuration), before the fiche, any spawn or any row is written.
    if is_resume:
        _refuse_a_resume_under_another_configuration(
            settings, run_id, roster_entry, local_producer_fields
        )
    run_fiche = build_fiche(
        capture_fiche(),
        **engine_fields,
        machine_id=run_profile.machine_id,
        compute_mode=run_profile.compute_mode,
        profile_id=launch_profile.profile_id,
        roster_entry_id=roster_entry.entry_id,
        model_sha256=roster_entry.sha256,
        quant=roster_entry.quant,
        flags=flags,
    )
    fiche_hash_value = fiche_registry.write_fiche(
        run_fiche, settings.fiche_registry_dir
    )

    deprecation_notice = mistral_client.check_model_available(settings.mistral_api_key)
    if deprecation_notice:
        # A retirement date is news, not a failure: the model still answers
        # until then. stderr keeps stdout to the lines the operator reads.
        print(deprecation_notice, file=sys.stderr)
    google_model_info = google_client.check_model_available(settings.google_api_key)

    # Which items this invocation calls for: every one on a fresh run, only
    # the ones this run_id never wrote under `--resume` (none when complete).
    local_indexes = _indexes_to_run(settings, run_id, PROVIDER_LOCAL, is_resume)
    cloud_item_due = bool(
        not is_resume
        or results.resume_missing_items(
            settings.judge_probe_reference_path,
            run_id,
            judge_backends.PROVIDER_GOOGLE,
            [CLOUD_SUBJECT_ITEM_ID],
            task_suite=TASK_SUITE,
        )
    )
    # One pacer and one retry budget per provider for the whole run, not per
    # batch: the local batch's judge calls, the cloud item's own two subject
    # requests and its one judge call are all spaced against the same
    # per-provider clock, which is what the free tier's RPM ceiling actually
    # measures. Each budget is derived from the items this invocation judges
    # -- every one of them draws on both providers -- by the same rule the
    # quality CLI's batches run under.
    items_called = len(local_indexes) + int(cloud_item_due)
    budget_total = retry.derived_retry_budget(
        items_called,
        per_item=settings.cloud_retry_retries_per_item,
        minimum=settings.cloud_retry_min_retries,
    )
    mistral_pacer = retry.Pacer(settings.mistral_request_pacing_s, sleep=time.sleep)
    mistral_budget = retry.RetryBudget(budget_total)
    google_pacer = retry.Pacer(settings.google_request_pacing_s, sleep=time.sleep)
    google_budget = retry.RetryBudget(budget_total)

    mistral_judge = judge.Judge(
        model_id=mistral_client.MODEL,
        provider=judge_backends.PROVIDER_MISTRAL,
        family=roster.family_of(mistral_client.MODEL),
        backend=judge_backends.mistral_judge_backend(
            settings.mistral_api_key,
            pacer=mistral_pacer,
            budget=mistral_budget,
            temperature=JUDGE_SAMPLING_MISTRAL["temperature"],
            random_seed=JUDGE_SAMPLING_MISTRAL["random_seed"],
            max_tokens=JUDGE_MAX_TOKENS,
        ),
    )
    google_judge = judge.Judge(
        model_id=google_client.MODEL,
        provider=judge_backends.PROVIDER_GOOGLE,
        family=roster.family_of(google_client.MODEL),
        backend=judge_backends.google_judge_backend(
            settings.google_api_key,
            pacer=google_pacer,
            budget=google_budget,
            temperature=JUDGE_SAMPLING_GOOGLE["temperature"],
            top_p=JUDGE_SAMPLING_GOOGLE["top_p"],
            top_k=JUDGE_SAMPLING_GOOGLE["top_k"],
            seed=JUDGE_SAMPLING_GOOGLE["seed"],
            max_tokens=JUDGE_MAX_TOKENS,
        ),
    )

    context = _RunContext(
        settings=settings,
        run_id=run_id,
        resumed=is_resume,
        provenance_fields=provenance_fields,
        roster_entry=roster_entry,
        roster_version=loaded_roster.roster_version,
        fiche_hash=fiche_hash_value,
        gate_result=gate_result,
        retry_budget={
            judge_backends.PROVIDER_MISTRAL: mistral_budget.total,
            judge_backends.PROVIDER_GOOGLE: google_budget.total,
        },
        engine=engine,
        local_producer_fields=local_producer_fields,
    )

    local_summary = _run_local_batch(
        context, flags, local_indexes, judges=[mistral_judge, google_judge]
    )
    if cloud_item_due:
        _run_cloud_subject_item(
            context,
            google_model_info,
            pacer=google_pacer,
            budget=google_budget,
            subject_judge=mistral_judge,
        )
    else:
        print(
            f"{judge_backends.PROVIDER_GOOGLE} skipped: run {run_id} already complete",
            file=sys.stderr,
        )
    _print_summary(local_summary)


def _judge_model_ids(row: dict[str, Any]) -> list[str]:
    """The judges a row was scored by, as sorted model ids."""
    return sorted(str(record.get("model_id")) for record in row.get("judges") or [])


def _refuse_a_resume_under_another_configuration(
    settings: Settings,
    run_id: str,
    roster_entry: roster.RosterEntry,
    local_producer_fields: Mapping[str, Any],
) -> None:
    """Raise `ResumeConfigurationError` unless every row this run already
    wrote was produced, and judged, the way this invocation would.

    The quality CLI's rule, plus the judges: a resume folds the rows on disk
    into the batch's agreement and headline, so a row judged by another
    judge model would make one published agreement span two judge pairs.
    Checked before anything spawns or is written.
    """
    prompt_variant = prompt_variants.resolve(PROMPT_VARIANT_ID)
    shared = {
        "suite_version": SUITE_VERSION,
        "prompt_set_hash": PROMPT_SET_HASH,
        "prompt_variant_id": prompt_variant.variant_id,
        "prompt_variant_version": prompt_variant.version,
        "roster_entry_id": roster_entry.entry_id,
        "thinking_policy": THINKING_POLICY,
    }
    by_provider = {
        PROVIDER_LOCAL: (
            roster_entry.display_id,
            LOCAL_SAMPLING,
            prompt_provenance.LOCAL_CHAT_ENDPOINT,
            sorted([mistral_client.MODEL, google_client.MODEL]),
            local_producer_fields,
        ),
        judge_backends.PROVIDER_GOOGLE: (
            google_client.MODEL,
            GOOGLE_SAMPLING,
            google_client.GENERATE_URL,
            [mistral_client.MODEL],
            quality_rows.NO_LOCAL_PRODUCER_FIELDS,
        ),
    }
    for provider, (
        model_id,
        sampling,
        endpoint,
        judge_ids,
        producer_fields,
    ) in by_provider.items():
        prior_rows = results.batch_rows(
            settings.judge_probe_reference_path, run_id, provider, task_suite=TASK_SUITE
        )
        conflict = results.resume_configuration_conflict(
            prior_rows,
            {
                **shared,
                "model_id": model_id,
                "sampling": dict(sampling),
                "endpoint": endpoint,
                "judge_model_ids": judge_ids,
                "campaign_id": row_contract.NO_CAMPAIGN,
                **producer_fields,
            },
            derived={"judge_model_ids": _judge_model_ids},
        )
        if conflict is not None:
            raise results.ResumeConfigurationError(
                f"refusing --resume {run_id}: the {provider} batch's {conflict}; "
                "a resumed batch's agreement would span two configurations"
            )


def _indexes_to_run(
    settings: Settings, run_id: str, provider: str, is_resume: bool
) -> list[int]:
    """The positions in `JUDGE_PROBE_ITEMS` this invocation generates and judges.

    The quality CLI's rule: every item on a fresh run, and under `--resume`
    exactly the items this `(run_id, provider, task_suite)` batch never wrote.
    """
    if not is_resume:
        return list(range(len(JUDGE_PROBE_ITEMS)))
    item_ids = [item["item_id"] for item in JUDGE_PROBE_ITEMS]
    missing = set(
        results.resume_missing_items(
            settings.judge_probe_reference_path,
            run_id,
            provider,
            item_ids,
            task_suite=TASK_SUITE,
        )
    )
    return [index for index, item_id in enumerate(item_ids) if item_id in missing]


def _preflight_judges(settings: Settings) -> None:
    """Refuse the run unless both judges are configured. No skip, no default.

    The quality CLI skips a cloud provider that is missing or disabled and
    continues, because there its providers are subjects. Here they are the
    judges, and a run that quietly produced ten single-judge rows would
    publish the honest-flag path as if it were the two-judge path -- so this
    is one stderr line and exit 1, before any generation is paid for.
    """
    for provider, env_var, api_key in (
        (
            judge_backends.PROVIDER_MISTRAL,
            "MISTRAL_API_KEY",
            settings.mistral_api_key,
        ),
        (judge_backends.PROVIDER_GOOGLE, "GOOGLE_API_KEY", settings.google_api_key),
    ):
        if provider not in settings.quality_providers:
            raise SettingsError(
                f"{provider} is not enabled in QUALITY_PROVIDERS: the judge "
                "probe needs both judges and refuses rather than publishing "
                "single-judge rows as if two judges had scored them"
            )
        if not api_key:
            raise SettingsError(
                f"{env_var} is not set: the judge probe needs both judges and "
                "refuses rather than publishing single-judge rows as if two "
                "judges had scored them"
            )


def _local_model_path(settings: Settings, roster_entry: roster.RosterEntry) -> Path:
    """Resolve the local GGUF, or raise: a missing file must cost no network call."""
    model_path = settings.slm_models_dir / roster_entry.file
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")
    return model_path


def _item_by_id(item_id: str) -> ProbeItem:
    for item in JUDGE_PROBE_ITEMS:
        if item["item_id"] == item_id:
            return item
    raise ValueError(f"no probe item with item_id {item_id!r}")


def _generate_local_outputs(
    settings: Settings,
    flags: list[str],
    prompts: list[str],
    roster_entry: roster.RosterEntry,
    engine: engines.EngineEntry,
) -> tuple[list[_ProbeCompletion], list[str], str]:
    """One llama-server launch, one chat completion per probe item.

    The same path `quality_cli` takes and for the same reason: `/completion`
    sends the prompt byte-for-byte, so a chat-tuned model continues the item
    text rather than answering it. Returns the completions, the string each
    item was rendered to, and the template that rendered them -- the row
    publishes the first two and the hash of the third. `prompts` are the
    items' prompts as the declared variant left them, one per item.

    The entry's thinking control is resolved before the server launches and
    verified against the loaded template before the first item, exactly as
    `quality_cli` does: these rows publish `thinking_policy` too.
    """
    completions: list[_ProbeCompletion] = []
    rendered_prompts: list[str] = []
    base_url = engines.base_url(engine)
    thinking_kwargs = local_client.thinking_kwargs(
        THINKING_POLICY, roster_entry, engine
    )

    with server.running_server(settings.llama_server_path, flags, engine=engine):
        template = local_client.chat_template(base_url, timeout=REQUEST_TIMEOUT_S)
        if thinking_kwargs:
            local_client.verify_thinking_control(
                base_url,
                roster_entry,
                chat_template=template,
                timeout=REQUEST_TIMEOUT_S,
            )
        for prompt in prompts:
            rendered = local_client.render_prompt(
                base_url,
                prompt,
                thinking_kwargs=thinking_kwargs,
                timeout=REQUEST_TIMEOUT_S,
            )
            rendered_prompts.append(rendered)
            item_prompt_tokens = local_client.count_tokens(
                base_url, rendered, timeout=REQUEST_TIMEOUT_S
            )
            response = local_client.complete_chat(
                base_url,
                prompt,
                max_tokens=MAX_OUTPUT_TOKENS,
                sampling=LOCAL_SAMPLING,
                thinking_kwargs=thinking_kwargs,
                timeout=REQUEST_TIMEOUT_S,
            )
            completions.append(
                _ProbeCompletion(
                    content=response["content"],
                    truncated=response["finish_reason"]
                    in local_client.TRUNCATING_FINISH_REASONS,
                    generated_tokens=response["generated_tokens"],
                    # The local path has no retryable error type and never
                    # retries.
                    retries=0,
                    prompt_tokens=response["prompt_tokens"],
                    measurement=response["measurement"],
                    item_prompt_tokens=item_prompt_tokens,
                )
            )

    return completions, rendered_prompts, template


def _judge_failure_provider(exc: BaseException) -> str:
    """Which provider a judge failure came from, read off the exception itself.

    `RetryBudgetExhausted` is always raised `from` the provider error that
    spent the last retry, so the cause is where the provider's identity lives.
    """
    cause = exc.__cause__ if isinstance(exc, retry.RetryBudgetExhausted) else exc
    if isinstance(cause, mistral_client.MistralRequestError):
        return judge_backends.PROVIDER_MISTRAL
    if isinstance(cause, google_client.GoogleRequestError):
        return judge_backends.PROVIDER_GOOGLE
    return "unknown"


def _judge_item_naming_failures(item_id: str, **kwargs: Any) -> dict[str, Any]:
    """`judge.judge_item`, with a failure re-raised naming the item and provider."""
    try:
        return judge.judge_item(**kwargs)
    except (
        mistral_client.MistralRequestError,
        google_client.GoogleRequestError,
        retry.RetryBudgetExhausted,
    ) as exc:
        provider = _judge_failure_provider(exc)
        raise JudgeCallError(
            f"judge call failed on item {item_id!r} at provider {provider}: {exc}",
            provider=provider,
            item_id=item_id,
        ) from exc


def _judge_score(block: dict[str, Any], provider: str) -> agreement.JudgeScore | None:
    """That provider's own score off a judged block, or raise if it never ran."""
    for record in block["judges"]:
        if record["provider"] == provider:
            return record["score"]
    raise ValueError(
        f"no judge record from provider {provider!r} on this block: "
        f"{[record['provider'] for record in block['judges']]}"
    )


def _subject_failure_reason(content: str, truncated: bool) -> str | None:
    """Name why a subject generation is unusable, or `None`.

    `scoring.score_item`'s taxonomy minus the two branches that need a label:
    an open-ended item has nothing to parse, so `unparseable` can never fire,
    and a blank answer or one cut off at the cap are the two failures a judge
    would otherwise be asked to score.
    """
    if content.strip() == "":
        return scoring.FAILURE_REASON_EMPTY
    if truncated:
        return scoring.FAILURE_REASON_TRUNCATED_MAX_TOKENS
    return None


def _failure_counts(reasons: list[str | None]) -> dict[str, int]:
    """The batch's tally over `reasons`, always carrying all four keys."""
    counts = dict.fromkeys(_FAILURE_COUNT_KEYS, 0)
    for reason in reasons:
        if reason is not None:
            counts[reason] += 1
    return counts


def _build_row(
    context: _RunContext,
    *,
    item: ProbeItem,
    subject_output: str,
    model_id: str,
    provider: str,
    sampling: dict[str, Any],
    call_path_fields: dict[str, Any],
    batch_fields: dict[str, Any],
    judge_block: dict[str, Any],
    # The item's own generation figures (`quality_rows.item_measurement_fields`).
    item_measurement: dict[str, Any],
    # The harness that ran the subject call (`quality_rows.direct_harness_fields`).
    harness_fields: dict[str, Any],
    failure_reason: str | None,
    failure_counts: dict[str, int],
    retries: int,
    # The declared variant and what it made of the item's authored prompt,
    # before any templating.
    prompt_variant: prompt_variants.PromptVariant,
    prompt_before_template: str,
    # What the row publishes as `prompt`. The local chat path renders the
    # variant's output into something else and passes it here (Methodology 2);
    # the cloud path sends the variant's output and declares its wrapper, so
    # it passes nothing.
    prompt: str | None = None,
    # The failure that left the batch partial; `None` on a complete batch.
    partial_failure: dict[str, str] | None = None,
) -> dict[str, Any]:
    """One probe row: the quality contract's key set, the judge block, the output.

    Four fields are deliberately `null` on every probe row. An open-ended item
    has no label, so `expected_label`, `predicted_label` and `correct` have
    nothing honest to carry, and `suite_accuracy` is an exact-match rate over
    labels that do not exist -- as is `language_breakdown`, which is that same
    rate per language. Fabricating any of them would make a probe row read as
    a classification row that scored zero. The score a reader wants is the
    judged one, in the block below.

    `subject_output` is the one non-required key: the row must be inspectable
    (the judge block carries only the judges' replies, never the text they
    judged), and `predicted_label` cannot hold free-form prose without meaning
    two different things across two stores. Same extra-key mechanism google
    rows already use for `model_version`/`api_version`, so no contract change
    and no schema bump.
    """
    return {
        "schema_version": row_contract.SCHEMA_VERSION,
        "run_id": context.run_id,
        "captured_at": captured_at(),
        **context.provenance_fields,
        "roster_entry_id": context.roster_entry.entry_id,
        "roster_version": context.roster_version,
        **call_path_fields,
        "model_id": model_id,
        "provider": provider,
        # The subject call alone; what judging sent stays in `judge_egress`.
        "subject_egress": row_contract.subject_egress_for(provider),
        **quality_rows.subject_composition_fields(
            model_id, provider, context.roster_entry
        ),
        **(
            context.local_producer_fields
            if provider == PROVIDER_LOCAL
            else quality_rows.NO_LOCAL_PRODUCER_FIELDS
        ),
        "fiche_hash": context.fiche_hash,
        **batch_fields,
        "task_suite": TASK_SUITE,
        "item_id": item["item_id"],
        "prompt": prompt if prompt is not None else prompt_before_template,
        "prompt_variant_id": prompt_variant.variant_id,
        "prompt_variant_version": prompt_variant.version,
        "prompt_before_template": prompt_before_template,
        "expected_label": None,
        "predicted_label": None,
        "correct": None,
        "suite_accuracy": None,
        "language_breakdown": None,
        # No exact-match or graded suite score to qualify: the judged
        # headline's interval is not this row's to publish.
        "score_interval": None,
        "sampling": dict(sampling),
        "max_output_tokens": MAX_OUTPUT_TOKENS,
        "stop_sequences": list(STOP_SEQUENCES),
        "thinking_policy": THINKING_POLICY,
        "context_length": CONTEXT_LENGTH,
        "suite_id": SUITE_ID,
        "suite_version": SUITE_VERSION,
        "prompt_set_hash": PROMPT_SET_HASH,
        "language": item["language"],
        "provenance": item["provenance"],
        "contamination_risk": item["contamination_risk"],
        "indicative": context.gate_result["indicative"],
        "indicative_reasons": list(context.gate_result["indicative_reasons"]),
        **quality_rows.suite_item_fields(context.gate_result, item),
        "failure_reason": failure_reason,
        "failure_counts": dict(failure_counts),
        # The subject generation's retries. Each judge call's own retries stay
        # on that judge's record inside the block below.
        "retries": retries,
        "resumed": context.resumed,
        "retry_budget": dict(context.retry_budget),
        "partial_failure": (
            dict(partial_failure) if partial_failure is not None else None
        ),
        **item_measurement,
        **harness_fields,
        "verdict": {
            "verdict": verdict.VERDICT_NOT_COMPARABLE,
            "reference_run_id": None,
            "differing_fields": [],
            "reason": _VERDICT_NOT_COMPARABLE_REASON,
        },
        **judge_block,
        "subject_output": subject_output,
    }


def _run_local_batch(
    context: _RunContext,
    flags: list[str],
    indexes: list[int],
    *,
    judges: list[judge.Judge],
) -> tuple[agreement.Agreement, int] | None:
    """Generate, judge and write the local rows of `indexes`.

    `None` when there is nothing to run (a resume of a complete batch).

    A judge call that fails on an item stops the judging there: the items
    already judged are written as a partial batch naming the provider and
    the item, then the failure is re-raised, so the probe still exits 1. A
    `--resume` of that run generates and judges only the items never
    written, so no judge call whose result is on a row is issued again; the
    unwritten items' local generations are simply redone, which costs
    nothing. Once every item is on disk, the batch figures (agreement,
    headline, failure counts) are computed over the prior rows and the new
    ones together, so a resumed batch publishes what an uninterrupted one
    over the same responses would.
    """
    settings = context.settings
    if not indexes:
        print(
            f"{PROVIDER_LOCAL} skipped: run {context.run_id} already complete",
            file=sys.stderr,
        )
        return None

    items = [JUDGE_PROBE_ITEMS[index] for index in indexes]
    prompt_variant = prompt_variants.resolve(PROMPT_VARIANT_ID)
    variant_prompts = [
        prompt_variants.apply_variant(prompt_variant, item["prompt"]) for item in items
    ]
    local_batch, energy = measure_energy(
        lambda: _generate_local_outputs(
            settings, flags, variant_prompts, context.roster_entry, context.engine
        ),
        country_iso_code=settings.emission_country_iso_code,
    )
    completions, rendered_prompts, chat_template = local_batch

    # Judging happens after the measured block closed: a judge call is network
    # time on someone else's machine, and letting it land inside the tracker's
    # span would attribute a remote provider's latency to this row's energy.
    subject_family = roster.family_of(
        context.roster_entry.display_id, context.roster_entry
    )
    threshold = agreement.ContestedThreshold(settings.contested_ordinal_max_delta)
    blocks: list[dict[str, Any]] = []
    failure: JudgeCallError | None = None
    for item, completion in zip(items, completions, strict=True):
        try:
            blocks.append(
                _judge_item_naming_failures(
                    item["item_id"],
                    subject_family=subject_family,
                    subject_provider=PROVIDER_LOCAL,
                    subject_output=completion["content"],
                    item_prompt=item["prompt"],
                    item_language=item["language"],
                    rubric=RUBRIC,
                    judges=judges,
                    threshold=threshold,
                    single_judge_reason=None,
                )
            )
        except JudgeCallError as exc:
            failure = exc
            break
    judged = len(blocks)

    failure_reasons = [
        _subject_failure_reason(completion["content"], completion["truncated"])
        for completion in completions[:judged]
    ]
    prior_rows = (
        results.batch_rows(
            settings.judge_probe_reference_path,
            context.run_id,
            PROVIDER_LOCAL,
            task_suite=TASK_SUITE,
        )
        if context.resumed
        else []
    )
    # Every item the batch has now written, in suite order: its two judge
    # scores, its contested marking and its failure reason, read off the
    # prior rows or off this invocation's judging.
    outcome_by_item: dict[str, tuple[tuple[Any, Any], bool, str | None]] = {
        row["item_id"]: (
            (
                _judge_score(row, judge_backends.PROVIDER_MISTRAL),
                _judge_score(row, judge_backends.PROVIDER_GOOGLE),
            ),
            bool(row["contested"]),
            row["failure_reason"],
        )
        for row in prior_rows
    }
    for item, block, reason in zip(items, blocks, failure_reasons, strict=False):
        outcome_by_item[item["item_id"]] = (
            (
                _judge_score(block, judge_backends.PROVIDER_MISTRAL),
                _judge_score(block, judge_backends.PROVIDER_GOOGLE),
            ),
            bool(block["contested"]),
            reason,
        )
    outcomes = [
        outcome_by_item[item["item_id"]]
        for item in JUDGE_PROBE_ITEMS
        if item["item_id"] in outcome_by_item
    ]
    failure_counts = _failure_counts([reason for _, _, reason in outcomes])

    partial_failure: dict[str, str] | None = None
    summary: tuple[agreement.Agreement, int] | None = None
    if failure is not None:
        partial_failure = {
            "provider": failure.provider,
            "item_id": failure.item_id,
            "reason": str(failure),
        }
        # A partial batch publishes no headline: each row keeps the per-item
        # figures `judge_item` returned, and no suite-level score is computed
        # over the items that happened to be judged before the failure.
        for block in blocks:
            block["judged_headline_score"] = None
            block["judged_headline_excluded_n"] = None
    else:
        # The suite-level figures replace the per-item ones `judge_item`
        # returns. Kappa over one item is null by construction --
        # `agreement.cohens_kappa` answers `insufficient_items` there, and
        # says why in its own docstring -- so the batch figure is the only
        # real one this run can publish. Repeating it on every row of the
        # batch is the pattern `suite_accuracy`, `failure_counts` and
        # `language_breakdown` already follow. Nothing is lost: each row keeps
        # its own two judge scores under `judges` and its own `contested`
        # marking, so any other statistic is recomputable from the published
        # rows alone.
        pairs = [pair for pair, _, _ in outcomes]
        contested_flags = [contested for _, contested, _ in outcomes]
        batch_agreement = agreement.agreement_for_rubric(RUBRIC, pairs)
        headline = agreement.headline_score(
            [list(pair) for pair in pairs], contested_flags
        )
        for block in blocks:
            block["agreement"] = batch_agreement
            block["judged_headline_score"] = headline["score"]
            block["judged_headline_excluded_n"] = headline["n_excluded"]
        summary = (batch_agreement, sum(contested_flags))

    # What this invocation's local generation spent, every generated item
    # included: an item generated but never judged is regenerated on resume.
    batch_fields = quality_rows.local_batch_fields(settings, energy, completions)
    model_id = context.roster_entry.display_id

    for position, (
        item,
        completion,
        block,
        failure_reason,
        variant_prompt,
        rendered_prompt,
    ) in enumerate(
        zip(
            items,
            completions,
            blocks,
            failure_reasons,
            variant_prompts,
            rendered_prompts,
            strict=False,
        )
    ):
        row = _build_row(
            context,
            item=item,
            subject_output=completion["content"],
            model_id=model_id,
            provider=PROVIDER_LOCAL,
            sampling=LOCAL_SAMPLING,
            call_path_fields=_local_call_path(chat_template),
            prompt_variant=prompt_variant,
            prompt_before_template=variant_prompt,
            prompt=rendered_prompt,
            batch_fields=batch_fields,
            judge_block=block,
            # The first generation of this server launch is the cold one.
            item_measurement=quality_rows.item_measurement_fields(
                completion["measurement"], first_in_batch=position == 0
            ),
            harness_fields=quality_rows.direct_harness_fields(
                completion["measurement"], completion.get("item_prompt_tokens")
            ),
            failure_reason=failure_reason,
            failure_counts=failure_counts,
            retries=completion["retries"],
            partial_failure=partial_failure,
        )
        append_row(settings.judge_probe_reference_path, "quality", row)

    judge_calls = sum(len(block["judges"]) for block in blocks)
    print(
        f"model={model_id} provider={PROVIDER_LOCAL} "
        f"items={judged} judge_calls={judge_calls}"
    )
    if failure is not None:
        print(
            f"{PROVIDER_LOCAL} partial: run {context.run_id} stopped at item "
            f"{failure.item_id!r} (judge provider {failure.provider}) after "
            f"{judged} item(s) this invocation; resume with --resume "
            f"{context.run_id}",
            file=sys.stderr,
        )
        raise failure
    return summary


def _run_cloud_subject_item(
    context: _RunContext,
    model_info: google_client.GoogleModelInfo,
    *,
    pacer: retry.Pacer,
    budget: retry.RetryBudget,
    subject_judge: judge.Judge,
) -> None:
    """Generate the one Google-subject output and judge it with Mistral alone.

    The Google judge is never handed to `judge_item` here: `select_judges`
    refuses a judge of the subject's own family by name, and that refusal is
    the behaviour being proven, not a code path to route around.
    """
    settings = context.settings
    item = _item_by_id(CLOUD_SUBJECT_ITEM_ID)
    api_key = settings.google_api_key
    prompt_variant = prompt_variants.resolve(PROMPT_VARIANT_ID)
    variant_prompt = prompt_variants.apply_variant(prompt_variant, item["prompt"])

    pacer.wait()
    _, context_retries = retry.call_with_retry(
        lambda: google_client.check_context_fits(
            variant_prompt, api_key, model_info["input_token_limit"]
        ),
        is_retryable=_is_google_retryable,
        retry_hint_s=_google_retry_hint_s,
        budget=budget,
        base_delay_s=_RETRY_BASE_DELAY_S,
        sleep=time.sleep,
    )
    pacer.wait()
    response, generate_retries = retry.call_with_retry(
        lambda: google_client.complete_prompt(
            variant_prompt,
            api_key,
            temperature=GOOGLE_SAMPLING["temperature"],
            top_p=GOOGLE_SAMPLING["top_p"],
            top_k=GOOGLE_SAMPLING["top_k"],
            seed=GOOGLE_SAMPLING["seed"],
            max_tokens=MAX_OUTPUT_TOKENS,
        ),
        is_retryable=_is_google_retryable,
        retry_hint_s=_google_retry_hint_s,
        budget=budget,
        base_delay_s=_RETRY_BASE_DELAY_S,
        sleep=time.sleep,
    )

    block = _judge_item_naming_failures(
        item["item_id"],
        subject_family=roster.family_of(google_client.MODEL),
        subject_provider=judge_backends.PROVIDER_GOOGLE,
        subject_output=response["content"],
        item_prompt=item["prompt"],
        item_language=item["language"],
        rubric=RUBRIC,
        judges=[subject_judge],
        threshold=agreement.ContestedThreshold(settings.contested_ordinal_max_delta),
        single_judge_reason=judge.SINGLE_JUDGE_REASON_CLOUD_SUBJECT,
    )

    truncated = response["finish_reason"] in google_client.TRUNCATING_FINISH_REASONS
    failure_reason = _subject_failure_reason(response["content"], truncated)
    batch_fields = quality_rows.cloud_batch_fields(
        settings,
        google_client.MODEL,
        cost.PRICE_TABLES[judge_backends.PROVIDER_GOOGLE],
        [response["prompt_tokens"]],
        response["generated_tokens"],
    )
    measurement = quality_rows.cloud_item_measurement(
        response["prompt_tokens"], response["generated_tokens"]
    )
    row = _build_row(
        context,
        item=item,
        subject_output=response["content"],
        model_id=google_client.MODEL,
        provider=judge_backends.PROVIDER_GOOGLE,
        sampling=GOOGLE_SAMPLING,
        call_path_fields=_google_call_path(),
        prompt_variant=prompt_variant,
        prompt_before_template=variant_prompt,
        batch_fields=batch_fields,
        judge_block=block,
        # The probe's one cloud subject item is its batch's only generation.
        item_measurement=quality_rows.item_measurement_fields(
            measurement, first_in_batch=True
        ),
        # A plain client call; no count of the item under Google's tokenizer.
        harness_fields=quality_rows.direct_harness_fields(measurement, None),
        failure_reason=failure_reason,
        failure_counts=_failure_counts([failure_reason]),
        retries=context_retries + generate_retries,
    )
    append_row(settings.judge_probe_reference_path, "quality", row)
    print(
        f"model={google_client.MODEL} provider={judge_backends.PROVIDER_GOOGLE} "
        f"items=1 judge_calls={len(block['judges'])} "
        f"single_judge_reason={block['single_judge_reason']}"
    )


def _print_summary(local_summary: tuple[agreement.Agreement, int] | None) -> None:
    """The line the operator reads into the results README."""
    if local_summary is None:
        print("agreement: not computed this invocation (local batch skipped)")
        return
    batch_agreement, contested_count = local_summary
    value = batch_agreement["value"]
    reported = (
        f"{value:.4f}"
        if value is not None
        else f"null ({batch_agreement['value_null_reason']})"
    )
    print(
        f"agreement statistic={batch_agreement['statistic']} value={reported} "
        f"exact_match_rate={batch_agreement['exact_match_rate']:.2f} "
        f"n_items={batch_agreement['n_items']} "
        f"n_items_excluded={batch_agreement['n_items_excluded']} "
        f"contested={contested_count}"
    )


def _is_google_retryable(exc: Exception) -> bool:
    return isinstance(exc, google_client.RetryableRequestError)


def _google_retry_hint_s(exc: Exception) -> float | None:
    return (
        exc.retry_after_s
        if isinstance(exc, google_client.RetryableRequestError)
        else None
    )


def _local_call_path(chat_template: str) -> dict[str, Any]:
    """The four call-path fields of the local chat path.

    Same shape and same reasoning as `quality_cli._local_call_path`: the id
    names the mechanism, the hash names which model's template rendered the
    row, and `reconstructed` says the stored string came from
    `/apply-template` rather than from the answering request.
    """
    return {
        "endpoint": prompt_provenance.LOCAL_CHAT_ENDPOINT,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_LLAMACPP_MODEL_CHAT,
        "prompt_template_hash": prompt_provenance.template_hash(chat_template),
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_RECONSTRUCTED,
    }


def _google_call_path() -> dict[str, Any]:
    """The four call-path fields of the Google generateContent path."""
    return {
        "endpoint": google_client.GENERATE_URL,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_GOOGLE_CHAT_MESSAGE,
        "prompt_template_hash": prompt_provenance.GOOGLE_CHAT_MESSAGE_HASH,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
    }
