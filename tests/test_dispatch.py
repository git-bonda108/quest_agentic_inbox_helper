"""The send gate: nothing reaches the outbox without a matching approval.

These tests were written before the code they judge (directive: checks first).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from inbox_helper.dispatch import NotApprovedError, send
from inbox_helper.models import Action, Intent, Message, Stage, Triage
from inbox_helper.store import DraftNotAllowedError, Store, UnknownMessageError

SRC = Path(__file__).resolve().parents[1] / "src" / "inbox_helper"


def _message(message_id: str = "m1") -> Message:
    return Message.model_validate(
        {
            "id": message_id,
            "received_at": "2026-11-09T08:12:00Z",
            "from_name": "Aiko Tanaka",
            "from_email": "aiko.tanaka@example.com",
            "subject": "Application status",
            "body": "Could you tell me where my application stands?",
            "stage": Stage.APPLICATION_REVIEW,
        }
    )


def _triage(message_id: str, intent: Intent, action: Action) -> Triage:
    return Triage(
        message_id=message_id, intent=intent, action=action, confidence=0.95, reason="test"
    )


@pytest.fixture
def store() -> Store:
    return Store(":memory:")


@pytest.fixture
def drafted(store: Store) -> Store:
    """A store holding one message that has an agent-written draft."""
    store.add_message(_message())
    store.save_triage(_triage("m1", Intent.STATUS_CHECK, Action.DRAFT))
    store.save_draft("m1", "Thanks for your message. We review applications within 5 days.")
    return store


def test_send_without_approval_is_refused(drafted: Store) -> None:
    with pytest.raises(NotApprovedError):
        send(drafted, "m1")
    assert drafted.outbox() == []


def test_approved_draft_is_sent_exactly_as_approved(drafted: Store) -> None:
    drafted.record_decision("m1", reviewer="rita", approved=True)
    entry = send(drafted, "m1")
    assert entry.text == "Thanks for your message. We review applications within 5 days."
    assert entry.to_email == "aiko.tanaka@example.com"
    assert [e.message_id for e in drafted.outbox()] == ["m1"]


def test_editing_after_approval_voids_the_approval(drafted: Store) -> None:
    drafted.record_decision("m1", reviewer="rita", approved=True)
    drafted.save_draft("m1", "You have the job.", origin="reviewer")
    with pytest.raises(NotApprovedError):
        send(drafted, "m1")
    assert drafted.outbox() == []


def test_edited_draft_can_be_sent_after_fresh_approval(drafted: Store) -> None:
    drafted.save_draft("m1", "Thank you. A recruiter will follow up.", origin="reviewer")
    drafted.record_decision("m1", reviewer="rita", approved=True)
    assert send(drafted, "m1").text == "Thank you. A recruiter will follow up."


def test_rejection_after_approval_revokes_it(drafted: Store) -> None:
    drafted.record_decision("m1", reviewer="rita", approved=True)
    drafted.record_decision("m1", reviewer="rita", approved=False)
    with pytest.raises(NotApprovedError):
        send(drafted, "m1")
    assert drafted.outbox() == []


def test_sending_twice_does_not_duplicate(drafted: Store) -> None:
    drafted.record_decision("m1", reviewer="rita", approved=True)
    first = send(drafted, "m1")
    second = send(drafted, "m1")
    assert first == second
    assert len(drafted.outbox()) == 1


@pytest.mark.parametrize(
    ("intent", "action"),
    [(Intent.ESCALATE, Action.ESCALATE), (Intent.NOT_CANDIDATE, Action.IGNORE)],
)
def test_messages_routed_away_from_drafting_cannot_get_a_draft(
    store: Store, intent: Intent, action: Action
) -> None:
    store.add_message(_message())
    store.save_triage(_triage("m1", intent, action))
    with pytest.raises(DraftNotAllowedError):
        store.save_draft("m1", "We are sorry to hear that.")
    with pytest.raises(NotApprovedError):
        send(store, "m1")
    assert store.outbox() == []


def test_untriaged_message_cannot_get_a_draft(store: Store) -> None:
    store.add_message(_message())
    with pytest.raises(DraftNotAllowedError):
        store.save_draft("m1", "Hello.")


def test_decision_needs_a_draft_and_a_named_reviewer(store: Store, drafted: Store) -> None:
    with pytest.raises(UnknownMessageError):
        store.record_decision("nope", reviewer="rita", approved=True)
    with pytest.raises(ValueError, match="reviewer"):
        drafted.record_decision("m1", reviewer="  ", approved=True)


def test_every_step_is_written_to_the_audit_trail(drafted: Store) -> None:
    drafted.record_decision("m1", reviewer="rita", approved=True)
    send(drafted, "m1")
    events = [e.event for e in drafted.audit_trail()]
    assert events == ["message_added", "triaged", "draft_saved", "approved", "sent"]
    assert drafted.audit_trail()[-2].actor == "rita"


def test_only_the_dispatch_module_writes_to_the_outbox() -> None:
    """Structural rule: one place in the codebase can put a row in the outbox."""
    writers = [
        path.name
        for path in SRC.rglob("*.py")
        if "INSERT INTO outbox" in path.read_text(encoding="utf-8")
    ]
    assert writers == ["dispatch.py"]
