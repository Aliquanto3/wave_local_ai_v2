set -u
S="$1"
W=/c/Users/Anael/dev/wave_local_ai_v2-night
cd "$W"
# Two machines' live stores and fiches, constructed rows.
mkdir -p "$S/laptop-live/fiches" "$S/tower-live/fiches"
echo '{"cpu": "laptop"}' > "$S/laptop-live/fiches/aaa111.json"
echo '{"cpu": "tower"}'  > "$S/tower-live/fiches/bbb222.json"
echo '{"run_id": "run-laptop-1", "machine_id": "laptop-mobile-gpu", "compute_mode": "gpu", "fiche_hash": "aaa111", "schema_version": "26"}' > "$S/laptop-live/runtime.jsonl"
echo '{"run_id": "run-laptop-2", "machine_id": "laptop-mobile-gpu", "compute_mode": "cpu_only", "fiche_hash": "aaa111", "item_id": "it-1", "provider": "local", "schema_version": "26"}' > "$S/laptop-live/quality.jsonl"
echo '{"run_id": "run-tower-1", "machine_id": "tower-desktop-gpu", "compute_mode": "gpu", "fiche_hash": "bbb222", "schema_version": "26"}' > "$S/tower-live/runtime.jsonl"
: > "$S/tower-live/quality.jsonl"
promote() { # machine live-dir run-ids...
  m=$1; d=$2; shift 2
  args=(); for r in "$@"; do args+=(--run-id "$r"); done
  MACHINE_ID=$m RUNTIME_RESULTS_PATH="$d/runtime.jsonl" QUALITY_RESULTS_PATH="$d/quality.jsonl" \
  FICHE_REGISTRY_DIR="$d/fiches" MACHINE_RESULTS_ROOT="$S/repo/machines" TRACKED_FICHE_REGISTRY_DIR="$S/repo/fiches" \
  uv run --quiet wave-local-ai-v2-promote "${args[@]}"
  echo "exit $?"
}
merge() { MACHINE_RESULTS_ROOT="$S/repo/machines" uv run --quiet wave-local-ai-v2-merge-bundle --bundle-dir "$S/repo/bundle" "$@"; echo "exit $?"; }
echo '$ promote laptop run-laptop-1 run-laptop-2'; promote laptop-mobile-gpu "$S/laptop-live" run-laptop-1 run-laptop-2
echo '$ promote laptop again (idempotent)'; promote laptop-mobile-gpu "$S/laptop-live" run-laptop-1 run-laptop-2
echo '$ promote laptop run-tower-1 (foreign row)'; cp "$S/tower-live/runtime.jsonl" "$S/foreign.jsonl"; cat "$S/foreign.jsonl" >> "$S/laptop-live/runtime.jsonl"; promote laptop-mobile-gpu "$S/laptop-live" run-tower-1
echo '$ promote laptop no-such-run'; promote laptop-mobile-gpu "$S/laptop-live" no-such-run
echo '$ promote tower run-tower-1'; promote tower-desktop-gpu "$S/tower-live" run-tower-1
echo '$ merge'; merge
echo '$ merge again, byte-compare'; cp -r "$S/repo/bundle" "$S/bundle-first"; merge; diff -r "$S/bundle-first" "$S/repo/bundle" && echo "byte-identical"
echo '$ merge --check'; merge --check
echo '$ hand-edit the bundle, merge --check'; sed -i 's/run-tower-1/run-tower-9/' "$S/repo/bundle/runtime-reference.jsonl"; merge --check
echo '$ inject a collision: a tower row citing the laptop fiche aaa111'; echo '{"run_id": "run-tower-2", "machine_id": "tower-desktop-gpu", "compute_mode": "gpu", "fiche_hash": "aaa111", "schema_version": "26"}' >> "$S/repo/machines/tower-desktop-gpu/runtime.jsonl"; merge
echo '$ an undeclared machine id'; mkdir -p "$S/repo/machines/garage-box"; echo '{"run_id": "g1", "machine_id": "garage-box"}' > "$S/repo/machines/garage-box/runtime.jsonl"; merge
echo '$ bundle files'; ls "$S/repo/bundle"; cat "$S/bundle-first/runtime-reference.jsonl"
