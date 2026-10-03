# Phase 1: Registry entry, engine mechanisms, campaign refusal

## Steps

1. `prompt_variants.py`: `CONSTRAINED_OUTPUT_ID`, transformation `constrain_output` (identity unless the family's `instruction` is set, then appended), `output_formats` validated at load (every `applies_to` family declares one, each with a `constraint` `{mechanism, grammar}`), `Constraint` dataclass and `constraint_for(variant, family)`, `grammar_hash`. Register v1 with its hash.
2. `engines.py` + `aidd_docs/roster/engines.json`: required `constraint_mechanisms` (`gbnf` -> `{"request_field": "grammar", "read_from": ...}`), parsed into `EngineEntry.constraint_mechanisms`.
3. `campaigns.py`: refuse at load a declared variant whose constraint mechanisms an engine of the campaign does not declare.
4. Tests: `test_prompt_variants.py`, `test_engines.py`, `test_campaigns.py`.
