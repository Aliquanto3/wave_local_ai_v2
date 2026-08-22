# Evidence: three refused commits, then let through

Falsification ran on scratch branch `chore/fast-gate-falsification`, cut from the
working branch after `uv run pre-commit install` had already written
`.git/hooks/pre-commit` and `.git/hooks/pre-push`. Nothing here was pushed; the
branch and its three scratch files are deleted once this transcript is written.

## 1. Planted credential — `detect-secrets`

**Command:** `git add scratch_secret.py && git commit -m "scratch: planted credential"`

File: `AWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"` <!-- pragma: allowlist secret -->

The literal above is AWS's own documentation example key, kept so the transcript
shows what was planted; the pragma is the audited non-secret verdict on it.

**Refusal (shortest decisive line):**

```
detect-secrets...........................................................Failed
- hook id: detect-secrets
- exit code: 1
Secret Type: AWS Access Key
Location:    scratch_secret.py:1
```

**Fix:** removed the assignment. **Pass:**

```
detect-secrets...........................................................Passed
[chore/fast-gate-falsification a7a4771] scratch: planted credential removed
```

## 2. Lint violation — `ruff-check`

**Command:** `git add scratch_lint.py && git commit -m "scratch: unused import"`

File: `import os` followed by an unused function, correctly formatted.

**Refusal (shortest decisive line):**

```
ruff check...............................................................Failed
- hook id: ruff-check
F401 [*] `os` imported but unused
```

**Fix:** deleted the unused import. **Pass:**

```
ruff check...............................................................Passed
[chore/fast-gate-falsification 2779364] scratch: unused import removed
```

## 3. Formatting only — `ruff-format`

**Command:** `git add scratch_format.py && git commit -m "scratch: unformatted file"`

File: `x = [1,2,3]` — confirmed `uv run ruff check scratch_format.py` passed
beforehand, so the refusal below is attributable to formatting alone.

**Refusal (shortest decisive line):**

```
ruff format --check......................................................Failed
- hook id: ruff-format
unformatted: File would be reformatted
 --> scratch_format.py:1:8
  - x = [1,2,3]
  + x = [1, 2, 3]
```

**Fix:** ran `uv run ruff format scratch_format.py`. **Pass:**

```
ruff format --check......................................................Passed
[chore/fast-gate-falsification 09b0bc9] scratch: file formatted
```

## Attribution summary

| # | Defect | Refusing hook | Reason |
| - | ------ | -------------- | ------ |
| 1 | Planted AWS key | `detect-secrets` | AWS Access Key |
| 2 | Unused import | `ruff-check` | F401 |
| 3 | Unformatted list literal | `ruff-format` | file would be reformatted |
