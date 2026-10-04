# Licence notice

The data files in this directory, the reference bundle's `*-reference.jsonl` rows, the
client-session record `client-sessions.jsonl` and any record a project command publishes
here, are licensed under the Creative Commons Attribution 4.0 International licence
(CC-BY 4.0). The repository's code is MIT.

Not covered by CC-BY 4.0 here:

- the untracked per-machine `runtime.jsonl` and `quality.jsonl`, which are not published;
- the model-output fields the rows carry (`predicted_label` today), redistributed on the
  author's declaration that this is permitted, unverified against each model's and
  provider's terms;
- the item fields of a row whose item is drawn from a public benchmark, which carry that
  benchmark's licence (`item_licence`), named in `LICENSE-DATA` section 2. Rows citing
  `translation-mixed-domain-wmt24pp` carry WMT24++ items under the Apache License, Version
  2.0, whose text is `LICENSE-APACHE-2.0.txt` in this directory; each segment's source text
  is wrapped in the suite's prompt template and the reference (`reference_output`) is
  unchanged.

Exactly what is covered, what is not, and why: `LICENSE-DATA` at the repository root
(https://github.com/Aliquanto3/wave_local_ai_v2/blob/main/LICENSE-DATA).
