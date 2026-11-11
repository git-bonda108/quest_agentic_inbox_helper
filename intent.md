# Intent

Written on day one, before any code. This file says what I am building and how I
will know it works. `directive.md` says how the AI that builds it must behave.

## The problem

A hiring team's inbox fills with candidate messages. Most of them want one of a
handful of things: a status update, a new interview slot, more time on a
take-home task. Reading each one, deciding what it wants and typing a reply is
slow, and slow replies cost good candidates.

An AI can sort and draft. It must not send. A wrong reply to a candidate can
promise a job, quote a salary nobody approved, or answer a legal complaint with
a cheerful template.

## The tool

Quest format A, the inbox helper. One small tool that:

1. takes a pile of candidate messages,
2. groups them by what the person wants,
3. drafts a short reply for each one,
4. shows every draft to a human reviewer, who approves, edits or rejects it,
5. sends nothing that a reviewer has not approved.

## Who uses it

A recruiter or hiring coordinator clearing the inbox once or twice a day. They
know the hiring policy. They do not want to read logs or prompts. They want a
queue of drafts they can clear quickly and trust.

## Decisions I am making up front

- **Agents have no way to send.** Sending is ordinary code that refuses to run
  without an approval record for the exact text. This is a structural rule, not
  a prompt instruction.
- **The model proposes, code decides.** Grouping, routing, length limits and the
  approval rule are code. The model classifies and writes.
- **Some messages get no draft.** Complaints, legal threats, data-rights
  requests and signs of distress go to a person untouched.
- **Replies come from a written policy.** A draft may only state facts found in
  `data/policy/hiring_policy.md`. If the policy does not cover it, the draft
  says a person will follow up.
- **Synthetic data only.** Every message and name is invented. "Send" writes to
  a simulated outbox. No real mailbox is connected.
- **Anyone can run it.** The README's run command works with no account and no
  key, by replaying recorded model outputs that are labelled as recorded.

## Intents

| Intent | Action |
|---|---|
| `status_check` | draft |
| `reschedule` | draft |
| `withdraw` | draft |
| `compensation_question` | draft |
| `assessment_issue` | draft |
| `document_submission` | draft |
| `feedback_request` | draft |
| `accommodation_request` | draft (acknowledge and route; never grant or refuse) |
| `escalate` | no draft; a person handles it |
| `not_candidate` | no draft; set aside |

## How I will know it works

These are targets set before building. Results go in the daily logs with the
command that produced them. A target I miss gets reported as missed.

| Measure | Target |
|---|---|
| Sends without an approval record | 0, proven by a test |
| Intent accuracy on the labelled set | at least 90% |
| `escalate` messages that receive a draft | 0 |
| Drafts that state a fact the policy does not contain | 0 on the evaluation set |
| Draft length | 90 words or fewer |
| Injected instructions inside a message that the tool obeys | 0 on the adversarial set |
| Latency and model cost per message | measured and reported; no target yet |

I also track three numbers about the build itself, one line per day: how many
times I had to step in and correct the AI, model cost for the day, and time
from first prompt to a working version.

## What I am not building

A mail client. A chatbot. Automatic sending. Memory across sessions. Support
for attachments. Anything that reads a real inbox.

## How the five days are used

Day one ships the working core. Each day after that adds one harder thing and
proves it with a number: adversarial tests, then managed hosting with platform
guardrails and tracing, then a public link, then a cold run from a fresh clone.
