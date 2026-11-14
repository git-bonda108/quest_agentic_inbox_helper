# Architecture: the inbox helper in nine layers

I design agentic systems against a nine-layer model, with governance running
across all nine. This page draws the inbox helper on that model: what each layer does here, and the
test that proves it still works. Every number has its command in
[`evals/README.md`](../evals/README.md).

```
candidate message ─► guardrail policy ─► hosted agent on Microsoft Foundry ─► proposal ─► checks again ─► review desk ─► send gate ─► outbox
                     (blocks at input)   classifier ─► drafter ─► critic                  (code)          (a person)     (code)
```

| # | Layer | In this tool | Tested by |
|---|---|---|---|
| 1 | **Handoff (experience)** | A review desk where a signed-in person approves, edits or rejects each draft. Sending is the one irreversible step, and it needs that person's approval of the exact text | Browser journey from message to approved reply: 18 of 18 checks. Tests that a send needs an approval record, and that a sent reply cannot be re-approved, overwritten or rejected |
| 2 | **Orchestration** | Three specialist agents in a fixed chain under a deterministic supervisor: classifier, drafter, critic. Typed hand-offs between them; two draft attempts at most; one turn per agent | Contract tests on every hand-off schema; scenario tests per route (draft, person, set aside, blocked, failed) |
| 3 | **Decision intelligence** | Routing, the confidence floor, the word limit, the money check, the length limit and the hand-off rule are code. The model proposes; code decides | Boundary tests just above and below each limit. No sensitive message drafted in any run since the hand-off rule went in |
| 4 | **Integration** | One typed API: the hosted agent's Responses endpoint, returning a proposal. The agent holds no tools and is shipped without the sending code, so it cannot act on anything | A packaging test that nothing shipped can write to the outbox; the deployed zip's SHA-256 matches the repository |
| 5 | **Context and memory** | Each agent sees only what its step needs: four fields of the message, never the address; the drafter and critic get the policy. Message text is wrapped as inert data. No memory, by design | Contract tests on what reaches a model. 53 planted injections, none obeyed |
| 6 | **Data foundation** | One written hiring policy is the only source of facts for a reply. All messages are synthetic. Labels live apart from inputs | Five labelled sets, 162 messages, each committed before its first run. A grader checks every draft against the policy |
| 7 | **Model layer** | A fast model classifies and drafts; a different model critiques; a third vendor's model judges; a fourth model grades in the cloud. All four are set by configuration | The same sets re-run on every change. Each reviewer is tested on 23 planted drafts before its verdicts count |
| 8 | **Security and trust** | Identity instead of keys, end to end. A guardrail policy on the agent and a content filter on each model. Sessions, CSRF tokens and a strict content policy on the desk | A 40-message attack set in ten disguises: 0 obeyed. A control version without the guardrail shows both layers. Secrets, dependency and static scans on every push |
| 9 | **Observability** | One trace per message in Application Insights, with a span and token counts for each agent step. Billed cost per day from Azure. An audit trail of every decision | Step counts and token totals in the traces match three scored runs exactly |
| + | **Governance, across every layer** | `intent.md` sets the targets. `directive.md` sets the standing rules. Nothing ships unless the evaluation gate passes. Every approval names its reviewer and is bound to a hash of the text | A test ties every number on the results page to its result file. 168 tests in CI |

## The boundaries, where systems succeed or fail

| Boundary | The design question | In this tool |
|---|---|---|
| Handoff ↔ Orchestration | When does the agent ask, and when does it act? | It drafts on its own. It never sends. Eight kinds of message (a complaint, a legal threat, distress and so on) get no draft and go to a person |
| Orchestration ↔ Decision | Who makes the final call? | The classifier answers two questions; code routes on the answers. A draft that fails a code check never reaches the critic |
| Integration ↔ Security | What may each tool do? | The agent has no tools. The only writer to the outbox is plain code on the reviewer's side, and it refuses without an approval |
| Context ↔ Data foundation | What reaches the model, from where? | The policy, and four fields of one message. A reply may state only what the policy contains |
| Model ↔ Observability | How do we know what each call did and cost? | Every call is traced with its tokens. Quality is re-tested on every push against recorded runs, and live on demand |

## Layers kept thin on purpose

- **Integration.** The tool reads messages from a file and writes to a
  simulated outbox. A real mailbox or hiring system would arrive as a read-only
  MCP server with permission tests. A toolbox was planned and cut, because no
  requirement called for one.
- **Memory.** My August 2025 email agent keeps user preferences in memory.
  This tool keeps none: each message is handled on its own, which is also why
  one sandbox can serve a whole inbox.
- **Data foundation.** The policy is one page, so it goes to the model whole.
  There is no index to drift.
- **Observability.** Re-testing runs on every push and on demand. A nightly
  live re-test with an alert is the first thing production would add.

Layer model as presented in "Architect the System", The Agentic Enterprise
podcast (Episode 5). The application to this tool is mine.
