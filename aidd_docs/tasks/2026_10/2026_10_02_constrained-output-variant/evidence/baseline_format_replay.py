"""Replay the baseline arm's requests on the same build, model and launch
flags (port moved to 8091) to read each raw answer, which a classification
row does not carry, and count those outside the declared format."""

import json
import os
import subprocess
import time
from pathlib import Path

import requests

from wave_local_ai_v2 import (
    engines,
    local_client,
    prompt_variants,
    quality_cli,
    roster,
    suite_registry,
)

E = os.environ["E"]
fiche_dir = Path(E, "fiches")
fiche = json.loads(next(fiche_dir.iterdir()).read_text(encoding="utf-8"))
flags = [("8091" if f == "8080" else f) for f in fiche["flags"]]
proc = subprocess.Popen(
    [os.environ["LLAMA_SERVER_PATH"], *flags],
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
try:
    base = "http://127.0.0.1:8091"
    for _ in range(120):
        try:
            if requests.get(base + "/health", timeout=2).status_code == 200:
                break
        except requests.RequestException:
            pass
        time.sleep(1)
    spec = suite_registry.resolve("classification-support-routing")
    entry = roster.resolve_entry(
        roster.load_roster(quality_cli.load_settings().roster_path), "qwen3-0.6b-q8"
    )
    kwargs = local_client.thinking_kwargs(
        spec.thinking_policy, entry, engines.tracked_reference_engine()
    )
    lines = Path(E, "quality.jsonl").read_text(encoding="utf-8").splitlines()
    rows = [json.loads(line) for line in lines]
    predicted = {
        r["item_id"]: r["predicted_label"]
        for r in rows
        if r["prompt_variant_id"] == "baseline"
    }
    fmt = prompt_variants.resolve("constrained_output", "1").definition[
        "output_formats"
    ]["classification"]["format"]
    labels = {"account", "billing", "other", "technical"}
    items = []
    for item in spec.items:
        c = local_client.complete_chat(
            base,
            item["prompt"],
            max_tokens=spec.max_output_tokens,
            sampling=quality_cli.LOCAL_SAMPLING,
            thinking_kwargs=kwargs,
            timeout=120,
        )
        items.append(
            {
                "item_id": item["item_id"],
                "raw_output": c["content"],
                "inside_format": c["content"] in labels,
                "baseline_row_predicted_label": predicted[item["item_id"]],
            }
        )
    outside = [i for i in items if not i["inside_format"]]
    print(
        json.dumps(
            {
                "declared_format": fmt,
                "items": len(items),
                "outside_format": len(outside),
                "share_outside_format": len(outside) / len(items),
                "outside_items": outside,
                "items_detail": items,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
finally:
    proc.terminate()
    proc.wait(timeout=30)
