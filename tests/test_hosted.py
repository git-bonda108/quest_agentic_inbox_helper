"""Processing an inbox through the hosted agent: every reply ends in the right place."""

from __future__ import annotations

import asyncio

from inbox_helper.hosted import process_inbox_hosted
from inbox_helper.models import Action, Intent, Message
from inbox_helper.service import Proposal, Reply
from inbox_helper.store import Store
from inbox_helper.team import InputBlockedError
from scripted import GOOD, message


class FakeAgent:
    """Stands in for the hosted agent. Answers by message id."""

    def __init__(self, replies: dict[str, Reply | Exception]) -> None:
        self.replies = replies

    async def propose(self, message: Message) -> Reply:
        reply = self.replies[message.id]
        if isinstance(reply, Exception):
            raise reply
        return reply


def _proposal(message_id: str, action: Action, draft: str | None) -> Reply:
    intent = Intent.STATUS_CHECK if action is Action.DRAFT else Intent.ESCALATE
    return Reply(
        proposal=Proposal(
            message_id=message_id,
            intent=intent,
            action=action,
            confidence=0.9,
            reason="because",
            draft=draft,
            blocked=False,
        )
    )


def _run(replies: dict[str, Reply | Exception]) -> tuple[Store, dict[str, object]]:
    store = Store(":memory:")
    messages = [message(message_id) for message_id in replies]
    outcomes = asyncio.run(process_inbox_hosted(store, FakeAgent(replies), messages))
    return store, {outcome.message_id: outcome for outcome in outcomes}


def test_a_proposal_with_a_draft_is_stored_for_review_and_not_sent() -> None:
    store, _ = _run({"m1": _proposal("m1", Action.DRAFT, GOOD)})
    draft = store.draft("m1")
    assert draft is not None
    assert draft.text == GOOD
    assert store.outbox() == []


def test_a_proposal_for_a_person_stores_no_draft() -> None:
    store, _ = _run({"m1": _proposal("m1", Action.ESCALATE, None)})
    triage = store.triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert store.draft("m1") is None


def test_a_request_the_platform_blocks_goes_to_a_person() -> None:
    store, outcomes = _run({"m1": InputBlockedError(["content safety policy"])})
    triage = store.triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert "content safety policy" in triage.reason
    assert getattr(outcomes["m1"], "blocked", False)


def test_a_refusal_or_a_crash_is_reported_and_the_rest_carry_on() -> None:
    store, outcomes = _run(
        {
            "m1": Reply(error="Processing failed: RuntimeError."),
            "m2": RuntimeError("connection reset"),
            "m3": _proposal("m3", Action.DRAFT, GOOD),
        }
    )
    assert getattr(outcomes["m1"], "error", None)
    assert getattr(outcomes["m2"], "error", None)
    assert store.draft("m3") is not None
    assert [e.event for e in store.audit_trail()].count("failed") == 2


def test_a_draft_that_breaks_a_code_check_is_not_trusted_just_because_the_agent_sent_it() -> None:
    """The caller re-runs the deterministic checks. A hosted agent's word is not enough."""
    store, outcomes = _run({"m1": _proposal("m1", Action.DRAFT, "The salary is $95,000.")})
    triage = store.triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert store.draft("m1") is None
    assert not getattr(outcomes["m1"], "drafted", True)


def test_a_reply_about_a_different_message_is_a_failure() -> None:
    _, outcomes = _run({"m1": _proposal("someone-else", Action.DRAFT, GOOD)})
    assert getattr(outcomes["m1"], "error", None)
