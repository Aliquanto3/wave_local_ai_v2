# Contributing

`main` takes changes only through a checked pull request.

## Branch naming

`type/short-description`, where `type` is one of: `feat`, `fix`, `chore`,
`docs`, `test`, `refactor`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/):
`type(scope): description`, imperative mood, lowercase, English only.

## Fast gate — enforced on every commit

Installed with `uv run pre-commit install` (run once per clone; see
`docs/setup.md`). A `pre-commit` stage hook runs these, in order, and refuses
the commit if any fails:

```sh
uv run ruff check .
uv run ruff format --check .
uv run mypy src/ scripts/
uv run python -X utf8 -m detect_secrets.pre_commit_hook --baseline .secrets.baseline
```

If the hook refuses, fix the tree, not the hook — the entry above is the
contract with `aidd_docs/memory/coding-assertions.md`.

To run the gate by hand, use `uv run pre-commit run --all-files`. The last
command scans only the filenames the hook hands it, so running it on its own
exits 0 without checking anything.

## Before push

Runs at the `pre-push` stage, installed by the same command above:

```sh
uv run pytest
```

Tests stub HTTP and never start `llama-server` or call a live API — `pytest`
needs no GPU and no API key either.

## Continuous Integration

Triggers on every push to `main` and on every pull request. Runs on a
`ubuntu-latest` + `windows-latest` matrix, Python 3.12, the same commands as
the fast gate and pre-push hook above, plus the dependency audit — see
[`aidd_docs/memory/coding-assertions.md`](aidd_docs/memory/coding-assertions.md)
for the exact command list. Branch protection references one check name,
`required`, that stays stable as the matrix grows; it is green only when
every matrix leg is green.

## Branch protection on `main`

The protection is a GitHub repository ruleset, exported to
[`.github/rulesets/main.json`](.github/rulesets/main.json) so a reader can diff
the stated intent against what the repository actually enforces. It requires a
pull request (0 approvals), requires the `required` check to be green, requires
the branch to be up to date with `main` before merging, and refuses force-push
and deletion of `main`. `bypass_actors` is empty: nobody bypasses it, the
repository owner included.

Apply it to a fresh fork or a restored repository:

```sh
gh api -X POST repos/<owner>/<repo>/rulesets --input .github/rulesets/main.json
```

Re-apply it to an existing ruleset (get `<id>` from
`gh api repos/<owner>/<repo>/rulesets --jq '.[] | select(.name=="main") | .id'`):

```sh
gh api -X PUT repos/<owner>/<repo>/rulesets/<id> --input .github/rulesets/main.json
```

The tracked file is the live ruleset minus the fields the server generates and
rejects on input: `id`, `source_type`, `source`, `node_id`, `created_at`,
`updated_at`, `current_user_can_bypass`, `_links`. To check the file still
matches what GitHub enforces, re-export and compare. This prints `no diff` and
exits 0 when they match, and exits 1 when they have drifted, so it can gate a
script:

```sh
gh api repos/<owner>/<repo>/rulesets/<id> | python -c "import json,sys; GEN=('id','source_type','source','node_id','created_at','updated_at','current_user_can_bypass','_links'); live={k:v for k,v in json.loads(sys.stdin.buffer.read().decode('utf-8-sig')).items() if k not in GEN}; tracked=json.load(open('.github/rulesets/main.json',encoding='utf-8')); print('no diff' if live==tracked else 'DIFF: the tracked file no longer matches the live ruleset'); sys.exit(0 if live==tracked else 1)"
```

Comparison is on the parsed objects, not the text: the API returns its keys in
a different order from the tracked file, so a plain `diff` reports the whole
file as changed even when nothing has. The `utf-8-sig` decode is there because
PowerShell adds a BOM when it pipes, which a plain `json.load` rejects.

## Severity gate

- 🔴 and 🟡 findings block merge and are fixed on the same branch.
- 🟢 findings are appended to `aidd_docs/backlog/tech-debt.md`, never block,
  and never trigger another review round.

See [`aidd_docs/GUIDELINES.md`](aidd_docs/GUIDELINES.md) for the full house
rules.
