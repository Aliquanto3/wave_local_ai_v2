---
type: spike
status: open
source: aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
parents:
  - aidd_docs/backlog/epics/one-download-holds-the-tables-their-licences-and-how-to-cite-them.md
---

# Spike: May the model outputs in the published rows be redistributed, and on what terms

## Question

For each model and provider whose output the published bundle carries, do that model's licence and that provider's terms permit redistributing its outputs inside a download whose rows are published under CC-BY 4.0, and does any of them restrict republication, require attribution of its own, or forbid use of outputs for benchmarking?

## Decision

How `LICENSE-DATA` and the export state the model-output part of each row: kept in the download under the author's declaration with the terms found named per model and provider, kept with an added condition the terms impose, or removed from the download for a model or provider whose terms forbid it. This is the epic's falsification clause on "whether generated completions may be redistributed under the bundle's terms", which today is an unverified author declaration.

## Bounds

- Evidence needed: the committed bundle's actual output-bearing fields and their producers (today `predicted_label` from `Qwen3.6-35B-A3B` served locally and from `mistral-small-2603` through Mistral's API, read from `aidd_docs/results/quality-reference.jsonl`); for each local roster model, the licence of the weights at the pinned repo revision in `aidd_docs/roster/models.json`, read for any clause on outputs; for each cloud provider (Mistral today, Google AI Studio as the documented second cloud subject), the terms of service in force for the API tier the project uses, read for output ownership, redistribution and benchmark-publication clauses; each text quoted with its URL and retrieval date.
- Stop when: every model and provider that produced an output in the committed bundle has its redistribution position stated from its own terms text, or a term is found that forbids redistribution, which settles the decision for that producer.
