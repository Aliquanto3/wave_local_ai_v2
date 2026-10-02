# Review: A comparison family carries its adjusted p-values and is superseded, not edited

## Round 1

VERDICT: CHANGES-REQUIRED

### Gates

- `uv run pytest -q` => `1421 passed, 2 warnings in 50.28s`, coverage 97.32% (floor 95%).
- `ruff check` clean, `ruff format --check` clean, `mypy src/ scripts/` clean, detect-secrets over the changed files exit 0.

### Acceptance, one by one

1. One invocation, one record, every comparison, definition, size, Holm over the closed set: met. `build_family_record` (`comparison.py` family section); tests `test_each_verdict_reads_its_holm_adjusted_p_with_the_raw_p_beside_it`, `test_comparisons_that_cannot_form_one_family_are_refused`, `test_an_invocation_spanning_two_suites_writes_nothing`.
2. Default family = one suite x one dimension, definition on the record: written on the record, but see blocking 1. `FAMILY_RULE` narrows Methodology 24's family to "every comparison this invocation declared, and only those", so the current record of a suite x dimension can hold fewer comparisons than were already run for it.
3. Verdict on adjusted p, raw p beside it: met. `_verdict(..., adjusted_p_value, alpha)`; test above shows model-c distinguishable raw (0.03125) and not adjusted (0.0625).
4. Immutable; 11 -> 12 writes a new record superseding by id, old file byte-identical: met for growth (`test_a_family_of_eleven_grown_to_twelve_is_superseded_not_edited`). The two committed `"1"` records are untouched (`git diff --stat -- aidd_docs/results/comparisons/` empty) and are superseded by the `"2"` record; `test_a_published_record_recomputes_or_is_unedited` self-hashes each `"1"` file. `supersedes` as `{"family_id": ...}` objects is still "by id"; acceptable.
5. Family of one: adjusted p = raw p, field present: met (`test_a_family_of_one_states_its_adjusted_p_and_is_deterministic`, `holm_adjust([0.375])`).
6. Refused member listed, field named, no p, tested/refused counts: met (`test_a_refused_member_is_listed_and_enters_no_count`).
7. Re-run identical: met (same test, re-runs of 12 and 11 re-emit the published bytes).

Holm: correct. Step-down `(m - rank) * p` with 0-based rank = `(m - j + 1) p(j)`, running max enforces monotonicity, `min(1, ...)` caps, exact in `Fraction`. Wikipedia worked example (0.03, 0.06, 0.06, 0.02) and a hand fixture with a tie and a cap both reproduce.

Observations counted in m: consistent with the acceptance (only refusals are excluded) and conservative; fine.

### Blocking

1. `comparison.py` `resolve_family_record` / `FAMILY_RULE`: a later invocation declaring fewer (or disjoint) comparisons of the same suite x dimension silently supersedes the current head. Reproduced: a 12-member family, then a 1-member declaration => `family 6328ab830e6e of 1 (1 tested, 0 refused, Holm over 1); supersedes d6e9a3fa455c`, exit 0, and `heads()` now returns only the family of one. The epic defines supersession for growth ("superseded by id when the family grows"), states that an adjusted p is wrong once the family holds more comparisons than it was computed over, and the story's "so that" is that a significant pair among twenty-eight is not the one that came up by chance; a shrink lets an analyst re-declare only the favourable pair and publish it as the current, unadjusted record. Fix expected: refuse (exit 1, nothing written) when the declared member keys do not include every member key of each current head of the same family definition (or carry prior members forward), align `FAMILY_RULE`, README and `cli.md` wording, and add a test for a shrinking and a disjoint re-declaration.

### Non-blocking

1. A non-refused member with a null p (`no_discordant_pairs`, `all_differences_zero`) counts in `tested_count` but not in Holm's m, so `tested_count != adjustment_size` and the other members' adjusted p is lower than if it entered as p = 1. The acceptance ties "the size the adjustment ran over" to the tested/refused counts; `adjustment_size` keeps it visible, but counting such a member (as p = 1) would be the conservative reading.
2. Re-running a superseded declaration (11 after 12) exits 0 with "identical to a published record" and does not say the re-emitted record is superseded; the console line could say so.
3. A change of `--alpha` alone (same members) supersedes the head; arguably a different family, not a successor. Worth a sentence in the README.
4. `aidd_docs/results/README.md` points at a declaration file inside a task folder (`aidd_docs/tasks/.../evidence/...comparisons.json`); evidence a published record depends on would be steadier beside the records.

## Round 2

VERDICT: PASS

### Gates

- `uv run pytest -q` => `1423 passed, 2 warnings in 47.28s`, coverage 97.32%.
- `ruff check`, `ruff format --check`, `mypy src/ scripts/` clean; detect-secrets over the changed files exit 0.

### Round 1 findings

- Blocking 1 (shrink): fixed. `resolve_family_record` refuses with `FamilyError` when the current head holds a member key the declaration omits, and `main` exits 1 with nothing written. Re-running the probe gives a 12-member family, then a 1-member declaration => `the current record of this family holds comparisons this invocation does not declare: ... a family only grows, so declare every one of them`, exit 1. The head stays the 12-member record. Test `test_a_declaration_dropping_a_current_comparison_is_refused[shrinking|disjoint]` asserts exit 1, the missing pair named, no new file and the head byte-identical. `FAMILY_RULE`, the README and `cli.md` now say a family only grows.
- Non-blocking 1 (null p): fixed. A non-refused member with a null p enters Holm as p = 1 and keeps its own adjusted p null with its reason, so `adjustment_size == tested_count` (`test_an_observation_is_adjusted_and_a_null_p_counts_as_one`).
- Non-blocking 2: fixed. Re-running a superseded declaration prints `superseded by <id>` (asserted in the 11 -> 12 test).
- Evidence: the version-2 record is now `classification-support-routing@2.model.1e1658cbe073.json`. `1921905d047a` is gone from disk and from the README and memory. The two version-1 records show no diff.

### Non-blocking (carried)

1. A change of `--alpha` alone still supersedes the head. This is undocumented.
2. The README's evidence declaration still lives in a task folder.
