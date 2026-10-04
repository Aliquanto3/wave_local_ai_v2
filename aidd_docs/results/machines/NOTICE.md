# Licence notice

The per-machine tracked results in this directory (`<machine_id>/runtime.jsonl`,
`quality.jsonl`, `refusals.jsonl`), from which the published bundle is derived, are
licensed under the Creative Commons Attribution 4.0 International licence (CC-BY 4.0),
except the model-output fields the rows carry. The repository's code is MIT.

Not covered by CC-BY 4.0 here: the item fields of a row whose item is drawn from a public
benchmark, which carry that benchmark's licence (`item_licence`, `item_source`,
`item_source_revision`), named in `LICENSE-DATA` section 2:

- rows citing `classification-banking-intents-minds14` carry MInDS-14 items
  (`PolyAI/minds14`) under CC BY 4.0, with the attribution `LICENSE-DATA` section 2.1
  states;
- rows citing `translation-mixed-domain-wmt24pp` carry WMT24++ items (`google/wmt24pp`)
  under the Apache License, Version 2.0, whose text is `LICENSE-APACHE-2.0.txt` in this
  directory; each segment's source text is wrapped in the suite's prompt template and the
  reference (`reference_output`) is unchanged (`LICENSE-DATA` section 2.2).

Exactly what is covered, what is not, and why: `LICENSE-DATA` at the repository root
(https://github.com/Aliquanto3/wave_local_ai_v2/blob/main/LICENSE-DATA).
