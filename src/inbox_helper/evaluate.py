"""Score a processed inbox against the hand-written labels."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from inbox_helper.models import Action, Intent, Message
from inbox_helper.pipeline import Outcome
from inbox_helper.store import Store


class Label(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    intent: Intent
    action: Action
    note: str = ""


def load_messages(path: Path) -> list[Message]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Message.model_validate_json(line) for line in lines if line.strip()]


def load_labels(path: Path) -> dict[str, Label]:
    lines = path.read_text(encoding="utf-8").splitlines()
    labels = [Label.model_validate_json(line) for line in lines if line.strip()]
    return {label.id: label for label in labels}


@dataclass
class Report:
    total: int = 0
    intent_correct: int = 0
    action_correct: int = 0
    drafts: int = 0
    longest_draft_words: int = 0
    escalations_drafted: list[str] = field(default_factory=list)
    failures: list[str] = field(default_factory=list)
    misses: list[dict[str, str]] = field(default_factory=list)

    @property
    def intent_accuracy(self) -> float:
        return self.intent_correct / self.total if self.total else 0.0

    @property
    def action_accuracy(self) -> float:
        return self.action_correct / self.total if self.total else 0.0

    def to_json(self) -> str:
        data = asdict(self) | {
            "intent_accuracy": round(self.intent_accuracy, 4),
            "action_accuracy": round(self.action_accuracy, 4),
        }
        return json.dumps(data, indent=2) + "\n"


def evaluate(store: Store, outcomes: list[Outcome], labels: dict[str, Label]) -> Report:
    report = Report()
    for outcome in outcomes:
        label = labels[outcome.message_id]
        report.total += 1
        if outcome.error is not None:
            report.failures.append(f"{outcome.message_id}: {outcome.error}")
            continue
        triage = store.triage(outcome.message_id)
        draft = store.draft(outcome.message_id)
        if triage is None:
            report.failures.append(f"{outcome.message_id}: no triage stored")
            continue
        report.intent_correct += triage.intent is label.intent
        report.action_correct += triage.action is label.action
        if draft is not None:
            report.drafts += 1
            report.longest_draft_words = max(report.longest_draft_words, len(draft.text.split()))
            if label.action is Action.ESCALATE:
                report.escalations_drafted.append(outcome.message_id)
        if triage.intent is not label.intent or triage.action is not label.action:
            report.misses.append(
                {
                    "id": outcome.message_id,
                    "expected": f"{label.intent.value}/{label.action.value}",
                    "got": f"{triage.intent.value}/{triage.action.value}",
                    "confidence": f"{triage.confidence:.2f}",
                    "reason": triage.reason,
                }
            )
    return report
