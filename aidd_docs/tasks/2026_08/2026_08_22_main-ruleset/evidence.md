# Evidence: `main` refuses an unchecked merge, including the maintainer's

Date: 2026-08-22
Story: `aidd_docs/backlog/stories/main-refuses-an-unchecked-merge-including-the-maintainers.md`
Ruleset: `Aliquanto3/wave_local_ai_v2` ruleset id `21200105`, exported to
`.github/rulesets/main.json`.

## 1. The required check name is not a guess

The ruleset names one context, `required`, taken from the live check-run list on
the merge commit of PR #10 rather than from the workflow file:

```console
$ gh api repos/Aliquanto3/wave_local_ai_v2/commits/$(git rev-parse HEAD)/check-runs --jq '.check_runs[].name'
required
test (ubuntu-latest)
test (windows-latest)
```

It is pinned to the GitHub Actions app so a differently-owned check of the same
name cannot satisfy it:

```console
$ gh api repos/Aliquanto3/wave_local_ai_v2/commits/$(git rev-parse HEAD)/check-runs \
    --jq '.check_runs[] | select(.name=="required") | {name, app_id: .app.id, app_slug: .app.slug}'
{"app_id":15368,"app_slug":"github-actions","name":"required"}
```

## 2. The ruleset was applied from the tracked file

```console
$ gh api -X POST repos/Aliquanto3/wave_local_ai_v2/rulesets --input .github/rulesets/main.json
{"id":21200105,"name":"main","target":"branch","source_type":"Repository",
 "source":"Aliquanto3/wave_local_ai_v2","enforcement":"active",
 ...
 "bypass_actors":[],"current_user_can_bypass":"never", ...}
```

`"bypass_actors": []` and `"current_user_can_bypass": "never"` are the answer to
"is bypass off for the owner too": the API says never, for the account that owns
the repository and created the ruleset.

## 3. The tracked file matches the live setting

The file is the live ruleset minus the fields the server generates and rejects
on input: `id`, `source_type`, `source`, `node_id`, `created_at`, `updated_at`,
`current_user_can_bypass`, `_links`. Every remaining field, including the
defaults the server filled in (`required_reviewers`,
`require_extra_approval_for_unattributed_changes`, `do_not_enforce_on_create`),
is what the tracked file states.

Re-exported and compared, modulo those stripped fields. The comparison is on
the parsed objects: the API returns its keys in a different order from the
tracked file, so a plain `diff` of the two texts reports the whole file as
changed even when nothing has.

```console
$ gh api repos/Aliquanto3/wave_local_ai_v2/rulesets/21200105 | python -c "import json,sys; GEN=('id','source_type','source','node_id','created_at','updated_at','current_user_can_bypass','_links'); live={k:v for k,v in json.loads(sys.stdin.buffer.read().decode('utf-8-sig')).items() if k not in GEN}; tracked=json.load(open('.github/rulesets/main.json',encoding='utf-8')); print('no diff' if live==tracked else 'DIFF: the tracked file no longer matches the live ruleset'); sys.exit(0 if live==tracked else 1)"
no diff
=== exit code: 0 ===
```

The same command is in
[`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) under "Branch protection on
`main`", so a reader can re-run it against the repository as it stands rather
than trusting this transcript. Verified under both `bash` and PowerShell.

## 4. A direct push to `main` from the maintainer's machine is refused

The probe commit was made and pushed with `--no-verify` on purpose: the point is
to prove the *platform* refuses, not that a local hook does.

```console
$ echo "throwaway ruleset probe" > ruleset-probe.tmp
$ git add ruleset-probe.tmp
$ git commit --no-verify -m "chore: throwaway probe commit (never intended to land)"
[main 75288c4] chore: throwaway probe commit (never intended to land)
 1 file changed, 1 insertion(+)
 create mode 100644 ruleset-probe.tmp

$ git push --no-verify origin main
remote: error: GH013: Repository rule violations found for refs/heads/main.
remote: Review all repository rules at https://github.com/Aliquanto3/wave_local_ai_v2/rules?ref=refs%2Fheads%2Fmain
remote:
remote: - Changes must be made through a pull request.
remote:
remote: - Required status check "required" is expected.
remote:
To https://github.com/Aliquanto3/wave_local_ai_v2.git
 ! [remote rejected] main -> main (push declined due to repository rule violations)
error: failed to push some refs to 'https://github.com/Aliquanto3/wave_local_ai_v2.git'
=== exit code: 1 ===
```

The probe was then discarded:

```console
$ git reset --hard origin/main
HEAD is now at 6d60b31 Merge pull request #10 from Aliquanto3/ci/check-suite
```

## 5. A pull request with a red check offers no merge

PR #11 <https://github.com/Aliquanto3/wave_local_ai_v2/pull/11>
("scratch: CI must refuse this"), whose CI run
<https://github.com/Aliquanto3/wave_local_ai_v2/actions/runs/32574709902>
failed on both matrix legs and therefore on the summary check:

```console
$ gh pr view 11 --json number,state,mergeable,mergeStateStatus,statusCheckRollup
{"number":11,"state":"CLOSED","mergeable":"MERGEABLE","mergeStateStatus":"BLOCKED",
 "statusCheckRollup":[
   {"name":"test (ubuntu-latest)","conclusion":"FAILURE", ...},
   {"name":"test (windows-latest)","conclusion":"FAILURE", ...},
   {"name":"required","conclusion":"FAILURE",
    "detailsUrl":"https://github.com/Aliquanto3/wave_local_ai_v2/actions/runs/32574709902/job/97035284053", ...}]}
```

`mergeable: MERGEABLE` means the branches have no textual conflict;
`mergeStateStatus: BLOCKED` is the platform refusing the merge. The two together
are the point: nothing about the *content* stops this merge, only the red check
does.

## What this does not prove

- Force-push and deletion of `main` (rules `non_fast_forward` and `deletion`)
  are declared active in the ruleset but were not probed by hand — probing
  deletion would destroy the branch.
- A repository *administrator* can still edit or delete the ruleset itself.
  Empty `bypass_actors` removes the ability to push past it, not the ability to
  change it. The tracked file plus this transcript are what make such a change
  visible in a diff.
