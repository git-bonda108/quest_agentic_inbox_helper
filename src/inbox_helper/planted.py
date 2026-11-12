"""Planted drafts: prove that a reviewer of drafts rejects what it should.

Each case is a hand-written reply to a known message. Some carry one planted
flaw; the rest are controls a careful recruiter would send. Every case passes
the code checks, so only the reviewer under test can catch the flaw.
"""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import asdict, dataclass, field
from pathlib import Path

from pydantic import BaseModel, ConfigDict

from inbox_helper.models import Intent, Message
from inbox_helper.team import Critique

Reviewer = Callable[[Message, Intent, str], Awaitable[Critique]]


class Case(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str
    message_id: str
    intent: Intent
    acceptable: bool
    flaw: str = ""
    draft: str


def load_cases(path: Path) -> list[Case]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [Case.model_validate_json(line) for line in lines if line.strip()]


@dataclass
class PlantedReport:
    planted: int = 0
    caught: int = 0
    controls: int = 0
    controls_passed: int = 0
    missed: list[dict[str, str]] = field(default_factory=list)
    false_rejections: list[dict[str, str]] = field(default_factory=list)

    @property
    def catch_rate(self) -> float:
        return self.caught / self.planted if self.planted else 0.0

    def to_dict(self) -> dict[str, object]:
        return asdict(self) | {"catch_rate": round(self.catch_rate, 4)}


async def run_cases(
    reviewer: Reviewer,
    cases: list[Case],
    messages: Mapping[str, Message],
    *,
    concurrency: int = 4,
) -> PlantedReport:
    gate = asyncio.Semaphore(concurrency)

    async def one(case: Case) -> Critique:
        async with gate:
            return await reviewer(messages[case.message_id], case.intent, case.draft)

    verdicts = await asyncio.gather(*(one(case) for case in cases))
    report = PlantedReport()
    for case, verdict in zip(cases, verdicts, strict=True):
        if case.acceptable:
            report.controls += 1
            if verdict.acceptable:
                report.controls_passed += 1
            else:
                report.false_rejections.append(
                    {"id": case.id, "problems": " ".join(verdict.problems)}
                )
        else:
            report.planted += 1
            if verdict.acceptable:
                report.missed.append({"id": case.id, "flaw": case.flaw})
            else:
                report.caught += 1
    return report
