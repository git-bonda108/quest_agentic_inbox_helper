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
- **The public link planned for today was replaced** on day three by rigorous
  testing. The tool runs from the README with no account.

## Build numbers

| Times I stepped in | Model cost for the day | First prompt to a working version |
|---|---|---|
| 1 (calling the stocktake) | Small and not yet billed: one 18-message live run | Not applicable: consolidation and validation |

Four days in, Azure has billed ₹716.91 in total for the quest.
