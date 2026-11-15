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
| 2 (approving the public link and its network access) | Two live messages, plus the App Service plan, billed by the hour until I delete it after the review | Clone to a running desk in one pass; deploy to a working live site in about 15 minutes |
