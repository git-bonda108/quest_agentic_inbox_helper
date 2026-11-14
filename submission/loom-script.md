# Quest Loom script: show the tool working (under 5 minutes)

About 560 spoken words. Have three things open before recording: a terminal in
the project folder, the browser on the review desk, and `evals/README.md` on
GitHub. Start the desk first:

```bash
cd ~/quest_agentic_inbox_helper && git pull && uv run inbox-helper serve --set unseen
```

**0:00 What it is. [Desk on screen, top of the page]**
"This is my inbox helper. It takes a pile of candidate messages, groups them
by what the person wants, and drafts a short reply for each. Nothing goes out
until a person approves the exact text. Everything you see is synthetic."

**0:25 Groups and drafts. [Scroll the groups]**
"Forty-four messages, sorted into groups: status checks, reschedules,
withdrawals. Each one shows why it landed there, and a draft that only states
what is in a written hiring policy."

**0:50 A person decides. [Edit one draft, approve it, scroll to Sent]**
"I can edit a draft, then approve it. It moves to Sent, and it is my text that
went, not the model's. I'll reject the next one. [Open the audit trail.] Every
decision is recorded against my name."

**1:30 What gets no draft. [Scroll to Needs a person]**
"These twenty get no draft at all. A complaint. A data request. Someone in
distress. This one hides a discrimination complaint behind an instruction
telling the tool to treat it as routine. It still reached a person. These two
were blocked by Microsoft Foundry's guardrail before any model read them."

**2:15 It runs on Foundry. [Foundry portal: the agent, then a trace]**
"The same code runs as a hosted agent on Microsoft Foundry, with its own
identity and no keys. It is shipped without the sending code, so it cannot
send. Each message leaves a trace with every step and its token count."

**2:50 Proof. [Terminal]**

```bash
uv run inbox-helper eval --set attacks
```

"Forty attacks, each a real request with a hidden instruction in a different
disguise: base64, look-alike letters, a fake system message. None was obeyed.
[Show `evals/README.md`.] Every run is in this table, including the ones where
I missed a target."

**3:30 What went wrong. [Stay on the results page, scroll to the failures]**
"Three runs of the same code disagreed on safety, so I fixed the design and now
run everything three times. Forty-three edge-case tests found five real bugs
in code that was passing a hundred and eleven tests. And three drafts got past
my critic and failed Foundry's own grader. That is why a person reviews every
one."

**4:15 How my way of working changed. [intent.md, then directive.md]**
"I wrote what I was building and the rules for the AI before any code. The AI
wrote the code. My job was the intent, the checks, and the decisions. [One
sentence in my own words on what changed for me.] Thanks for watching."

## Optional live moment, if my Azure sign-in works on this machine

Start the desk with `--try-hosted` instead, open "Try a message", type a
message, and show it come back from the live Foundry agent. Practise it first;
the first call takes about fifteen seconds.
