"""The contract between the pipeline and the agents that do the language work.

The pipeline depends on this protocol only. A live team calls models; a replay
team returns recorded answers; tests use a scripted one.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from inbox_helper.models import Intent, Message


class _Output(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class Classification(_Output):
    intent: Intent
    confidence: float
    reason: str


class Critique(_Output):
    acceptable: bool
    problems: list[str]


class Team(Protocol):
    async def classify(self, message: Message) -> Classification: ...

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str: ...

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique: ...
