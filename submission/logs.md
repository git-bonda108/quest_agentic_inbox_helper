# Daily logs

One short log per day of the quest, joined from `logs/`. Run-by-run detail is in `evals/README.md`.

---

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

---

# Day 2 log

> Draft written by the AI. Satya: check it against `evals/README.md`, correct
> it, then delete this note.

12 November 2026, UTC. Two sessions. The first ran unattended from 04:00 on a
schedule; I asked for the second. Goal: does the tool hold up on messages its
prompts have never met, and does anything check the checker?

## What shipped

- 44 unseen messages (injection, personal data, mixed intents, other
  languages, abuse, third parties), committed before any model saw them, and
  an 18-message holdout set committed before the fix it tests was run.
- 23 hand-written drafts to test the reviewers: 16 with a planted flaw.
- An independent judge with a written rubric, on a model from another vendor.
- Two fixes from failing checks: a message the platform blocks goes to a
  person, and the classifier answers "must a person handle this?" separately.
- Second session: the tool deployed as a **hosted agent on Microsoft
  Foundry**, with a guardrail policy and tracing. It is shipped without the
  sending code.

## Numbers

| Measure | Target | Result |
|---|---|---|
| Injected instructions obeyed, 12 planted | 0 | 0 in all 13 runs |
| Sensitive message given a draft, before the fix | 0 | 1 in two of three runs |
| Sensitive message given a draft, after the fix | 0 | 0 in nine runs |
| Intent accuracy, unseen set, first honest score | at least 90% | 92.9%, 92.9%, 95.2% |
| Intent accuracy, holdout set, after the fix | at least 90% | 88.9%, 94.4%, 88.9%: **missed twice** |
| Harmless messages sent to a person, unseen set | n/a | 2 of 44 before the fix, 4 after |
| Planted flaws caught: critic; judge | n/a | 16/16; 15/16 |
| Hosted agent, 104 messages, three sets | 0 unsafe | 0 unsafe, 0 failed |
| Time per message through the hosted agent | n/a | median 5.7 to 7.7 s |

What these numbers do not show: nine safe runs is not a guarantee. The unseen
set stopped being unseen once its misses changed a prompt.

## What failed, and what changed

- **One run would have lied to me.** Three runs of identical code gave three
  different answers on safety. I now run everything three times.
- **The fix was to the design, not the wording.** One label had to carry both
  what the person wants and whether a person must handle it.
- **The fix costs reviewer time.** More harmless messages now go to a person.
- **I planned an injection guardrail agent and did not build it.** The platform
  already blocks the blatant cases and nothing that got through was obeyed.
- **The judge was fooled by an injection the tool resisted**, and it missed the
  one draft that really was unsafe. It caught every planted flaw and was wrong
  on real drafts in both directions.
- **The first two Foundry deployments failed.** The zip's files were not
  flagged as regular files and the builder skipped them. Pinned by a test.
- **Tracing was silent for 20 minutes** until Application Insights was
  connected to the Foundry project.
- **Every message was starting its own sandbox.** Reusing one session cut the
  median time per message from 15.5 s to 6.1 s.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 1 (asking for the early start) | ₹409.75 | 11 minutes to the first scored run; 13 minutes to the first reply from the hosted agent |

Cost is what Azure billed for the day: ₹389.81 for models and ₹19.93 for the
hosted agent. Tokens, from Azure's own meters: 1,536,919 in and 126,204 out on
the two OpenAI models, plus the judge.

---

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

---

# Day 4 log

> Draft written by the AI at the end of an unattended run. Satya: check it,
> correct it, then delete this note.

14 November 2026, from 04:00 UTC, started on a schedule. Consolidation only: no
model was called and no result changed.

## What shipped

- The logs for days one and two trimmed to a page each. The brief asks for
  short logs; day two had grown to 180 lines.
- One combined log file for the quest page's single slot.
- `directive.md` v3, with one rule from the testing day.
- `docs/architecture.md`: the design in nine layers, each with its evidence.
- A submission checklist, a Loom script and a draft of the unlearned note.
- The README followed from an empty folder on a fresh clone: it works.

## What failed, and what changed

- **The unlearned note is not finished, and the AI cannot finish it.** It can
  list what the logs show changed. It cannot know how I worked before this
  week. The draft has a gap after every point for my own words.
- **The architecture page does not map to my nine-layer brief.** The AI could
  not re-open the brief in this session and would not guess its layer names,
  so the page uses the tool's own nine layers.
- **No public link.** It needs my approval for a hosting cost and I have not
  given it. The tool still runs from the README with no account.
- **A stocktake found the logs were not keeping a promise in `intent.md`**:
  three build numbers a day, one of them model cost. They are in every log
  now, with the cost Azure actually billed. A new test also ties every number
  on the results page to the file it came from.
- **Four decisions from day two are still open**, and the directive's rule 3
  wording with them.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 0 | None expected; no model was called | Not applicable: consolidation only |

Four days in, Azure has billed ₹716.91 in total for the quest.

## Left for me

Record both videos, fill in the unlearned note, check the four logs and remove
their draft notes, and submit before the timer ends on 16 November.
