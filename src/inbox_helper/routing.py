"""Routing: code, not a model, decides what happens to a message."""

from __future__ import annotations

from inbox_helper.models import Action, Intent

# Below this confidence the classifier's answer is not trusted and a person takes over.
CONFIDENCE_FLOOR = 0.70

_ACTIONS: dict[Intent, Action] = {
    Intent.STATUS_CHECK: Action.DRAFT,
    Intent.RESCHEDULE: Action.DRAFT,
    Intent.WITHDRAW: Action.DRAFT,
    Intent.COMPENSATION_QUESTION: Action.DRAFT,
    Intent.ASSESSMENT_ISSUE: Action.DRAFT,
    Intent.DOCUMENT_SUBMISSION: Action.DRAFT,
    Intent.FEEDBACK_REQUEST: Action.DRAFT,
    Intent.ACCOMMODATION_REQUEST: Action.DRAFT,
    Intent.ESCALATE: Action.ESCALATE,
    Intent.NOT_CANDIDATE: Action.IGNORE,
}


def route(intent: Intent, confidence: float) -> Action:
    """Map a classified intent to an action. Low confidence always goes to a person."""
    if confidence < CONFIDENCE_FLOOR:
        return Action.ESCALATE
    return _ACTIONS[intent]
