# What I unlearned

**Speed is not the load.**
With Claude Code I could have finished an inbox helper in a day, and that was
my plan: build on day one, record on day two. The quest is called "Raise the
Load". So I spread the work: a working core on day one, then one harder thing
each day, each proven with a number. Unseen and adversarial messages. Managed
hosting with a guardrail and tracing. Edge cases and forty attacks. The tool on
day four is the same small tool as on day one. What grew is the evidence.

**Starting from the architecture.**
I think in nine layers, and my habit is to fill every one. I asked for a
toolbox, guardrails and every platform layer before a single check had failed.
Then I cut what had no reason to be there. A toolbox, because the tool calls
no external system. Memory, because each message stands on its own. A separate
guardrail agent, because the platform already blocked the blatant attacks and
nothing that got through was obeyed. A layer now has to be asked for by a requirement or a failing check.
The nine layers are still on the page; several are thin on purpose.

**One green run means it works.**
On day two, three runs of identical code disagreed about whether a sensitive
message got a draft. It was a different message each time. One run would have
told me the tool was safe. I now run everything three times and report every
run, including the ones that miss a target.

**A checker is a check.**
My critic approved every draft on day one, which proved nothing. I wrote bad
drafts by hand and planted them. The critic caught all sixteen. An independent
judge also caught every planted flaw, then missed the one real one, and was
fooled by an injection the tool itself resisted. I trust a reviewer only after
it has rejected something it should.

**Passing tests mean a tested tool.**
With 111 tests green, I wrote 43 edge-case tests. Eight failed and exposed
five real defects, including a reply that could be approved again after it was
sent.

**Fixing the wording.**
When a sensitive message slipped through, the easy fix was to reword the
prompt. The real cause was structural: one label had to carry both what the person
wants and whether a person must handle it. Splitting the question fixed it.

**What I kept.**
The AI drafts, a person signs off, and nothing goes out until they do. That
rule was in my August 2025 email agent and it is the one thing I did not have
to unlearn.
