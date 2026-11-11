"""The send gate. This is the only module that writes to the outbox.

A reply is sent only when the reviewer's latest decision on the message is an
approval of the exact text that is about to go out. Sending is plain code: no
agent holds a reference to this function.

"Sent" means a row in the simulated outbox. No real mailbox is connected.
"""

from __future__ import annotations

from inbox_helper.models import Action, OutboxEntry
from inbox_helper.store import SYSTEM_ACTOR, Store, text_hash, utc_now


class NotApprovedError(PermissionError):
    """The reply may not be sent. The message says why."""


def send(store: Store, message_id: str) -> OutboxEntry:
    """Send the approved reply for one message, at most once.

    Calling it again for a message that was already sent returns the original
    outbox entry and sends nothing, so a retry cannot produce a duplicate.
    """
    with store.transaction() as db:
        already = db.execute(
            "SELECT message_id, to_email, text, text_sha256, decision_id, sent_at "
            "FROM outbox WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        if already is not None:
            return OutboxEntry.model_validate(dict(already))

        message = store.message(message_id)
        triage = store.triage(message_id)
        if triage is None or triage.action is not Action.DRAFT:
            raise NotApprovedError(f"{message_id} is not routed to drafting")

        draft = store.draft(message_id)
        if draft is None:
            raise NotApprovedError(f"{message_id} has no draft")

        decision = store.latest_decision(message_id)
        if decision is None:
            raise NotApprovedError(f"{message_id} has not been reviewed")
        if not decision.approved:
            raise NotApprovedError(f"{message_id} was rejected by {decision.reviewer}")

        digest = text_hash(draft.text)
        if decision.text_sha256 != digest:
            raise NotApprovedError(f"{message_id} was edited after it was approved")

        entry = OutboxEntry(
            message_id=message_id,
            to_email=message.from_email,
            text=draft.text,
            text_sha256=digest,
            decision_id=decision.id,
            sent_at=utc_now(),
        )
        db.execute(
            "INSERT INTO outbox (message_id, to_email, text, text_sha256, decision_id, sent_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                entry.message_id,
                entry.to_email,
                entry.text,
                entry.text_sha256,
                entry.decision_id,
                entry.sent_at.isoformat(),
            ),
        )
        store.log(db, SYSTEM_ACTOR, "sent", message_id, f"decision {decision.id} {digest[:12]}")
    return entry
