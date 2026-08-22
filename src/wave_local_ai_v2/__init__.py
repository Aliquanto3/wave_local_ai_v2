"""CLI entry point: run one fixed prompt against llama-server, write one runtime row."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import prompt_provenance, provenance, row_contract, server
from wave_local_ai_v2.energy import measure_energy
from wave_local_ai_v2.gpu import read_gpu_stats
from wave_local_ai_v2.hardware import capture_fiche
from wave_local_ai_v2.results import append_row, captured_at, new_run_id
from wave_local_ai_v2.settings import SettingsError, load_settings
from wave_local_ai_v2.timings import (
    MissingTimingsError,
    parse_timings,
    read_process_rss,
)

# Run-specific fields, validated on this machine per context_input/baseline_qwen36.md.
LLAMA_CPP_BUILD = "b10537"
MODEL_RELATIVE_PATH = Path("Qwen3.6-35B-A3B") / "Qwen3.6-35B-A3B-UD-IQ4_XS.gguf"
QUANT = "UD-IQ4_XS"

# Fixed prompt length chosen from live measurement, not just toward llama-bench's pp512
# window. A debug session (aidd_docs/tasks/2026_08/2026_08_21_runtime-measurement-harness/
# debug-prefill-gap.md) found prompt_tok_per_s from a fresh, single-request llama-server
# launch is NOT directly comparable to llama-bench's pp512 figure (measured live at
# 314.81 +/- 5.60 tok/s with these same flags): part of the gap is per-request overhead a
# short prompt doesn't amortize (closes with length), and part is an inherent, unavoidable
# cold-start tax on the first request served after a fresh model load -- a warm-up request
# tried to remove it, but bled its context into the measured request via the shared -np 1
# slot and wrecked gen_tok_per_s (26 -> 11.8), so this harness accepts the cold-start cost
# rather than adding slot-management complexity to hide it. At this length (~1500 tok), two
# real runs land at 255.9/259.3 tok/s -- the harness's honest ceiling for "one fixed prompt,
# one fresh server, one real request" (see plan.md's Decisions table for the re-scoped bar).
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


def main() -> None:
    try:
        _run()
    except (
        SettingsError,
        server.ServerStartupError,
        # requests.RequestException subclasses OSError, so every HTTP failure is
        # still caught here and the disk failures append_row can raise now are
        # too. The widening is deliberate and covers the whole run: any OS-level
        # failure (an absent llama-server binary, a denied read) is an operator
        # problem and belongs on stderr as one line, not as a traceback.
        OSError,
        MissingTimingsError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    settings = load_settings()
    run_id = new_run_id()
    fiche = capture_fiche()
    provenance_fields = provenance.capture_provenance()

    model_path = settings.slm_models_dir / MODEL_RELATIVE_PATH
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")

    flags = server.build_flags(model_path)

    with server.running_server(settings.llama_server_path, flags) as process:
        # A streamed request was tried here to get an independent wall-clock TTFT
        # (phase-4 task 1.2) from the time of the first received SSE chunk, then
        # reverted: gen_tok_per_s dropped from ~26 to ~17-18 tok/s right after
        # switching to streaming, consistent with llama-server counting each SSE
        # chunk's HTTP flush inside its own reported generation timings -- but this
        # machine's GPU independently hit sw_thermal_slowdown (confirmed via
        # `nvidia-smi --query-gpu=clocks_event_reasons...`) around the same point in
        # the session, after ~50 minutes of repeated real runs, so streaming-caused-it
        # is plausible but NOT cleanly proven; re-testing needs the GPU to cool down
        # first. Separately, a discarded warm-up request tried before this one was
        # rejected on unconfounded evidence: it leaked context into the measured
        # request's single -np 1 slot and collapsed gen_tok_per_s from 26 to 11.8.
        # Given that risk is real regardless of the streaming confound, this harness
        # keeps `ttft_ms` server-reported only, uncorroborated by an independent
        # measurement, rather than retry a fix with a demonstrated way to contaminate
        # the metric it must not break.
        def send_request() -> dict[str, Any]:
            response = requests.post(
                f"http://{server.HOST}:{server.PORT}/completion",
                json={
                    "prompt": FIXED_PROMPT,
                    "n_predict": FIXED_MAX_TOKENS,
                },
                timeout=REQUEST_TIMEOUT_S,
            )
            response.raise_for_status()
            result: dict[str, Any] = response.json()
            return result

        wall_clock_start = time.monotonic()
        response_json, energy = measure_energy(send_request)
        wall_clock_s = time.monotonic() - wall_clock_start

        timings = parse_timings(response_json)
        gpu_stats = read_gpu_stats()
        # None when the server exited or the OS denied the read: the row is
        # still written, with the column null rather than the run aborted.
        rss_bytes: int | None = read_process_rss(process.pid)

    row: dict[str, Any] = {
        "schema_version": row_contract.SCHEMA_VERSION,
        "run_id": run_id,
        "captured_at": captured_at(),
        **provenance_fields,
        "endpoint": prompt_provenance.LOCAL_COMPLETION_ENDPOINT,
        "prompt_template_id": prompt_provenance.TEMPLATE_ID_NONE,
        "prompt_template_hash": None,
        "prompt_capture": prompt_provenance.PROMPT_CAPTURE_CAPTURED,
        **fiche,
        "llama_cpp_build": LLAMA_CPP_BUILD,
        "model_file": MODEL_RELATIVE_PATH.name,
        "quant": QUANT,
        "flags": flags,
        "prompt": FIXED_PROMPT,
        "max_tokens": FIXED_MAX_TOKENS,
        "wall_clock_s": wall_clock_s,
        **timings,
        **gpu_stats,
        "process_rss_bytes": rss_bytes,
        **energy,
    }
    append_row(settings.results_path, "runtime", row)

    print(
        f"gen_tok_per_s={row['gen_tok_per_s']:.1f} "
        f"prompt_tok_per_s={row['prompt_tok_per_s']:.1f} "
        f"ttft_ms={row['ttft_ms']:.1f} "
        f"energy_method={row['energy_method']} "
        f"-> {settings.results_path}"
    )
