# Codebase Map

The macro layout: the top-level areas and what each holds.

```mermaid
flowchart TD
    src["src/wave_local_ai_v2/\nMain package"]
    tests["tests/\nUnit tests"]
    ctx["context_input/\nSource material"]
    docs["aidd_docs/\nAI context"]
    results["aidd_docs/results/\nBenchmark rows"]
    backlog["aidd_docs/backlog/\nEpics and stories"]
    cfg["pyproject.toml · uv.lock\nProject config"]

    tests --> src
    docs --> results
    docs --> backlog
```

## Areas

- `src/wave_local_ai_v2/`: the main Python package; `read_model.py` is the typed read layer over the two stores (the four views, the three finite absence reasons, the schema-floor selection, and the resolution of `fiche_hash`/`roster_entry_id`/`suite_id`+`suite_version`), and `service.py` is the FastAPI app that answers those views over HTTP behind the API-key gate — both are read-only and import no writer; `row_contract.py` (the row schema contract and writer gate), `suite_gate.py` (the suite size/language-mix/provenance gate), `provenance.py` (code/tree identity: release version, commit sha, tree dirtiness) and `prompt_provenance.py` (call-path identity: endpoint, prompt-template id/hash, consistency rule) and `prompt_variants.py` (the versioned, hash-checked prompt variant registry and `apply_variant`, the one place a variant transforms an authored prompt before any templating) are shared by both benchmark CLIs; `fiche_registry.py` (write-once fiche storage, lookup, edited/missing verification), `fiche_validator.py` (the `wave-local-ai-v2-validate` command) and `verdict.py` (the three-state reproduction verdict, runtime and quality) are shared by all three; `mistral_client.py` and `google_client.py` are the quality CLI's two cloud-provider clients, one `requests`-only module per provider, dispatched by `quality_cli.py`'s `_CLOUD_PROVIDERS` table; the judge path follows the same one-module-per-provider discipline — `judge_protocol.py` (the per-language prompt shells, their content hashes and the versioned rubrics) and `agreement.py` (the two kappas, the raw agreement rates, the contested rule and the headline) are pure and provider-free, `judge.py` calls through an injected backend and enforces family independence, and `judge_backends.py` is the single seam that binds the two cloud clients to that backend protocol; `roster.py` resolves a model's family through `family_of`, preferring a roster entry's own optional `family` and falling back to an in-code declaration until Methodology 13's roster carries one; a task suite is data: `suite_data/<suite_id>.json` holds each definition (identity, caps, scoring-rule name, tagged items), `suite_registry.py` resolves `--suite`'s id to it and gates it at load, `scoring_rules.py` is the name-to-rule table (`exact_label_match`, `chrf_against_reference`), and `classification_suite.py`/`translation_suite.py` keep only what those rules need (label set, item shapes) and each suite's rationale; `subset_sampler.py` is the publication subset's selection rule (canonical ordering, a draw stratified by language and, for classification, label, recorded seed retries, a per-item content hash) checked by the registry at load and replayed by `subset_replay.py`; `use_case_coverage.py` gates and publishes the declared coverage record (`use_case_coverage.json`, one state per PRD use case, every named suite resolved through the registry); `chrf.py` is the character n-gram F-score itself — pure, no I/O, reproducing sacreBLEU's defaults in-repo rather than depending on the package; `comparison.py` is the paired test between two published configurations (side selection, refusal list, computed differing fields, McNemar/Wilcoxon on the standard library with scipy as a dev-only test oracle, Holm over a closed family, the family record and its supersede-by-id lookup); `leader_set.py` derives the leader set per suite and machine class from the rows, their fiches and the suite's family, and publishes and reads its superseded-not-edited records (`read_model` imports only its readers)
- `tests/`: pytest unit tests, one `test_<module>.py` per source module
- `context_input/`: French-language research notes (hardware fiches, benchmark baselines) — source material to inform implementation, not a language precedent for the repo
- `aidd_docs/`: AIDD memory bank and team docs, not application code
- `aidd_docs/results/`: benchmark output — the untracked live stores the CLIs append to, plus the committed `*-reference.jsonl` acceptance evidence (see its README)
- `aidd_docs/backlog/`: product backlog, epics and stories

## Entry points

- `wave-local-ai-v2` CLI command → `src/wave_local_ai_v2/__init__.py:main` (runtime benchmark)
- `wave-local-ai-v2-quality` CLI command → `src/wave_local_ai_v2/quality_cli.py:main` (quality benchmark)
- `wave-local-ai-v2-validate` CLI command → `src/wave_local_ai_v2/fiche_validator.py:main` (fiche invalidation validator)
- `wave-local-ai-v2-serve` CLI command → `src/wave_local_ai_v2/service.py:main` (read-only results service — see `cli.md`)
- `wave-local-ai-v2-export` CLI command → `src/wave_local_ai_v2/bundle_export.py:main` (the bundle as flat CSV tables — see `cli.md`)
- `wave-local-ai-v2-compare` CLI command → `src/wave_local_ai_v2/comparison.py:main` (paired comparison record — see `cli.md`)
- `wave-local-ai-v2-candidate-gate` CLI command → `src/wave_local_ai_v2/candidate_gate.py:main` (the roster's candidate verification gate — see `cli.md`)
- `wave-local-ai-v2-composition-check` CLI command → `src/wave_local_ai_v2/composition_check.py:main` (the roster's size-class composition rule — see `cli.md`)
- Gap, not fixed here: `pyproject.toml` also declares `wave-local-ai-v2-judge-probe` → `judge_probe.py:main`, which this list has never named.
