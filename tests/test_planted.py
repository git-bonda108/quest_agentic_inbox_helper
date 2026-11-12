"""The planted-draft harness, and the integrity of the hand-written evaluation data."""

from __future__ import annotations

import asyncio
from pathlib import Path

from inbox_helper.checks import draft_problems
from inbox_helper.cli import CASES, ROOT, SETS, shown
from inbox_helper.evaluate import load_labels, load_messages
from inbox_helper.models import Action, Intent, Message
from inbox_helper.planted import Case, load_cases, run_cases
from inbox_helper.team import Critique


def _all_messages() -> dict[str, Message]:
    return {m.id: m for data in SETS.values() for m in load_messages(data.inbox)}


def test_every_set_has_exactly_one_label_per_message() -> None:
    for name, data in SETS.items():
        messages = load_messages(data.inbox)
        assert sorted(m.id for m in messages) == sorted(load_labels(data.labels)), name


def test_every_injection_label_says_how_obedience_would_show() -> None:
    labels = load_labels(SETS["unseen"].labels).values()
    injections = [label for label in labels if label.category == "injection"]
    assert len(injections) >= 8
    for label in injections:
        assert label.forbidden or label.injected_intent, label.id
        assert all(phrase == phrase.lower() for phrase in label.forbidden), label.id


def test_planted_cases_can_only_be_caught_by_a_reviewer() -> None:
    cases, messages = load_cases(CASES), _all_messages()
    assert sum(not c.acceptable for c in cases) >= 10
    assert sum(c.acceptable for c in cases) >= 5
    for case in cases:
        assert case.message_id in messages, case.id
        assert draft_problems(case.draft) == [], case.id
        assert case.intent not in {Intent.ESCALATE, Intent.NOT_CANDIDATE}, case.id
        assert bool(case.flaw) is not case.acceptable, case.id


def test_harness_counts_catches_misses_and_false_rejections() -> None:
    message = next(iter(_all_messages().values()))
    cases = [
        Case(id="b1", message_id=message.id, intent=Intent.STATUS_CHECK, acceptable=False,
             flaw="caught", draft="reject me"),
        Case(id="b2", message_id=message.id, intent=Intent.STATUS_CHECK, acceptable=False,
             flaw="slips_through", draft="fine"),
        Case(id="g1", message_id=message.id, intent=Intent.STATUS_CHECK, acceptable=True,
             draft="fine"),
        Case(id="g2", message_id=message.id, intent=Intent.STATUS_CHECK, acceptable=True,
             draft="reject me"),
    ]  # fmt: skip

    async def reviewer(_message: Message, _intent: Intent, draft: str) -> Critique:
        bad = draft == "reject me"
        return Critique(acceptable=not bad, problems=["Planted."] if bad else [])

    report = asyncio.run(run_cases(reviewer, cases, {message.id: message}))
    assert (report.planted, report.caught) == (2, 1)
    assert (report.controls, report.controls_passed) == (2, 1)
    assert report.missed == [{"id": "b2", "flaw": "slips_through"}]
    assert report.false_rejections == [{"id": "g2", "problems": "Planted."}]
    assert report.catch_rate == 0.5


def test_unseen_set_covers_every_action() -> None:
    labels = load_labels(SETS["unseen"].labels).values()
    assert {label.action for label in labels} == set(Action)


def test_a_recording_outside_the_repository_can_still_be_named(tmp_path: Path) -> None:
    assert shown(ROOT / "data" / "recordings" / "golden.json") == "data/recordings/golden.json"
    assert shown(tmp_path / "tape.json") == str((tmp_path / "tape.json").resolve())
