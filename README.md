# Inbox helper

Takes a pile of candidate messages, groups them by what the person wants, and
drafts a short reply for each. A human reviews every draft. Nothing is sent
until that person approves the exact text.

Built in five days for a hiring quest, working AI-first. Start with
[`intent.md`](intent.md) (what and why) and [`directive.md`](directive.md)
(the rules the AI builder works under). The daily logs are in [`logs/`](logs/).

![The review desk: a candidate message on the left, the drafted reply on the right](docs/images/review-desk.png)

## Run it

You need [uv](https://docs.astral.sh/uv/) and nothing else. No account, no key.

```bash
uv sync
```

```bash
uv run inbox-helper serve
```

Open http://127.0.0.1:8000, enter any name, and review the drafts.

Without credentials the tool **replays recorded model outputs**. They were
recorded from a real run against the live models, and every page says so. All
messages are synthetic, and "send" writes to a simulated outbox.

## Check it

```bash
uv run pytest
```

```bash
uv run inbox-helper eval
```

`eval` processes the 42 labelled messages and prints the scores. The latest
recorded run is in [`evals/results/`](evals/results/).

## Run it against live models

The agents run on Microsoft Foundry and sign in with your Azure identity. There
are no API keys.

1. Create a Foundry project with two model deployments.
2. Give your identity the **Foundry User** role on the Foundry resource.
3. Sign in with `az login`.
4. Copy `.env.example` to `.env`, fill it in, and export the variables.

```bash
uv run inbox-helper eval --live
```

```bash
uv run inbox-helper serve --live
```

## How it works

```
messages ─► classifier ─► routing (code) ─┬─► drafter ─► checks (code) ─► critic ─► review desk ─► send gate (code) ─► outbox
                                          ├─► needs a person (no draft)
                                          └─► set aside
```

- **Three agents, one job each**, on the OpenAI Agents SDK. The classifier and
  drafter use one model; the critic uses a different one.
- **Code decides.** Routing, the word limit, the money check and the approval
  rule are plain code with tests. The agents classify and write.
- **Agents cannot send.** `dispatch.py` is the only module that writes to the
  outbox, and a test enforces that. It refuses unless the reviewer's latest
  decision approves the exact text, and it sends at most once.
- **Some messages get no draft.** Complaints, legal threats, data requests and
  signs of distress go to a person.
- **Replies come from a written policy**,
  [`data/policy/hiring_policy.md`](data/policy/hiring_policy.md). If the policy
  does not cover it, the reply says a person will follow up.
- **Every step is in an audit trail**, shown in the desk.

## Layout

| Path | What it holds |
|---|---|
| `src/inbox_helper/` | The tool |
| `tests/` | Tests, including the evaluation gate on the recorded run |
| `data/inbox/` | 42 synthetic candidate messages |
| `evals/golden/` | Expected intent and action for each message, kept apart from the inputs |
| `data/recordings/` | Recorded model outputs for offline replay |
| `logs/` | One log per day: numbers, failures, changes of plan |
