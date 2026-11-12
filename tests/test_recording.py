"""Recording and replay, including a message the platform refused."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from inbox_helper.models import Action, Intent, Message
from inbox_helper.pipeline import process_inbox
from inbox_helper.recording import RecordedTeam, ReplayMissError
from inbox_helper.store import Store
from scripted import GOOD, ScriptedTeam, message


def _process(team: RecordedTeam, *messages: Message) -> Store:
    store = Store(":memory:")
    asyncio.run(process_inbox(store, team, list(messages)))
    return store


def test_a_replay_gives_the_same_draft_without_the_live_team(tmp_path: Path) -> None:
    tape = tmp_path / "tape.json"
    recorder = RecordedTeam(tape, live=ScriptedTeam(), meta={"worker": "scripted"})
    _process(recorder, message("m1"))
    recorder.save()

    replay = RecordedTeam(tape)
    draft = _process(replay, message("m1")).draft("m1")
    assert draft is not None
    assert draft.text == GOOD
    assert "RECORDED" in replay.describe()
    assert "scripted" in replay.describe()


def test_a_blocked_message_replays_as_blocked(tmp_path: Path) -> None:
    tape = tmp_path / "tape.json"
    recorder = RecordedTeam(tape, live=ScriptedTeam(block_at="classify"))
    _process(recorder, message("m1"))
    recorder.save()

    triage = _process(RecordedTeam(tape), message("m1")).triage("m1")
    assert triage is not None
    assert triage.action is Action.ESCALATE
    assert triage.intent is Intent.ESCALATE
    assert "jailbreak" in triage.reason


def test_a_replay_refuses_a_message_it_never_recorded(tmp_path: Path) -> None:
    tape = tmp_path / "tape.json"
    recorder = RecordedTeam(tape, live=ScriptedTeam())
    _process(recorder, message("m1"))
    recorder.save()

    with pytest.raises(ReplayMissError):
        asyncio.run(RecordedTeam(tape).classify(message("m2")))
