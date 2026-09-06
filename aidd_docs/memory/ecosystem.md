# Ecosystem

```mermaid
flowchart LR
  Agent([Agent])
  App([App])
  Browser([Browser])

  GitHub["GitHub · vcs.md"]
  HF["Hugging Face"]
  Llama["llama.cpp server\nlocalhost:8080"]
  Mistral["Mistral API\nbenchmark subject · judge"]
  Google["Google AI API\nbenchmark subject · judge"]
  CC["CodeCarbon\nin-process"]
  Serve["Results service · ours\nSERVICE_HOST:SERVICE_PORT"]

  Agent -- cli --> GitHub
  Agent -- cli --> HF
  App -- http --> Llama
  App -- http --> Mistral
  App -- http --> Google
  App -- in-process --> CC
  Browser -- "http · X-API-Key off loopback" --> Serve
```

`wave-local-ai-v2-serve` is the first process of this project's own that a
second machine can reach: every other edge above is this project acting as a
client of someone else's service. That inversion is why the key is required at
startup rather than configured later, and why the default bind is loopback —
the story that puts a browser in front of it, over TLS, comes after this one.

Google AI Studio (`gemini-3.5-flash-lite`, pinned) is the quality CLI's second
cloud subject, alongside Mistral (`mistral-small-2603`). Its Scope-3
energy/emissions estimate reuses the same `SCOPE3_WH_PER_TOKEN` formula
Mistral's rows already use — no new formula id, per plan.md's Decisions for
`aidd_docs/tasks/2026_09/2026_09_05_google-cloud-subject/plan.md`.

Each cloud provider is both a benchmark subject and a judge, and a judge never
scores output from its own model family: a Mistral judge pointed at a Mistral
subject's output is refused with the collision named, never skipped and never
substituted for another judge. The consequence for a cloud subject is that it
is scored by the other-family judge only — one score, no agreement figure, and
the single-judge flag with its reason on the row. A local model's output is
scored by both judges and carries an agreement figure. One judged item is
therefore one generation plus up to two judge calls, all through the same
pacing/retry layer as the subject batches, all recorded as egress on the row.
