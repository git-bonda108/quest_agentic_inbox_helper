"""Fixed sequence for one message: classify, route, draft, check, critique.

Code owns the order and every decision. The agents only classify and write.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

from inbox_helper.checks import draft_problems
from inbox_helper.models import Action, Intent, Message, Triage
from inbox_helper.routing import route
from inbox_helper.store import Store
from inbox_helper.team import InputBlockedError, Team

MAX_DRAFT_ATTEMPTS = 2
DEFAULT_CONCURRENCY = 4


@dataclass(frozen=True)
class Outcome:
    message_id: str
    intent: Intent | None
    action: Action | None
    drafted: bool
    attempts: int = 0
    error: str | None = None
    blocked: bool = False


def _hand_to_a_person(
    store: Store, message: Message, intent: Intent | None, blocked: InputBlockedError
) -> Outcome:
    """The platform refused the message. Nobody guesses; a person reads it."""
    store.save_triage(
        Triage(
            message_id=message.id,
            intent=intent or Intent.ESCALATE,
            action=Action.ESCALATE,
            confidence=1.0,
            reason=(
                "The platform's content filter blocked this message "
                f"({', '.join(blocked.categories)}), so no model handled it. "
                "A person should read it."
            ),
        )
    )
    return Outcome(message.id, intent, Action.ESCALATE, drafted=False, blocked=True)


async def process_message(store: Store, team: Team, message: Message) -> Outcome:
    try:
        classification = await team.classify(message)
    except InputBlockedError as blocked:
        return _hand_to_a_person(store, message, None, blocked)
    confidence = classification.confidence if 0.0 <= classification.confidence <= 1.0 else 0.0
    asked, handoff = classification.intent, classification.handoff
    action = route(asked, confidence, handoff)
    intent, reason = asked, classification.reason
    if handoff:
        # Group it under "needs a person", and keep what was asked visible to that person.
        intent = Intent.ESCALATE
        reasons = ", ".join(sorted(item.value for item in handoff))
        reason = f"Needs a person: {reasons}. Asked for: {asked.value}. {classification.reason}"
    store.save_triage(
        Triage(
            message_id=message.id,
            intent=intent,
            action=action,
            confidence=confidence,
            reason=reason,
        )
    )
    if action is not Action.DRAFT:
        return Outcome(message.id, intent, action, drafted=False)

    feedback: list[str] = []
    try:
        for attempt in range(1, MAX_DRAFT_ATTEMPTS + 1):
            text = (await team.draft(message, intent, feedback)).strip()
            problems = draft_problems(text)
            if not problems:
                critique = await team.critique(message, intent, text)
                if critique.acceptable:
                    store.save_draft(message.id, text)
                    return Outcome(message.id, intent, action, drafted=True, attempts=attempt)
                problems = critique.problems or ["The critic rejected the draft without a reason."]
            feedback = problems
    except InputBlockedError as blocked:
        return _hand_to_a_person(store, message, intent, blocked)

    # No draft passed. A person takes over, and sees why.
    store.save_triage(
        Triage(
            message_id=message.id,
            intent=intent,
            action=Action.ESCALATE,
            confidence=confidence,
            reason=f"No acceptable draft after {MAX_DRAFT_ATTEMPTS} attempts: {' '.join(feedback)}",
        )
    )
    return Outcome(message.id, intent, Action.ESCALATE, drafted=False, attempts=MAX_DRAFT_ATTEMPTS)


async def process_inbox(
    store: Store,
    team: Team,
    messages: list[Message],
    *,
    concurrency: int = DEFAULT_CONCURRENCY,
) -> list[Outcome]:
    """Process a pile of messages. One failure is reported and never stops the rest."""
    for message in messages:
        store.add_message(message)
    gate = asyncio.Semaphore(concurrency)

    async def guarded(message: Message) -> Outcome:
        async with gate:
            try:
                return await process_message(store, team, message)
            except Exception as error:
                detail = f"{type(error).__name__}: {error}"
                store.record_failure(message.id, detail)
                return Outcome(message.id, None, None, drafted=False, error=detail)

    return list(await asyncio.gather(*(guarded(message) for message in messages)))
