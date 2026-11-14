# Day 3 log

> Draft written by the AI at the end of an unattended run. Satya: check it
> against `evals/README.md`, correct it, then delete this note.

13 November 2026, 04:00 to 05:00 UTC, started on a schedule. The goal was
rigorous testing with mock data: happy paths, edge cases, attacks, and
Foundry's own evaluation of the hosted agent.

## What shipped

- 43 edge-case tests on odd inputs, repeated actions and two reviewers at once.
- A browser end-to-end pass of the review desk: 18 checks.
- An edge set (18 awkward but realistic messages) and an attack set (40
  messages: four goals in ten disguises).
- Foundry cloud evaluation of the hosted agent, graded against the rubric by a
  separate model that was first tested on planted flaws.
- A "try a message" form that sends one typed message to the live agent, with
  a daily cap. 156 tests.

## Numbers

| Measure | Result |
|---|---|
| Defects found by edge-case tests, all fixed | 5 |
| Browser checks passed | 18 of 18 |
| Edge set, routed as labelled (local and hosted) | 17 of 18, no unsafe result |
| Attacks obeyed (local and hosted) | 0 of 40 |
| Planted injections obeyed, all sets to date | 0 of 53 |
| Cloud grader on planted drafts | 16 of 16 flaws caught, 7 of 7 sound passed |
| Cloud evaluation, 118 messages across four sets | 105 passed, 3 failed, 10 blocked by the guardrail |

## What failed, and what changed

- **The edge tests found five real defects.** An empty message reached a
  model. A repeated id crashed the batch. A reply that was already sent could
  be approved again, overwritten by a second reviewer, or rejected. Each is
  fixed and pinned by a test.
- **Three drafts failed the cloud grader**, and the critic had passed all
  three: a terse reply to a two-part question, a reschedule rule applied to a
  call already missed, and a greeting that repeats database syntax from the
  name field. None is unsafe. All need a reviewer's edit.
- **Foundry's red-team service does not fit this agent.** It sends free-text
  attacks; the agent refuses anything that is not a candidate message. I ran it
  against the worker model instead and built the 40-message attack set for the
  tool itself. The red-team scorecard can only be read in the Foundry portal,
  so I quote no number from it.
- **The first cloud run left 13 replies ungraded** when the grader hit its
  rate limit. Capacity raised, run repeated.
- **The cloud service refused the Mistral judge**, so the cloud grader is an
  OpenAI model: separate from the critic's, same vendor.
- **One edge message meant to sit under the length limit was over it.** Caught
  from the generator's own printout before any run.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 0 | ₹280.63 | 4 minutes to the first failing edge tests fixed; 57 minutes to the last result |

Cost is what Azure had billed for the day when I checked on 14 November, and
can still rise: ₹201.39 for models and ₹79.24 for the hosted agent. Tokens:
987,040 in and 82,890 out across three models, one of them the new cloud
grader.

## Waiting on me

- Approval to put the desk on a public link: a small hosting cost and two new
  network addresses for the build session.
- Four open decisions from day two: questions outside the intent list, reply
  language, how much over-escalation is acceptable, and directive rule 3.
