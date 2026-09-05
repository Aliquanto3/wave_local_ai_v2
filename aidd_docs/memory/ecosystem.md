# Ecosystem

```mermaid
flowchart LR
  Agent([Agent])
  App([App])

  GitHub["GitHub · vcs.md"]
  HF["Hugging Face"]
  Llama["llama.cpp server\nlocalhost:8080"]
  Mistral["Mistral API\nbenchmark subject · judge"]
  Google["Google AI API\nbenchmark subject · judge"]
  CC["CodeCarbon\nin-process"]

  Agent -- cli --> GitHub
  Agent -- cli --> HF
  App -- http --> Llama
  App -- http --> Mistral
  App -- http --> Google
  App -- in-process --> CC
```

Google AI Studio (`gemini-3.5-flash-lite`, pinned) is the quality CLI's second
cloud subject, alongside Mistral (`mistral-small-2603`). Its Scope-3
energy/emissions estimate reuses the same `SCOPE3_WH_PER_TOKEN` formula
Mistral's rows already use — no new formula id, per plan.md's Decisions for
`aidd_docs/tasks/2026_09/2026_09_05_google-cloud-subject/plan.md`.
