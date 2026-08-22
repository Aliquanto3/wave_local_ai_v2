# Review: main refuses an unchecked merge, including the maintainer's

- **Verdict**: approve
- **Diff**: `6d60b31...working-tree`
- **Axes run**: code, functional, relevancy
- **Date**: 2026_08_22
- **Findings**: 0 critical, 2 warning (both fixed on this branch), 3 minor (routed to `aidd_docs/backlog/tech-debt.md`)

## Phases

### Phase 1 — Story acceptance (no plan file; the story's acceptance list is the contract)

- [x] `main` accepts changes only through a pull request, and the order-3 summary check must be green before merge — `.github/rulesets/main.json:14-15` (`pull_request` rule) + `:31-43` (`required_status_checks`, context `required`, `integration_id: 15368`); refusal observed at `evidence.md:74-83` ("Changes must be made through a pull request" / "Required status check \"required\" is expected")
- [x] Bypass is off for everyone, maintainer and repository owner included — `.github/rulesets/main.json:51` (`"bypass_actors": []`); live API returns `"current_user_can_bypass":"never"` for the owning account
- [x] Force-push to `main` and deletion of `main` are refused — `.github/rulesets/main.json:44-46` (`non_fast_forward`), `:47-49` (`deletion`); both present in the live ruleset, not hand-probed (`evidence.md:118-120` says so)
- [x] A branch must be up to date with `main` before merging — `.github/rulesets/main.json:34` (`"strict_required_status_checks_policy": true`)
- [x] A direct push to `main` from the maintainer's machine is refused, transcript kept — `evidence.md:60-92`, `GH013` + `[remote rejected]`, exit 1, probe discarded
- [x] A red PR offers no merge — `evidence.md:94-114`, PR #11 `mergeable: MERGEABLE` + `mergeStateStatus: BLOCKED`, `required` conclusion `FAILURE`
- [x] Ruleset exported to a tracked file alongside the apply/re-apply command — `.github/rulesets/main.json` (new) + `CONTRIBUTING.md:66-77` (POST and PUT commands) + `CONTRIBUTING.md:87` (the compare command, repaired under finding 1)
- [x] `README.md` and `CONTRIBUTING.md` state in one line that `main` takes changes only through a checked pull request — `README.md:26-28`, `CONTRIBUTING.md:3`
- [x] The maintainer being the only committer does not soften any of the above — no bypass actor, no admin exemption, no `enforcement: evaluate`; `required_approving_review_count: 0` (`.github/rulesets/main.json:17`) is the only relaxation and touches review, not the check gate

## Findings

| Sev | Kind | Phase | Location | Issue | Fix |
| --- | ---- | ----- | -------- | ----- | --- |
| 🟡 fixed | code | 1 | `CONTRIBUTING.md:79-93` (was `:81-87`) | The block introduced by "re-export and compare" only re-exported. `gh --jq` emits compact single-line JSON with jq's key order; the tracked file is pretty-printed in a different order, so `diff` against it reported the whole file changed (verified: `1c1,52`). `jq` is not installed on this machine either, so the obvious `\| jq -S .` repair does not run. Acceptance criterion 7 and the story's stated verification method ("re-exporting it and finding no diff") both rest on this command. | Fixed at `CONTRIBUTING.md:87`: replaced with a `python -c` one-liner that compares the parsed objects, prints `no diff`, and exits 1 on drift. Two additions beyond the report's draft — the draft failed under PowerShell, which adds a BOM when it pipes (`json.decoder.JSONDecodeError: Unexpected UTF-8 BOM`), so the stdin read now decodes `utf-8-sig`, and the tracked file opens with an explicit `encoding='utf-8'`. Re-verified `no diff` / exit 0 under both `bash` and PowerShell. `CONTRIBUTING.md:90-93` states why the comparison is not textual and why the BOM decode is there. |
| 🟡 fixed | fit | 1 | `aidd_docs/tasks/2026_08/2026_08_22_main-ruleset/evidence.md:52-66` (was `:54-58`) | §3's transcript was a placeholder, not a command: `python -c "...del stripped fields; compare to .github/rulesets/main.json..."` with a hand-written `no diff`. Sections 1, 2, 4 and 5 are real transcripts; this is the one a skeptical client engineer most needs to re-run, and it could not be. The claim was true — the live ruleset (id `21200105`) minus the eight generated fields equals `.github/rulesets/main.json` exactly — but the evidence did not carry it. | Fixed at `evidence.md:56-61`: the real command and its real captured output (`no diff`, `=== exit code: 0 ===`), matching the transcript style of §1 and §4. `evidence.md:63-66` points at the same command in `CONTRIBUTING.md` so a reader re-runs it against the repository rather than trusting the transcript. |
| 🟢 | rot | 1 | `.github/rulesets/main.json:23` | `require_extra_approval_for_unattributed_changes: true` (a server default captured on export) combined with `required_approving_review_count: 0` and a solo maintainer who cannot approve their own PR: a commit whose author email is not linked to a GitHub account would demand an approval nobody can give, deadlocking the merge. Latent, never exercised — the five most recent commits all resolve to `author_login: Aliquanto3`, and the ruleset was created after PR #10 merged. | Either set it to `false` and say why in `CONTRIBUTING.md`, or keep it and add one line noting the unattributed-commit deadlock so the next maintainer recognises the symptom. |
| 🟢 | conform | 1 | `aidd_docs/backlog/stories/main-refuses-an-unchecked-merge-including-the-maintainers.md:3` | Frontmatter flipped to `status: done` before this review ran and before the branch merged. `aidd_docs/GUIDELINES.md:18` places the single review after the last phase, then the merge. The same pattern is already an open tech-debt row (2026-08-21, `full-branch-review`). | Flip to `done` in the merge commit, not ahead of the review. |
| 🟢 | rot | 1 | `aidd_docs/tasks/2026_08/2026_08_22_main-ruleset/evidence.md:29-32,47-50` | §2 titles itself "The ruleset was applied from the tracked file", while §3 explains the tracked file carries "the defaults the server filled in" — so the file as tracked was reconciled with the POST response afterwards and is not byte-for-byte what §2 POSTed. Harmless (both forms apply cleanly) but the two sections read as circular. | Retitle §2 "The ruleset was created from the tracked file, then the file reconciled with the server's response", or state the back-fill in §2 itself. |

## Verification

| Metric        | Value                                             |
| ------------- | ------------------------------------------------- |
| Verified      | 100% (9/9)                                        |
| Files checked | `.github/rulesets/main.json`, `CONTRIBUTING.md`, `README.md`, `aidd_docs/tasks/2026_08/2026_08_22_main-ruleset/evidence.md`, `aidd_docs/backlog/stories/main-refuses-an-unchecked-merge-including-the-maintainers.md`, live `gh api repos/Aliquanto3/wave_local_ai_v2/rulesets/21200105` |
| Unchecked     | none                                              |
| Unplanned     | `aidd_docs/backlog/stories/main-refuses-an-unchecked-merge-including-the-maintainers.md:3` — `status: ready` → `done`; the story file is not in its own "Files it creates or changes" list (see finding 4) |
