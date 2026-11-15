# Quest Loom script: show the tool working (under 5 minutes)

About 430 spoken words, so there is room to pause on the desk. Have three things open before recording: a terminal in
the project folder, the browser on the review desk, and the repository on
GitHub. Four of the five minutes are on the tool itself. Start the desk first:

```bash
cd ~/quest_agentic_inbox_helper && git pull && uv run inbox-helper serve --set unseen
```

**0:00 What it is. [Desk on screen, top of the page]**
"This is my inbox helper. It takes a pile of candidate messages, groups them
by what the person wants, and drafts a short reply for each. Nothing goes out
until a person approves the exact text. Everything you see is synthetic."

**0:25 Groups and drafts. [Scroll slowly through the groups]**
"Forty-four messages, sorted into groups: status checks, reschedules,
withdrawals, questions about pay. Each one shows why it landed there. Each
draft is under ninety words and only states what is in a written hiring
policy. If the policy does not cover it, the reply says a person will follow
up."

**1:05 A person decides. [Edit one draft, approve it, scroll to Sent]**
"I can edit a draft, then approve it. It moves to Sent, and it is my text that
went, not the model's. I'll reject this next one. [Open the audit trail.]
Every decision is recorded against my name."

**1:50 What gets no draft, and why. [Scroll to Needs a person]**
"The brief says a reply for each. I made one exception on purpose. These
twenty get no draft: a complaint, a data request, someone in distress. A
cheerful template is the wrong answer to those, so a person handles them. This
one hides a discrimination complaint behind an instruction telling the tool to
treat it as routine. It still reached a person."

**2:40 Try to break it. [Terminal]**

```bash
uv run inbox-helper eval --set attacks
```

"Forty messages, each a real request with a hidden instruction in a different
disguise. None was obeyed."

**3:10 What went wrong along the way. [`evals/README.md`, the failures]**
"Three runs of the same code disagreed on safety, so I changed the design and
now run everything three times. Forty-three edge-case tests found five real
bugs in code that was already passing its tests. Every run is on this page,
including the ones where I missed a target."

**3:50 How I worked. [`intent.md`, then `directive.md`, then one daily log]**
"I worked AI-first. Before any code I wrote what I was building and the rules
the build works under. Claude Code wrote the code against them; the intent, the
checks and every decision were mine. It also
runs as a hosted agent on Microsoft Foundry, with a guardrail and tracing. I
could have finished in a day. I spent five raising the load instead, and the
tool stayed small while the evidence grew. Thanks for watching."

## Optional live moment, if my Azure sign-in works on this machine

Start the desk with `--try-hosted` instead, open "Try a message", type a
message, and show it come back from the live Foundry agent. Practise it first;
the first call takes about fifteen seconds.
