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

## The build itself

Times I had to act: 1 (asking for the early start). Model usage: 1,227 metered
calls, 1,157,448 tokens in and 120,320 out in the first session; about 2,045 in
and 165 out per message through the hosted agent.
