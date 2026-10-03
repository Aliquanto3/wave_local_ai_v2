# Phase 2: Request path, row fields (schema "28"), gate, comparison

## Steps

1. `local_client.complete_chat(..., constraint_body=...)` merged into the request; `quality_cli` resolves the per-family constraint once, maps it through the engine's request field, refuses a missing mechanism or an enabled cloud provider, and passes it to each item's call.
2. `row_contract.py`: `SCHEMA_VERSION = "28"`, `CONSTRAINT_FIELDS` required on quality rows from "28", gate checks them against `prompt_variants.constraint_for`.
3. `quality_cli._score_and_write` writes both fields; `comparison.py` puts them on the `prompt_variant` dimension; `bundle_export.py` documents them.
4. Tests: grammar sent only under the variant and only for declared families; hash on the row; gate refusals; invariance; a grammar-admitted but unscorable output scores 0 with its reason; comparison differing set.
