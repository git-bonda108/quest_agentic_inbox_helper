"""An independent judge for final drafts. It scores against evals/rubric.md.

The judge is evaluation, not product: the pipeline never calls it. It exists so
that the claim "no draft states an unsupported fact" does not rest on the
tool's own critic.
"""

from __future__ import annotations

from pathlib import Path
from typing import Protocol

from pydantic import BaseModel, ConfigDict

from inbox_helper.models import Intent, Message
from inbox_helper.recording import Cassette, call_key
from inbox_helper.team import Critique

CRITERIA = (
    "grounded",
    "policy_applied",
    "responsive",
    "no_commitments",
    "privacy",
    "not_manipulated",
    "tone",
)


class Finding(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    passed: bool
    evidence: str


class Verdict(BaseModel):
    """One finding per rubric criterion."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    grounded: Finding
    policy_applied: Finding
    responsive: Finding
    no_commitments: Finding
    privacy: Finding
    not_manipulated: Finding
    tone: Finding

    def failed(self) -> dict[str, str]:
        findings = {name: getattr(self, name) for name in CRITERIA}
        return {name: f.evidence for name, f in findings.items() if not f.passed}

    def as_critique(self) -> Critique:
        failed = self.failed()
        return Critique(
            acceptable=not failed,
            problems=[f"{name}: {evidence}" for name, evidence in failed.items()],
        )


class Judge(Protocol):
    async def judge(self, message: Message, draft: str) -> Verdict: ...


class RecordedJudge:
    """Wraps a live judge to record its verdicts, or replays a recording when given none."""

    def __init__(self, path: Path, live: Judge | None = None, meta: dict[str, str] | None = None):
        self._live = live
        self._tape = Cassette(path, recording=live is not None, meta=meta)

    def describe(self) -> str:
        return self._tape.describe()

    def save(self) -> None:
        self._tape.save()

    async def judge(self, message: Message, draft: str) -> Verdict:
        key = call_key("judge", message.model_dump(mode="json"), draft)
        if self._live is None:
            return Verdict.model_validate(self._tape.lookup(key))
        verdict = await self._live.judge(message, draft)
        self._tape.store(key, verdict.model_dump(mode="json"))
        return verdict

    async def review(self, message: Message, _intent: Intent, draft: str) -> Critique:
        """The judge as a planted-draft reviewer. It is never told the intent."""
        return (await self.judge(message, draft)).as_critique()
