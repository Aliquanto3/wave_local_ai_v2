"""CLI entry point: run one fixed prompt against llama-server, write one runtime row."""

from __future__ import annotations

import sys
import time
from pathlib import Path
from typing import Any

import requests

from wave_local_ai_v2 import server
from wave_local_ai_v2.energy import measure_energy
from wave_local_ai_v2.gpu import read_gpu_stats
from wave_local_ai_v2.hardware import capture_fiche
from wave_local_ai_v2.results import append_row
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

# Fixed prompt sized to make prefill tok/s (baseline: ~280 tok/s, measured by llama-bench's
# pp512 test) measurable rather than dominated by fixed per-request overhead. A short prompt
# under-reports prefill throughput because tokenization/batch-setup overhead is a larger
# fraction of the total; this prompt is sized to approach llama-bench's ~512-token window.
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
    "rather than treating every number in the report as equally trustworthy."
)
FIXED_MAX_TOKENS = 128
REQUEST_TIMEOUT_S = 300


def main() -> None:
    try:
        _run()
    except (
        SettingsError,
        server.ServerStartupError,
        requests.RequestException,
        MissingTimingsError,
    ) as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


def _run() -> None:
    settings = load_settings()
    fiche = capture_fiche()

    model_path = settings.slm_models_dir / MODEL_RELATIVE_PATH
    if not model_path.exists():
        raise SettingsError(f"model file not found: {model_path}")

    flags = server.build_flags(model_path)

    with server.running_server(settings.llama_server_path, flags) as process:

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
        rss_bytes = read_process_rss(process.pid)

    row: dict[str, Any] = {
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
    append_row(settings.results_path, row)

    print(
        f"gen_tok_per_s={row['gen_tok_per_s']:.1f} "
        f"prompt_tok_per_s={row['prompt_tok_per_s']:.1f} "
        f"ttft_ms={row['ttft_ms']:.1f} "
        f"energy_method={row['energy_method']} "
        f"-> {settings.results_path}"
    )
