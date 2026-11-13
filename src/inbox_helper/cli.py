"""Command line entry point."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import statistics
import sys
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from inbox_helper.evaluate import Report, evaluate, load_labels, load_messages
from inbox_helper.judge import CRITERIA, RecordedJudge
from inbox_helper.pipeline import process_inbox
from inbox_helper.planted import PlantedReport, load_cases, run_cases
from inbox_helper.recording import RecordedTeam
from inbox_helper.store import Store

if TYPE_CHECKING:  # the cloud packages are imported late, only for live runs
    from inbox_helper.foundry_team import Call, FoundryJudge, FoundryTeam

ROOT = Path(__file__).resolve().parents[2]
RECORDINGS = ROOT / "data" / "recordings"
POLICY = ROOT / "data" / "policy" / "hiring_policy.md"
RUBRIC = ROOT / "evals" / "rubric.md"
CASES = ROOT / "evals" / "critic" / "cases.jsonl"
WORKER_MODEL = os.environ.get("INBOX_HELPER_WORKER_MODEL", "gpt-5.6-luna")
CRITIC_MODEL = os.environ.get("INBOX_HELPER_CRITIC_MODEL", "gpt-5.5")
JUDGE_MODEL = os.environ.get("INBOX_HELPER_JUDGE_MODEL", "Mistral-Large-3")
AGENT_NAME = os.environ.get("INBOX_HELPER_AGENT_NAME", "inbox-helper")


@dataclass(frozen=True)
class DataSet:
    """A pile of messages, their hand-written labels and the recorded run on them."""

    inbox: Path
    labels: Path
    recording: Path
    judge_recording: Path


SETS = {
    "golden": DataSet(
        inbox=ROOT / "data" / "inbox" / "messages.jsonl",
        labels=ROOT / "evals" / "golden" / "labels.jsonl",
        recording=RECORDINGS / "golden.json",
        judge_recording=RECORDINGS / "judge-golden.json",
    ),
    "unseen": DataSet(
        inbox=ROOT / "data" / "inbox" / "unseen.jsonl",
        labels=ROOT / "evals" / "unseen" / "labels.jsonl",
        recording=RECORDINGS / "unseen.json",
        judge_recording=RECORDINGS / "judge-unseen.json",
    ),
    "holdout": DataSet(
        inbox=ROOT / "data" / "inbox" / "holdout.jsonl",
        labels=ROOT / "evals" / "holdout" / "labels.jsonl",
        recording=RECORDINGS / "holdout.json",
        judge_recording=RECORDINGS / "judge-holdout.json",
    ),
    "edge": DataSet(
        inbox=ROOT / "data" / "inbox" / "edge.jsonl",
        labels=ROOT / "evals" / "edge" / "labels.jsonl",
        recording=RECORDINGS / "edge.json",
        judge_recording=RECORDINGS / "judge-edge.json",
    ),
    "attacks": DataSet(
        inbox=ROOT / "data" / "inbox" / "attacks.jsonl",
        labels=ROOT / "evals" / "attacks" / "labels.jsonl",
        recording=RECORDINGS / "attacks.json",
        judge_recording=RECORDINGS / "judge-attacks.json",
    ),
}


def shown(path: Path) -> str:
    """A path as printed: relative to the repository when it is inside it."""
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def _endpoint() -> str:
    endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
    if not endpoint:
        raise SystemExit("FOUNDRY_PROJECT_ENDPOINT is not set; see .env.example")
    return endpoint


def _live_team() -> FoundryTeam:
    from inbox_helper.foundry_team import FoundryTeam

    return FoundryTeam(_endpoint(), WORKER_MODEL, CRITIC_MODEL, POLICY.read_text("utf-8"))


def _live_judge() -> FoundryJudge:
    from inbox_helper.foundry_team import FoundryJudge

    return FoundryJudge(
        _endpoint(), JUDGE_MODEL, POLICY.read_text("utf-8"), RUBRIC.read_text("utf-8")
    )


def _usage(calls: Sequence[Call]) -> dict[str, Any]:
    """Model calls, tokens and latency for a live run. Empty for a replay."""
    if not calls:
        return {}
    seconds = sorted(call.seconds for call in calls)
    return {
        "model_calls": len(calls),
        "calls_by_step": dict(sorted(Counter(call.step for call in calls).items())),
        "tokens_in": sum(call.input_tokens for call in calls),
        "tokens_out": sum(call.output_tokens for call in calls),
        "latency_median_s": round(statistics.median(seconds), 2),
        "latency_p95_s": seconds[max(0, round(0.95 * len(seconds)) - 1)],
    }


def _run_block(argv: Sequence[str], source: str, calls: Sequence[Call]) -> dict[str, Any]:
    return {
        "command": "inbox-helper " + " ".join(argv),
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "source": source,
        **_usage(calls),
    }


def _write(path: Path | None, run: dict[str, Any], result: dict[str, Any]) -> None:
    if path is not None:
        path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps({"run": run, **result}, indent=2, ensure_ascii=False)
        path.write_text(text + "\n", encoding="utf-8")


def _print_run(run: dict[str, Any]) -> None:
    print(f"source:            {run['source']}")
    if "model_calls" in run:
        print(f"model calls:       {run['model_calls']} {run['calls_by_step']}")
        print(f"tokens in/out:     {run['tokens_in']}/{run['tokens_out']}")
        print(
            f"call latency:      median {run['latency_median_s']:.2f}s, "
            f"p95 {run['latency_p95_s']:.2f}s"
        )


def _print_report(report: Report) -> None:
    print(f"messages:          {report.total}")
    print(
        f"intent accuracy:   {report.intent_correct}/{report.intent_scored} = "
        f"{report.intent_accuracy:.1%}"
    )
    print(
        f"action accuracy:   {report.action_correct}/{report.total} = {report.action_accuracy:.1%}"
    )
    print(f"drafts written:    {report.drafts} (longest: {report.longest_draft_words} words)")
    print(f"UNSAFE, escalation given a draft:  {report.escalations_drafted}")
    print(f"UNSAFE, escalation set aside:      {report.escalations_set_aside}")
    print(f"UNSAFE, injection obeyed:          {report.injections_obeyed}")
    print(f"candidate set aside:               {report.candidates_set_aside}")
    print(f"sent to a person unnecessarily:    {report.sent_to_person_unnecessarily}")
    print(f"blocked by the content filter:     {report.blocked}")
    for name, counts in sorted(report.by_category.items()):
        print(f"  {name}: {counts['action_correct']}/{counts['total']} routed as labelled")
    print(f"failures:          {len(report.failures)}")
    for failure in report.failures:
        print(f"  FAILED {failure}")
    for miss in report.misses:
        print(
            f"  MISS {miss['id']}: expected {miss['expected']}, got {miss['got']} "
            f"({miss['confidence']}) {miss['reason']}"
        )


async def _eval(args: argparse.Namespace, argv: Sequence[str]) -> int:
    data = SETS[args.set]
    recording: Path = args.recording or data.recording
    messages = load_messages(data.inbox)[: args.limit]
    labels = load_labels(data.labels)
    store = Store(":memory:")
    calls: Sequence[Call] = ()
    timing: dict[str, Any] = {}
    if args.hosted:
        from inbox_helper.hosted import FoundryAgent, process_inbox_hosted

        agent = FoundryAgent(_endpoint(), AGENT_NAME)
        try:
            outcomes = await process_inbox_hosted(
                store, agent, messages, concurrency=args.concurrency
            )
        finally:
            await agent.aclose()
        source = f"hosted agent '{AGENT_NAME}' on Microsoft Foundry"
        seconds = sorted(agent.seconds)
        timing = {
            "agent_calls": len(seconds),
            "seconds_per_message_median": round(statistics.median(seconds), 2),
            "seconds_per_message_p95": seconds[max(0, round(0.95 * len(seconds)) - 1)],
        }
    elif args.live:
        live = _live_team()
        meta = {"worker": WORKER_MODEL, "critic": CRITIC_MODEL}
        recorder = RecordedTeam(recording, live=live, meta=meta)
        try:
            outcomes = await process_inbox(store, recorder, messages, concurrency=args.concurrency)
        finally:
            await live.aclose()
        if args.record and not any(o.error for o in outcomes):
            recorder.save()
            print(f"recorded to {shown(recording)}")
        source = f"live models (worker {WORKER_MODEL}, critic {CRITIC_MODEL})"
        calls = live.ledger
    else:
        replay = RecordedTeam(recording)
        outcomes = await process_inbox(store, replay, messages, concurrency=args.concurrency)
        source = replay.describe()
    report = evaluate(store, outcomes, labels)
    run = _run_block(argv, source, calls) | timing
    _print_run(run)
    if timing:
        print(
            f"time per message:  median {timing['seconds_per_message_median']:.2f}s, "
            f"p95 {timing['seconds_per_message_p95']:.2f}s ({timing['agent_calls']} agent calls)"
        )
    _print_report(report)
    _write(args.out, run, json.loads(report.to_json()))
    return 1 if report.failures or report.unsafe else 0


def _print_planted(report: PlantedReport) -> None:
    print(f"planted flaws caught:   {report.caught}/{report.planted} = {report.catch_rate:.1%}")
    print(f"controls passed:        {report.controls_passed}/{report.controls}")
    for miss in report.missed:
        print(f"  MISSED {miss['id']}: {miss['flaw']}")
    for wrong in report.false_rejections:
        print(f"  FALSE REJECTION {wrong['id']}: {wrong['problems']}")


async def _planted(args: argparse.Namespace, argv: Sequence[str]) -> int:
    """Run the planted drafts past the critic or the judge."""
    cases = load_cases(CASES)
    messages = {m.id: m for data in SETS.values() for m in load_messages(data.inbox)}
    recording = RECORDINGS / f"planted-{args.reviewer}.json"
    calls: Sequence[Call] = ()
    if args.reviewer == "critic":
        team = _live_team() if args.live else None
        recorded_team = RecordedTeam(recording, live=team, meta={"critic": CRITIC_MODEL})
        try:
            report = await run_cases(
                recorded_team.critique, cases, messages, concurrency=args.concurrency
            )
        finally:
            if team is not None:
                await team.aclose()
                calls = team.ledger
        saver, source = recorded_team.save, recorded_team.describe()
    else:
        judge = _live_judge() if args.live else None
        recorded_judge = RecordedJudge(recording, live=judge, meta={"judge": JUDGE_MODEL})
        try:
            report = await run_cases(
                recorded_judge.review, cases, messages, concurrency=args.concurrency
            )
        finally:
            if judge is not None:
                await judge.aclose()
                calls = judge.ledger
        saver, source = recorded_judge.save, recorded_judge.describe()
    if args.live:
        source = (
            f"live {args.reviewer} ({JUDGE_MODEL if args.reviewer == 'judge' else CRITIC_MODEL})"
        )
        if args.record:
            saver()
            print(f"recorded to {shown(recording)}")
    run = _run_block(argv, source, calls)
    _print_run(run)
    _print_planted(report)
    _write(args.out, run, report.to_dict())
    return 0


async def _judge(args: argparse.Namespace, argv: Sequence[str]) -> int:
    """Score the final drafts of a recorded run against the rubric."""
    data = SETS[args.set]
    messages = load_messages(data.inbox)
    store = Store(":memory:")
    replay = RecordedTeam(args.recording or data.recording)
    await process_inbox(store, replay, messages)
    drafted = [(m, d.text) for m in messages if (d := store.draft(m.id)) is not None]

    live = _live_judge() if args.live else None
    judge = RecordedJudge(data.judge_recording, live=live, meta={"judge": JUDGE_MODEL})
    gate = asyncio.Semaphore(args.concurrency)

    async def one(message: Any, text: str) -> dict[str, str]:
        async with gate:
            return (await judge.judge(message, text)).failed()

    try:
        results = await asyncio.gather(*(one(m, text) for m, text in drafted))
    finally:
        if live is not None:
            await live.aclose()
    source = judge.describe()
    if live is not None:
        source = f"live judge ({JUDGE_MODEL})"
        if args.record:
            judge.save()
            print(f"recorded to {shown(data.judge_recording)}")

    flagged = [(m.id, text, failed) for (m, text), failed in zip(drafted, results, strict=True)]
    flagged = [item for item in flagged if item[2]]
    by_criterion = {name: sum(name in failed for _, _, failed in flagged) for name in CRITERIA}
    run = _run_block(argv, source, live.ledger if live is not None else ())
    _print_run(run)
    print(f"drafts on:         {replay.describe()}")
    print(f"drafts judged:     {len(drafted)}")
    print(f"drafts flagged:    {len(flagged)}")
    print(f"flags by criterion: {by_criterion}")
    for message_id, _, failed in flagged:
        for name, evidence in failed.items():
            print(f"  FLAG {message_id} {name}: {evidence}")
    _write(
        args.out,
        run,
        {
            "drafts_from": replay.describe(),
            "drafts_judged": len(drafted),
            "drafts_flagged": len(flagged),
            "flags_by_criterion": by_criterion,
            "flagged": [
                {"id": message_id, "failed": failed, "draft": text}
                for message_id, text, failed in flagged
            ],
        },
    )
    return 0


async def _load_demo(args: argparse.Namespace, store: Store) -> str:
    """Process the chosen inbox into the store and say where the drafts came from."""
    data = SETS[args.set]
    messages = load_messages(data.inbox)
    if args.hosted:
        from inbox_helper.hosted import FoundryAgent, process_inbox_hosted

        agent = FoundryAgent(_endpoint(), AGENT_NAME)
        try:
            await process_inbox_hosted(store, agent, messages)
        finally:
            await agent.aclose()
        return f"the hosted agent '{AGENT_NAME}' on Microsoft Foundry, live"
    if args.live:
        live = _live_team()
        try:
            await process_inbox(store, live, messages)
        finally:
            await live.aclose()
        return f"live models (worker {WORKER_MODEL}, critic {CRITIC_MODEL})"
    replay = RecordedTeam(args.recording or data.recording)
    await process_inbox(store, replay, messages)
    return replay.describe()


def _serve(args: argparse.Namespace) -> int:
    import secrets

    import uvicorn

    from inbox_helper.desk import create_app

    store = Store(":memory:")
    source = asyncio.run(_load_demo(args, store))
    local = args.host in {"127.0.0.1", "localhost"}
    passcode = os.environ.get("INBOX_HELPER_PASSCODE") or None
    if passcode is None and not local:
        raise SystemExit("Set INBOX_HELPER_PASSCODE before serving on a public address.")
    live = None
    if args.try_hosted:
        from inbox_helper.hosted import FoundryAgent, process_inbox_hosted
        from inbox_helper.models import Message

        agent = FoundryAgent(_endpoint(), AGENT_NAME)

        async def live(message: Message) -> None:
            [outcome] = await process_inbox_hosted(store, agent, [message])
            if outcome.error:
                raise RuntimeError(outcome.error)

        source += (
            f"; typed messages go live to the hosted agent '{AGENT_NAME}' on Microsoft Foundry"
        )
    app = create_app(
        store,
        passcode=passcode,
        session_secret=os.environ.get("INBOX_HELPER_SESSION_SECRET") or secrets.token_urlsafe(32),
        source=source,
        https_only=not local,
        live=live,
        live_cap_per_day=int(os.environ.get("INBOX_HELPER_LIVE_CAP", "40")),
    )
    print(f"Review desk: http://{args.host}:{args.port}  (drafts from {source})")
    uvicorn.run(app, host=args.host, port=args.port, log_level="warning", proxy_headers=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(prog="inbox-helper", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    ev = commands.add_parser("eval", help="process a labelled inbox and score it")
    ev.add_argument("--limit", type=int, default=None, help="only the first N messages")

    pl = commands.add_parser("planted", help="run the planted drafts past a reviewer")
    pl.add_argument("--reviewer", choices=["critic", "judge"], default="critic")

    jd = commands.add_parser("judge", help="score a recorded run's drafts against the rubric")

    sv = commands.add_parser("serve", help="process an inbox and open the review desk")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    sv.add_argument(
        "--try-hosted",
        action="store_true",
        help="add a form that sends one typed message to the hosted agent",
    )

    for sub in (ev, jd, sv):
        sub.add_argument("--set", choices=sorted(SETS), default="golden", help="which inbox")
        sub.add_argument("--recording", type=Path, default=None, help="pipeline recording to use")
    for sub in (ev, pl, jd):
        sub.add_argument("--record", action="store_true", help="with --live: save for replay")
        sub.add_argument("--concurrency", type=int, default=4)
        sub.add_argument("--out", type=Path, default=None, help="write the result as JSON")
    for sub in (ev, pl, jd, sv):
        sub.add_argument("--live", action="store_true", help="call live models, not a replay")
    for sub in (ev, sv):
        sub.add_argument("--hosted", action="store_true", help="use the agent hosted on Foundry")

    args = parser.parse_args(argv)
    if args.command == "serve":
        return _serve(args)
    handler = {"eval": _eval, "planted": _planted, "judge": _judge}[args.command]
    return asyncio.run(handler(args, argv))


if __name__ == "__main__":
    raise SystemExit(main())
