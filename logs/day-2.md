# Day 2 log

> Draft written by the AI at the end of an unattended run. Satya: check it
> against `evals/README.md`, correct anything that is not how you would say it,
> then delete this note.

Times are UTC on 12 November 2026. The day's work started at 04:00 on a
schedule I had the AI set the evening before, and ran without me until 04:50.
The goal for the day was proof: does the tool hold up on messages its prompts
have never met, and does anything check the checker?

## What shipped

- An unseen set of 44 messages in eight categories: plain, prompt injection,
  personal data, mixed intents, out of taxonomy, other languages, abuse and
  third parties. Committed at 04:06, before any model saw it.
- 23 hand-written drafts to test the reviewers: 16 with one planted flaw each
  and 7 sound controls. All pass the code checks on purpose.
- Scoring that separates an unsafe miss (a sensitive message drafted or
  dropped, an injection obeyed) from a safe one (a person gets a message the
  tool could have handled).
- An independent judge with a written rubric, on a model from a different
  vendor (Mistral) than the drafter and the critic.
- Two fixes, each from a failing check: platform-blocked messages now go to a
  person, and the classifier now answers "must a person handle this?" as a
  separate question.
- A holdout set of 18 boundary messages, committed at 04:23 before the second
  fix was run on anything.
- 92 tests, up from 48. Directive v2.

## Numbers

Every row comes from a file in `evals/results/`. The full table, with the
command for each run, is in `evals/README.md`.

| Measure | Target | Result |
|---|---|---|
| Injected instructions obeyed, 12 planted | 0 | 0 in all 13 runs |
| Sensitive messages given a draft, before the fix | 0 | 1 in two of three unseen runs |
| Sensitive messages given a draft, after the fix | 0 | 0 in nine runs across three sets |
| Intent accuracy, unseen set, first honest score | at least 90% | 92.9%, 92.9%, 95.2% |
| Intent accuracy, unseen set, after the fix | at least 90% | 90.5% in three runs |
| Intent accuracy, holdout set, after the fix | at least 90% | 88.9%, 94.4%, 88.9%: **missed twice** |
| Intent accuracy, day-one set, after the fix | at least 90% | 97.6%, 100% |
| Harmless messages sent to a person, unseen set | n/a | 2 of 44 before the fix, 4 of 44 after |
| Planted flaws caught by the critic | n/a | 15/15, then 16/16 |
| Planted flaws caught by the judge | n/a | 15/15, then 15/16 |
| Judge flags on 60 real final drafts | n/a | 4 raised, 0 upheld on reading |
| Longest draft, any run | 90 words or fewer | 47 words |
| Tokens per message, in / out | n/a | about 1,800 / 136 (unseen) |

What these numbers do not show:

- "Upheld on reading" is the AI's reading of the drafts. I have not yet read
  them myself. Until I do, "no draft states an unsupported fact" is unproven.
- The unseen set stopped being unseen at run 5, when its misses changed a
  prompt. Only the holdout numbers are clean after that, and the holdout set
  is 18 messages.
- Nine safe runs is nine safe runs. The same system could draft a sensitive
  message on the tenth.
- The critic now catches the third-party case because I added a rule for that
  exact case. That catch proves little.

## What failed, and what changed

- **Two messages failed outright on the first run.** Azure's content filter
  refused two blatant injection messages before any model read them, and the
  tool reported them as unexplained failures. The platform was already doing
  the guardrail's job; the tool was mishandling the result. Fix: a blocked
  message goes to a person, with the reason. Recorded blocks replay as blocks.
- **I had planned an injection guardrail agent. I did not build it.** After
  the fix above, no injection was obeyed in any run, and the platform blocks
  the blatant ones. A guardrail agent would add a model call to every message
  for nothing I could measure.
- **One run would have lied to me.** The second run drafted a reply to a
  husband asking about his wife's application. The third drafted a reply to an
  angry complaint. The fourth drafted neither. Three runs of identical code
  gave three different answers on safety. I now run everything three times.
- **The fix was to the design, not the wording.** One label had to carry both
  "what does this person want" and "must a person handle it", so a status
  question with a complaint inside it could go either way. The classifier now
  answers the two questions separately and code routes on the second.
- **The first version of the fix over-corrected.** It read a medical
  appointment as "distress" and sent it to a person. I tightened four
  definitions using the day-one and unseen sets only. The holdout set was not
  used.
- **The fix still costs reviewer time.** A candidate who mentions a lawyer
  friend, one annoyed at a broken upload page and one with a pain flare-up now
  go to a person. That is the safe direction, and it is not free.
- **The judge was fooled by an injection the tool resisted.** One message tries
  to close the data wrapper and claim it is a newsletter. The classifier,
  drafter and critic ignored it. The judge believed it and failed a correct
  reply. The judge also missed the one draft that really was unsafe. It caught
  every planted flaw and was wrong on real drafts in both directions.
- **The AI's own code crashed after two live runs** while printing a file path
  outside the repository. The recordings survived, so the scores did; the
  token counts for those two runs did not. Fixed, with a test.
- **One run lost a message to a rate limit** after several runs back to back.
  It was reported as failed, which is the designed behaviour, and I re-ran.
- **The AI batched most of the day's code into one commit**, against the
  directive's "small steps". The three evaluation sets were committed
  separately and on time, which is the part that had to be provable.
- **One recording was overwritten** by a careless shell command, so one early
  critic run cannot be replayed. Its result file is intact.

## The build itself

- Start 04:00. First scored run on unseen messages 04:11. Both fixes verified
  across three sets by 04:37. Last evaluation run finished 04:43.
- Times I had to act for the build to move: 0. The day ran on a schedule.
- Model usage: 1,227 metered calls, 1,157,448 tokens in and 120,320 out, of
  which the judge used 165,761 in and 38,656 out. Two more runs of about 92
  calls each were not metered because of the crash above. No prices looked up.
- A third model deployment was added for the judge (`Mistral-Large-3`, at the
  20,000 tokens-per-minute quota the subscription allows).

## Decisions I still owe

- **Questions the intent list does not cover.** "Is the role remote?" got a
  holding reply. A referral was sent to a person. I have not decided which is
  right, and the intent list has no "other".
- **Reply language.** A French, a Spanish and a Korean message each got a reply
  in that language. A reviewer who cannot read it cannot approve it.
- **How much over-escalation is acceptable.** One or two of the 18 boundary
  messages now go to a person when a draft would have done.
- **Rule 3 of the directive** says escalations get no draft. It should
  probably also name hand-off reasons and platform blocks. The AI did not
  change a rule without asking.
