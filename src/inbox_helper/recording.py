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
from inbox_helper.team import Classification, Critique, InputBlockedError, Team


class ReplayMissError(LookupError):
    """The recording has no answer for this call. Run against live models to record one."""


def call_key(step: str, *parts: Any) -> str:
    canonical = json.dumps([step, *parts], sort_keys=True, ensure_ascii=False)
    return f"{step}:{hashlib.sha256(canonical.encode('utf-8')).hexdigest()[:20]}"


_BLOCKED = "blocked_by_content_filter"


class Cassette:
    """Answers on disk, keyed by a hash of the call that produced them."""

    def __init__(self, path: Path, *, recording: bool, meta: dict[str, str] | None = None):
        self.path = path
        self.recording = recording
        self.meta: dict[str, str] = meta or {}
        self._calls: dict[str, Any] = {}
        if not recording:
            data = json.loads(path.read_text(encoding="utf-8"))
            self._calls = data["calls"]
            self.meta = data["meta"]

    def lookup(self, key: str) -> Any:
        if key not in self._calls:
            raise ReplayMissError(f"no recorded answer for {key} in {self.path}")
        answer = self._calls[key]
        if isinstance(answer, dict) and _BLOCKED in answer:
            raise InputBlockedError(answer[_BLOCKED])
        return answer

    def store(self, key: str, value: Any) -> None:
        self._calls[key] = value

    def store_block(self, key: str, blocked: InputBlockedError) -> None:
        """A refusal by the platform is recorded, so a replay refuses the same message."""
        self._calls[key] = {_BLOCKED: list(blocked.categories)}

    def save(self) -> None:
        if not self.recording:
            raise RuntimeError("a replay has nothing new to save")
        meta = {**self.meta, "recorded_at": datetime.now(UTC).isoformat(timespec="seconds")}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(
            json.dumps({"meta": meta, "calls": self._calls}, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )

    def describe(self) -> str:
        """One line that says these are recorded answers, from when and from which models."""
        models = ", ".join(f"{k} {v}" for k, v in sorted(self.meta.items()) if k != "recorded_at")
        return f"RECORDED model outputs from {self.meta.get('recorded_at', '?')} ({models})"


class RecordedTeam:
    """Wraps a live team to record its answers, or replays a recording when given none."""

    def __init__(self, path: Path, live: Team | None = None, meta: dict[str, str] | None = None):
        self._live = live
        self._tape = Cassette(path, recording=live is not None, meta=meta)

    @property
    def meta(self) -> dict[str, str]:
        return self._tape.meta

    def describe(self) -> str:
        return self._tape.describe()

    def save(self) -> None:
        self._tape.save()

    async def classify(self, message: Message) -> Classification:
        key = call_key("classify", message.model_dump(mode="json"))
        if self._live is None:
            # Recordings made before hand-off reasons existed replay as having none.
            return Classification.model_validate({"handoff": [], **self._tape.lookup(key)})
        try:
            result = await self._live.classify(message)
        except InputBlockedError as blocked:
            self._tape.store_block(key, blocked)
            raise
        self._tape.store(key, result.model_dump(mode="json"))
        return result

    async def draft(self, message: Message, intent: Intent, feedback: Sequence[str]) -> str:
        key = call_key("draft", message.model_dump(mode="json"), intent.value, list(feedback))
        if self._live is None:
            return str(self._tape.lookup(key))
        try:
            text = await self._live.draft(message, intent, feedback)
        except InputBlockedError as blocked:
            self._tape.store_block(key, blocked)
            raise
        self._tape.store(key, text)
        return text

    async def critique(self, message: Message, intent: Intent, draft: str) -> Critique:
        key = call_key("critique", message.model_dump(mode="json"), intent.value, draft)
        if self._live is None:
            return Critique.model_validate(self._tape.lookup(key))
        try:
            result = await self._live.critique(message, intent, draft)
        except InputBlockedError as blocked:
            self._tape.store_block(key, blocked)
            raise
        self._tape.store(key, result.model_dump(mode="json"))
        return result
