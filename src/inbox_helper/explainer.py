"""The data behind the animated explainer, taken from recorded live runs.

Nothing in the explainer is typed by hand. This module replays two recorded runs
through the real pipeline, notes every agent call and every code decision for the
messages it shows, and writes them to ``web/explainer.json``. A test rebuilds the
file from the recordings and fails if the two differ.

Run ``python -m inbox_helper.explainer`` to rebuild the file.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from inbox_helper.checks import MAX_WORDS, draft_problems
from inbox_helper.models import Action, Intent, Message
from inbox_helper.pipeline import MAX_DRAFT_ATTEMPTS, Outcome, admit, process_message
from inbox_helper.recording import RecordedTeam
from inbox_helper.routing import CONFIDENCE_FLOOR
from inbox_helper.store import Store, text_hash
from inbox_helper.team import Classification, Critique, InputBlockedError

ROOT = Path(__file__).resolve().parents[2]
STORY_FILE = Path(__file__).parent / "web" / "explainer.json"

# Two recorded runs of the same agents and models: the 44-message unseen set and
# the 42-message golden set. Marcus's message comes from the golden run because it
# is one where the Critic sent a draft back, which the unseen run never did.
RUNS = {
    "unseen": (ROOT / "data/inbox/unseen.jsonl", ROOT / "data/recordings/unseen.json"),
    "golden": (ROOT / "data/inbox/messages.jsonl", ROOT / "data/recordings/golden.json"),
}
# Inbox order on screen: (run, message id).
SHOWN = [
    ("unseen", "u001"),
    ("golden", "m022"),
    ("unseen", "u003"),
    ("unseen", "u014"),
    ("unseen", "u005"),
    ("unseen", "u009"),
    ("unseen", "u015"),
    ("unseen", "u010"),
    ("unseen", "u008"),
]
FOCUS = "m022"
# The message with an instruction hidden in double brackets.
INJECTED = "u015"
# The sentence in Marcus's first draft that the Critic's note asks to remove.
FLAGGED = "A member of the hiring team will follow up if any further information is available."
REVIEWER = "Rita"


class StoryError(ValueError):
    """The recordings no longer tell the story the explainer shows."""


@dataclass
class _Calls:
    classification: Classification | None = None
    blocked: list[str] | None = None
    attempts: list[dict[str, Any]] = field(default_factory=list)


class _Tracer:
    """Passes every call to the recording and keeps a copy of what came back."""

    def __init__(self, team: RecordedTeam) -> None:
        self.team = team
        self.calls: dict[str, _Calls] = {}

    def _of(self, message: Message) -> _Calls:
        return self.calls.setdefault(message.id, _Calls())

    async def classify(self, message: Message) -> Classification:
        try:
            result = await self.team.classify(message)
        except InputBlockedError as blocked:
            self._of(message).blocked = list(blocked.categories)
            raise
        self._of(message).classification = result
        return result

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str:
        text = await self.team.draft(message, intent, feedback)
        self._of(message).attempts.append(
            {"feedback": list(feedback), "text": text.strip(), "checks": draft_problems(text)}
        )
        return text

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique:
        result = await self.team.critique(message, intent, draft)
        self._of(message).attempts[-1]["critique"] = result.model_dump(mode="json")
        return result


def _label(intent: Intent) -> str:
    return intent.value.replace("_", " ").capitalize()


def _initials(name: str) -> str:
    parts = [p for p in name.replace("-", " ").split() if p[:1].isalpha()]
    return (parts[0][0] + (parts[-1][0] if len(parts) > 1 else "")).upper()


async def _replay(run: str, ids: list[str]) -> tuple[dict[str, Any], dict[str, Any]]:
    inbox, recording = RUNS[run]
    raw = {m["id"]: m for m in map(json.loads, inbox.read_text("utf-8").splitlines())}
    team = RecordedTeam(recording)
    tracer = _Tracer(team)
    store = Store(":memory:")
    shown: dict[str, Any] = {}
    for message_id in ids:
        message = Message.model_validate(raw[message_id])
        admit(store, [message])
        outcome = await process_message(store, tracer, message)
        calls = tracer.calls.get(message_id, _Calls())
        shown[message_id] = {"message": message, "outcome": outcome, "calls": calls}
    return shown, dict(team.meta)


def _row(message: Message, outcome: Outcome, calls: _Calls) -> dict[str, Any]:
    first = message.from_name.split()[0]
    row: dict[str, Any] = {
        "key": message.id,
        "name": message.from_name,
        "first": first,
        "initials": _initials(message.from_name),
        "subject": message.subject,
        "blocked": calls.blocked is not None,
    }
    if calls.blocked is not None:
        return row | {
            "group": "person",
            "lane": "person",
            "tag": "Needs a person",
            "why": "blocked by the guardrail",
        }
    c = calls.classification
    if c is None:
        raise StoryError(f"{message.id} has no recorded classification")
    handoff = [h.value.replace("_", " ") for h in c.handoff]
    row |= {
        "group": c.intent.value,
        "wants": _label(c.intent),
        "person": ("yes: " + ", ".join(handoff)) if handoff else "no",
        "confidence": f"{c.confidence:.2f}",
    }
    if outcome.action is Action.ESCALATE:
        return row | {"lane": "person", "tag": "Needs a person", "why": ", ".join(handoff)}
    if outcome.action is Action.IGNORE:
        return row | {"lane": "aside", "tag": "Set aside", "why": "not a candidate"}
    if not outcome.drafted:
        raise StoryError(f"{message.id} was routed to drafting but has no accepted draft")
    return row | {
        "lane": c.intent.value,
        "tag": "To the Drafter",
        "why": "",
        "attempts": outcome.attempts,
    }


def build_story() -> dict[str, Any]:
    by_run: dict[str, list[str]] = {}
    for run, message_id in SHOWN:
        by_run.setdefault(run, []).append(message_id)
    traced: dict[str, Any] = {}
    meta: dict[str, dict[str, Any]] = {}
    for run, ids in by_run.items():
        shown, meta[run] = asyncio.run(_replay(run, ids))
        traced |= shown

    rows = [_row(**traced[mid]) for _, mid in SHOWN]
    workers = {m["worker"] for m in meta.values()}
    critics = {m["critic"] for m in meta.values()}
    if len(workers) != 1 or len(critics) != 1:
        raise StoryError("the runs shown must use the same models")

    focus = traced[FOCUS]
    message: Message = focus["message"]
    attempts = focus["calls"].attempts
    final = attempts[-1]["text"]
    if FLAGGED not in attempts[0]["text"] or FLAGGED in final:
        raise StoryError("the flagged sentence must be in the first draft and not the last")
    blocked = next(r for r in rows if r["blocked"])
    blocked_message: Message = traced[blocked["key"]]["message"]
    injected: Message = traced[INJECTED]["message"]

    lanes: list[dict[str, Any]] = []
    for intent in Intent:
        count = sum(1 for r in rows if r["lane"] == intent.value)
        if count:
            lanes.append({"key": intent.value, "label": _label(intent), "count": count})
    lanes.append(
        {
            "key": "person",
            "label": "Needs a person",
            "count": sum(r["lane"] == "person" for r in rows),
        }
    )
    lanes.append(
        {"key": "aside", "label": "Set aside", "count": sum(r["lane"] == "aside" for r in rows)}
    )

    focus_row = next(r for r in rows if r["key"] == FOCUS)
    digest = text_hash(final)[:12]
    return {
        "rows": rows,
        "lanes": lanes,
        "worker_model": workers.pop(),
        "critic_model": critics.pop(),
        "recorded": sorted({m["recorded_at"][:10] for m in meta.values()}),
        "floor": f"{CONFIDENCE_FLOOR:.2f}",
        "max_words": MAX_WORDS,
        "max_attempts": MAX_DRAFT_ATTEMPTS,
        "reviewer": REVIEWER,
        "blocked": {
            "key": blocked["key"],
            "name": blocked_message.from_name,
            "subject": blocked_message.subject,
            "ask": blocked_message.body.split("\n\n", 1)[0],
            "hidden": blocked_message.body.split("\n\n", 1)[1],
        },
        "injected": {
            "key": injected.id,
            "first": injected.from_name.split()[0],
            "hidden": injected.body.split("[[", 1)[1].split("]]", 1)[0].split(": ", 1)[1],
        },
        "focus": {
            "key": message.id,
            "name": message.from_name,
            "first": message.from_name.split()[0],
            "email": message.from_email,
            "subject": message.subject,
            "body": message.body,
            "group": _label(traced[FOCUS]["calls"].classification.intent),
            "attempts": attempts,
            "flagged": FLAGGED,
            "final": final,
            "words": len(final.split()),
            "digest": digest,
            "audit": [
                ["system", "message_added", ""],
                ["system", "triaged", f"{focus_row['group']} -> draft"],
                ["system", "draft_saved", f"agent {digest}"],
                [REVIEWER, "approved", digest],
                ["system", "sent", f"decision 1 {digest}"],
            ],
        },
    }


def write_story(path: Path = STORY_FILE) -> None:
    path.write_text(
        json.dumps(build_story(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    write_story()
    print(f"wrote {STORY_FILE.relative_to(ROOT)}")
