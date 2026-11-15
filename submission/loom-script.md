# Quest Loom script: show the tool working (4:40, limit 5:00)

Seven beats, timed to finish at 4:40 and leave twenty seconds of slack. The
spoken words are in quotes; what to do on screen is in [brackets]. There are
453 spoken words. At a calm 140 words a minute that is about three and a
quarter minutes of speech, and the rest is the 86-second explainer playing,
clicks and the live agent answering.

| Beat | Starts | Length | Spoken words |
|---|---|---|---|
| 1. How it works (explainer) | 0:00 | 1:26 | 130, in seven short lines over the video |
| 2. The desk | 1:26 | 0:30 | 60 |
| 3. A person decides | 1:56 | 0:34 | 42, plus four clicks |
| 4. Live, on Foundry | 2:30 | 0:35 | 39, spoken while the agent answers |
| 5. What gets no draft | 3:05 | 0:30 | 61 |
| 6. Try to break it | 3:35 | 0:30 | 44 |
| 7. How I worked | 4:05 | 0:35 | 77 |

## Before you record

Open these in tabs, in this order, so nothing loads on camera:

1. The explainer: https://inbox-helper-quest-b108.azurewebsites.net/explainer
2. The review desk: https://inbox-helper-quest-b108.azurewebsites.net (sign in
   with your name)
3. A terminal in the project folder, with this already typed (do not press
   Enter yet):

```bash
cd ~/quest_agentic_inbox_helper && git pull && uv run inbox-helper eval --set attacks
```

4. The repository on GitHub, at `intent.md`.

Run the terminal command once beforehand, so the recorded run starts at once
instead of installing packages on camera. Copy the message for beat 4 so you
can paste it. Send one practice message through "Try a message" before recording: the
first call wakes the agent and takes about fifteen seconds, later ones about
seven. If someone else has used the shared desk, restart it for a clean
start (see `hosting/webapp.md`).

## The script

**0:00 How it works. [Explainer tab. Press Restart, then let it play]**

[0:00, inbox fills] "This is my inbox helper. It sorts a pile of candidate
messages by what each person wants, and drafts a reply for each."

[0:10, Guard] "This one tries to give the tool orders. The guardrail on
Microsoft Foundry blocks it, and it goes to a person."

[0:19, Classify] "The Classifier asks two things: what does this person
want, and does a person need to handle it?"

[0:29, Route] "Then plain code decides where each message goes. Not a model."

[0:37, Draft] "The Drafter writes from the hiring policy, and code checks
every draft."

[0:48, Critique] "Here the Critic, a different model, sends a draft back. It
promised a follow-up the policy doesn't. The Drafter fixes it."

[1:04, Review] "And nothing goes out until a person approves the exact text.
Every message, label and draft here is replayed from a recorded live run."

**1:26 The desk. [Desk tab, top of the page; scroll slowly through the groups]**
"Here's the desk itself, with the same flow drawn up top. Forty-four
synthetic messages, sorted into groups: status checks, reschedules,
withdrawals, questions about pay. Each card says why it landed there. A
draft stays under ninety words and can only state what's in the written
policy. If the policy doesn't cover it, the reply says a person will follow
up."

**1:56 A person decides. [Edit one draft, Approve and send, scroll to Sent]**
"I can edit a draft before I approve it. Once I do, it moves to Sent, and
what went out is my text, not the model's. [Reject the next draft.] I'll
reject this one, so nothing is sent. [Open the audit trail.] And every
decision is logged against my name."

**2:30 Live, on Foundry. [Try a message. Paste the message below and send it]**

Candidate name: `Jordan Lee` · Subject: `Take-home link`

> Hi, my take-home link says it expired before I could open it. Could you
> send me a new one? Thanks, Jordan

"This one isn't recorded. It goes straight to the agent hosted on Microsoft
Foundry, under the app's own identity, with no keys. [Wait for the answer.]
It came back as [read the group out], with a draft waiting for me to approve.
Same rules, same gate."

**3:05 What gets no draft, and why. [Scroll to Needs a person]**
"I made one exception to 'a reply for each', on purpose. These twenty get no
draft: a complaint, a data request, someone in distress. A cheerful template
is the wrong answer there, so a person takes over. Four of the twenty didn't
need a person. That costs reviewer time, and I chose it over a draft that
should never be written."

**3:35 Try to break it. [Terminal: press Enter]**
"This replays a recorded live run: forty ordinary requests, each hiding one
of four instructions in one of ten disguises. The line that matters is
'injection obeyed', and it's empty. The six misses are messages the platform
blocked, and they went to a person."

**4:05 How I worked. [GitHub: `intent.md`, then `directive.md`, then `logs/`]**
"I worked AI-first. Before any code, I wrote down what I was building and
the rules the build had to follow. A coding agent wrote the code against
them; the intent, the checks and every call were mine. Every result is in
the repo, including the targets I missed. I could have wrapped this up in a
day. I spent five raising the load instead, and the tool stayed small while
the evidence grew. Thanks for watching."

**4:40 End.**

## If you run long

Cut in this order, and you are back under 4:30 each time:

1. In beat 5, drop the last two sentences (saves 12 seconds).
2. In beat 2, drop "If the policy doesn't cover it..." (saves 6 seconds).
3. Skip beat 6 and say instead, over `evals/README.md`: "Forty planted
   attacks, none obeyed." (saves 20 seconds).

## If "Try a message" is slow or down

Skip beat 4 and say over the desk: "The same flow runs live as a hosted agent
on Microsoft Foundry; the README has the link to try it." You will finish at
about 4:10.
