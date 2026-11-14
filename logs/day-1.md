# Day 1 log

11 November 2026, UTC. I worked through Claude Code in a cloud session; it wrote
the code and ran the commands, and I directed and approved. Goal: a working
core on day one. Detail and every run: `evals/README.md`.

## What shipped

- `intent.md` and `directive.md` v1, written before any code.
- A fictional hiring policy and 42 synthetic candidate messages, with labels in
  a separate file so they cannot leak into a prompt.
- The send gate: nothing reaches the outbox without a reviewer's approval of
  the exact text. Tests written first and seen failing.
- Three agents on the OpenAI Agents SDK, on Microsoft Foundry models reached by
  identity, with no keys: a classifier, a drafter and a critic.
- Offline replay of recorded model outputs, labelled as recorded, so anyone can
  run the tool with no account.
- The review desk, checked in a real browser. A README and CI.

## Numbers

First full live run, 07:42: `uv run inbox-helper eval --live --record`.

| Measure | Target | Result |
|---|---|---|
| Intent accuracy, 42 messages | at least 90% | 41/42 = 97.6% |
| Routed to the right action | n/a | 42/42 |
| `escalate` messages given a draft | 0 | 0 |
| Longest draft | 90 words or fewer | 44 words |
| Model calls; tokens in / out | n/a | 106; 80,985 / 7,621 |
| Call latency | n/a | median 2.35 s, p95 4.78 s |

What these numbers do not show: the prompts were written with these 42
messages in view, so this is a development score. The critic approved all 32
drafts, and a critic that has never rejected anything is unproven.

## What failed, and what changed

- **My plan was two days.** The AI pushed back: the brief asks for a log for
  each of five days. I changed the plan to a working core on day one and one
  harder thing each day.
- **I wanted every platform feature in.** The AI argued that a tool with no
  external tools needs no toolbox. A feature now goes in only when a
  requirement or a failing check calls for it.
- **Device-code sign-in was refused** by my Azure tenant. Rather than weaken
  the tenant, we used a certificate identity limited to one resource group.
- **The Azure CLI installed as a 2019 version.** Caught by checking the version
  instead of assuming.
- **A test call looked like eight failures in a row.** The models were fine;
  the AI's own response parser crashed on a `null` and it retried for four
  minutes before reading the error.
- **I could not open the review desk.** The AI ran it in its cloud session and
  gave me an address that only works on the machine running the tool. The
  README now starts from an empty terminal on my own computer.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 4 | ₹26.53 | 47 minutes (06:58 to 07:45) |

Cost is what Azure billed for the day. Almost all of it was the one 42-message
run, so roughly ₹0.60 a message.
