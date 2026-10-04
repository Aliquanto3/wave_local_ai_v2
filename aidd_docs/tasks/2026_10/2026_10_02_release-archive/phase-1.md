---
status: done
---

# Instruction: the assembly script

## Architecture projection

```txt
.
├── scripts/
│   └── assemble_release_archive.py          ✅ build + verify
└── tests/
    └── test_assemble_release_archive.py     ✅
```

## Steps

1. `build --tag vX.Y.Z --commit <sha> --output-dir <dir>`: check tag, packaged version, `CITATION.cff` version and `git rev-parse HEAD` agree; regenerate the export from the committed bundle (cwd = repository root, so the manifest names repository-relative paths); copy the bundle parts and their `NOTICE.md` files at their repository paths; ship `LICENSE`, `LICENSE-DATA`, the stamped `CITATION.cff` and a generated `README.md`; write a deterministic zip; run `verify` on it.
2. `verify --tag vX.Y.Z --commit <sha> <zip>`: every expected entry present and nothing else; every bundle file equals the repository's bytes; every CSV equals the regenerated export; README and stamped citation name the version and commit; no text file names a clone-only path outside the `LICENSE-DATA` exception list.
3. Tests over the committed bundle in `tmp_path`: happy path, edited table, edited bundle copy, missing file, clone-only path added, version mismatch, commit mismatch, CLI exit codes.
