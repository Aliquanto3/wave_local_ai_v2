set -u
S="$1"; DR="$2"
W=/c/Users/Anael/dev/wave_local_ai_v2-night
g() { git -c user.name=night-run -c user.email=night-run@example.invalid -c core.autocrlf=false "$@"; }
g init -q --bare -b main "$S/origin.git"
g clone -q "$S/origin.git" "$S/main" 2>/dev/null; cd "$S/main"; mkdir -p results/machines results/fiches results/bundle; touch results/machines/.keep; g add .; g commit -q -m "chore: seed"; g push -q origin main
for m in laptop-mobile-gpu tower-desktop-gpu; do g clone -q "$S/origin.git" "$S/$m"; done
promote_into() { # clone machine live run...
  c=$1; m=$2; d=$3; shift 3; args=(); for r in "$@"; do args+=(--run-id "$r"); done
  (cd "$W" && MACHINE_ID=$m RUNTIME_RESULTS_PATH="$d/runtime.jsonl" QUALITY_RESULTS_PATH="$d/quality.jsonl" FICHE_REGISTRY_DIR="$d/fiches" \
   MACHINE_RESULTS_ROOT="$c/results/machines" TRACKED_FICHE_REGISTRY_DIR="$c/results/fiches" uv run --quiet wave-local-ai-v2-promote "${args[@]}")
}
bundle() { # clone [--check]  (stands in for the CI "Derived bundle" step when --check)
  c=$1; shift
  (cd "$W" && MACHINE_RESULTS_ROOT="$c/results/machines" uv run --quiet wave-local-ai-v2-merge-bundle --bundle-dir "$c/results/bundle" "$@"); echo "exit $?"
}
land() { # branch: CI check on the branch tip, then merge into main (stand-in for the pull request)
  cd "$S/main"; g fetch -q origin; g switch -q --detach "origin/$1"
  echo "-- CI on $1:"; bundle "$S/main" --check
  g switch -q main; g merge -q --ff-only origin/main 2>/dev/null; g merge -q --no-ff -m "Merge $1" "origin/$1" && echo "landed $1 on main"; g push -q origin main
}
echo "== laptop and tower both branch from the same main"
cd "$S/laptop-mobile-gpu"; g switch -q -c results/laptop-mobile-gpu
cd "$S/tower-desktop-gpu"; g switch -q -c results/tower-desktop-gpu
echo "== laptop: promote, regenerate the bundle on the branch, check, one commit"
cd "$S/laptop-mobile-gpu"; promote_into "$PWD" laptop-mobile-gpu "$DR/laptop-live" run-laptop-1 run-laptop-2
bundle "$PWD"; bundle "$PWD" --check
g add results; g commit -q -m "feat(results): promote laptop-mobile-gpu runs"; g push -q origin results/laptop-mobile-gpu; g show --stat --format=%s HEAD | cat
echo "== tower: same, in parallel"
cd "$S/tower-desktop-gpu"; promote_into "$PWD" tower-desktop-gpu "$DR/tower-live" run-tower-1
bundle "$PWD"; bundle "$PWD" --check
g add results; g commit -q -m "feat(results): promote tower-desktop-gpu runs"; g push -q origin results/tower-desktop-gpu; g show --stat --format=%s HEAD | cat
echo "== the laptop's pull request lands first"
land results/laptop-mobile-gpu
echo "== the tower's branch, as pushed, against the new main: its bundle is stale"
cd "$S/tower-desktop-gpu"; g fetch -q origin
g merge-tree --write-tree origin/main HEAD >/dev/null 2>&1 && echo "merges cleanly" || echo "conflicts with main (bundle files)"
echo "== tower: rebase, take main's bundle files, re-run the merge, never hand-resolve"
g rebase origin/main >/dev/null 2>&1; g status --short | cat
g checkout -q --ours results/bundle; bundle "$PWD"; bundle "$PWD" --check
g add results; GIT_EDITOR=true g rebase --continue >/dev/null 2>&1 && echo "rebase continued"
g push -q -f origin results/tower-desktop-gpu
land results/tower-desktop-gpu
echo "== operator-carried: pro-pc-no-gpu cannot push; its location is carried to the laptop"
mkdir -p "$S/usb/results/machines/pro-pc-no-gpu"
echo '{"record_kind": "refusal", "machine_id": "pro-pc-no-gpu", "roster_entry_id": "qwen3.6-35b-a3b-ud-iq4xs", "run_id": "refusal-1"}' > "$S/usb/results/machines/pro-pc-no-gpu/refusals.jsonl"
cd "$S/laptop-mobile-gpu"; g fetch -q origin; g switch -q -c results/pro-pc-no-gpu origin/main
cp -r "$S/usb/results/." results/
bundle "$PWD"; bundle "$PWD" --check
g add results; g commit -q -m "feat(results): promote pro-pc-no-gpu records" -m "Transport: operator-carried
Source-machine: pro-pc-no-gpu
Carried-by: laptop-mobile-gpu
Transport-verification: declared, not verified"
g push -q origin results/pro-pc-no-gpu; g log -1 --format='%s%n%b' | cat
land results/pro-pc-no-gpu
echo "== main after three pull requests"
cd "$S/main"; g ls-files results | cat; bundle "$S/main" --check
echo "== remotes are only the local bare repo:"; g remote -v | cat
