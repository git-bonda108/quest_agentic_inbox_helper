# The inbox helper, drawn on nine layers

When I review an agentic system I draw it on nine layers and look at two
things: which boxes are empty, and where one layer hands over to the next. I
did that with this tool on day four. It is a small tool, so some boxes are
nearly empty, and for this tool that is the right answer. The drawing still
found one thing I had missed.

```
candidate message ─► guardrail policy ─► hosted agent ─► proposal ─► checks again ─► review desk ─► send gate ─► outbox
                     (blocks at input)   classifier ─► drafter ─► critic      (code)          (a person)     (code)
```

| # | Layer | What is here | How I know it works |
|---|---|---|---|
| 1 | Handoff | A review desk. A signed-in person approves, edits or rejects each draft, and sending needs their approval of the exact text | A browser run from message to approved reply; tests that a send needs an approval record |
| 2 | Orchestration | Three agents in a fixed order, sequenced by code: classifier, drafter, critic. Two draft attempts at most | Tests for each route a message can take, and for the shape of each hand-off |
| 3 | Decision intelligence | Routing, the confidence floor, the word limit, the money check and the "needs a person" rule are code, not prompts | Tests just above and just below each limit |
| 4 | Integration | Thin. One API: the hosted agent returns a proposal. The agent has no tools and is packaged without the sending code | A test that nothing packaged can write to the outbox |
| 5 | Context and memory | Each agent gets four fields of the message and, where needed, the policy. Never the address. No memory | Tests on exactly what reaches a model; the injection and attack sets |
| 6 | Data foundation | Thin. One page of hiring policy is the only source of facts. All messages are synthetic | A grader checks each draft against the policy |
| 7 | Model layer | One model classifies and drafts; a different one critiques. Two more only grade the results | The same message sets re-run after every change |
| 8 | Security and trust | Sign-in by identity, no keys. A guardrail policy on the agent, a content filter on each model. The usual protections on the desk | The attack set; a comparison run with the guardrail removed; scans on every push |
| 9 | Observability | A trace per message with each agent step and its tokens. An audit trail of every decision. Billed cost per day | Trace counts checked against three scored runs |
| + | Governance | `intent.md` sets the targets, `directive.md` the standing rules. Each approval names its reviewer | An evaluation gate in CI; a test that ties the results page to the run files |

The numbers behind the right-hand column are in
[`evals/README.md`](../evals/README.md).

## What the drawing found

Layer 5 had no test of its own. The injection sets showed that hostile text
did not get through, but nothing checked directly what a model is given. I
added nine small contract tests. One of them confirms the candidate's address
is never among it.

## Where one layer hands over to the next

| Hand-over | The question | The answer here |
|---|---|---|
| Handoff and orchestration | When does the tool act, and when does it ask? | It drafts on its own and never sends. Some messages, such as a complaint or a sign of distress, get no draft at all |
| Orchestration and decision | Who makes the final call? | The classifier answers two questions; code routes on the answers |
| Integration and security | What may the agent do? | Return a proposal. The only code that can send sits with the reviewer and refuses without an approval |
| Context and data | What reaches the model? | The policy and four fields of one message |
| Model and observability | What did each call do and cost? | Every call is traced. Quality is re-checked on every push against recorded runs, and live when I ask |

## Thin on purpose

- **Integration.** Messages come from a file and "send" writes to a simulated
  outbox. A real mailbox would arrive as a read-only connector with its own
  permission tests. I planned a toolbox and cut it.
- **Memory.** My August 2025 email agent writes each correction back to
  memory. This one keeps none, because each message stands alone.
- **Data foundation.** The policy fits in a prompt, so there is no index.
- **Observability.** There is no nightly live re-test and no alert. That is
  the first thing I would add before real use.

The nine-layer model is from "Architect the System", The Agentic Enterprise
podcast (Episode 5). How I apply it here is my own.
