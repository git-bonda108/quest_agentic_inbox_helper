# Day 5 log

15 November 2026, from 04:00 UTC. A cold run and the hand-in. No code, prompt
or result changed today.

## What shipped

- The cold run that `intent.md` planned for the last day: a fresh clone,
  the README followed from an empty folder, the tests, and the review desk.
- Every message set replayed once more from its recorded run.
- This log, and the combined log file with all five days.

## Numbers

| Measure | Result |
|---|---|
| Fresh clone: tests | 168 passed |
| Fresh clone: review desk | Started and answered on the first try |
| Five message sets replayed, 162 messages | No unsafe result, no failures |
| Lint, format and type checks | Clean |

## Five days, in one table

| Day | The harder thing | The number that proved it |
|---|---|---|
| 1 | A working core, with a send gate | 41 of 42 intents right; nothing sent without approval |
| 2 | Messages the prompts had never met, then hosting on Foundry | A safety gap found over three runs and closed; 104 messages through the hosted agent, none unsafe |
| 3 | Edge cases, attacks and Foundry's own grader | 5 defects fixed; 0 of 40 attacks obeyed; 105 of 108 graded replies passed |
| 4 | Drawing the tool on nine layers | One untested layer found and covered |
| 5 | A cold run from a fresh clone | Works from the README alone |

## What failed, and what changed

- **Azure's cost service refused my query today** with "too many requests",
  four times over ten minutes. The last figure it gave me, on 14 November,
  stands: ₹716.91 billed for the quest.
- **Three targets from day one were not fully met**, and they stay on the
  results page as misses: intent accuracy on the holdout set dipped to 88.9%
  in two of five runs, three drafts needed a reviewer's edit, and replies to
  non-English messages come back in that language.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 0 | None: no model was called | Clone to a running desk in one pass; I did not time it |
