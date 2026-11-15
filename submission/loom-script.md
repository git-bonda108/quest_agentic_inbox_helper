# Quest Loom script: show the tool working (under 5 minutes)

About 470 spoken words: around three and a half minutes of speech, which
leaves time to click and pause. It opens on the explainer, which runs 86
seconds and carries its own captions, so speak lightly over it. Have four
things open before recording: the explainer, the review desk, a terminal in
the project folder, and the repository on GitHub.

- Explainer: https://inbox-helper-quest-b108.azurewebsites.net/explainer
  (or the MP4 from that page, played full screen)
- Review desk: https://inbox-helper-quest-b108.azurewebsites.net (any name)

To run the desk on your own computer instead:

```bash
cd ~/quest_agentic_inbox_helper && git pull && uv run inbox-helper serve --set unseen
```

Then the explainer is at http://127.0.0.1:8000/explainer.

**0:00 How it works. [The explainer, from the start]**
"This is my inbox helper. It takes a pile of candidate messages, groups them
by what the person wants, and drafts a short reply for each. [Guard] The
guardrail on Foundry stops a message that tries to give orders. [Classify]
The Classifier asks two things: what does this person want, and must a person
handle it? [Route] Code decides where each message goes, not a model. [Draft,
Critique] The Drafter writes from the hiring policy; the Critic, on a
different model, sends a draft back when it promises something the policy
doesn't. [Review] And nothing goes out until a person approves the exact
text. Everything on screen is replayed from recorded live runs."

**1:30 The desk. [Live desk, top of the page, then scroll the groups]**
"Here is the desk itself, with the same flow drawn above the groups.
Forty-four messages: status checks, reschedules, withdrawals, questions about
pay. Each shows why it landed there. A draft is under ninety words and may
state only what is in the written policy."

**2:00 A person decides. [Edit one draft, approve it, scroll to Sent]**
"I can edit a draft, then approve it. It moves to Sent, and it is my text
that went, not the model's. I'll reject this next one. [Open the audit trail.]
Every decision is recorded against my name."

**2:30 What gets no draft, and why. [Scroll to Needs a person]**
"I made one exception to 'a reply for each', on purpose. These twenty get no
draft: a complaint, a data request, someone in distress. A cheerful template
is the wrong answer to those, so a person handles them. Four of the twenty did
not need a person. That costs reviewer time, and I chose it over a draft that
should never be written."

**3:05 Try to break it. [Terminal]**

```bash
uv run inbox-helper eval --set attacks
```

"This replays the recorded live run. Forty ordinary requests, each hiding one
of four instructions in one of ten disguises. The line that matters is
'injection obeyed', and it is empty. The six misses are messages the platform
blocked; they went to a person."

**3:35 What went wrong along the way. [`evals/README.md`, the failures]**
"Three runs of the same code disagreed on safety, so I changed the design and
now run every message set at least three times. Thirty-four edge-case tests
found five real bugs in code that was already passing its tests. Every run is
on this page, including the ones where I missed a target."

**4:10 How I worked. [`intent.md`, then `directive.md`, then one daily log]**
"I worked AI-first. Before any code I wrote what I was building and the rules
the build works under. A coding agent wrote the code against them; the intent,
the checks and every decision were mine. The tool also runs as a hosted agent
on Microsoft Foundry, with a guardrail and tracing. I could have finished in a
day. I spent five raising the load instead, and the tool stayed small while
the evidence grew. There is a live link in the README if you want to try it
yourself. Thanks for watching."

## If the Azure sign-in works on this Mac, show it live

This is the strongest proof that the tool works. Start the desk this way
instead, then open "Try a message", type a message of your own, and let the
live agent on Foundry answer it. The first call takes about fifteen seconds,
so practise once before recording.

```bash
cd ~/quest_agentic_inbox_helper && FOUNDRY_PROJECT_ENDPOINT=https://inbox-helper-quest-b108.services.ai.azure.com/api/projects/inbox-helper uv run inbox-helper serve --set unseen --try-hosted
```

Say: "This one is live. It just went to the agent on Foundry and came back
grouped, with a draft for me to approve."
