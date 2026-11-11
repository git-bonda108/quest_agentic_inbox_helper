"""Record a team's answers once, then replay them with no model and no credentials.

Replayed output is recorded output. Every recording file says when it was made
and with which models, and the tool labels replayed runs as such.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from inbox_helper.models import Intent, Message
from inbox_helper.team import Classification, Critique, Team


class ReplayMissError(LookupError):
    """The recording has no answer for this call. Run against live models to record one."""


def _key(step: str, *parts: Any) -> str:
    canonical = json.dumps([step, *parts], sort_keys=True, ensure_ascii=False)
    return f"{step}:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:20]}"


class RecordedTeam:
    """Wraps a live team to record its answers, or replays a recording when given none."""

    def __init__(self, path: Path, live: Team | None = None, meta: dict[str, str] | None = None):
        self._path = path
        self._live = live
        self._calls: dict[str, Any] = {}
        self.meta: dict[str, str] = meta or {}
        if live is None:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._calls = data["calls"]
            self.meta = data["meta"]

    @property
    def replaying(self) -> bool:
        return self._live is None

    def save(self) -> None:
        if self._live is None:
            raise RuntimeError("a replay has nothing new to save")
        meta = {**self.meta, "recorded_at": datetime.now(UTC).isoformat(timespec="seconds")}
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps({"meta": meta, "calls": self._calls}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def _replay(self, key: str) -> Any:
        if key not in self._calls:
            raise ReplayMissError(f"no recorded answer for {key} in {self._path}")
        return self._calls[key]

    async def classify(self, message: Message) -> Classification:
        key = _key("classify", message.model_dump(mode="json"))
        if self._live is None:
            return Classification.model_validate(self._replay(key))
        result = await self._live.classify(message)
        self._calls[key] = result.model_dump(mode="json")
        return result

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str:
        key = _key("draft", message.model_dump(mode="json"), intent.value, list(feedback))
        if self._live is None:
            return str(self._replay(key))
        text = await self._live.draft(message, intent, feedback)
        self._calls[key] = text
        return text

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique:
        key = _key("critique", message.model_dump(mode="json"), intent.value, draft)
        if self._live is None:
            return Critique.model_validate(self._replay(key))
        result = await self._live.critique(message, intent, draft)
        self._calls[key] = result.model_dump(mode="json")
        return result
