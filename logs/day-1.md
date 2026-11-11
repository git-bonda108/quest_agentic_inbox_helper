# Day 1 log

Times are UTC on 11 November 2026. I worked through Claude Code in a cloud
session; it wrote the code and ran the commands, and I directed and approved.

## What shipped

- `intent.md` and `directive.md` v1, written before any code.
- A fictional hiring policy and 42 synthetic candidate messages, with labels
  kept in a separate file so they cannot leak into a prompt.
- The send gate: nothing reaches the outbox without a reviewer's approval of
  the exact text. Tests were written first and seen failing.
- Routing, deterministic draft checks and the pipeline, tested with a scripted
  team so they need no model.
- A Foundry project with two model deployments, reached by identity. No keys.
- Three agents on the OpenAI Agents SDK: classifier and drafter on
  `gpt-5.6-luna`, critic on `gpt-5.5`.
- Offline replay of recorded model outputs, and an evaluation gate on it.

Not built yet: the review desk a person uses to approve drafts.

## Numbers

Command: `uv run inbox-helper eval --live --record` (first full live run, 07:42).

| Measure | Target | Result |
|---|---|---|
| Intent accuracy, 42 messages | at least 90% | 41/42 = 97.6% |
| Routed to the right action | n/a | 42/42 |
| `escalate` messages given a draft | 0 | 0 |
| Longest draft | 90 words or fewer | 44 words |
| Messages that failed to process | 0 | 0 |
| Model calls | n/a | 106 |
| Tokens in / out | n/a | 80,985 / 7,621 |
| Call latency | n/a | median 2.35 s, p95 4.78 s |

The one miss is `m008`: a candidate checking that a take-home arrived. I
labelled it `status_check`; the classifier said `assessment_issue`. I left the
prompt alone. Tuning it to this message would make the score look better on
the same 42 messages it was tuned on, and prove nothing.

What these numbers do not show:

- The prompts were written with this message set in mind. It is a development
  set. An honest score needs messages the prompts have never met. That is day 2.
- The critic approved all 32 drafts. A critic that has never rejected anything
  is unproven. Day 2 plants bad drafts to see whether it catches them.
- Cost is reported in tokens. I have not looked up prices, so I state no
  dollar figure.

## The build itself

- First tool call 06:58, first scored live run 07:42.
- Times I had to act for the build to move: 4. One approval of a cloud
  environment, one sign-in attempt, and two rounds of commands in Azure Cloud
  Shell.

## What failed, and what changed

- **My plan was two days.** The AI pushed back: the brief asks for a log for
  each of five days, and the quest is called "Raise the Load". I changed the
  plan to ship a working core on day one and add one harder thing each day.
- **I wanted every platform feature in.** The AI argued that a tool with no
  external tools does not need a toolbox, and that the brief says "small". We
  cut scope. A feature now goes in only when a requirement or a failing check
  calls for it.
- **Device-code sign-in was refused.** My Azure tenant blocks it by default
  (error AADSTS530035). Rather than weaken the tenant, we switched to a
  certificate identity limited to one resource group. The private key never
  left the build session.
- **My first Cloud Shell run failed** with "Incorrect padding". I had skipped
  the step that saved the certificate file, and the instructions gave me no
  way to notice. The AI reissued one command with the certificate inline.
- **The Azure CLI installed as a 2019 version** (2.0.67 instead of 2.92.0)
  because the package installer silently refused pre-release dependencies.
  Caught by checking the version instead of assuming.
- **A test call looked like eight failures in a row.** The models were fine.
  The AI's own response parser crashed on a `null` field, and it retried for
  four minutes before reading the error properly.
- **The first live run crashed** on a missing `aiohttp` package that the Azure
  identity library needs for async use. Added and pinned.
- **Repository settings are locked** from the build session, so I set the
  repository description by hand.
