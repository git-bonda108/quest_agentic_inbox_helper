"""Routing, deterministic draft checks and the per-message pipeline.

The pipeline is tested with a scripted team, so these tests need no model.
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence

import pytest

from inbox_helper.checks import MAX_WORDS, SIGN_OFF, draft_problems
from inbox_helper.models import Action, Intent, Message
from inbox_helper.pipeline import process_inbox
from inbox_helper.routing import CONFIDENCE_FLOOR, route
from inbox_helper.store import Store
from inbox_helper.team import Classification, Critique

GOOD = f"Thank you for your message. We review applications within 5 business days.\n\n{SIGN_OFF}"


def _message(message_id: str, body: str = "Any update?") -> Message:
    return Message.model_validate(
        {
            "id": message_id,
            "received_at": "2026-11-09T08:12:00Z",
            "from_name": "Aiko Tanaka",
            "from_email": "aiko.tanaka@example.com",
            "subject": "Hello",
            "body": body,
        }
    )


class ScriptedTeam:
    """Returns canned answers and counts calls."""

    def __init__(
        self,
        intent: Intent = Intent.STATUS_CHECK,
        confidence: float = 0.95,
        drafts: Sequence[str] = (GOOD,),
        critiques: Sequence[Critique] = (Critique(acceptable=True, problems=[]),),
        fail_on: str | None = None,
    ) -> None:
        self.intent, self.confidence = intent, confidence
        self.drafts, self.critiques = list(drafts), list(critiques)
        self.fail_on = fail_on
        self.draft_calls = 0
        self.critique_calls = 0
        self.feedback_seen: list[list[str]] = []

    async def classify(self, message: Message) -> Classification:
        if message.id == self.fail_on:
            raise RuntimeError("model unavailable")
        return Classification(intent=self.intent, confidence=self.confidence, reason="scripted")

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str:
        self.feedback_seen.append(list(feedback))
        text = self.drafts[min(self.draft_calls, len(self.drafts) - 1)]
        self.draft_calls += 1
        return text

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique:
        verdict = self.critiques[min(self.critique_calls, len(self.critiques) - 1)]
        self.critique_calls += 1
        return verdict


def _run(team: ScriptedTeam, *messages: Message) -> Store:
    store = Store(":memory:")
    asyncio.run(process_inbox(store, team, list(messages)))
    return store


# -- routing ------------------------------------------------------------------


@pytest.mark.parametrize(
    ("intent", "expected"),
    [
        (Intent.STATUS_CHECK, Action.DRAFT),
        (Intent.ACCOMMODATION_REQUEST, Action.DRAFT),
        (Intent.ESCALATE, Action.ESCALATE),
        (Intent.NOT_CANDIDATE, Action.IGNORE),
    ],
)
def test_route_follows_the_table(intent: Intent, expected: Action) -> None:
    assert route(intent, 0.99) is expected


def test_every_intent_has_a_route() -> None:
    for intent in Intent:
        assert isinstance(route(intent, 1.0), Action)


def test_confidence_just_below_the_floor_goes_to_a_person() -> None:
    assert route(Intent.STATUS_CHECK, CONFIDENCE_FLOOR) is Action.DRAFT
    assert route(Intent.STATUS_CHECK, CONFIDENCE_FLOOR - 0.01) is Action.ESCALATE
    assert route(Intent.NOT_CANDIDATE, CONFIDENCE_FLOOR - 0.01) is Action.ESCALATE


# -- deterministic draft checks -------------------------------------------------


def test_a_good_draft_has_no_problems() -> None:
    assert draft_problems(GOOD) == []


def test_word_limit_boundary() -> None:
    sign_off_words = len(SIGN_OFF.split())
    at_limit = " ".join(["word"] * (MAX_WORDS - sign_off_words)) + f"\n\n{SIGN_OFF}"
    over_limit = "word " + at_limit
    assert draft_problems(at_limit) == []
    assert any("words" in p for p in draft_problems(over_limit))


@pytest.mark.parametrize(
    "bad",
    [
        f"Great news!\n\n{SIGN_OFF}",
        f"The salary is $95,000.\n\n{SIGN_OFF}",
        f"The trial pays 400 EUR per day.\n\n{SIGN_OFF}",
        f"We offer 80k for this role.\n\n{SIGN_OFF}",
        "Thank you for your message.",
        "   ",
    ],
)
def test_bad_drafts_are_caught(bad: str) -> None:
    assert draft_problems(bad) != []


def test_policy_numbers_are_not_mistaken_for_money() -> None:
    text = f"You may reschedule once with 24 hours' notice, within 5 business days.\n\n{SIGN_OFF}"
    assert draft_problems(text) == []


# -- pipeline -----------------------------------------------------------------


def test_drafted_message_is_stored_and_awaits_review() -> None:
    store = _run(ScriptedTeam(), _message("m1"))
    triage, draft = store.triage("m1"), store.draft("m1")
    assert triage is not None
    assert triage.action is Action.DRAFT
    assert draft is not None
    assert draft.text == GOOD
    assert store.outbox() == []


def test_escalated_message_never_reaches_the_drafter() -> None:
    team = ScriptedTeam(intent=Intent.ESCALATE)
    store = _run(team, _message("m1"))
    assert team.draft_calls == 0
    assert store.draft("m1") is None


def test_low_confidence_is_escalated_without_drafting() -> None:
    team = ScriptedTeam(confidence=0.4)
    store = _run(team, _message("m1"))
    triage = store.triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert team.draft_calls == 0


def test_out_of_range_confidence_is_treated_as_zero() -> None:
    store = _run(ScriptedTeam(confidence=7.0), _message("m1"))
    triage = store.triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE


def test_failed_check_is_fed_back_and_the_retry_is_used() -> None:
    team = ScriptedTeam(drafts=[f"You got the job!\n\n{SIGN_OFF}", GOOD])
    store = _run(team, _message("m1"))
    draft = store.draft("m1")
    assert draft is not None
    assert draft.text == GOOD
    assert team.draft_calls == 2
    assert team.feedback_seen[0] == []
    assert team.feedback_seen[1] != []
    assert team.critique_calls == 1  # the critic never sees a draft that failed code checks


def test_critic_rejection_is_fed_back() -> None:
    team = ScriptedTeam(
        critiques=[
            Critique(acceptable=False, problems=["States an outcome."]),
            Critique(acceptable=True, problems=[]),
        ]
    )
    store = _run(team, _message("m1"))
    assert store.draft("m1") is not None
    assert team.feedback_seen[1] == ["States an outcome."]


def test_no_acceptable_draft_goes_to_a_person_with_the_reason() -> None:
    team = ScriptedTeam(critiques=[Critique(acceptable=False, problems=["Invents a date."])])
    store = _run(team, _message("m1"))
    triage = store.triage("m1")
    assert store.draft("m1") is None
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert triage.intent is Intent.STATUS_CHECK
    assert "Invents a date." in triage.reason


def test_one_failing_message_does_not_stop_the_batch_and_is_reported() -> None:
    team = ScriptedTeam(fail_on="m2")
    store = Store(":memory:")
    outcomes = asyncio.run(
        process_inbox(store, team, [_message("m1"), _message("m2"), _message("m3")])
    )
    by_id = {o.message_id: o for o in outcomes}
    assert by_id["m2"].error is not None
    assert by_id["m1"].drafted
    assert by_id["m3"].drafted
    assert store.triage("m2") is None
    assert "failed" in [e.event for e in store.audit_trail()]
