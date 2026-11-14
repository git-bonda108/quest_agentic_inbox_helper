# Architecture and evidence, on one page

The tool in nine layers, with where each lives and what shows it works. These
are the tool's own layers. Every number has its command in
[`evals/README.md`](../evals/README.md).

```
candidate message ─► guardrail policy ─► hosted agent on Foundry ─► proposal ─► checks again ─► review desk ─► send gate ─► outbox
                                         classifier ─► drafter ─► critic                        (a person)     (code)
```

| # | Layer | What it is here | Where | Evidence |
|---|---|---|---|---|
| 1 | Intent and rules | What is being built, how success is measured, and the standing rules for the AI builder | `intent.md`, `directive.md` | Written before any code; directive at v3, each change traced to a failure |
| 2 | Data | Synthetic messages only, one written hiring policy as the single source of facts, labels kept apart from inputs | `data/`, `evals/*/labels.jsonl` | 162 messages in five sets; each set committed before its first run |
| 3 | Agents | Three agents, one job each: classifier, drafter, critic. The critic runs on a different model | `foundry_team.py` | Critic caught 16 of 16 planted flaws, passed 7 of 7 sound drafts |
| 4 | Control in code | Routing, word limit, money check, length limit and hand-off are code. The model proposes; code decides | `routing.py`, `checks.py`, `pipeline.py` | No sensitive message drafted in nine runs after the hand-off fix |
| 5 | Human review | A signed-in person approves, edits or rejects each draft. Sending needs their approval of the exact text | `desk.py`, `dispatch.py` | Browser pass 18 of 18; a second reviewer on a stale page is refused |
| 6 | Guardrails | Foundry's policy blocks at the agent's input; each model's filter blocks behind it; a blocked message goes to a person | `hosting/deploy.py`, `hosted.py` | 53 planted injections, none obeyed; a control version without the policy shows both layers |
| 7 | Hosting and identity | A hosted agent with its own identity and no keys, shipped without the sending code | `hosting/`, `service.py` | Deployed zip's SHA-256 matches the repository; a test checks nothing shipped can send |
| 8 | Observability | One trace per message with a span and token counts per agent step; an audit trail of every decision | Application Insights, `store.py` | Step counts and token totals in traces match three scored runs exactly |
| 9 | Evaluation | Labelled sets, planted flaws for every reviewer, an independent judge, Foundry cloud evaluation, replay gates in CI | `evals/`, `tests/` | 159 tests; cloud run of 118 messages: 105 passed, 3 need an edit, 10 blocked |

## What this design refuses to do

- **No agent can send.** The outbox has one writer, and it is plain code.
- **No draft for a complaint, a legal threat, a data request, distress, an
  identity document, a threat or a third party.** A person handles those.
- **No fact that is not in the policy.** Otherwise the reply says a person will
  follow up.
- **No component because it was available.** A toolbox and a guardrail agent
  were both planned and both left out when no failing check called for them.

## Known limits

- Three drafts passed the critic and failed the cloud grader. Review by a
  person is the control that catches them.
- More harmless messages go to a person than strictly need to.
- Replies to non-English messages come back in that language.
- Network egress rules for the agent are not set.
