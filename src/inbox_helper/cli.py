"""Command line entry point."""

from __future__ import annotations

import argparse
import asyncio
import os
import statistics
import sys
from pathlib import Path

from inbox_helper.evaluate import Report, evaluate, load_labels, load_messages
from inbox_helper.pipeline import process_inbox
from inbox_helper.recording import RecordedTeam
from inbox_helper.store import Store
from inbox_helper.team import Team

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INBOX = ROOT / "data" / "inbox" / "messages.jsonl"
DEFAULT_LABELS = ROOT / "evals" / "golden" / "labels.jsonl"
DEFAULT_POLICY = ROOT / "data" / "policy" / "hiring_policy.md"
DEFAULT_RECORDING = ROOT / "data" / "recordings" / "golden.json"
WORKER_MODEL = os.environ.get("INBOX_HELPER_WORKER_MODEL", "gpt-5.6-luna")
CRITIC_MODEL = os.environ.get("INBOX_HELPER_CRITIC_MODEL", "gpt-5.5")


def _print_report(report: Report, source: str) -> None:
    print(f"source:            {source}")
    print(f"messages:          {report.total}")
    print(
        f"intent accuracy:   {report.intent_correct}/{report.total} = {report.intent_accuracy:.1%}"
    )
    print(
        f"action accuracy:   {report.action_correct}/{report.total} = {report.action_accuracy:.1%}"
    )
    print(f"drafts written:    {report.drafts} (longest: {report.longest_draft_words} words)")
    print(
        f"escalations given a draft: {len(report.escalations_drafted)} {report.escalations_drafted}"
    )
    print(f"failures:          {len(report.failures)}")
    for failure in report.failures:
        print(f"  FAILED {failure}")
    for miss in report.misses:
        print(
            f"  MISS {miss['id']}: expected {miss['expected']}, got {miss['got']} "
            f"({miss['confidence']}) {miss['reason']}"
        )


async def _eval(args: argparse.Namespace) -> int:
    messages = load_messages(args.inbox)[: args.limit]
    labels = load_labels(args.labels)
    store = Store(":memory:")
    team: Team
    if args.live:
        from inbox_helper.foundry_team import FoundryTeam  # imported late: needs cloud packages

        endpoint = os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        if not endpoint:
            print("FOUNDRY_PROJECT_ENDPOINT is not set; see .env.example", file=sys.stderr)
            return 2
        live = FoundryTeam(endpoint, WORKER_MODEL, CRITIC_MODEL, args.policy.read_text("utf-8"))
        meta = {"worker_model": WORKER_MODEL, "critic_model": CRITIC_MODEL}
        recorder = RecordedTeam(args.recording, live=live, meta=meta)
        team = recorder
        try:
            outcomes = await process_inbox(store, team, messages, concurrency=args.concurrency)
        finally:
            await live.aclose()
        if args.record and not any(o.error for o in outcomes):
            recorder.save()
            print(f"recorded to {args.recording.relative_to(ROOT)}")
        source = f"live models ({WORKER_MODEL}, critic {CRITIC_MODEL})"
        calls = live.ledger
        if calls:
            seconds = sorted(c.seconds for c in calls)
            p95 = seconds[max(0, round(0.95 * len(seconds)) - 1)]
            print(f"model calls:       {len(calls)}")
            print(
                f"tokens in/out:     {sum(c.input_tokens for c in calls)}/"
                f"{sum(c.output_tokens for c in calls)}"
            )
            print(f"call latency:      median {statistics.median(seconds):.2f}s, p95 {p95:.2f}s")
    else:
        replay = RecordedTeam(args.recording)
        outcomes = await process_inbox(store, replay, messages, concurrency=args.concurrency)
        source = (
            f"RECORDED model outputs from {replay.meta.get('recorded_at', '?')} "
            f"({replay.meta.get('worker_model', '?')}, "
            f"critic {replay.meta.get('critic_model', '?')})"
        )
    report = evaluate(store, outcomes, labels)
    _print_report(report, source)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(report.to_json(), encoding="utf-8")
    return 1 if report.failures or report.escalations_drafted else 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="inbox-helper", description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    ev = commands.add_parser("eval", help="process the labelled inbox and score it")
    ev.add_argument("--inbox", type=Path, default=DEFAULT_INBOX)
    ev.add_argument("--labels", type=Path, default=DEFAULT_LABELS)
    ev.add_argument("--policy", type=Path, default=DEFAULT_POLICY)
    ev.add_argument("--recording", type=Path, default=DEFAULT_RECORDING)
    ev.add_argument("--live", action="store_true", help="call live models instead of replaying")
    ev.add_argument("--record", action="store_true", help="with --live: save answers for replay")
    ev.add_argument("--limit", type=int, default=None, help="only the first N messages")
    ev.add_argument("--concurrency", type=int, default=4)
    ev.add_argument("--out", type=Path, default=None, help="write the report as JSON")
    args = parser.parse_args(argv)
    return asyncio.run(_eval(args))


if __name__ == "__main__":
    raise SystemExit(main())
