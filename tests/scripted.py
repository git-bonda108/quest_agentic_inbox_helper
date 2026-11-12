"""A scripted team and sample data for tests. No model is called."""

from __future__ import annotations

from collections.abc import Sequence

from inbox_helper.checks import SIGN_OFF
from inbox_helper.models import Handoff, Intent, Message
from inbox_helper.team import Classification, Critique, InputBlockedError

GOOD = f"Thank you for your message. We review applications within 5 business days.\n\n{SIGN_OFF}"


def message(message_id: str, body: str = "Any update?") -> Message:
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
        block_at: str | None = None,
        handoff: Sequence[Handoff] = (),
    ) -> None:
        self.handoff = list(handoff)
        self.intent, self.confidence = intent, confidence
        self.drafts, self.critiques = list(drafts), list(critiques)
        self.fail_on = fail_on
        self.block_at = block_at
        self.draft_calls = 0
        self.critique_calls = 0
        self.feedback_seen: list[list[str]] = []

    async def classify(self, message: Message) -> Classification:
        if message.id == self.fail_on:
            raise RuntimeError("model unavailable")
        if self.block_at == "classify":
            raise InputBlockedError(["jailbreak"])
        return Classification(
            intent=self.intent,
            confidence=self.confidence,
            reason="scripted",
            handoff=self.handoff,
        )

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str:
        if self.block_at == "draft":
            raise InputBlockedError(["jailbreak"])
        self.feedback_seen.append(list(feedback))
        text = self.drafts[min(self.draft_calls, len(self.drafts) - 1)]
        self.draft_calls += 1
        return text

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique:
        if self.block_at == "critique":
            raise InputBlockedError(["violence", "jailbreak"])
        verdict = self.critiques[min(self.critique_calls, len(self.critiques) - 1)]
        self.critique_calls += 1
        return verdict
