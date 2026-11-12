"""Typed records. Every hand-off and every stored row is one of these."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class Intent(StrEnum):
    """What the sender wants. The list is fixed in intent.md."""

    STATUS_CHECK = "status_check"
    RESCHEDULE = "reschedule"
    WITHDRAW = "withdraw"
    COMPENSATION_QUESTION = "compensation_question"
    ASSESSMENT_ISSUE = "assessment_issue"
    DOCUMENT_SUBMISSION = "document_submission"
    FEEDBACK_REQUEST = "feedback_request"
    ACCOMMODATION_REQUEST = "accommodation_request"
    ESCALATE = "escalate"
    NOT_CANDIDATE = "not_candidate"


class Handoff(StrEnum):
    """A reason a person must handle a message, whatever else it asks for."""

    COMPLAINT = "complaint"
    DISCRIMINATION = "discrimination"
    LEGAL = "legal"
    DATA_REQUEST = "data_request"
    DISTRESS = "distress"
    IDENTITY_DOCUMENT = "identity_document"
    THREAT_OR_ABUSE = "threat_or_abuse"
    THIRD_PARTY = "third_party"


class Action(StrEnum):
    """What the tool does with a message. Chosen by code, never by a model."""

    DRAFT = "draft"
    ESCALATE = "escalate"
    IGNORE = "ignore"


class Stage(StrEnum):
    """Hiring stage, when the hiring system supplies it with the message."""

    APPLICATION_REVIEW = "application_review"
    TAKE_HOME = "take_home"
    PEOPLE_CALL = "people_call"
    PAID_TRIAL = "paid_trial"


class _Record(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Message(_Record):
    id: str = Field(min_length=1)
    received_at: datetime
    from_name: str
    from_email: str = Field(pattern=r"^[^@\s]+@[^@\s]+$")
    subject: str
    body: str
    stage: Stage | None = None


class Triage(_Record):
    message_id: str
    intent: Intent
    action: Action
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str


class Draft(_Record):
    message_id: str
    text: str = Field(min_length=1)
    origin: Literal["agent", "reviewer"]
    updated_at: datetime


class Decision(_Record):
    """A reviewer's verdict on one exact text, identified by its hash."""

    id: int
    message_id: str
    reviewer: str
    approved: bool
    text_sha256: str
    decided_at: datetime


class OutboxEntry(_Record):
    message_id: str
    to_email: str
    text: str
    text_sha256: str
    decision_id: int
    sent_at: datetime


class AuditEvent(_Record):
    id: int
    at: datetime
    actor: str
    event: str
    message_id: str | None
    detail: str
