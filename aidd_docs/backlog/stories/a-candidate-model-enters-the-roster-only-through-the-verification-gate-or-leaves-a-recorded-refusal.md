---
type: story
status: ready
source: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
parent: aidd_docs/backlog/epics/every-size-class-spans-two-families-or-says-it-does-not.md
depends_on:
  - aidd_docs/backlog/stories/every-roster-entry-states-its-family-its-licence-and-its-language-claim.md
  - aidd_docs/backlog/stories/a-thinking-switch-the-template-ignores-is-refused-never-published-as-disabled.md
order: 4
---

# Story: A candidate model enters the roster only through the verification gate, or leaves a recorded refusal

**As** an academic or technical reviewer reading a size class published as a single-family ladder
**I want** every candidate model to pass a verification gate before it enters the roster, and every candidate that fails it to leave a tracked refusal naming the step and the evidence
**So that** a single-family class reads as searched and found empty rather than not looked at, and no entry reaches a suite run on an assumption about its weights, its architecture, its licence or its thinking control

Maps to: Methodology 13 ("Every roster model has an entry in a versioned roster file pinning its repo revision, file name, quant, checksum, its architecture"); PRD Dependencies "Obtainability of the roster's model weights and of the local inference runtime: each GGUF named by its source repository and revision with a checksum", "Licence terms of each roster model"; epic Boundaries "a verification step per candidate model, as a gate rather than a report", "a recorded refusal for every candidate that does not enter"; epic decisions "Licence policy" (the one refusal), "The thinking control is per entry, declared and verified", "Unsupported architecture: defer by default", "EN/FR/DE capability is a claim, not a measurement"; epic Dependencies "`b10537` may not implement every candidate family's architecture", "Bench cost" (verify cheaply before downloading the next candidate, disk headroom checked before a download).

Needs: a real local model run, only for the evidence: the already-downloaded `qwen3-0.6b-q8` taken through the gate on the dev machine. Every acceptance condition is proved with the hub listing, the download and the server stubbed.

## Acceptance

- A command takes one candidate (repo, file, revision, quant, declared family, declared thinking control) and runs the gate's steps cheapest first, stopping at the first failure:
  1. the revision is a commit sha, never a branch, and the file exists at it;
  2. the licence is read and recorded as order 1's block; a licence forbidding publication of benchmark results refuses the candidate, and any other licence passes with its terms recorded;
  3. free disk under the models directory is checked against the file's size before any download starts;
  4. the file is downloaded at the revision and its sha256 is read off the downloaded bytes in lowercase hex, never copied from a model card, together with its byte size and its total parameter count from the GGUF metadata;
  5. one `llama-server` load under the build the binary reports through `build_probe`; a load failure refuses the candidate naming the GGUF's declared architecture and the build;
  6. the chat template is read from `/props` and the declared thinking control is verified with order 2's with-and-without comparison; a control that changes nothing refuses the candidate unless it is declared `allowed`, and a `none` declaration is checked on one live generation returning no reasoning content;
  7. the EN/FR/DE claim and its source are recorded.
- Every run writes one tracked candidate record beside the roster file: a pass carries every value the roster entry needs; a refusal names the failed step, the evidence (the server's error line, the licence clause, the missing file) and the date. Records are appended, never overwritten, so a candidate refused twice shows both attempts.
- A refused candidate never enters `aidd_docs/roster/models.json`. A passing candidate does not enter it by the gate either: authoring the entry stays a reviewed change, made from the pass record.
- An architecture the pinned build does not load is recorded as deferred, naming the architecture and the build. The gate never offers another build and never changes the pinned one.

## Code it changes

- `src/wave_local_ai_v2/` (new candidate-gate module and command): the seven steps and the record writer, reusing `build_probe`, `server.py`'s launch path, `local_client.chat_template` and order 2's comparison.
- `aidd_docs/roster/` (new candidate record file).
- `docs/setup.md`: how to run the gate before adding an entry.

## Tests it needs

- A new candidate-gate test module (hub, download and server stubbed): each of the seven steps can refuse, and a refusal stops every later step, asserted on the stubs' call counts (no download after a licence refusal, no load after a checksum is missing); a branch revision is refused; a pass record carries every field a roster entry requires; a second run on the same candidate appends.

## Evidence it publishes

- The pass record for `qwen3-0.6b-q8`, its sha256, bytes and template hash matching the shipped entry, committed as the first line of the candidate record.

## Cancellation

n/a: not cancelled.
