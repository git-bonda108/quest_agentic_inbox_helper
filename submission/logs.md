# Daily logs

One short log per day of the quest, joined from `logs/`. Run-by-run detail is in `evals/README.md`.

---

# Day 1 log

11 November 2026, UTC. I worked AI-first, with a coding agent in a cloud
session: I set the intent, the rules and the checks, and it wrote the code and
ran the commands. Goal: a working core on day one. Detail and every run:
`evals/README.md`.

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

- **My plan was two days.** The brief asks for a log for each of five days,
  and the quest is called "Raise the Load". I changed the plan to a working
  core on day one and one harder thing each day.
- **I wanted every platform feature in.** A tool that calls no external
  system needs no toolbox, so I cut it. A feature now goes in only when a
  requirement or a failing check calls for it.
- **Device-code sign-in was refused** by my Azure tenant. Rather than weaken
  the tenant, I used a certificate identity limited to one resource group.
- **The Azure CLI installed as a 2019 version.** Caught by checking the version
  instead of assuming.
- **A test call looked like eight failures in a row.** The models were fine;
  a response parser in the build crashed on a `null`, and four minutes went
  on retries before the error itself was read.
- **I could not open the review desk.** It was running in the cloud build
  session, and its address only works on the machine running the tool. The
  README now starts from an empty terminal on any computer.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 4 | ₹26.53 | 47 minutes (06:58 to 07:45) |

Cost is what Azure billed for the day. Almost all of it was the one 42-message
run, so roughly ₹0.60 a message.

---

# Day 2 log

12 November 2026, UTC. Two sessions: the first from 04:00 on a schedule I had
set the evening before, the second from 06:42. Goal: does the tool hold up on messages its
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
  different answers on safety. I now run every message set at least three times.
- **The fix was to the design, not the wording.** One label had to carry both
  what the person wants and whether a person must handle it.
- **The fix costs reviewer time.** More harmless messages now go to a person.
- **I planned an injection guardrail agent and did not build it.** The platform
  already blocks the blatant cases and nothing that got through was obeyed.
- **The judge was fooled by an injection the tool resisted**, and it missed the
  one draft that really was unsafe. It caught all 15 planted flaws and was still wrong
  on real drafts in both directions.
- **The first two Foundry deployments failed.** The zip's files were not
  flagged as regular files and Foundry's build step skipped them. Pinned by a test.
- **Tracing was silent for 20 minutes** until Application Insights was
  connected to the Foundry project.
- **Every message was starting its own sandbox.** Reusing one session cut the
  median time per message from 15.5 s to 6.1 s.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 1 (starting the Foundry work a day early) | ₹409.75 | 11 minutes to the first scored run; 13 minutes to the first reply from the hosted agent |

Cost is what Azure billed for the day: ₹389.81 for models and ₹19.93 for the
hosted agent. Tokens, from Azure's own meters: 1,536,919 in and 126,204 out on
the two OpenAI models, plus the judge.

---

# Day 3 log

13 November 2026, 04:00 to 05:00 UTC, on a schedule. The goal was
testing with mock data: happy paths, edge cases, attacks, and
Foundry's own evaluation of the hosted agent.

## What shipped

- 34 edge-case tests on odd inputs, repeated actions and two reviewers at once,
  written first; nine more followed for the new limits and the live form.
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

---

# Day 4 log

14 November 2026, UTC. Two sessions: consolidation from 04:00, then a full
stocktake against the brief in the afternoon. No prompt changed and no earlier
result changed.

## What shipped

- The logs for days one and two trimmed to a page each, and one combined file
  for the quest page's single log slot.
- `directive.md` v3, with one rule from the testing day.
- `docs/architecture.md`: the tool drawn on the nine-layer model I design
  against, with the test that proves each layer and each boundary.
- Contract tests on what reaches a model and on what an agent may hand back.
- A scorecard at the top of `evals/README.md`: where each target in
  `intent.md` stands.
- The one-page unlearned note, both video scripts and a submission checklist.

## Numbers

| Measure | Result |
|---|---|
| Tests in CI | 168 |
| Five message sets replayed, 162 messages | No unsafe result, no failures |
| Live run through the hosted agent, 18 messages | 17 of 18 as labelled, no unsafe result |
| Browser pass of the review desk | 18 of 18 |
| README followed on a fresh clone | Works |
| Deployed agent's zip against the repository | Same SHA-256 |

## What failed, and what changed

- **The logs were not keeping a promise in `intent.md`**: three build numbers a
  day, one of them model cost. They are in every log now, with the cost Azure
  actually billed.
- **Drawing the tool on the nine layers showed a gap.** The context layer had
  no test of its own: nothing checked directly what reaches a model. Nine
  contract tests now do, including that the candidate's address never does.
- **Numbers in a document can drift from the runs.** A test now ties every row
  on the results page to the result file it cites.
- **The public link planned for today was replaced** on day three by a day of
  testing. The tool runs from the README with no account.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 1 (calling the stocktake) | Small and not yet billed: one 18-message live run | Not applicable: consolidation and validation |

Four days in, Azure has billed ₹716.91 in total for the quest.

---

# Day 5 log

15 November 2026, UTC. A cold run, the hand-in, and the public link. No prompt
and no earlier result changed today.

## What shipped

- The cold run that `intent.md` planned for the last day: a fresh clone,
  the README followed from an empty folder, the tests, and the review desk.
- Every message set replayed once more from its recorded run.
- This log, and the combined log file with all five days.
- The public link: the review desk on Azure App Service, with the "Try a
  message" form wired to the agent on Foundry. Steps in `hosting/webapp.md`.
- A bolder, clearer desk: a colour for each group, counts at the top, DM Sans
  and Montserrat served by the app itself. No password: the data is
  synthetic, so the desk asks only for the reviewer's name.
- How it works, on the live site: a diagram above the groups showing the
  agents, their models, the code that decides, what Foundry provides and where
  the person sits; and an 86-second animated explainer at `/explainer`, with an
  MP4. Nothing in it is typed by hand. Nine messages are replayed from the
  recorded runs, and a test rebuilds the explainer from the recordings, then
  approves and sends the featured reply through the real send gate and checks
  the audit lines on screen against the ones the store writes.

## Numbers

| Measure | Result |
|---|---|
| Fresh clone: tests | 168 passed |
| Fresh clone: review desk | Started and answered on the first try |
| Five message sets replayed, 162 messages | No unsafe result, no failures |
| Lint, format and type checks | Clean |
| Browser pass on the live site | 18 of 18 |
| A typed message on the live site | Classified live by the hosted agent; the complaint inside it went to a person |

## Five days, in one table

| Day | The harder thing | The number that proved it |
|---|---|---|
| 1 | A working core, with a send gate | 41 of 42 intents right; nothing sent without approval |
| 2 | Messages the prompts had never met, then hosting on Foundry | A safety gap found over three runs and closed; 104 messages through the hosted agent, none unsafe |
| 3 | Edge cases, attacks and Foundry's own grader | 5 defects fixed; 0 of 40 attacks obeyed; 105 of 108 graded replies passed |
| 4 | Drawing the tool on nine layers | One untested layer found and covered |
| 5 | A cold run, then a public link | Works from the README alone; the live site passes the same 18 browser checks |

## What failed, and what changed

- **Azure's cost service refused my query today** with "too many requests",
  four times over ten minutes. The last figure it gave me, on 14 November,
  stands: ₹716.91 billed for the quest.
- **The public link took three regions.** The subscription had no App
  Service quota in East US 2 or Central US, and it already holds the maximum
  of five Container Apps environments. West US 3 had quota.
- **The first live message was lost** in the seconds while App Service
  swapped in the new container; the desk keeps its state in memory. I
  restarted the app so reviewers start from a clean desk.
- **One target from day one was missed**, and it stays on the results page:
  intent accuracy of at least 90%. It fell to 88.9% on the holdout set in two
  of six runs, and to 85% on the attack set, where six messages the platform
  blocked had been labelled for a draft. Every miss sent a message to a
  person, never the other way. Two weaknesses outside the targets stay listed
  too: three drafts that need a reviewer's edit, and replies to non-English
  messages, which come back in that language.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 4 (approving the public link and its network access, asking for a bolder design without a password, then asking for the diagram and the explainer) | Two live messages, plus the App Service plan, billed by the hour until I delete it after the review | Clone to a running desk in one pass; deploy to a working live site in about 15 minutes |
