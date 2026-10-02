---
status: done
---

# Instruction: The two paired tests, their effect sizes and their null reasons

## Architecture projection

```txt
.
├── pyproject.toml                         ✏️ scipy in the dev group
├── uv.lock                                ✏️
├── src/wave_local_ai_v2/comparison.py     ✅ mcnemar_exact, wilcoxon_signed_rank
└── tests/test_comparison.py               ✅ worked examples, scipy oracle, null reasons
```

## User Journey

```mermaid
flowchart TD
  A[per-item candidate minus reference differences] --> B{scoring kind}
  B -->|binary| C[McNemar exact over discordant pairs]
  B -->|graded| D[Wilcoxon signed-rank, Pratt, exact or normal]
  C --> E[statistic, p, direction, odds ratio or a named null reason]
  D --> E
```

## Test Scope

```mermaid
---
title: Test scope
---
journey
  section Setup
    constructed outcome vectors => known 2x2 and signed-rank tables: 5: system
  section Happy path
    epic's 4/1 and 4/2 discordant pairs => p 0.375 and 0.6875: 5: system
    Wikipedia signed-rank differences => W+ 27, W- 18: 5: system
    random vectors => p equals scipy binomtest and wilcoxon: 5: system
  section Edge case - undefined statistics
    no discordant pairs => McNemar => p null with no_discordant_pairs: 1: system
    one empty cell => McNemar => odds ratio null with odds_ratio_empty_cell: 1: system
    every difference zero => Wilcoxon => p and effect null with all_differences_zero: 1: system
    no pairs => either test => paired_n_below_minimum: 1: system
```

## Tasks to do

### `1)` McNemar exact

1. Count concordant and discordant pairs; p = min(1, 2 * sum_{k<=min(b,c)} C(n,k) / 2^n) in `Fraction`.
2. Odds ratio c / b, null with `odds_ratio_empty_cell` on an empty cell.

### `2)` Wilcoxon signed-rank

1. Pratt ranks with tie averaging; W+ and W-; tie and zero counts.
2. Exact sign-flip distribution on doubled ranks when non-zero count <= 50, else normal approximation (Cureton, tie correction, no continuity correction).
3. Rank-biserial (W+ - W-) / (W+ + W-).

### `3)` Oracle and worked-example tests

1. Add scipy to the dev group; compare against `binomtest` and `wilcoxon(zero_method="pratt", correction=False)`.

## Test acceptance criteria

| Task | Acceptance criteria |
| ---- | ------------------- |
| 1 | The epic's two published pairs reproduce p = 0.375 and 0.6875; an empty cell or no discordance gives its named reason, never a number |
| 2 | p agrees with scipy within 1e-9 on exact and approximate cases; all-zero differences give `all_differences_zero` |
| 3 | scipy is importable in tests only; no module under `src/` imports it |
