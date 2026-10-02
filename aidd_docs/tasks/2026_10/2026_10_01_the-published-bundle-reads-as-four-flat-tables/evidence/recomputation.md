Recomputed from <temp>/bundle-export-evidence/quality_items.csv with Python's csv module only (no repo code):

| run_id | provider | model_id | n | correct | recomputed | published suite_accuracy | match | per-language recomputed (n) | per-language published | match |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `5e13166d...` | local | Qwen3.6-35B-A3B | 20 | 16 | 0.8 | 0.8 | True | en 0.6 (10); fr 1.0 (5); de 1.0 (5) | en 0.6 (10); fr 1.0 (5); de 1.0 (5) | True |
| `5e13166d...` | mistral | mistral-small-2603 | 20 | 19 | 0.95 | 0.95 | True | en 1.0 (10); fr 1.0 (5); de 0.8 (5) | en 1.0 (10); fr 1.0 (5); de 0.8 (5) | True |
| `d20afbda...` | local | Qwen3.6-35B-A3B | 20 | 16 | 0.8 | 0.8 | True | en 0.6 (10); fr 1.0 (5); de 1.0 (5) | en 0.6 (10); fr 1.0 (5); de 1.0 (5) | True |
| `d20afbda...` | mistral | mistral-small-2603 | 20 | 18 | 0.9 | 0.9 | True | en 1.0 (10); fr 1.0 (5); de 0.6 (5) | en 1.0 (10); fr 1.0 (5); de 0.6 (5) | True |

ALL MATCH

Script used (`uv run python recompute.py <quality_items.csv>`):

```python
"""Recompute each published run's accuracy from quality_items.csv alone (csv module only)."""

import csv, sys
from collections import defaultdict

rows = list(csv.DictReader(open(sys.argv[1], encoding="utf-8", newline="")))
batches = defaultdict(list)
for r in rows:
    batches[(r["run_id"], r["provider"], r["model_id"])].append(r)
print(
    "| run_id | provider | model_id | n | correct | recomputed | published suite_accuracy | match | per-language recomputed (n) | per-language published | match |"
)
print("| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |")
ok = True
for (run, prov, model), rs in batches.items():
    c = sum(r["correct"] == "true" for r in rs)
    rec = c / len(rs)
    pub = {r["suite_accuracy"] for r in rs}
    m1 = pub == {repr(rec)}
    langs = defaultdict(list)
    for r in rs:
        langs[r["language"]].append(r["correct"] == "true")
    lrec, lpub, m2 = [], [], True
    for lang, a in langs.items():
        v = sum(a) / len(a)
        p = {r[f"language_breakdown_{lang}_accuracy"] for r in rs}
        n = {r[f"language_breakdown_{lang}_n"] for r in rs}
        lrec.append(f"{lang} {v!r} ({len(a)})")
        lpub.append(f"{lang} {'/'.join(sorted(p))} ({'/'.join(sorted(n))})")
        m2 &= p == {repr(v)} and n == {str(len(a))}
    ok &= m1 and m2
    print(
        f"| `{run[:8]}...` | {prov} | {model} | {len(rs)} | {c} | {rec!r} | {'/'.join(sorted(pub))} | {m1} | {'; '.join(lrec)} | {'; '.join(lpub)} | {m2} |"
    )
print()
print("ALL MATCH" if ok else "MISMATCH")
```
