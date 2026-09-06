---
type: story
status: ready
source: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
parent: aidd_docs/backlog/epics/the-pitch-runs-from-a-browser-and-only-with-the-key.md
depends_on:
  - aidd_docs/backlog/stories/dense-and-moe-stand-side-by-side-on-the-same-items.md
  - aidd_docs/backlog/stories/the-demo-address-serves-over-tls-and-refuses-a-keyless-request.md
order: 6
---

# Story: The second laptop walks the pitch, and the walk is recorded

**As** a consultant about to run this in front of a client
**I want** the whole pitch walked once for real from a second machine, with the five checks that can fail actually failed and passed, and short recordings a reviewer can watch
**So that** the first time this happens in front of a client is not the first time it happens

## Acceptance

- The epic's success walk, done once for real: the service started on the bench machine bound to its LAN address over TLS, opened from a second laptop, the key entered once, and the comparison taken end to end without a terminal.
- The five checks, each performed from the second machine and each shown failing before it is shown passing:
  - a request without a key, and one with a wrong key, is refused — from that machine, not from a test client;
  - the service refuses to start with no key in the environment, and the key's value appears in no log line and no tracked file — verified by searching the run's output;
  - a row without all three energy channel labels yields no headline energy figure anywhere — verified by handing the service such a row and watching the figure be withheld and its absence stated;
  - a judged score carrying neither an agreement figure nor the single-judge flag is never rendered as a plain score — verified the same way, by removing the field and watching the surface refuse;
  - quality and runtime never arrive together — verified by there being no endpoint that returns both.
- PRD AC "the documented setup steps produce a working benchmark run without undocumented manual fixes": `docs/demo.md` is the path that was actually walked, including trusting the certificate on the second machine **before** the pitch, so the trust decision is never made in front of a client. Any step taken during the walk that the document did not name is added to it.
- `aidd-dev:11-browser-qa` produces short named videos: the locked happy path (open, key once, runs list, quality, runtime with fiche, energy headline and its drill-down, dense versus MoE), plus the sourced edge cases — keyless, wrong key, withheld energy headline, absent judged score.
- No number shown in the walk was produced for the walk. Every figure comes from a row already written by a CLI, and the walk writes no row: the service has no writer, and this story adds none.
- The epic's post-`done` record is filled in with what the walk actually produced: what a viewer asked to see that the dashboard did not show, whether a certificate warning appeared in front of anyone, and whether the declared-absent contract had to be relaxed to make the pitch presentable. A relaxation, if it happened, is recorded as a finding against this epic rather than quietly applied.

## Code it changes

- `docs/demo.md` — corrected to the path actually walked.
- `aidd_docs/results/README.md` — a dated section recording the walk, the rows it showed and the withholdings it demonstrated, in the same form as the increments already recorded there.
- Whatever the walk proves wrong. A step the document missed, a refusal that read badly on the second machine, a number that was unreadable at distance: found here, fixed here, and named in the record.

## Tests it needs

- None new. This story's proof is a walk, not an assertion, and the code paths it exercises are covered by orders 1 to 5. What it adds to the suite is only whatever regression the walk uncovers — and if it uncovers none, that is stated rather than filled with a test written to have written one.
- The existing suite stays green on both operating systems in CI, front-end job included, on the branch the walk is taken from.

## Evidence it publishes

- The browser QA videos, named per path, filed with the delivery task.
- The walk's record in `aidd_docs/results/README.md`, and the epic's Success Evidence block completed with the three questions it reserves for `done`.

## Cancellation

n/a — not cancelled.
