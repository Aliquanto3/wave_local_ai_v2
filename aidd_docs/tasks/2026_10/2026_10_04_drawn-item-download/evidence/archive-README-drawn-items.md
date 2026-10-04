## Drawn items and their terms

Repeated from `LICENSE-DATA` section 2, as written there:

An item drawn from a public benchmark is not covered by CC-BY 4.0 through
this file. It carries its source's licence, recorded per item in its
`licence`, `source` and `source_revision` fields, and on every row that
publishes it in `item_licence`, `item_source` and `item_source_revision`.
Each drawn source is named below with its terms, the rung its licence puts
it on (permissive, share-alike or no-redistribution), what that rung does to
its items and rows, and the attribution it requires.

What each rung does to a source's items and to the rows carrying them:

- Permissive: the items and their rows ship unchanged beside the
  hand-written ones, in the same files, under their source's licence and
  with the notices that licence requires on redistribution.
- Share-alike: the items and their rows ship apart, under their source's
  licence. In the published results directory, the suite-definition
  snapshots of a source under licence <licence id> sit in
  `share-alike/<licence id>/suite-definitions/`, its rows in
  `share-alike/<licence id>/quality-reference.jsonl`, and that licence's
  full text in `share-alike/<licence id>/LICENSE`, none of them in the
  CC-BY 4.0 `suite-definitions/` or `quality-reference.jsonl`. The exported
  quality table names that licence file on each such row, in
  `item_licence_file`.
- No redistribution: the items' text is published nowhere. Each row
  carrying such an item records its item text fields (`prompt`,
  `prompt_before_template`, `expected_label`, `reference_output`) as null
  and carries `item_redaction` `no_redistribution`, `item_content_hash`,
  `item_source`, `item_source_revision` and `item_source_key`; its
  suite-definition snapshot keeps the item's `item_id`, `language`,
  `licence`, `source`, `source_revision`, `content_hash` and `source_key`
  and drops its text. A reader obtains the text from the source, under its
  terms, and joins it to the rows by `item_source_key`; such a row's score
  cannot be recomputed from the published data alone. No script or other
  code that downloads a source's corpus ships with the data.

Every drawn item carries a content hash (`content_hash` on the item,
`item_content_hash` in the exported quality table), with which a reader
proves that a source row they fetched is the one that was scored. It is
the SHA-256 hex digest of the UTF-8 bytes of the JSON object with keys
`licence`, `source`, `source_revision` and `text`, serialised with sorted
keys, separators `,` and `:` and non-ASCII characters written as
themselves. `licence`, `source` and `source_revision` are the source's as
the suite's selection rule records them (`selection_rule.benchmarks`);
`text` lists, in the rule's `content_fields` order, each of those fields
of the source row, NFC-normalised with every whitespace run collapsed to
one space and leading and trailing whitespace dropped. It hashes the source
row as the suite's loader wrote it, not the prompt the model was sent.

### 2.1 MInDS-14

- Source: `PolyAI/minds14` on the Hugging Face Hub, at revision
  `40ce77cb32a384e4d50a568e1ec39ac804019d33`
  (https://huggingface.co/datasets/PolyAI/minds14/tree/40ce77cb32a384e4d50a568e1ec39ac804019d33),
  configs `en-US`, `fr-FR` and `de-DE`.
- Creator: PolyAI (Gerz, Su, Kusztos, Mondal, Lis, Singhal, Mrksic, Wen and
  Vulic, "Multilingual and Cross-Lingual Intent Detection from Spoken Data",
  2021, https://arxiv.org/abs/2104.08524).
- Copyright notice: the dataset card states none; the work is attributed to
  its creator.
- Licence: Creative Commons Attribution 4.0 International (CC BY 4.0),
  https://creativecommons.org/licenses/by/4.0/. The dataset card at the
  pinned revision is the licence of record (`license: cc-by-4.0`, and
  "All datasets are licensed under the Creative Commons license (CC-BY)"):
  the revision ships no licence file, and the original `MInDS-14.zip`
  release was not fetched. A licence file at that revision naming anything
  other than CC BY 4.0 would reopen the licence decision.
- Rung: permissive. The drawn items and the rows carrying them ship
  unchanged inside this repository and its bundle, with no segregation and
  no redaction.
- What is drawn: 300 utterance transcriptions and their intent labels, 100
  per language, published as the suite
  `classification-banking-intents-minds14` in
  `src/wave_local_ai_v2/suite_data/` and
  `aidd_docs/results/suite-definitions/`, and in the item fields (`item_id`,
  `prompt`, `expected_label`) of the rows citing that suite.
- Changes made: each transcription is wrapped in a prompt template, an
  instruction naming the fourteen intents; each intent is mapped from its
  class index to its name. The transcriptions are otherwise verbatim.
- Attribution, as CC BY 4.0 Section 3(a) requires: "MInDS-14 by PolyAI
  (https://huggingface.co/datasets/PolyAI/minds14, revision
  40ce77cb32a384e4d50a568e1ec39ac804019d33), licensed under CC BY 4.0
  (https://creativecommons.org/licenses/by/4.0/); each item wrapped in a
  prompt template."

### 2.2 WMT24++

- Source: `google/wmt24pp` on the Hugging Face Hub, at revision
  `fd7405c06494bc66a57b25f55d217a72f96e60dc`
  (https://huggingface.co/datasets/google/wmt24pp/tree/fd7405c06494bc66a57b25f55d217a72f96e60dc),
  pair files `en-fr_FR.jsonl` and `en-de_DE.jsonl`.
- Creator: Google (Deutsch et al., "WMT24++: Expanding the Language
  Coverage of WMT24 to 55 Languages & Dialects", 2025,
  https://arxiv.org/abs/2502.12404, as the dataset card cites it). The
  English sources are the WMT24 general test set's (see section 3,
  declaration 3).
- Copyright notice: the dataset card states none; the work is attributed to
  its creator.
- Licence: Apache License, Version 2.0 (Apache-2.0),
  https://www.apache.org/licenses/LICENSE-2.0. The dataset card at the
  pinned revision is the licence of record (`license: apache-2.0`): the
  revision ships no licence or NOTICE file. A copy of the Apache-2.0 text,
  `LICENSE-APACHE-2.0.txt`, ships in each directory holding drawn WMT24++
  items: `src/wave_local_ai_v2/suite_data/`,
  `aidd_docs/results/suite-definitions/`, `aidd_docs/results/` and
  `aidd_docs/results/machines/`. A licence
  file at that revision naming anything other than Apache-2.0 would reopen
  the licence decision.
- Rung: permissive. The drawn items and the rows carrying them ship
  unchanged inside this repository and its bundle, with no segregation and
  no redaction.
- What is drawn: 300 segments, 100 per direction (English to French,
  French to German, German to English), each with its reference
  translation, published as the suite `translation-mixed-domain-wmt24pp` in
  `src/wave_local_ai_v2/suite_data/` and
  `aidd_docs/results/suite-definitions/`, and in the item fields (`item_id`,
  `prompt`, `reference_output`) of the rows citing that suite. The French
  and German source texts are themselves translations from English.
- Changes made, as Apache-2.0 Section 4(b) requires: each segment's source
  text is wrapped in the suite's prompt template, an instruction naming the
  source and target languages; the reference is unchanged. The two pair
  files are joined on `segment_id`, segments marked `is_bad_source` are
  dropped, and each segment is assigned to one direction
  (`scripts/wmt24pp_suite.py`).
- Attribution: "WMT24++ by Google
  (https://huggingface.co/datasets/google/wmt24pp, revision
  fd7405c06494bc66a57b25f55d217a72f96e60dc), licensed under the Apache
  License, Version 2.0; each source text wrapped in a prompt template, the
  references unchanged."

