# What I unlearned

I have built agentic systems in public since February 2025, and in August 2025
I built an email agent with the same rule this quest asks for: nothing is sent
until a person approves it. So this week was never about whether I could build
an inbox helper. It was about whether I would build it differently. Six things
changed.

**1. Speed is not the load.**
Working AI-first with a coding agent, I had a working inbox helper 47 minutes
after I shared the brief on day one. My plan was to finish that day and record on
day two. I dropped the plan. When code is this cheap, the scarce work is the
intent, the checks and the evidence. So I raised the load each day: unseen and
adversarial messages, managed hosting with a guardrail and tracing, edge cases
and forty attacks. The tool stayed small. What grew is the proof.

**2. I write the contract, not the code.**
Before any code I wrote `intent.md`, what success means in numbers, and
`directive.md`, the rules the build works under. Every later change traces back
to one of them. The directive is on version 3, and each new version was forced
by a failure, not by a new idea.

**3. Every layer has to be earned.**
I think in nine layers, and my reflex is to fill all of them. On day one I
wanted every platform feature in, before a single check had failed. What I left
out: a toolbox, because the tool calls no external system; memory, because each
message stands alone; a separate guardrail agent, because the platform already
blocked the blatant attacks and nothing that got through was obeyed. A layer now
goes in when a requirement or a failing check asks for it.

**4. One green run is an anecdote.**
On day two, three runs of identical code disagreed about whether a sensitive
message got a draft, and it was a different message each time. One run would
have told me the tool was safe. I now run every message set through the live
models at least three times and publish every run, including the misses.

**5. Fix the structure, not the wording.**
The quick fix was to reword the prompt. The cause was structural: one label had
to carry both what the person wants and whether a person must handle it. I split
it into two questions and let code route on the second. No sensitive message has
been drafted in any run since.

**6. A checker is not a check until it has caught something.**
My critic approved every draft on day one, which proved nothing. I planted
flawed drafts by hand and it caught every one, yet on day two it had passed the
one real failure: a reply confirming to a husband that his wife had applied. An
independent judge on another vendor's model also caught all fifteen planted
flaws, missed that same real failure, and was fooled by an injection my own
agents had ignored. Tests taught the same lesson: with 111 passing, 34 new
edge-case tests found five real defects. I now trust a check only after
it has failed something it should.

**What I kept.**
The model drafts, a person signs off, and nothing goes out until they do. That
rule was in my August 2025 email agent. This week it was enforced in code,
tested, and never broken.
