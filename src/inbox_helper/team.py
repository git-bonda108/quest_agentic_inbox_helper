"""The contract between the pipeline and the agents that do the language work.

The pipeline depends on this protocol only. A live team calls models; a replay
team returns recorded answers; tests use a scripted one.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from inbox_helper.models import Handoff, Intent, Message


class _Output(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Classification(_Output):
    """What the sender wants, and separately, every reason a person must handle it."""

    intent: Intent
    confidence: float
    reason: str
    handoff: list[Handoff]


class Critique(_Output):
    acceptable: bool
    problems: list[str]


class InputBlockedError(Exception):
    """The platform's content filter refused to pass this message to a model."""

    def __init__(self, categories: Sequence[str]) -> None:
        self.categories = tuple(categories)
        super().__init__(f"blocked by the content filter: {', '.join(self.categories)}")


class Team(Protocol):
    async def classify(self, message: Message) -> Classification: ...

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str: ...

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique: ...
