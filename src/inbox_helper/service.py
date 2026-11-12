"""The tool as a service: one candidate message in, one proposal out.

This is what runs as a hosted agent. It classifies and drafts. It cannot send:
it holds no outbox, and the review desk and the send gate live with the caller.
The input is hostile text, so it is validated as a message before any model sees it.
"""

from __future__ import annotations

import json

from pydantic import BaseModel, ConfigDict, ValidationError

from inbox_helper.models import Action, Intent, Message
from inbox_helper.pipeline import process_message
from inbox_helper.store import Store
from inbox_helper.team import Team

MAX_INPUT_CHARS = 20_000


class Proposal(BaseModel):
    """What the tool proposes for one message. A person decides what happens next."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    message_id: str
    intent: Intent
    action: Action
    confidence: float
    reason: str
    draft: str | None
    blocked: bool


class Reply(BaseModel):
    """Exactly one of the two fields is set."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    proposal: Proposal | None = None
    error: str | None = None


def _refuse(error: str) -> str:
    return Reply(error=error).model_dump_json()


async def propose(text: str, team: Team) -> str:
    """Turn one message, given as JSON, into a proposal, given as JSON."""
    if len(text) > MAX_INPUT_CHARS:
        return _refuse(f"The input is too long: {len(text)} characters, limit {MAX_INPUT_CHARS}.")
    try:
        message = Message.model_validate(json.loads(text))
    except json.JSONDecodeError:
        return _refuse("The input must be one candidate message as a JSON object.")
    except ValidationError as error:
        fields = sorted(
            {".".join(str(part) for part in e["loc"]) or "message" for e in error.errors()}
        )
        return _refuse(f"The input is not a valid candidate message. Check: {', '.join(fields)}.")

    store = Store(":memory:")  # scratch space for this one message; nothing outlives the call
    store.add_message(message)
    try:
        outcome = await process_message(store, team, message)
    except Exception as error:
        return _refuse(f"Processing failed: {type(error).__name__}.")
    triage, draft = store.triage(message.id), store.draft(message.id)
    if triage is None:  # pragma: no cover - process_message always stores a triage
        return _refuse("Processing failed: no decision was stored.")
    proposal = Proposal(
        message_id=message.id,
        intent=triage.intent,
        action=triage.action,
        confidence=triage.confidence,
        reason=triage.reason,
        draft=draft.text if draft else None,
        blocked=outcome.blocked,
    )
    return Reply(proposal=proposal).model_dump_json()
