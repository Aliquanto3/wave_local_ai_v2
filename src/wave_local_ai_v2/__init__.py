"""CLI entry point: run a warmed and cooled repetition set against llama-server,
write one aggregated runtime row.
"""

from __future__ import annotations

import sys
import time
from typing import Any

import requests

from wave_local_ai_v2 import (
    aggregation,
    build_probe,
    fiche_registry,
    prompt_provenance,
    provenance,
    results,
    roster,
    row_contract,
    server,
    verdict,
)
from wave_local_ai_v2.energy import measure_energy
from wave_local_ai_v2.gpu import read_gpu_stats
from wave_local_ai_v2.hardware import build_fiche, capture_fiche
from wave_local_ai_v2.machine_state import read_machine_state
from wave_local_ai_v2.repetitions import (
    EXCEED_CONTEXT_ERROR_TYPE,
    SLOT_RESET_METHOD,
    THERMAL_POSTURE_FIXED_COOLDOWN,
    RepetitionFailure,
    RepetitionResult,
    run_repetition_set,
)
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.settings import SettingsError, load_settings
from wave_local_ai_v2.timings import MissingTimingsError, read_process_rss

# The seed is pinned in the request body, not by a server flag, so
# `server.build_flags` stays byte-for-byte the validated baseline command --
# the same pattern `quality_cli.QUALITY_SEED` / `LOCAL_SAMPLING` uses for
# exactly this reason. Probed live on this build: two `/completion` calls with
# the same `seed` returned byte-identical `content`; the same call with no
# seed did not (see plan.md's Resources table).
RUNTIME_SEED = 20260822

# Fixed prompt length chosen from live measurement, not just toward llama-bench's pp512
# window. A debug session (aidd_docs/tasks/2026_08/2026_08_21_runtime-measurement-harness/
# debug-prefill-gap.md) found prompt_tok_per_s from a fresh, single-request llama-server
# launch is NOT directly comparable to llama-bench's pp512 figure (measured live at
# 314.81 +/- 5.60 tok/s with these same flags): part of the gap is per-request overhead a
# short prompt doesn't amortize (closes with length), and part was, at the time, an
# unavoidable cold-start tax on the first request served after a fresh model load: at this
# length (~1500 tok) two single-request runs landed at 255.9/259.3 tok/s, which was that
# harness's ceiling. That ceiling no longer describes this code. The repetition protocol
# pays the cold start once in an uncounted warm-up and forces a full prefill on every
# request with `cache_prompt: False` (see the block in `_run` below), and the counted
# repetitions now land at a median 272.08 tok/s over the five of the phase-4 live run
# (aidd_docs/tasks/2026_08/2026_08_22_runtime-repetition-protocol/phase-4.md). The prompt's
# length is kept for the reason above -- amortizing per-request overhead -- not because a
# single request is all the harness sends.
FIXED_PROMPT = (
    "You are a technical writer producing internal documentation for a consulting "
    "team that advises clients on local versus cloud LLM deployment. Summarize, in "
    "plain English and without bullet points, how a mixture-of-experts language "
    "model routes tokens to a subset of its experts at inference time, why this "
    "reduces active-parameter compute compared to a dense model of the same total "
    "size, and what tradeoffs this introduces for memory layout when some experts "
    "are offloaded to CPU RAM while others stay resident in GPU VRAM.\n\n"
    "Then explain why quantization format (for example IQ4_XS versus Q3_K_XL) "
    "affects both the memory footprint and the achievable generation throughput on "
    "consumer-grade hardware with limited VRAM, and why these effects are not "
    "visible on public leaderboards that only benchmark full-precision weights on "
    "datacenter hardware. Cover how the number of offloaded expert layers interacts "
    "with the model's fixed expert count: past a certain point, offloading more "
    "layers to CPU RAM stops changing throughput meaningfully, because the ceiling "
    "is the total number of experts the architecture defines, not an arbitrary knob.\n\n"
    "Next, describe why runtime benchmarks are fundamentally hardware-bound in a way "
    "that quality benchmarks are not: a tokens-per-second figure measured on one "
    "machine's GPU, VRAM budget, memory bandwidth, and thermal envelope cannot be "
    "compared against a figure from a different machine without a complete hardware "
    "fiche attached to it. Explain what fields such a fiche should carry at minimum "
    "-- CPU model, RAM size and speed, GPU model and driver version, CUDA ceiling, "
    "the exact inference engine build, the model file and its quantization, and the "
    "full set of runtime flags used -- and why omitting any one of them makes the "
    "reported number effectively unfalsifiable.\n\n"
    "Finally, discuss why energy and carbon figures reported by software-based "
    "estimators are categorically different from tokens-per-second or VRAM "
    "measurements: on a platform without access to hardware energy counters, an "
    "estimator must fall back to a thermal-design-power-based approximation that "
    "can be off by a large margin under sustained load or thermal throttling, "
    "particularly on laptop-class hardware, whereas a GPU's instantaneous power "
    "draw read directly from its driver is a real measurement. Explain why every "
    "energy figure in a client-facing report should be labeled with which of these "
    "two categories it belongs to, so a technical reviewer can weigh it correctly "
    "rather than treating every number in the report as equally trustworthy.\n\n"
    "Now repeat the same analysis in different words, as if writing the executive "
    "summary for a client who only wants the practical takeaways: restate the "
    "mixture-of-experts routing tradeoff, the quantization-format tradeoff, the "
    "hardware-fiche requirement, and the energy-measurement caveat, this time framed "
    "as concrete recommendations a consulting team could hand to a client evaluating "
    "whether to deploy a local model on consumer GPU hardware versus a cloud API. "
    "Be explicit about which of the four topics matters most when VRAM is the binding "
    "constraint, which matters most when energy reporting will be audited by a third "
    "party, and which matters most when the client's workload is dominated by long "
    "prompts rather than long generations, since the prefill-versus-decode balance "
    "changes which throughput figure the client should actually care about.\n\n"
    "Next, draft a short deployment checklist a consulting team could actually hand "
    "to a client's infrastructure engineer before a local model goes live. Cover, in "
    "plain English, how to size the context window against the client's real prompt "
    "lengths rather than the model's maximum, why the number of parallel request "
    "slots the server exposes should match the client's expected concurrent traffic "
    "rather than a default value, why a load-mode setting that avoids paging the "
    "model file from disk should be set explicitly rather than left to a default that "
    "may silently fall back to memory-mapping under low-RAM conditions, and why the "
    "sampling parameters (temperature, top-p, top-k, presence penalty) should be "
    "pinned and version-controlled alongside the runtime flags, since a silent "
    "sampler default change between engine versions can shift output quality without "
    "any corresponding change in the reported throughput numbers.\n\n"
    "Then write a short risk register for the same deployment, again in plain "
    "English and without bullet points: the risk that a throughput number reported "
    "without its full hardware fiche gets compared against an unrelated machine and "
    "produces a false conclusion about model efficiency; the risk that an energy "
    "figure labeled as measured is actually a software estimate and misleads a "
    "sustainability report; the risk that a quantization format chosen purely for "
    "its smaller file size degrades output quality in ways that are not visible in a "
    "tokens-per-second benchmark at all; and the risk that a runtime validated on one "
    "prompt length and one request pattern is silently assumed to generalize to a "
    "very different production workload without being re-validated. For each of "
    "these four risks, note briefly what evidence a technical reviewer should ask "
    "for before accepting the corresponding claim in a client-facing report, so the "
    "checklist and the risk register together give the consulting team a concrete, "
    "auditable basis for every number they eventually hand to the client, rather "
    "than a single headline figure presented without the context needed to judge "
    "whether it actually applies to that client's hardware, workload, and budget.\n\n"
    "Finally, address a question a skeptical client is likely to ask directly: why "
    "should they trust a single consulting team's benchmark over the numbers already "
    "published by the model's own creators or by a public leaderboard? Explain, in "
    "plain English, that a published leaderboard number is almost always produced on "
    "datacenter-class hardware with abundant VRAM and no CPU-offload constraints, "
    "conditions that do not resemble a client's actual consumer-grade deployment "
    "target, and that reproducing the benchmark on the client's own candidate "
    "hardware, with the client's own expected prompt lengths and concurrency, is the "
    "only way to get a number that predicts the client's real operating cost rather "
    "than an upper bound the client's hardware will never reach. Explain further why "
    "a benchmark run once should be treated skeptically even when it was run on the "
    "right hardware: engine warm-up effects, thermal throttling over a sustained "
    "session, background processes competing for the same GPU, and ordinary run-to-"
    "run variance can each shift a single measurement by a double-digit percentage, "
    "which is why a credible runtime report repeats the measurement, states the "
    "spread across repetitions, and discloses the exact prompt length and request "
    "pattern used, so a reviewer can judge whether the reported number was measured "
    "under conditions close enough to the client's real workload to be trusted, or "
    "whether it merely demonstrates the hardware's best case under an artificially "
    "favorable, short-prompt, single-request test that does not resemble how the "
    "client will actually use the system once it is deployed in production.\n\n"
    "As a closing exercise, write out a worked example the consulting team could "
    "reuse almost verbatim in a client deliverable: pick a hypothetical client whose "
    "workload is dominated by long-document summarization rather than short chat "
    "turns, walk through why that workload's prefill-to-decode token ratio makes "
    "prompt throughput the dominant cost driver rather than generation throughput, "
    "estimate in plain terms how the choice between two quantization formats with a "
    "roughly ten percent memory-footprint difference would change how many "
    "concurrent documents the client's GPU could hold in VRAM at once, and describe "
    "how the consulting team would phrase the recommendation to the client so that "
    "the tradeoff between fewer concurrent documents at higher fidelity and more "
    "concurrent documents at slightly lower fidelity is presented as a business "
    "decision the client makes deliberately, rather than a technical detail buried "
    "in a footnote the client never reads before signing off on the deployment."
)
FIXED_MAX_TOKENS = 128
REQUEST_TIMEOUT_S = 300


def _is_exceed_context_refusal(response: requests.Response) -> bool:
    """True only for llama-server's documented refusal of an over-long prompt.

    Probed live on this build: HTTP 400 carrying `error.type ==
    "exceed_context_size_error"` (plan.md's Resources table). Every other 400
    -- a malformed body, a rejected parameter -- must stay an HTTP error: its
    payload has no `content` either, so passing it through to `repetitions.py`
    would have it classified as an `empty` generation and the server's own
    message thrown away.
    """
    if response.status_code != 400:
        return False
    try:
        body = response.json()
    except ValueError:
        return False
    error = body.get("error") if isinstance(body, dict) else None
    return isinstance(error, dict) and error.get("type") == EXCEED_CONTEXT_ERROR_TYPE


def main() -> None:
    try:
        _run()
    except (
        SettingsError,
        roster.RosterError,
        server.ServerStartupError,
        # requests.RequestException subclasses OSError, so every HTTP failure is
        # still caught here and the disk failures append_row can raise now are
        # too. The widening is deliberate and covers the whole run: any OS-level
        # failure (an absent llama-server binary, a denied read) is an operator
        # problem and belongs on stderr as one line, not as a traceback.
        OSError,
        MissingTimingsError,
        RepetitionFailure,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    settings = load_settings()
    run_id = new_run_id()
    fiche = capture_fiche()
    provenance_fields = provenance.capture_provenance()
    # Loaded once per run, not once per row: `roster.load_roster` raises on
    # any structurally invalid entry before any HTTP call is made.
    loaded_roster = roster.load_roster(settings.roster_path)
    roster_entry = roster.resolve_entry(loaded_roster, settings.roster_entry_id)

    model_path = settings.slm_models_dir / roster_entry.file
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")

    # Refuses (roster.RosterError) before any process spawns when
    # settings.host_n_cpu_moe cannot be applied to roster_entry -- the check
    # lives inside build_flags itself (server.py's one call site).
    flags = server.build_flags(
        roster_entry, settings.host_n_cpu_moe, settings.host_threads, model_path
    )
    # The five sampler values already reach the model through `flags`; only
    # `seed` is sent per request, so a request never diverges from what the
    # server was actually launched with.
    runtime_sampling: dict[str, Any] = {
        "seed": RUNTIME_SEED,
        **server.sampler_settings(roster_entry),
    }
    # Probing the binary itself doesn't need the server running, so this is
    # done before launch rather than costing readiness-wait time. An
    # unreadable build is an explicit None, never a fallback string.
    llama_cpp_build = build_probe.probe_build(settings.llama_server_path)

    run_fiche = build_fiche(
        fiche,
        llama_cpp_build=llama_cpp_build,
        roster_entry_id=roster_entry.entry_id,
        model_sha256=roster_entry.sha256,
        quant=roster_entry.quant,
        flags=flags,
    )
    fiche_hash_value = fiche_registry.write_fiche(
        run_fiche, settings.fiche_registry_dir
    )

    # A RepetitionFailure is a verdict on a generation, not on the server: the
    # process answered normally, so its stderr tail would bury the one-line
    # diagnosis the operator actually needs under unrelated log.
    with server.running_server(
        settings.llama_server_path, flags, quiet_exceptions=(RepetitionFailure,)
    ) as process:
        # A streamed request was tried here to get an independent wall-clock TTFT
        # from the time of the first received SSE chunk, then reverted:
        # gen_tok_per_s dropped from ~26 to ~17-18 tok/s right after switching to
        # streaming, consistent with llama-server counting each SSE chunk's HTTP
        # flush inside its own reported generation timings -- but this machine's
        # GPU independently hit sw_thermal_slowdown (confirmed via
        # `nvidia-smi --query-gpu=clocks_event_reasons...`) around the same point in
        # the session, after ~50 minutes of repeated real runs, so streaming-caused-it
        # is plausible but NOT cleanly proven; re-testing needs the GPU to cool down
        # first. The row's `ttft_source` field (`timings.TTFT_SOURCE_SERVER_REPORTED`)
        # now carries the caveat this comment used to state alone: every published
        # `ttft_ms` is server-reported, uncorroborated by an independent measurement.
        #
        # A single warm-up request was also tried and reverted here at first: it
        # shared the measured request's single `-np 1` slot and, because the
        # server's context cache was still warm, collapsed gen_tok_per_s from 26 to
        # 11.8. The mechanism that replaced it (phase-1 of the repetition-protocol
        # increment, `aidd_docs/tasks/2026_08/2026_08_22_runtime-repetition-protocol/`)
        # sends `cache_prompt: False` on every request, warm-up included
        # (`repetitions.SLOT_RESET_METHOD`), rather than trying to avoid the shared
        # slot: this forces a full prefill every time, so a warm-up can no longer
        # leave a cache behind for the next repetition to benefit from unevenly.
        # Slot erase (`POST /slots/0?action=erase`) was probed as an alternative and
        # rejected: it returns HTTP 501 unless the server is launched with
        # `--slot-save-path`, which would change the validated baseline flag set.
        # Phase 4 re-validated this mechanism live (see its Evidence table):
        # repetition 1 (post-warm-up) landed mid-pack among repetitions 2..5
        # (25.43 tok/s vs 25.49/24.87/25.71/25.44), not systematically below
        # them -- the isolation held on this run.
        def send_request() -> dict[str, Any]:
            response = requests.post(
                f"http://{server.HOST}:{server.PORT}/completion",
                json={
                    "prompt": FIXED_PROMPT,
                    "n_predict": FIXED_MAX_TOKENS,
                    "cache_prompt": False,
                    "seed": RUNTIME_SEED,
                },
                timeout=REQUEST_TIMEOUT_S,
            )
            # The context-exceeded refusal is not raised here: `repetitions.py`
            # classifies its `error.type` into `truncated_context` rather than
            # crashing on an uncaught HTTPError. Every other status -- a 400
            # that means something else included -- still raises.
            if not _is_exceed_context_refusal(response):
                response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

        def read_rss() -> int | None:
            # None when the server exited or the OS denied the read: the
            # repetition is still recorded, with the column null rather than
            # the run aborted.
            return read_process_rss(process.pid)

        warmups, _ = run_repetition_set(
            send=send_request,
            read_gpu=read_gpu_stats,
            read_rss=read_rss,
            read_machine_state=read_machine_state,
            sleep=time.sleep,
            warmup_count=settings.runtime_warmup_count,
            count=0,
            cooldown_s=settings.runtime_cooldown_s,
        )

        def _run_counted() -> tuple[list[RepetitionResult], list[RepetitionResult]]:
            return run_repetition_set(
                send=send_request,
                read_gpu=read_gpu_stats,
                read_rss=read_rss,
                read_machine_state=read_machine_state,
                sleep=time.sleep,
                warmup_count=0,
                count=settings.runtime_repetitions,
                cooldown_s=settings.runtime_cooldown_s,
            )

        # The warm-up runs outside this tracker: energy spans only the counted
        # repetitions and the cooldowns between them (plan.md's Decisions table).
        (_, counted), energy = measure_energy(_run_counted)

    # The raw counted repetitions are kept on the row unmodified: a reader
    # recomputes these aggregates rather than trusting them.
    aggregated_timings = aggregation.aggregate_timings(
        counted, threshold=settings.runtime_spread_threshold
    )
    peaks = {
        metric: aggregation.peak([rep[metric] for rep in counted])  # type: ignore[literal-required]
        for metric in aggregation.PEAK_METRICS
    }
    # wall_clock_s is a sum, not a peak: AGGREGATION_LABELS declares it
    # "total_over_counted_repetitions" -- each repetition's own request time,
    # summed, excluding the cooldowns between them.
    wall_clock_s = sum(rep["wall_clock_s"] for rep in counted)

    row: dict[str, Any] = {
        "schema_version": row_contract.SCHEMA_VERSION,
        "run_id": run_id,
        "captured_at": captured_at(),
        **provenance_fields,
        "roster_entry_id": roster_entry.entry_id,
        "roster_version": loaded_roster.roster_version,
        "endpoint": prompt_provenance.LOCAL_COMPLETION_ENDPOINT,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_NONE,
        "prompt_template_hash": None,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
        "fiche_hash": fiche_hash_value,
        "prompt": FIXED_PROMPT,
        "max_tokens": FIXED_MAX_TOKENS,
        "sampling": dict(runtime_sampling),
        "seed_pinned": True,
        "warmup_count": settings.runtime_warmup_count,
        "warmup_repetitions": warmups,
        "restart_between_repetitions": False,
        "cooldown_s": settings.runtime_cooldown_s,
        "slot_reset_method": SLOT_RESET_METHOD,
        "thermal_posture": THERMAL_POSTURE_FIXED_COOLDOWN,
        "repetitions": counted,
        "wall_clock_s": wall_clock_s,
        **aggregated_timings,
        # Every counted repetition carries the same value today (one call
        # path reads it, `timings.parse_timings`), so citing the first is
        # not a loss of information.
        "ttft_source": counted[0]["ttft_source"],
        **peaks,
        "aggregation": dict(aggregation.AGGREGATION_LABELS),
        **energy,
    }
    reference_rows = results.read_rows(settings.runtime_reference_path)
    row["verdict"] = verdict.runtime_verdict(
        row,
        reference_rows,
        settings.fiche_registry_dir,
        settings.runtime_reproduction_tolerance,
    )
    append_row(settings.results_path, "runtime", row)

    print(
        f"gen_tok_per_s={row['gen_tok_per_s']:.1f} "
        f"prompt_tok_per_s={row['prompt_tok_per_s']:.1f} "
        f"ttft_ms={row['ttft_ms']:.1f} "
        f"repetitions_n={row['repetitions_n']} "
        f"unreliable={row['unreliable']} "
        f"energy_method={row['energy_method']} "
        f"-> {settings.results_path}"
    )
